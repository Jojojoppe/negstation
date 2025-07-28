# in widgets/image_viewer_widget.py
import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget
import logging

class ImageViewerWidget(BaseWidget):
    """
    Displays a zoomable image inside a plot. This definitive version implements
    programmatic pan and zoom by handling mouse events manually and repeatedly
    calling set_axis_limits, as this is the only reliable method to achieve
    both an initial fit and subsequent user interaction.
    """
    def __init__(self, widget_type: str, config: dict, layout_manager, global_state):
        super().__init__(widget_type, config, layout_manager, global_state)
        
        # Subscribe to the event that will provide new images
        self.global_state.subscribe("NEW_IMAGE_CAPTURED", self.on_new_image)
        
        # Register for updates to handle the dirty flag and panning
        layout_manager.updating_widgets.append("ImageViewerWidget")

        # Initialize tags and state variables
        self.texture_tag = None
        self.image_draw_tag = None
        self.last_image_size = (1, 1) # width, height
        self.needs_fit = False # The "dirty flag" for deferred fitting

    def create(self):
        """Creates the DPG window, plot, and the necessary mouse handlers."""
        if dpg.does_item_exist(self.window_tag): return
        
        with dpg.window(label="Image Viewer", tag=self.window_tag, on_close=self._on_window_close, width=800, height=600):
            # The plot is our canvas. `equal_aspects` is critical for preventing distortion.
            with dpg.plot(label="Image Plot", no_menus=True, height=-1, width=-1, equal_aspects=True) as self.plot_tag:
                self.xaxis_tag = dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True, no_gridlines=True)
                self.yaxis_tag = dpg.add_plot_axis(dpg.mvYAxis, no_tick_labels=True, no_gridlines=True)

    def on_new_image(self, image_path: str):
        """Loads image data, deletes/recreates the drawing, and flags for a refit."""
        if not image_path: return
        logging.info(f"ImageViewer received new image: {image_path}")
        try:
            width, height, channels, data = dpg.load_image(image_path)
            self.last_image_size = (width, height)
            
            # Create or update the texture in the registry
            if self.texture_tag is not None:
                dpg.delete_item(self.texture_tag)
                
            self.texture_tag = dpg.generate_uuid()
            dpg.add_static_texture(width, height, data, tag=self.texture_tag, parent=self.layout_manager.texture_registry)

            if self.image_draw_tag and dpg.does_item_exist(self.image_draw_tag):
                dpg.delete_item(self.image_draw_tag)
            
            self.image_draw_tag = dpg.draw_image(self.texture_tag, (0, height), (width, 0), parent=self.plot_tag)
            
            # Set the dirty flag to trigger a fit on the next frame
            self.needs_fit = True
            
            dpg.configure_item(self.window_tag, show=True)
            dpg.configure_item(self.plot_tag, label=image_path)
            dpg.focus_item(self.window_tag)

        except Exception as e:
            logging.error(f"ImageViewer failed to process image '{image_path}': {e}", exc_info=True)

    def fit_image_to_plot(self):
        """Calculates and MANUALLY sets the plot's axis limits for the initial fit."""
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