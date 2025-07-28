# in widgets/image_viewer_widget.py
import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget
import logging
import numpy as np

class ImageViewerWidget(BaseWidget):
    """
    Displays a zoomable image inside a plot. This definitive version uses a
    "reuse and reconfigure" pattern, creating DPG items only once and updating
    them on subsequent loads to ensure stability and avoid segmentation faults.
    """
    def __init__(self, widget_type: str, config: dict, layout_manager, global_state):
        super().__init__(widget_type, config, layout_manager, global_state)
        
        self.global_state.subscribe("PROCESSED_IMAGE_READY", self.on_new_image_data)
        layout_manager.updating_widgets.append("ImageViewerWidget")

        # --- Initialize state ---
        # A flag to know if the DPG items have been created yet.
        self.is_initialized = False
        # Generate the tags once. They will be reused for the widget's lifetime.
        self.texture_tag = dpg.generate_uuid()
        self.image_draw_tag = dpg.generate_uuid()
        
        self.last_image_size = (1, 1)
        self.needs_fit = False

    def create(self):
        """Creates the DPG window and plot container. Does NOT create textures or drawings."""
        if dpg.does_item_exist(self.window_tag): return
        
        with dpg.window(label="Image Viewer", tag=self.window_tag, on_close=self._on_window_close, width=800, height=600):
            with dpg.plot(label="Image Plot", no_menus=True, height=-1, width=-1, equal_aspects=True) as self.plot_tag:
                self.xaxis_tag = dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True, no_gridlines=True)
                self.yaxis_tag = dpg.add_plot_axis(dpg.mvYAxis, no_tick_labels=True, no_gridlines=True)

            with dpg.item_handler_registry(tag=f"my_window_handler_{self.window_tag}") as handler:
                dpg.add_item_resize_handler(callback=self.fit_image_to_plot, user_data=self)
                dpg.bind_item_handler_registry(self.window_tag, handler)

    def on_new_image_data(self, image_data: np.ndarray):
        """Handles receiving a processed NumPy array, creating/updating items safely."""
        logging.info("ImageViewer received new processed image data.")
        try:
            height, width, channels = image_data.shape
            self.last_image_size = (width, height)
            
            # --- THE "REUSE AND RECONFIGURE" LOGIC ---
            if not self.is_initialized:
                # FIRST RUN: Create the texture and drawing items for the first time.
                logging.info("First image load: creating new texture and drawing items.")
                dpg.add_dynamic_texture(width, height, image_data, tag=self.texture_tag, parent=self.layout_manager.texture_registry)
                dpg.draw_image(self.texture_tag, (0, height), (width, 0), tag=self.image_draw_tag, parent=self.plot_tag)
                self.is_initialized = True
            else:
                # SUBSEQUENT RUNS: Update the existing items. NO DELETION.
                logging.info("Subsequent image load: updating existing texture and drawing.")
                dpg.set_value(self.texture_tag, image_data)
                dpg.configure_item(self.image_draw_tag, pmin=(0, height), pmax=(width, 0))

            # Set the dirty flag to trigger a fit on the next frame in all cases.
            self.needs_fit = True
            
            dpg.configure_item(self.window_tag, show=True)
            dpg.focus_item(self.window_tag)

        except Exception as e:
            logging.error(f"ImageViewer failed to process image data: {e}", exc_info=True)

    def fit_image_to_plot(self):
        """Calculates and MANUALLY sets the plot's axis limits for the initial fit."""
        # This function is correct and necessary.
        plot_width = dpg.get_item_width(self.window_tag)
        plot_height = dpg.get_item_height(self.window_tag)
        if plot_width <= 0 or plot_height <= 0: return
        img_width, img_height = self.last_image_size
        if img_width <= 0 or img_height <= 0: return

        plot_aspect = plot_width / plot_height
        img_aspect = img_width / img_height

        if img_aspect > plot_aspect:
            x_min, x_max = 0, img_width
            required_y_span = img_width / plot_aspect
            center_y = img_height / 2
            y_min = center_y - required_y_span / 2
            y_max = center_y + required_y_span / 2
        else:
            y_min, y_max = 0, img_height
            required_x_span = img_height * plot_aspect
            center_x = img_width / 2
            x_min = center_x - required_x_span / 2
            x_max = center_x + required_x_span / 2
        
        dpg.set_axis_limits(self.xaxis_tag, x_min, x_max)
        dpg.set_axis_limits(self.yaxis_tag, y_min, y_max)

    def update(self):
        """On update, check if the image needs to be refit."""
        if self.needs_fit:
            if dpg.is_item_visible(self.plot_tag):
                self.fit_image_to_plot()
                self.needs_fit = False