import dearpygui.dearpygui as dpg
import numpy as np

from .base_widget import BaseWidget


class StageViewerWidget(BaseWidget):
    name: str = "Image Stage Viewer"

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        # Ensure shared texture registry
        if not hasattr(manager, "texture_registry"):
            manager.texture_registry = dpg.add_texture_registry(
                tag=dpg.generate_uuid())
        self.registry = manager.texture_registry

        self.stages = []
        self.current = None
        self.texture_tag = dpg.generate_uuid()
        self.img = None

        # Subscribe only to stage list updates
        self.manager.bus.subscribe(
            "pipeline_stages", self.on_stage_list, main_thread=True)
        self.manager.bus.subscribe(
            "pipeline_stage", self.on_stage, main_thread=True)

    def create(self):
        with dpg.window(label="Stage Viewer", tag=self.window_tag, width=400, height=400):
            # Dropdown for selecting a stage
            self.combo = dpg.add_combo(
                label="Stage", items=[], callback=self.on_select)
            # Placeholder 1×1 texture in registry
            dpg.add_dynamic_texture(
                1, 1, [0, 0, 0, 0], tag=self.texture_tag, parent=self.registry)
            # Image widget that will display the texture
            self.image_item = dpg.add_image(self.texture_tag)

            with dpg.item_handler_registry() as handler:
                dpg.add_item_resize_handler(
                    callback=self.on_resize)
                dpg.bind_item_handler_registry(self.window_tag, handler)

    def on_resize(self, app_data):
        if self.img is not None:
            self.update_texture(self.img)

    def on_stage_list(self, stages):
        # Update dropdown items
        self.stages = stages
        dpg.configure_item(self.combo, items=stages)

    def on_stage(self, stage):
        name, img = stage
        if name == self.current:
            if img is not None:
                self.img = img
                self.update_texture(img)

    def on_select(self, sender, selected_stage):
        # User-picked stage: fetch and render
        self.current = selected_stage
        img = self.manager.pipeline.get_stage(selected_stage)
        if img is not None:
            self.img = img
            self.update_texture(img)

    def update_texture(self, img: np.ndarray):
        # img is a NumPy array with shape (h, w, 4)
        h, w, _ = img.shape
        flat = img.flatten().tolist()

        # 1) Recreate the dynamic texture at the correct size
        if dpg.does_item_exist(self.texture_tag):
            dpg.delete_item(self.texture_tag)
        dpg.add_dynamic_texture(
            width=w, height=h,
            default_value=flat,
            tag=self.texture_tag,
            parent=self.registry
        )

        # 2) Compute available space: full window width, from just below combo to bottom
        win_w, win_h = dpg.get_item_rect_size(self.window_tag)
        combo_w, combo_h = dpg.get_item_rect_size(self.combo)
        combo_x, combo_y = dpg.get_item_pos(self.combo)
        avail_w = win_w - 15
        avail_h = win_h - combo_h - combo_y - 15

        # 3) Compute scale to fit the available rectangle
        scale = min(avail_w / w, avail_h / h, 1.0)
        disp_w = int(w * scale)
        disp_h = int(h * scale)

        # 4) Center horizontally, start exactly below the combo
        x_off = (avail_w - disp_w) / 2 + 7
        y_off = combo_h + combo_y + 7  # flush immediately below the dropdown

        # 5) Apply to the image widget
        dpg.configure_item(
            self.image_item,
            texture_tag=self.texture_tag,
            pos=(x_off, y_off),
            width=disp_w,
            height=disp_h
        )
