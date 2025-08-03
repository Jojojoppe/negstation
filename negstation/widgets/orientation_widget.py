import dearpygui.dearpygui as dpg
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class OrientationStage(PipelineStageWidget):
    name = "Orient Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="oriented_image")

        self.rotation = 0
        self.mirror_h = False
        self.mirror_v = False

        self.rotation_combo_tag = dpg.generate_uuid()
        self.mirror_h_tag = dpg.generate_uuid()
        self.mirror_v_tag = dpg.generate_uuid()

        self.last_image = None
    
    def create_pipeline_stage_content(self):
        dpg.add_combo(
            label="Rotation",
            items=["0°", "90°", "180°", "270°"],
            default_value="0°",
            callback=self._on_rotation_change,
            tag=self.rotation_combo_tag
        )

        dpg.add_checkbox(
            label="Mirror Horizontal",
            default_value=False,
            callback=self._on_mirror_h_change,
            tag=self.mirror_h_tag
        )

        dpg.add_checkbox(
            label="Mirror Vertical",
            default_value=False,
            callback=self._on_mirror_v_change,
            tag=self.mirror_v_tag
        ) 

    def _on_rotation_change(self, sender, value, user_data):
        degree_map = {
            "0°": 0,
            "90°": 90,
            "180°": 180,
            "270°": 270
        }
        self.rotation = degree_map.get(value, 0)
        self.on_pipeline_data(self.last_img)

    def _on_mirror_h_change(self, sender, value, user_data):
        self.mirror_h = value
        self.on_pipeline_data(self.last_img)

    def _on_mirror_v_change(self, sender, value, user_data):
        self.mirror_v = value
        self.on_pipeline_data(self.last_img)

    def on_pipeline_data(self, img):
        if img is None:
            return

        self.last_img = img
        img_out = img.copy()

        # Apply rotation
        if self.rotation == 90:
            img_out = np.rot90(img_out, k=3)
        elif self.rotation == 180:
            img_out = np.rot90(img_out, k=2)
        elif self.rotation == 270:
            img_out = np.rot90(img_out, k=1)

        # Apply mirroring
        if self.mirror_h:
            img_out = np.fliplr(img_out)
        if self.mirror_v:
            img_out = np.flipud(img_out)

        self.publish_stage(img_out)

    def get_config(self):
        config = super().get_config()
        config["orientation"] = {
            "rotation": self.rotation,
            "mirror_h": str(self.mirror_h),
            "mirror_v": str(self.mirror_v),
        }
        return config

    def set_config(self, config):
        super().set_config(config)
        orient_cfg = config.get("orientation", {})

        self.rotation = int(orient_cfg.get("rotation", 0))
        self.mirror_h = orient_cfg.get("mirror_h", "False") == "True"
        self.mirror_v = orient_cfg.get("mirror_v", "False") == "True"

        self._update_ui()

    def _update_ui(self):
        # Update rotation combo
        reverse_map = {
            0: "0°",
            90: "90°",
            180: "180°",
            270: "270°"
        }
        dpg.set_value(self.rotation_combo_tag, reverse_map.get(self.rotation, "0°"))

        # Update checkboxes
        dpg.set_value(self.mirror_h_tag, self.mirror_h)
        dpg.set_value(self.mirror_v_tag, self.mirror_v)