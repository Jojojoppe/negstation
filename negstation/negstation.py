import dearpygui.dearpygui as dpg
import logging
import os
import importlib
import inspect
import sys
import signal
from pathlib import Path

from .event_bus import EventBus
from .image_pipeline import ImagePipeline
from .layout_manager import LayoutManager

from .widgets.base_widget import BaseWidget

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class EditorManager:
    def __init__(self):
        dpg.create_context()
        self.texture_registry = dpg.add_texture_registry()
        self.bus = EventBus(logger)
        self.pipeline = ImagePipeline(self.bus)
        self.layout_manager = LayoutManager(self, logger)
        self.widgets = []
        self.widget_classes = {}

    def _discover_and_register_widgets(self, directory="widgets"):
        logging.info(f"Discovering widgets in '{directory}' directory...")
        dir_path = Path(directory)
        if not dir_path.is_dir():
            logging.error(f"Path '{directory}' is not a directory")
            return

        parent = str(dir_path.parent.resolve())
        if parent not in sys.path:
            sys.path.insert(0, parent)
        pkg_name = dir_path.name  # e.g. 'widgets'

        # 1) Load the package’s own BaseWidget
        try:
            base_mod = importlib.import_module(f"{pkg_name}.base_widget")
            ModuleBaseWidget = getattr(base_mod, "BaseWidget")
        except Exception:
            ModuleBaseWidget = None

        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            module_name = f"{pkg_name}.{py_file.stem}"
            try:
                module = importlib.import_module(module_name)
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    # 2) Use the BaseWidget defined *in* widgets/base_widget.py
                    if (
                        ModuleBaseWidget
                        and issubclass(cls, ModuleBaseWidget)
                        and cls is not ModuleBaseWidget
                        and cls.register
                    ):
                        logging.info(
                            f"  -> Found and registered widget: {name}")
                        self._register_widget(name, cls)
            except Exception as e:
                logging.error(f"Failed to import widget '{py_file.name}': {e}")

    def _register_widget(self, name: str, widget_class: object):
        if name in self.widget_classes:
            logging.warning(
                f"Widget '{name}' is already registered. Overwriting.")
        self.widget_classes[name] = widget_class

    def _add_widget(self, widget_type: str, config:dict = {}):
        WidgetClass = self.widget_classes[widget_type]
        instance = WidgetClass(self, logger)
        logger.info(f'Created instance: {str(instance)}')
        self.widgets.append(instance)
        instance.create()
        instance.set_config(config)

    def _on_drag(self, sender, app_data, user_data):
        self.bus.publish_deferred("mouse_dragged", {
            "button": (
                        "right"
                        if app_data[0] == 0
                        else ("left" if app_data[0] == 1 else ("middle"))
                    ),
            "delta": (app_data[1], app_data[2])
        })

    def setup(self):
        self._discover_and_register_widgets(
            f"{os.path.dirname(os.path.realpath(__file__))}/widgets"
        )
        self.layout_manager.load_layout()

        dpg.create_viewport(title="NegStation", width=1200, height=800)
        dpg.configure_app(docking=True, docking_space=True)

        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="Save Layout", callback=self.layout_manager.save_layout
                )
                dpg.add_menu_item(
                    label="Run full-res pipeline", callback=lambda: self.bus.publish_deferred("process_full_res", None)
                )
                dpg.add_menu_item(
                    label="Quit", callback=lambda: dpg.stop_dearpygui()
                )

            with dpg.menu(label="View"):
                for widget_name in sorted(self.widget_classes.keys()):
                    dpg.add_menu_item(
                        label=self.widget_classes[widget_name].name,
                        callback=lambda s, a, ud: self._add_widget(ud),
                        user_data=widget_name,
                    )
                
            with dpg.handler_registry() as self.handler_registry:
                dpg.add_mouse_drag_handler(callback=self._on_drag, threshold=1.0, button=0)
                dpg.add_mouse_drag_handler(callback=self._on_drag, threshold=1.0, button=1)
                dpg.add_mouse_drag_handler(callback=self._on_drag, threshold=1.0, button=2)

    def run(self):
        self.setup()
        dpg.setup_dearpygui()
        dpg.show_viewport()

        try:
            while dpg.is_dearpygui_running():
                self.bus.process_main_queue()
                for w in self.widgets:
                    w.update()
                dpg.render_dearpygui_frame()
        except KeyboardInterrupt:
            logger.info("CTRL-C pressed: exiting...")
        dpg.destroy_context()
