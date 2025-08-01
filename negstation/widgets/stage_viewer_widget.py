import dearpygui.dearpygui as dpg
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class PipelineStageViewer(PipelineStageWidget):
    name = "View Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = False

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_in="pipeline_out")
        self.texture_tag = dpg.generate_uuid()
        self.img = None
        self.needs_update = False
        self.registry = manager.texture_registry

    def create_pipeline_stage_content(self):
        dpg.add_dynamic_texture(
            1, 1, [0, 0, 0, 0], tag=self.texture_tag, parent=self.registry
        )
        self.image_item = dpg.add_image(self.texture_tag)

    def on_resize(self, width, height):
        self.needs_update = True

    def on_pipeline_data(self, img):
        self.img = img
        self.needs_update = True

    def update_texture(self, img: np.ndarray):
        """Only call from update function"""
        if img is None:
            dpg.configure_item(self.image_item, show=False)
            return

        h, w, _ = img.shape
        flat = img.flatten().tolist()

        if dpg.does_item_exist(self.texture_tag):
            dpg.delete_item(self.texture_tag)
        dpg.add_dynamic_texture(
            width=w,
            height=h,
            default_value=flat,
            tag=self.texture_tag,
            parent=self.registry,
        )

        win_w, win_h = self.window_width, self.window_height
        avail_w = win_w
        avail_h = win_h

        scale = min(avail_w / w, avail_h / h, 1.0)
        disp_w = int(w * scale)
        disp_h = int(h * scale)

        x_off = (avail_w - disp_w) / 2
        y_off = self.window_offset_y

        dpg.configure_item(
            self.image_item,
            texture_tag=self.texture_tag,
            pos=(x_off, y_off),
            width=disp_w,
            height=disp_h,
            show=True
        )

    def update(self):
        if self.needs_update:
            self.needs_update = False
            self.update_texture(self.img)
