import dearpygui.dearpygui as dpg
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class MonochromeStage(PipelineStageWidget):
    name = "Monochrome"
    register = True
    has_pipeline_in = True
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="monochrome")

    def create_pipeline_stage_content(self):
        pass

    def on_pipeline_data(self, img):
        if img is None:
            return
        gray = img.copy()
        rgb = gray[..., :3]
        alpha = gray[..., 3:] if gray.shape[2] == 4 else np.ones_like(
            rgb[..., :1])

        luminance = np.dot(rgb, [0.2126, 0.7152, 0.0722])[..., np.newaxis]
        gray_rgba = np.concatenate(
            [luminance, luminance, luminance, alpha], axis=-1)

        self.publish_stage(gray_rgba.astype(np.float32))
