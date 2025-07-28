import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget

class LogWidget(BaseWidget):
    """A widget to display captured log messages."""
    def create(self):
        if dpg.does_item_exist(self.window_tag): return
        with dpg.window(label="Log Viewer", tag=self.window_tag, on_close=self._on_window_close, width=500, height=300):
            self.text_item_tag = dpg.add_input_text(
                multiline=True, readonly=True, width=-1, height=-1, default_value="Log initialized.\n"
            )
    
    def update_logs(self, log_handler):
        """Called every frame to update the text with new logs."""
        if dpg.is_item_visible(self.window_tag):
            log_content = log_handler.get_all_logs()
            dpg.set_value(self.text_item_tag, log_content)