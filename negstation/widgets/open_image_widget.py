import dearpygui.dearpygui as dpg
from PIL import Image
import numpy as np

from .base_widget import BaseWidget


class OpenImageWidget(BaseWidget):
    name: str = "Open Image"

    def __init__(self, manager, logger, stage_out="loaded_image"):
        super().__init__(manager, logger)
        self.stage_out = stage_out
        self.dialog_tag = dpg.generate_uuid()
        self.output_tag = dpg.generate_uuid()

    def create(self):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_file_selected,
            tag=self.dialog_tag,
            height=300,
            width=400,
        ):
            dpg.add_file_extension(".*")

        with dpg.window(
            label="Open Image File",
            tag=self.window_tag,
            width=300,
            height=150,
            on_close=self._on_window_close,
        ):
            dpg.add_input_text(label="Stage Output Name", tag=self.output_tag)
            dpg.add_button(label="Open File...", callback=self._on_open_file)

        dpg.set_value(self.output_tag, self.stage_out)

    def _on_open_file(self):
        dpg.configure_item(self.dialog_tag, show=True)

    def _on_file_selected(self, sender, app_data):
        # app_data[0] is dict with selected file paths
        selection = (
            f"{app_data['current_path']}/{list(app_data['selections'].keys())[0]}"
            if isinstance(app_data, dict)
            else None
        )
        if not selection:
            return
        self.logger.info(f"Selected file '{selection}'")
        try:
            img = Image.open(selection).convert("RGBA")
            arr = np.asarray(img).astype(np.float32) / 255.0  # normalize to [0,1]
            # Publish into pipeline
            self.manager.pipeline.add_stage(dpg.get_value(self.output_tag), arr)
        except Exception as e:
            self.logger.error(f"Failed to load image {selection}: {e}")
