import dearpygui.dearpygui as dpg
import numpy as np
from .pipeline_stage_widget import PipelineStageWidget


class HistogramWidget(PipelineStageWidget):
    name = "Histogram"
    register = True
    has_pipeline_in = True
    has_pipeline_out = False

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_in="monochrome")
        self.plot_tag = dpg.generate_uuid()
        self.axis_x = dpg.generate_uuid()
        self.axis_y = dpg.generate_uuid()
        self.needs_redraw = False
        self.img = None
        self.series_tags = {
            "R": dpg.generate_uuid(),
            "G": dpg.generate_uuid(),
            "B": dpg.generate_uuid(),
            "L": dpg.generate_uuid(),
        }

    def create_pipeline_stage_content(self):
        with dpg.plot(label="Histogram", height=200, width=-1, tag=self.plot_tag):
            dpg.add_plot_legend()
            dpg.add_plot_axis(
                dpg.mvXAxis, tag=self.axis_x)
            with dpg.plot_axis(dpg.mvYAxis, tag=self.axis_y):
                for channel, tag in self.series_tags.items():
                    dpg.add_line_series([], [], label=channel, tag=tag)
        dpg.set_axis_limits(self.axis_x, 0.0, 1.0)
        dpg.set_axis_limits(self.axis_y, 0.0, 1.0)

    def on_pipeline_data(self, img: np.ndarray):
        if img is None or img.ndim != 3 or img.shape[2] < 3:
            return

        self.img = img
        self.needs_redraw = True

    def update(self):
        # TODO move calculations to on_pipeline_data
        if not self.needs_redraw or self.img is None:
            return

        self.needs_redraw = False
        img = np.clip(self.img, 0.0, 1.0)

        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

        bins = 64
        hist_range = (0.0, 1.0)
        bin_edges = np.linspace(*hist_range, bins)

        def compute_hist(channel):
            hist, _ = np.histogram(channel, bins=bin_edges)
            x = bin_edges[:-1]
            y = np.log1p(hist)
            y = y / np.max(y)
            return x.tolist(), y.tolist()

        dpg.set_value(self.series_tags["R"], compute_hist(r))
        dpg.set_value(self.series_tags["G"], compute_hist(g))
        dpg.set_value(self.series_tags["B"], compute_hist(b))
        dpg.set_value(self.series_tags["L"], compute_hist(luminance))
