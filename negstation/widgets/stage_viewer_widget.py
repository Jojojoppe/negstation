import dearpygui.dearpygui as dpg
import numpy as np

from .base_widget import BaseWidget


# class StageViewerWidget(BaseWidget):
#     name: str = "Stage Viewer"

#     def __init__(self, manager, logger):
#         super().__init__(manager, logger)
#         # ensure texture registry
#         if not hasattr(manager, "texture_registry"):
#             manager.texture_registry = dpg.add_texture_registry(tag=dpg.generate_uuid())
#         self.registry = manager.texture_registry

#         self.stages = []
#         self.current = None
#         self.texture_tag = dpg.generate_uuid()
#         self.image_item = None

#         manager.bus.subscribe("pipeline_stages", self.on_stage_list, main_thread=True)
#         manager.bus.subscribe("pipeline_stage", self.on_stage_data, main_thread=True)

#     def create(self):
#         with dpg.window(
#             label="Stage Viewer",
#             tag=self.window_tag,
#             width=400,
#             height=400,
#             on_close=self._on_window_close,
#         ):
#             self.combo = dpg.add_combo(label="Stage", items=[], callback=self.on_select)
#             # placeholder 1×1 texture
#             dpg.add_dynamic_texture(
#                 width=1,
#                 height=1,
#                 default_value=[0.0, 0.0, 0.0, 0.0],
#                 tag=self.texture_tag,
#                 parent=self.registry,
#             )
#             self.image_item = dpg.add_image(self.texture_tag)

#     def on_stage_list(self, stages):
#         self.stages = stages
#         dpg.configure_item(self.combo, items=stages)
#         if not self.current and stages:
#             self.current = stages[0]
#             dpg.set_value(self.combo, self.current)

#     def on_select(self, sender, stage_name):
#         self.current = stage_name
#         img = self.manager.pipeline.get_stage(stage_name)
#         if img is not None:
#             self.update_texture(img)

#     def on_stage_data(self, data):
#         name, img = data
#         if name == self.current:
#             self.update_texture(img)

#     def update_texture(self, img: np.ndarray):
#         h, w, _ = img.shape
#         flat = img.flatten().tolist()

#         # recreate texture at correct size
#         if dpg.does_item_exist(self.texture_tag):
#             dpg.delete_item(self.texture_tag)
#         dpg.add_dynamic_texture(
#             width=w,
#             height=h,
#             default_value=flat,
#             tag=self.texture_tag,
#             parent=self.registry,
#         )

#         # determine available window size
#         win_w, win_h = dpg.get_item_rect_size(self.window_tag)
#         # reserve space for combo box (approx 30px)
#         available_h = max(win_h - 30, 1)
#         # compute scale to fit
#         scale = min(win_w / w, available_h / h)

#         disp_w = int(w * scale)
#         disp_h = int(h * scale)

#         # update image widget
#         dpg.configure_item(
#             self.image_item, texture_tag=self.texture_tag, width=disp_w, height=disp_h
#         )


