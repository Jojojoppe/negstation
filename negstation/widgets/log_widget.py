import dearpygui.dearpygui as dpg
import logging
from .base_widget import BaseWidget


class DPGLogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)


class LogWindowWidget(BaseWidget):
    name = "Log Window"
    register = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        self.initialized = False
        self.log_tag = dpg.generate_uuid()
        self.log_lines = []

        # Create and attach handler
        self.handler = DPGLogHandler(self._on_log)
        self.handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'))
        self.logger.addHandler(self.handler)

    def create_content(self):
        dpg.add_text("Live Log Output")
        dpg.add_separator()
        dpg.add_child_window(tag=self.log_tag, autosize_x=True,
                             autosize_y=True, horizontal_scrollbar=True)
        self.initialized = True

    def _on_log(self, msg: str):
        self.log_lines.append(msg)
        if self.initialized:
            dpg.add_text(msg, parent=self.log_tag)
            dpg.set_y_scroll(self.log_tag, dpg.get_y_scroll_max(self.log_tag))

    def on_resize(self, width: int, height: int):
        # Optional: could resize child window here if needed
        pass

    def _on_window_close(self):
        if self.initialized:
            self.logger.removeHandler(self.handler)
            self.handler = None
        super()._on_window_close()
