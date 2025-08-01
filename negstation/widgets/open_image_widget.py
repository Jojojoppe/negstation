import dearpygui.dearpygui as dpg
from PIL import Image
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class OpenImageWidget(PipelineStageWidget):
    name = "Open Image"
    register = True
    has_pipeline_in = False
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="opened_image")
        self.dialog_tag = dpg.generate_uuid()
        self.output_tag = dpg.generate_uuid()

    def create_pipeline_stage_content(self):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_file_selected,
            tag=self.dialog_tag,
            height=300,
            width=400,
        ):
            dpg.add_file_extension(".*")
        dpg.add_button(label="Open File...", callback=self._on_open_file)

    def _on_open_file(self):
        dpg.configure_item(self.dialog_tag, show=True)

    def _on_file_selected(self, sender, app_data):
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
            self.manager.pipeline.publish(self.pipeline_stage_out_id, arr)
        except Exception as e:
            self.logger.error(f"Failed to load image {selection}: {e}")
