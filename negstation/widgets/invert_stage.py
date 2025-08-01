import dearpygui.dearpygui as dpg
import numpy as np
from .pipeline_stage_widget import PipelineStageWidget


class InvertStage(PipelineStageWidget):
    name = "Invert Image"
    register = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        self.stage_out = "inverted_image"

    def create_content(self):
        dpg.add_button(label="Invert", callback=lambda s, a, u: self._do_invert())

    def on_stage(self, img):
        self._do_invert()

    def _do_invert(self):
        if self.img is None:
            return
        inverted = self.img.copy()
        inverted[...,:3] = 1.0 - inverted[...,:3]
        self.publish(inverted)
