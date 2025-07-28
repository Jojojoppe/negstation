import rawpy
import numpy as np
import queue
import threading
import logging
import dearpygui.dearpygui as dpg

class RawProcessor:
    """
    A background service that listens for new RAW files, processes them,
    and dispatches the resulting RGB data.
    """
    def __init__(self, global_state):
        self.global_state = global_state
        self.work_queue = queue.Queue()
        
        # Subscribe to the event from the camera widget
        self.global_state.subscribe("NEW_IMAGE_CAPTURED", self.add_to_queue)
        
        # Start the processor's own background thread
        self.worker_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.worker_thread.start()
        logging.info("RAW Processor thread started.")

    def add_to_queue(self, image_path: str):
        """Adds a new RAW file path to the processing queue."""
        if image_path.lower().endswith(('.cr2')):
            logging.info(f"RAW Processor: Queued {image_path} for processing.")
            self.work_queue.put(image_path)
        else:
            # Not a supported raw file, hope for the best the viewer supports it
            try:
                width, height, channels, data = dpg.load_image(image_path)
                rgba_float32 = np.array(data, dtype=np.float32)
                rgba_float32 = rgba_float32.reshape(height, width, 4)
                self.global_state.raw_image_data = rgba_float32.copy()
                self.global_state.dispatch("PROCESSED_IMAGE_READY", image_data=rgba_float32.copy())

            except Exception as e:
                logging.error(f"Failed to load standard image {image_path}: {e}", exc_info=True)

    def _process_worker(self):
        """The background thread that performs RAW processing and data conversion."""
        while True:
            raw_path = self.work_queue.get()
            try:
                logging.info(f"Processing {raw_path}...")
                with rawpy.imread(raw_path) as raw:
                    rgb_uint8_potentially_corrupt = raw.postprocess(**self.global_state.raw_params)
                rgb_uint8 = rgb_uint8_potentially_corrupt.copy()
                logging.info("Defensive copy complete. Starting conversion...")
                rgb_float32 = (rgb_uint8 / pow(2,self.global_state.raw_params['output_bps'])).astype(np.float32)
                alpha_channel = np.ones((rgb_float32.shape[0], rgb_float32.shape[1], 1), dtype=np.float32)
                rgba_float32_data = np.concatenate((rgb_float32, alpha_channel), axis=2)
                logging.info(f"Processing and conversion complete for {raw_path}.")
                self.global_state.raw_image_data = rgba_float32_data.copy()
                self.global_state.dispatch("PROCESSED_IMAGE_READY", image_data=rgba_float32_data.copy())
            
            except Exception as e:
                logging.error(f"Failed to process RAW file {raw_path}: {e}", exc_info=True)
