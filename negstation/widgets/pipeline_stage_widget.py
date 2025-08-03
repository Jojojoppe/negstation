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
        self.stage_in_combo = dpg.generate_uuid()
        self.stage_out_input = dpg.generate_uuid()
        self._last_full = False

        if self.has_pipeline_out:
            self.pipeline_stage_out_id = self.manager.pipeline.register_stage(
                default_stage_out
            )

        self.manager.bus.subscribe("pipeline_stages", self._on_stage_list, True)
        if self.has_pipeline_in:
            self.pipeline_stage_in_id = 0
            self.manager.bus.subscribe("pipeline_stage", self._on_stage_data, True)
            self.manager.bus.subscribe(
                "pipeline_stage_full", self._on_stage_data_full, True
            )
        # force getting all available pipeline stages
        self.manager.pipeline.republish_stages()

    def create_content(self):
        with dpg.group(tag=self.pipeline_config_group_tag):
            if self.has_pipeline_in:
                dpg.add_combo(
                    label="Stage In",
                    items=[],
                    callback=self._on_stage_in_select,
                    default_value=f"{
                        self.manager.pipeline.get_stage_name(0)} : 0",
                    tag=self.stage_in_combo,
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
                    tag=self.stage_out_input,
                )
            dpg.add_separator()
        with dpg.group():
            self.create_pipeline_stage_content()

    def create_pipeline_stage_content(self):
        """Must be implemented by the widget, creates the content of the window"""
        raise NotImplementedError

    def on_pipeline_data(self, img: np.ndarray):
        """Must be implemented by the widget, is called when there is a new image published on the in stage"""
        pass

    def publish_stage(self, img):
        """Publishes an image to output stage"""
        if self.has_pipeline_out:
            self.manager.pipeline.publish(
                self.pipeline_stage_out_id, img, full_res=self._last_full
            )

    def get_config(self):
        return {
            "pipeline_config": {
                "stage_in": self.pipeline_stage_in_id,
                "stage_out": self.pipeline_stage_out_id,
            }
        }

    def set_config(self, config):
        # Set pipelinedata
        if "pipeline_config" in config:
            if self.has_pipeline_in:
                self.pipeline_stage_in_id = config["pipeline_config"]["stage_in"]
            if self.has_pipeline_out:
                self.pipeline_stage_out_id = config["pipeline_config"]["stage_out"]
        self._update_ui_from_state()

    def _update_ui_from_state(self):
        """
        Refresh the ‘Stage In’ combo (and ‘Stage Out’ input) so
        that:
          1. its items list matches the current pipeline stages, and
          2. its displayed value matches the saved ID.
        """
        # --- Build the ordered list of "name : id" labels ---
        ordered = sorted(self.manager.pipeline.stages.items(), key=lambda kv: kv[0])
        labels = [f"{name} : {sid}" for sid, name in ordered]

        # --- Update Stage In combo ---
        if self.has_pipeline_in:
            dpg.configure_item(self.stage_in_combo, items=labels)
            # set the combo's value if the saved ID still exists
            sid = self.pipeline_stage_in_id
            if sid in self.manager.pipeline.stages:
                name = self.manager.pipeline.get_stage_name(sid)
                dpg.set_value(self.stage_in_combo, f"{name} : {sid}")
            else:
                # clear if it no longer exists
                dpg.set_value(self.stage_in_combo, "")

        # --- Update Stage Out input text ---
        if self.has_pipeline_out:
            # show the stage name (without ID) or blank if missing
            sid = self.pipeline_stage_out_id
            if sid in self.manager.pipeline.stages:
                name = self.manager.pipeline.get_stage_name(sid)
                dpg.set_value(self.stage_out_input, name)
            else:
                dpg.set_value(self.stage_out_input, "")

    # Callbacks

    def _on_window_close(self):
        if self.has_pipeline_out:
            self.manager.pipeline.remove_stage(self.pipeline_stage_out_id)
        return super()._on_window_close()

    def _on_stage_list(self, stagelist):
        if self.has_pipeline_in:
            self._update_ui_from_state()

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
            self._last_full = False
            self.on_pipeline_data(img)

    def _on_stage_data_full(self, data):
        pipeline_id = data[0]
        img = data[1]
        if self.has_pipeline_in and pipeline_id == self.pipeline_stage_in_id:
            self._last_full = True
            if hasattr(self, "on_full_res_pipeline_data"):
                self.on_full_res_pipeline_data(img)
            else:
                self.on_pipeline_data(img)

    # Override the window resize callback

    def _on_window_resize(self, data):
        win_w, win_h = dpg.get_item_rect_size(self.window_tag)
        group_w, group_h = dpg.get_item_rect_size(self.pipeline_config_group_tag)
        group_x, group_y = dpg.get_item_pos(self.pipeline_config_group_tag)
        self.window_height = win_h - group_h - group_y - 12
        self.window_width = win_w - 7
        self.on_resize(win_w, win_h)
