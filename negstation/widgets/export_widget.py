# import dearpygui.dearpygui as dpg
# import numpy as np

# from .pipeline_stage_widget import PipelineStageWidget


# class ExportStage(PipelineStageWidget):
#     name = "Export Image"
#     register = True
#     has_pipeline_in = True
#     has_pipeline_out = False

#     def __init__(self, manager, logger):
#         super().__init__(manager, logger, default_stage_out="opened_image")
#         self.manager.bus.subscribe(
#             "process_full_res", self._on_process_full_res, True)

#     def create_pipeline_stage_content(self):
#         dpg.add_text("Some export fields")

#     def _on_process_full_res(self, data):
#         self.logger.info("Starting full res pipeline export")

#     def on_pipeline_data(self, img):
#         if img is None:
#             return
#         self.logger.info("low res image received, ignore")

#     def on_full_res_pipeline_data(self, img):
#         if img is None:
#             return
#         h, w, _ = img.shape
#         self.logger.info(f"Full res image received: {w}x{h}")


import os
import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image

from .pipeline_stage_widget import PipelineStageWidget


class ExportStage(PipelineStageWidget):
    name = "Export Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = False

    def __init__(self, manager, logger):
        # we don’t register an output stage — this widget only consumes
        super().__init__(manager, logger, default_stage_out="unused")
        # tags for our “Save As” dialog
        self._save_dialog_tag = dpg.generate_uuid()
        self._save_path = None

    def create_pipeline_stage_content(self):
        # Button to pop up the file-save dialog
        dpg.add_button(label="Save As…",
                       callback=lambda s,a,u: dpg.configure_item(self._save_dialog_tag, show=True))

        # File dialog for choosing export path & extension
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_save_selected,
            tag=self._save_dialog_tag,
            width=400,
            height=300
        ):
            dpg.add_file_extension("PNG {.png}")
            dpg.add_file_extension("JPEG {.jpg,.jpeg}")
            dpg.add_file_extension("TIFF {.tif,.tiff}")
            dpg.add_file_extension("All files {.*}")

        with dpg.child_window(autosize_x=True, autosize_y=True, horizontal_scrollbar=True):
            self.path_label = dpg.add_text("...")

    def _on_save_selected(self, sender, app_data):
        """
        Called when the user picks a filename in the Save As… dialog.
        Stores the path for the next full-res pass.
        """
        # app_data is a dict with 'current_path' and 'selections'
        path = os.path.join(
            app_data["current_path"],
            app_data["file_name"]
        )
        self._save_path = path
        self.logger.info(f"Export path set to: {path}")
        dpg.set_value(self.path_label, path)

    def on_pipeline_data(self, img: np.ndarray):
        # ignore all previews
        return

    def on_full_res_pipeline_data(self, img: np.ndarray):
        """
        Receives the full-resolution NumPy image when the user fires
        the “Run full-res pipeline” action. Saves via Pillow.
        """
        if img is None:
            self.logger.error("on_full_res_pipeline_data called with None image")
            return
        if not self._save_path:
            self.logger.warning("No export path set — click Save As… first")
            return

        # Decide bit depth by extension
        ext = os.path.splitext(self._save_path)[-1].lower()
        # Convert floats → uint; or leave ints alone
        if np.issubdtype(img.dtype, np.floating):
            if ext in (".tif", ".tiff"):
                arr = np.clip(img * 65535.0, 0, 65535).astype(np.uint16)
            else:
                arr = np.clip(img * 255.0, 0, 255).astype(np.uint8)
        else:
            arr = img

        # Determine PIL mode
        mode = None
        if arr.ndim == 2:
            mode = "L"
        elif arr.ndim == 3:
            c = arr.shape[2]
            if c == 3:
                mode = "RGB"
            elif c == 4:
                mode = "RGBA"

        try:
            im = Image.fromarray(arr, mode) if mode else Image.fromarray(arr)

            # JPEG doesn’t support alpha — drop it
            if ext in (".jpg", ".jpeg") and im.mode == "RGBA":
                im = im.convert("RGB")

            im.save(self._save_path)
        except Exception as e:
            self.logger.error(f"Failed to save image to {self._save_path}: {e}")
        else:
            self.logger.info(f"Saved full-resolution image to {self._save_path}")