class StageViewerWidget(BaseWidget):
    """
    A robust, zoomable stage viewer using a Dear PyGui Plot to display
    dynamic textures without ever deleting them—avoiding segfaults.
    """
    name = "Stage Viewer"

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        self.manager.bus.subscribe("pipeline_stages", self._on_stage_list, main_thread=True)
        self.manager.bus.subscribe("pipeline_stage", self._on_stage_data, main_thread=True)

        # one‐time flags and tags
        self._initialized = False
        self.texture_tag = dpg.generate_uuid()
        self.image_draw_tag = dpg.generate_uuid()
        self.plot_tag = dpg.generate_uuid()
        self.xaxis_tag = dpg.generate_uuid()
        self.yaxis_tag = dpg.generate_uuid()
        self.last_size = (1, 1)
        self.current_stage = None
        self.needs_fit = False

    def create(self):
        if dpg.does_item_exist(self.window_tag):
            return

        # ensure a texture registry exists
        if not hasattr(self.manager, "texture_registry"):
            self.manager.texture_registry = dpg.add_texture_registry(tag=dpg.generate_uuid())

        with dpg.window(label="Stage Viewer",
                        tag=self.window_tag,
                        on_close=self._on_window_close,
                        width=600, height=600):

            # stage selector
            self.combo = dpg.add_combo(label="Stage", items=[], callback=self._on_select)

            # plot container, equal_aspects ensures no distortion
            with dpg.plot(label="Image Plot", tag=self.plot_tag, height=-1, width=-1, equal_aspects=True):
                self.xaxis_tag = dpg.add_plot_axis(dpg.mvXAxis,
                                                   no_tick_labels=True, no_gridlines=True)
                self.yaxis_tag = dpg.add_plot_axis(dpg.mvYAxis,
                                                   no_tick_labels=True, no_gridlines=True)

            # resize handler to refit on window/plot size changes
            with dpg.item_handler_registry() as handler:
                dpg.add_item_resize_handler(callback=lambda s,a,u: self._fit_image(), user_data=None)
                dpg.bind_item_handler_registry(self.window_tag, handler)

    def _on_stage_list(self, stages):
        dpg.configure_item(self.combo, items=stages)
        if not self.current_stage and stages:
            self.current_stage = stages[0]
            dpg.set_value(self.combo, self.current_stage)

    def _on_select(self, sender, stage_name):
        self.current_stage = stage_name
        img = self.manager.pipeline.get_stage(stage_name)
        if img is not None:
            self._update_image(img)

    def _on_stage_data(self, data):
        name, img = data
        if name == self.current_stage:
            self._update_image(img)

    def _update_image(self, img: np.ndarray):
        h, w, _ = img.shape
        self.last_size = (w, h)

        # First time: create texture & draw-image inside the plot
        if not self._initialized:
            dpg.add_dynamic_texture(w, h, img, tag=self.texture_tag,
                                    parent=self.manager.texture_registry)
            dpg.draw_image(self.texture_tag,
                           pmin=(0, h), pmax=(w, 0),
                           tag=self.image_draw_tag,
                           parent=self.plot_tag)
            self._initialized = True
        else:
            # Subsequent updates: just set_value and adjust draw coords
            dpg.set_value(self.texture_tag, img)
            dpg.configure_item(self.image_draw_tag,
                               pmin=(0, self.last_size[1]),
                               pmax=(self.last_size[0], 0))

        # show & focus window
        dpg.configure_item(self.window_tag, show=True)
        dpg.focus_item(self.window_tag)

        # flag to refit axes
        self.needs_fit = True

    def _fit_image(self):
        """Adjust plot axes so the image fills the available space."""
        if not self._initialized or not self.needs_fit:
            return

        # get plot area size
        plot_w = dpg.get_item_width(self.window_tag)
        plot_h = dpg.get_item_height(self.window_tag) - 30  # reserve combo height
        if plot_w <= 0 or plot_h <= 0:
            return

        img_w, img_h = self.last_size
        if img_w <= 0 or img_h <= 0:
            return

        plot_aspect = plot_w / plot_h
        img_aspect = img_w / img_h

        if img_aspect > plot_aspect:
            x_min, x_max = 0, img_w
            needed_h = img_w / plot_aspect
            center_y = img_h / 2
            y_min = center_y - needed_h / 2
            y_max = center_y + needed_h / 2
        else:
            y_min, y_max = 0, img_h
            needed_w = img_h * plot_aspect
            center_x = img_w / 2
            x_min = center_x - needed_w / 2
            x_max = center_x + needed_w / 2

        dpg.set_axis_limits(self.xaxis_tag, x_min, x_max)
        dpg.set_axis_limits(self.yaxis_tag, y_min, y_max)
        self.needs_fit = False

    def update(self):
        # If we flagged a refit, do it now
        if self.needs_fit:
            self._fit_image()
