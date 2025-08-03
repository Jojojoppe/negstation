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
        self.img = None
        self.img_full = None

        self.manager.bus.subscribe(
            "process_full_res", self._on_process_full_res, True)

    def create_pipeline_stage_content(self):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_file_selected,
            tag=self.dialog_tag,
            height=300,
            width=400,
        ):
            dpg.add_file_extension(
                "Image files {.png,.jpg,.jpeg,.bmp .gif,.tif,.tiff}",
            )
            dpg.add_file_extension(".*")
        dpg.add_button(label="Open File...", callback=self._on_open_file)

    def _on_open_file(self):
        dpg.configure_item(self.dialog_tag, show=True)

    def _on_file_selected(self, sender, app_data):
        selection = (
            f"{app_data['current_path']
               }/{list(app_data['selections'].keys())[0]}"
            if isinstance(app_data, dict)
            else None
        )
        if not selection:
            return
        self.logger.info(f"Selected file '{selection}'")
        try:
            img = Image.open(selection).convert("RGBA")
            rgba = np.asarray(img).astype(np.float32) / \
                255.0  # normalize to [0,1]
            h, w, _ = rgba.shape

            # scale for small version
            max_dim = 500
            scale = min(1.0, max_dim / w, max_dim / h)
            if scale < 1.0:
                # convert to 0–255 uint8, resize with PIL, back to float32 [0–1]
                pil = Image.fromarray(
                    (rgba * 255).astype(np.uint8), mode="RGBA")
                new_w, new_h = int(w * scale), int(h * scale)
                pil = pil.resize((new_w, new_h), Image.LANCZOS)
                rgba_small = np.asarray(pil).astype(np.float32) / 255.0
                w_small, h_small = new_w, new_h

            self.img_full = rgba
            self.img = rgba_small

            self.manager.pipeline.publish(
                self.pipeline_stage_out_id, rgba_small)
        except Exception as e:
            self.logger.error(f"Failed to load image {selection}: {e}")

    def _on_process_full_res(self, data):
        self.manager.pipeline.publish(
            self.pipeline_stage_out_id, self.img_full, True)
