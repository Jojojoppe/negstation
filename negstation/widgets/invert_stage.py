import dearpygui.dearpygui as dpg
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class InvertStage(PipelineStageWidget):
    name = "Invert Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="inverted_image")
    
    def create_pipeline_stage_content(self):
        pass

    def on_pipeline_data(self, img):
        if img is None:
            return
        inverted = img.copy()
        inverted[...,:3] = 1.0 - inverted[...,:3]
        self.publish_stage(inverted)
