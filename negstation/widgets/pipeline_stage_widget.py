import dearpygui.dearpygui as dpg
import numpy as np
from .base_widget import BaseWidget


class PipelineStageWidget(BaseWidget):
    name = "Pipeline Stage Widget"
    register = False
    has_pipeline_in: bool = False
    has_pipeline_out: bool = False

    def __init__(
        self,
        manager,
        logger,
        default_stage_in: str = "pipeline_in",
        default_stage_out: str = "pipeline_out",
        window_width: int = 300,
        window_height: int = 200,
    ):
        super().__init__(manager, logger, window_width, window_height)
        self.pipeline_stage_in_id = None
        self.pipeline_stage_out_id = None
        self.pipeline_config_group_tag = dpg.generate_uuid()

        if self.has_pipeline_out:
            self.pipeline_stage_out_id = self.manager.pipeline.register_stage(
                default_stage_out
            )

        self.manager.bus.subscribe("pipeline_stages", self._on_stage_list, True)
        if self.has_pipeline_in:
            self.pipeline_stage_in_id = 0
            self.manager.bus.subscribe("pipeline_stage", self._on_stage_data, True)
        # force getting all available pipeline stages
        self.manager.pipeline.republish_stages()

    def create_content(self):
        with dpg.group(tag=self.pipeline_config_group_tag):
            if self.has_pipeline_in:
                self.stage_in_combo = dpg.add_combo(
                    label="Stage In",
                    items=[],
                    callback=self._on_stage_in_select,
                    default_value=f"{self.manager.pipeline.get_stage_name(0)} : 0",
                )
            if self.has_pipeline_out:
                dpg.add_input_text(
                    label="Stage Out",
                    default_value=self.manager.pipeline.get_stage_name(
                        self.pipeline_stage_out_id
                    ),
                    callback=lambda s, a, u: self.manager.pipeline.rename_stage(
                        self.pipeline_stage_out_id, a
                    ),
                )
            dpg.add_separator()
        self.create_pipeline_stage_content()

    def publish_stage(self, img: np.ndarray):
        """Publishes an image to output stage"""
        if self.has_pipeline_out:
            self.manager.pipeline.publish(self.pipeline_stage_out_id, img)

    def create_pipeline_stage_content(self):
        """Must be implemented by the widget, creates the content of the window"""
        raise NotImplementedError

    def on_pipeline_data(self, img: np.ndarray):
        """Must be implemented by the widget, is called when there is a new image published on the in stage"""
        pass

    # Callbacks

    def _on_stage_list(self, stagelist):
        if self.has_pipeline_in:
            stages = [f"{stage} : {id}" for id, stage in enumerate(stagelist)]
            dpg.configure_item(self.stage_in_combo, items=stages)

    def _on_stage_in_select(self, sender, selected_stage: str):
        d = selected_stage.split(" : ")
        name = d[0]
        id = int(d[1])
        self.pipeline_stage_in_id = id
        if self.has_pipeline_in:
            img = self.manager.pipeline.get_stage_data(id)
            self.on_pipeline_data(img)

    def _on_stage_data(self, data):
        pipeline_id = data[0]
        img = data[1]
        if self.has_pipeline_in and pipeline_id == self.pipeline_stage_in_id:
            self.on_pipeline_data(img)

    # Override the window resize callback
    def _on_window_resize(self, data):
        win_w, win_h = dpg.get_item_rect_size(self.window_tag)
        group_w, group_h = dpg.get_item_rect_size(self.pipeline_config_group_tag)
        group_x, group_y = dpg.get_item_pos(self.pipeline_config_group_tag)
        self.window_height = win_h - group_h - group_y - 12
        self.window_width = win_w - 7
        self.window_offset_y = group_h + group_y + 3
        self.on_resize(win_w, win_h)
