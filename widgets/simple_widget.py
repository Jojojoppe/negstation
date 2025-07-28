import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget

class SimpleWidget(BaseWidget):
    """A basic text widget to demonstrate dynamic loading."""
    def create(self):
        if dpg.does_item_exist(self.window_tag): return
        with dpg.window(label="Simple Widget", tag=self.window_tag, on_close=self._on_window_close, width=300, height=120):
            dpg.add_text("This widget was loaded dynamically!")
            dpg.add_button(label="A Button")