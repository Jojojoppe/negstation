# in widgets/camera_widget.py
import dearpygui.dearpygui as dpg
import gphoto2 as gp
import logging
import threading
import queue

from .base_widget import BaseWidget

# Set up a logger specific to this widget for clear debugging
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

class CamControlWidget(BaseWidget):
    def __init__(self, widget_type: str, config: dict, layout_manager, app_state):
        super().__init__(widget_type, config, layout_manager, app_state)
        layout_manager.updating_widgets.append("CamControlWidget")

        # A dictionary to map user-friendly camera names to technical port strings
        self.camera_map = {}
        
        # Queues for communicating with the worker thread
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # Start the background worker thread. It's a daemon so it exits with the app.
        self.worker_thread = threading.Thread(target=self._camera_worker, daemon=True)
        self.worker_thread.start()

    def create(self):
        if dpg.does_item_exist(self.window_tag): return

        with dpg.window(label="Camera Control", tag=self.window_tag, on_close=self._on_window_close, width=320, height=160):
            
            # This group contains all controls visible when disconnected
            with dpg.group(tag=f"connection_group_{self.widget_type}") as self.connection_group_tag:
                dpg.add_button(label="Detect Cameras", callback=lambda: self.command_queue.put(('DETECT', None)), width=-1)
                with dpg.group(horizontal=True):
                    self.camera_combo_tag = dpg.add_combo(label="Camera", items=[], width=-115)
                    
                    def connect_callback():
                        selected_name = dpg.get_value(self.camera_combo_tag)
                        if selected_name and selected_name in self.camera_map:
                            port = self.camera_map[selected_name]
                            self.command_queue.put(('CONNECT', port))
                        else:
                            logger.warning("No camera selected to connect to.")
                    
                    self.connect_button = dpg.add_button(label="Connect", callback=connect_callback)
            
            # This button is only visible when connected
            self.disconnect_button_tag = dpg.add_button(
                label="Disconnect", 
                callback=lambda: self.command_queue.put(('DISCONNECT', None)), 
                show=False,
                width=-1
            )
            
            self.status_text_tag = dpg.add_text("Status: Disconnected")

    def update(self):
        try:
            # Check for a result from the worker thread without blocking
            result_type, data = self.result_queue.get_nowait()

            if result_type == 'STATUS':
                dpg.set_value(self.status_text_tag, f"Status: {data}")

            elif result_type == 'CAMERAS_DETECTED':
                # data is a list of (name, port) tuples
                self.camera_map = {name: port for name, port in data}
                camera_names = list(self.camera_map.keys())
                dpg.configure_item(self.camera_combo_tag, items=camera_names)
                if camera_names:
                    dpg.set_value(self.camera_combo_tag, camera_names[0])

            elif result_type == 'CONNECTED' and data is True:
                # Hide connection controls and show the disconnect button
                dpg.configure_item(self.connection_group_tag, show=False)
                dpg.configure_item(self.disconnect_button_tag, show=True)

            elif result_type == 'DISCONNECTED' and data is True:
                # Hide disconnect button and show connection controls
                dpg.configure_item(self.connection_group_tag, show=True)
                dpg.configure_item(self.disconnect_button_tag, show=False)

        except queue.Empty:
            # This is expected when there are no new results from the worker
            pass

    def _camera_worker(self):
        camera = None
        logger.info("Camera worker thread started.")

        while True:
            try:
                command, args = self.command_queue.get()
                logger.info(f"Camera worker received command: {command}")

                if command == 'DETECT':
                    try:
                        # Autodetect returns a list of (name, port) tuples
                        camera_list = list(gp.Camera.autodetect())
                        logger.debug(f"Cameras found: {str(camera_list)}")
                        if not camera_list:
                            self.result_queue.put(('STATUS', 'No cameras found.'))
                            self.result_queue.put(('CAMERAS_DETECTED', []))
                            continue
                        
                        self.result_queue.put(('CAMERAS_DETECTED', camera_list))
                        self.result_queue.put(('STATUS', f'Detected {len(camera_list)} camera(s).'))
                    except Exception as e:
                        logger.error(f"Error during camera detection: {e}")
                        self.result_queue.put(('STATUS', 'Error during detection.'))

                elif command == 'CONNECT':
                    if camera is not None:
                        self.result_queue.put(('STATUS', 'A camera is already connected.'))
                        continue
                    
                    port = args
                    if not port:
                        self.result_queue.put(('STATUS', 'No camera port selected.'))
                        continue
                        
                    try:
                        camera = gp.Camera()
                        port_info_list = gp.PortInfoList(); port_info_list.load()
                        port_index = port_info_list.lookup_path(port)
                        camera.set_port_info(port_info_list[port_index])
                        
                        camera.init()
                        self.result_queue.put(('STATUS', f"Connected successfully!"))
                        self.result_queue.put(('CONNECTED', True))
                    except gp.GPhoto2Error as ex:
                        camera = None # Ensure camera is None on failure
                        logger.error(f"GPhoto2 Error on connect: {ex}")
                        self.result_queue.put(('STATUS', f"Error: {ex}"))
                        self.result_queue.put(('CONNECTED', False))

                elif command == 'DISCONNECT':
                    if camera:
                        try:
                            camera.exit()
                            camera = None # Critical to update state
                            self.result_queue.put(('STATUS', 'Disconnected.'))
                            self.result_queue.put(('DISCONNECTED', True))
                        except gp.GPhoto2Error as ex:
                            logger.error(f"Error on disconnect: {ex}")
                            self.result_queue.put(('STATUS', f"Error on disconnect: {ex}"))
                    else:
                        self.result_queue.put(('STATUS', 'Already disconnected.'))

            except Exception as e:
                # Broad exception to catch any other errors in the worker loop
                logger.error(f"An unexpected exception occurred in the camera worker: {e}")
                self.result_queue.put(('STATUS', f'Worker Error: {e}'))