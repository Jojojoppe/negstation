import dearpygui.dearpygui as dpg
import numpy as np
from .base_widget import BaseWidget


class PipelineStageWidget(BaseWidget):
    register = False

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        self.stage_in = ""
        self.stage_out = ""
        self.img = None

        self.manager.bus.subscribe(
            "pipeline_stage", self._on_pipeline, main_thread=True
        )
        self.manager.bus.subscribe(
            "pipeline_stages", self._on_stage_list, main_thread=True
        )

    def create(self):
        with dpg.window(label=self.name, tag=self.window_tag, width=400, height=300):
            # top‐row: input / output
            dpg.add_text("Configuration:")
            self.combo = dpg.add_combo(
                label="Stage In", items=[], callback=self._on_select
            )
            dpg.add_input_text(
                label="Stage Out",
                default_value=self.stage_out,
                callback=lambda s, a, u: setattr(self, "stage_out", a),
            )
            dpg.add_separator()
            # now let subclasses populate the rest
            self.create_content()

    def _on_select(self, sender, selected_stage):
        self.stage_in = selected_stage
        self.img = self.manager.pipeline.get_stage(selected_stage)
        self.on_stage(self.img)

    def update(self):
        pass

    def create_content(self):
        raise NotImplementedError

    def _on_pipeline(self, data):
        name, img = data
        if name == self.stage_in:
            self.img = img
            self.on_stage(img)

    def _on_stage_list(self, stages):
        self.stages = stages
        dpg.configure_item(self.combo, items=stages)

    def on_stage(self, img: np.ndarray):
        pass

    def publish(self, img: np.ndarray):
        self.manager.pipeline.add_stage(self.stage_out, img)
