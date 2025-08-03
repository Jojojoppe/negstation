import dearpygui.dearpygui as dpg
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class ExportStage(PipelineStageWidget):
    name = "Export Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = False

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="opened_image")
        self.manager.bus.subscribe(
            "process_full_res", self._on_process_full_res, True)

    def create_pipeline_stage_content(self):
        dpg.add_text("Some export fields")

    def _on_process_full_res(self, data):
        self.logger.info("Starting full res pipeline export")

    def on_pipeline_data(self, img):
        if img is None:
            return
        self.logger.info("low res image received, ignore")

    def on_full_res_pipeline_data(self, img):
        if img is None:
            return
        h, w, _ = img.shape
        self.logger.info(f"Full res image received: {w}x{h}")
