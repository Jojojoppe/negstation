import dearpygui.dearpygui as dpg
import logging

class BaseWidget:
    """A base class to handle common functionality for all widgets."""
    def __init__(self, widget_type: str, config: dict, layout_manager, global_state):
        self.widget_type = widget_type
        self.config = config
        self.layout_manager = layout_manager
        self.global_state = global_state
        self.window_tag = f"widget_win_{self.widget_type}"

    def create(self):
        raise NotImplementedError

    def get_config(self) -> dict:
        return self.config
    
    def update(self):
        raise NotImplementedError

    def _on_window_close(self, sender, app_data, user_data):
        logging.info(f"Hiding widget: {self.widget_type}")
        dpg.configure_item(self.window_tag, show=False)