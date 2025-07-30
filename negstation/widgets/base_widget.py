import dearpygui.dearpygui as dpg
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..negstation import EditorManager


class BaseWidget:
    name: str = "BaseWidget"

    def __init__(self, manager: "EditorManager", logger: logging.Logger):
        self.manager = manager
        self.logger = logger
        self.window_tag = dpg.generate_uuid()
        self.config = {}

    def create(self):
        raise NotImplementedError

    def update(self):
        pass

    def get_config(self):
        return self.config

    def _on_window_close(self):
        try:
            dpg.delete_item(self.window_tag)
            self.manager.widgets.remove(self)
        except ValueError:
            pass
