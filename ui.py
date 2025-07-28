import dearpygui.dearpygui as dpg
import os
import json
import logging
import importlib
import inspect
from collections import deque

import global_state
import raw_processor
from widgets.base_widget import BaseWidget

class DpgLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_queue = deque(maxlen=200)
    def emit(self, record):
        msg = self.format(record)
        self.log_queue.append(msg)
        print(msg)
    def get_all_logs(self):
        return "\n".join(self.log_queue)

log_handler = DpgLogHandler()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[log_handler])

INI_PATH = "negstation_layout.ini"
WIDGET_DATA_PATH = "negstation_widgets.json"

class LayoutManager:
    def __init__(self):
        self.active_widgets = {}
        self.widget_classes = {}
        self.updating_widgets = []
        self.global_state = global_state.GlobalState()

        self.texture_registry = dpg.add_texture_registry() 
        self.raw_processor = raw_processor.RawProcessor(self.global_state)

    def discover_and_register_widgets(self, directory="widgets"):
        """Dynamically discovers and registers widgets from a given directory."""
        logging.info(f"Discovering widgets in '{directory}' directory...")
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{directory}.{filename[:-3]}"
                try:
                    # Dynamically import the module
                    module = importlib.import_module(module_name)
                    
                    # Find all classes in the module that are subclasses of BaseWidget
                    for name, cls in inspect.getmembers(module, inspect.isclass):
                        if issubclass(cls, BaseWidget) and cls is not BaseWidget:
                            logging.info(f"  -> Found and registered widget: {name}")
                            self.register_widget(name, cls)
                except ImportError as e:
                    logging.error(f"Failed to import widget module {module_name}: {e}")

    def register_widget(self, name: str, widget_class: object):
        """Adds a widget class to the registry."""
        if name in self.widget_classes:
            logging.warning(f"Widget '{name}' is already registered. Overwriting.")
        self.widget_classes[name] = widget_class
    
    def add_widget(self, widget_type: str):
        if widget_type not in self.widget_classes: logging.error(f"Unknown widget type '{widget_type}'"); return
        if widget_type in self.active_widgets:
            widget_tag = self.active_widgets[widget_type].window_tag
            if dpg.does_item_exist(widget_tag):
                logging.info(f"Showing existing widget: {widget_type}"); dpg.configure_item(widget_tag, show=True); dpg.focus_item(widget_tag)
            return
        config = {"label": widget_type}
        WidgetClass = self.widget_classes[widget_type]
        widget_instance = WidgetClass(widget_type, config, self, self.global_state)
        logging.info(f"Creating new widget of type: {widget_type}")
        self.active_widgets[widget_type] = widget_instance
        widget_instance.create()

    def save_layout(self):
        logging.info("Saving layout..."); dpg.save_init_file(INI_PATH)
        widget_data = [{"widget_type": w_type, "config": w.get_config()} for w_type, w in self.active_widgets.items()]
        with open(WIDGET_DATA_PATH, 'w') as f: json.dump(widget_data, f, indent=4)
        logging.info("Layout saved successfully.")

    def load_layout(self):
        logging.info("Loading layout...");
        if not os.path.exists(WIDGET_DATA_PATH): return
        with open(WIDGET_DATA_PATH, 'r') as f: widget_data = json.load(f)
        for data in widget_data:
            if data.get("widget_type") in self.widget_classes: self.add_widget(widget_type=data.get("widget_type"))
        if os.path.exists(INI_PATH): dpg.configure_app(init_file=INI_PATH); logging.info(f"Applied UI layout from {INI_PATH}")

    def update_all_widgets(self):
        """Calls per-frame update methods on widgets that need it."""
        if "LogWidget" in self.active_widgets:
            # We need to pass the handler to the update method
            self.active_widgets["LogWidget"].update_logs(log_handler)
        for w in self.updating_widgets:
            if w in self.active_widgets:
                self.active_widgets[w].update()

    @staticmethod
    def run():
        dpg.create_context()
        dpg.create_viewport(title='Dynamic Docking Layout with Menu', width=1280, height=720)

        layout_manager = LayoutManager()
        layout_manager.discover_and_register_widgets()

        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Save Layout", callback=layout_manager.save_layout)
            
            with dpg.menu(label="View"):
                for widget_name in sorted(layout_manager.widget_classes.keys()):
                    dpg.add_menu_item(
                        label=f"Show {widget_name}",
                        callback=lambda s, a, ud: layout_manager.add_widget(ud),
                        user_data=widget_name
                    )
        
        dpg.configure_app(docking=True, docking_space=True)
        dpg.setup_dearpygui()
        
        layout_manager.load_layout()
        
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            layout_manager.update_all_widgets()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
