import dearpygui.dearpygui as dpg
import logging
import json
import os

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..negstation import EditorManager


class LayoutManager:
    INI_PATH = "negstation_layout.ini"
    WIDGET_DATA_PATH = "negstation_widgets.json"

    def __init__(self, manager: "EditorManager", logger: logging.Logger):
        self.manager = manager
        self.logger = logger

    def save_layout(self):
        self.logger.info("Saving layout...")
        dpg.save_init_file(self.INI_PATH)
        layout_data = {
            "pipeline_order" : { k:v  for k, v in self.manager.pipeline.stages.items() },
            "widgets": [
                {"widget_type": type(w).__name__, "config": w.get_config()}
                for w in self.manager.widgets
            ]
        }
        with open(self.WIDGET_DATA_PATH, "w") as f:
            json.dump(layout_data, f, indent=4)
        self.logger.info("Layout saved successfully.")

    def load_layout(self):
        self.logger.info("Loading layout...")
        if not os.path.exists(self.WIDGET_DATA_PATH):
            return
        with open(self.WIDGET_DATA_PATH, "r") as f:
            layout_data = json.load(f)

        # Load all widgets
        widget_data = layout_data["widgets"]
        for data in widget_data:
            if data.get("widget_type") in self.manager.widget_classes:
                self.manager._add_widget(widget_type=data.get("widget_type"), config=data.get("config"))

        # Reset the image pipeline and reload it
        pipelinestages = { int(k):v for k, v in layout_data["pipeline_order"].items() }
        self.manager.pipeline.load_stages(pipelinestages)

        if os.path.exists(self.INI_PATH):
            dpg.configure_app(init_file=self.INI_PATH)
            self.logger.info(f"Applied UI layout from {self.INI_PATH}")
