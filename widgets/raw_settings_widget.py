# in widgets/raw_settings_widget.py
import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget

class RawSettingsWidget(BaseWidget):
    """A widget to control the rawpy processing parameters stored in GlobalState."""
    def create(self):
        if dpg.does_item_exist(self.window_tag): return
        
        with dpg.window(label="RAW Development", tag=self.window_tag, on_close=self._on_window_close):
            dpg.add_text("rawpy Postprocessing Settings")
            dpg.add_separator()

            # Create UI elements that directly modify the shared state dictionary
            dpg.add_checkbox(
                label="Auto White Balance",
                default_value=self.global_state.raw_params["use_auto_wb"],
                callback=lambda s, a, u: self.global_state.raw_params.update({"use_auto_wb": a})
            )
            dpg.add_checkbox(
                label="Use Camera White Balance",
                default_value=self.global_state.raw_params["use_camera_wb"],
                callback=lambda s, a, u: self.global_state.raw_params.update({"use_camera_wb": a})
            )
            dpg.add_checkbox(
                label="Disable Auto-Brightness",
                default_value=self.global_state.raw_params["no_auto_bright"],
                callback=lambda s, a, u: self.global_state.raw_params.update({"no_auto_bright": a})
            )
            dpg.add_radio_button(
                label="Output BPS",
                items=["8", "16"],
                default_value=str(self.global_state.raw_params["output_bps"]),
                callback=lambda s, a, u: self.global_state.raw_params.update({"output_bps": int(a)}),
                horizontal=True
            )