import dearpygui.dearpygui as dpg
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..negstation import EditorManager


class BaseWidget:
    name: str = "BaseWidget"
    register: bool = False

    def __init__(
        self,
        manager: "EditorManager",
        logger: logging.Logger,
        window_width: int = 300,
        window_height: int = 200,
    ):
        self.manager = manager
        self.logger = logger
        self.window_width = window_width
        self.window_height = window_height
        self.window_offset_x = 0
        self.window_offset_y = 0
        self.window_tag = dpg.generate_uuid()
        self.config = {}

    def create(self):
        """Called by negstation itself, creates the window"""
        with dpg.window(
            label=self.name,
            tag=self.window_tag,
            width=self.window_width,
            height=self.window_height,
            on_close=self._on_window_close,
        ):
            self.window_handler = dpg.add_item_handler_registry()
            dpg.add_item_resize_handler(
                callback=self._on_window_resize, parent=self.window_handler
            )
            dpg.bind_item_handler_registry(self.window_tag, self.window_handler)

            self.create_content()

    def create_content(self):
        """Must be implemented by the widget, creates the content of the window"""
        raise NotImplementedError

    def update(self):
        """Must be implemented by the widget, is called in the render loop every frame"""
        pass

    def on_resize(self, width: int, height: int):
        """Must be implemented by the widget, is called after a resize"""
        pass

    # Internal but public funtions

    def get_config(self):
        """Caled by negstation itself, returns the saved widget config"""
        return self.config

    # Callbacks

    def _on_window_close(self):
        try:
            dpg.delete_item(self.window_tag)
            self.manager.widgets.remove(self)
        except ValueError:
            pass

    def _on_window_resize(self, data):
        win_w, win_h = dpg.get_item_rect_size(self.window_tag)
        self.window_height = win_h
        self.window_width = win_w
        self.on_resize(win_w, win_h)
