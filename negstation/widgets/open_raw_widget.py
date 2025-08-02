import dearpygui.dearpygui as dpg
import rawpy
import numpy as np

from .pipeline_stage_widget import PipelineStageWidget


class OpenRawWidget(PipelineStageWidget):
    name = "Open RAW File"
    register = True
    has_pipeline_in = False
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_out="opened_raw")
        self.dialog_tag = dpg.generate_uuid()
        self.output_tag = dpg.generate_uuid()
        self.config_group = dpg.generate_uuid()
        self.busy_group = dpg.generate_uuid()
        self.raw_path = None
        self.config = {
            # Demosaic algorithm
            "demosaic_algorithm": rawpy.DemosaicAlgorithm.AHD,
            # Output color space
            "output_color":       rawpy.ColorSpace.sRGB,
            # Bits per sample
            "output_bps":         16,
            # White balance
            "use_camera_wb":      True,
            "use_auto_wb":        False,
            "user_wb":            (1.0, 1.0, 1.0, 1.0),
            # Brightness/exposure
            "bright":             1.0,
            "no_auto_bright":     False,
            # Gamma correction (you’ll pass (1.0, config["gamma"]) down)
            "gamma":              1.0,
            # Size & quality toggles
            "half_size":          False,
            "four_color_rgb":     False,
        }

    def get_config(self):
        return {}

    def create_pipeline_stage_content(self):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_file_selected,
            tag=self.dialog_tag,
            height=300,
            width=400,
        ):
            dpg.add_file_extension(
                "RAW files {.nef,.cr2}",
            )
            dpg.add_file_extension(".*")

        with dpg.group(tag=self.config_group):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Open File...",
                               callback=self._on_open_file)
                dpg.add_button(label="Reprocess",
                               callback=self._process_and_publish)

            dpg.add_combo(
                label="Demosaic",
                items=[alg.name for alg in rawpy.DemosaicAlgorithm],
                default_value=rawpy.DemosaicAlgorithm.AHD.name,
                callback=lambda s, a, u: self.config.__setitem__(
                    "demosaic_algorithm", rawpy.DemosaicAlgorithm[a])
            )
            dpg.add_combo(
                label="Color Space",
                items=[cs.name for cs in rawpy.ColorSpace],
                default_value=rawpy.ColorSpace.sRGB.name,
                callback=lambda s, a, u: self.config.__setitem__(
                    "output_color", rawpy.ColorSpace[a])
            )
            dpg.add_combo(
                label="Output Bits",
                items=["8", "16"],
                default_value="16",
                callback=lambda s, a, u: self.config.__setitem__(
                    "output_bps", int(a))
            )
            dpg.add_checkbox(
                label="Use Camera WB",
                default_value=True,
                callback=lambda s, a, u: self.config.__setitem__(
                    "use_camera_wb", a)
            )
            dpg.add_checkbox(
                label="Auto WB",
                default_value=False,
                callback=lambda s, a, u: self.config.__setitem__(
                    "use_auto_wb", a)
            )
            dpg.add_slider_float(
                label="Manual WB R Gain",
                default_value=1.0, min_value=0.1, max_value=4.0,
                callback=lambda s, a, u: self.config.__setitem__(
                    "user_wb", (a, self.config["user_wb"][1], self.config["user_wb"][2], self.config["user_wb"][3]))
            )
            dpg.add_slider_float(
                label="Manual WB G Gain",
                default_value=1.0, min_value=0.1, max_value=4.0,
                callback=lambda s, a, u: self.config.__setitem__(
                    "user_wb", (self.config["user_wb"][0], a, a, self.config["user_wb"][3]))
            )
            dpg.add_slider_float(
                label="Manual WB B Gain",
                default_value=1.0, min_value=0.1, max_value=4.0,
                callback=lambda s, a, u: self.config.__setitem__(
                    "user_wb", (self.config["user_wb"][0], self.config["user_wb"][1], self.config["user_wb"][2], a))
            )
            dpg.add_slider_float(
                label="Bright",
                default_value=1.0, min_value=0.1, max_value=4.0,
                callback=lambda s, a, u: self.config.__setitem__("bright", a)
            )
            dpg.add_checkbox(
                label="No Auto Bright",
                default_value=False,
                callback=lambda s, a, u: self.config.__setitem__(
                    "no_auto_bright", a)
            )
            dpg.add_slider_float(
                label="Gamma",
                default_value=1.0, min_value=0.1, max_value=3.0,
                callback=lambda s, a, u: self.config.__setitem__("gamma", a)
            )
            dpg.add_checkbox(
                label="Half-size",
                default_value=False,
                callback=lambda s, a, u: self.config.__setitem__(
                    "half_size", a)
            )
            dpg.add_checkbox(
                label="4-color RGB",
                default_value=False,
                callback=lambda s, a, u: self.config.__setitem__(
                    "four_color_rgb", a)
            )

        with dpg.group(tag=self.busy_group, show=False):
            dpg.add_text("Processing...")

    def _on_open_file(self):
        dpg.configure_item(self.dialog_tag, show=True)

    def _on_file_selected(self, sender, app_data):
        selection = (
            f"{app_data['current_path']
               }/{list(app_data['selections'].keys())[0]}"
            if isinstance(app_data, dict)
            else None
        )
        if not selection:
            return
        self.raw_path = selection
        self.logger.info(f"Selected file '{selection}'")
        self._process_and_publish()

    def _process_and_publish(self):
        if self.raw_path is None:
            return
        self.logger.info("Processing RAW image")

        dpg.configure_item(self.config_group, show=False)
        dpg.configure_item(self.busy_group, show=True)

        with rawpy.imread(self.raw_path) as raw:
            # Prepare postprocess kwargs from config
            postprocess_args = {
                'demosaic_algorithm': self.config["demosaic_algorithm"],
                'output_color':       self.config["output_color"],
                'output_bps':         self.config["output_bps"],
                'bright':             self.config["bright"],
                'no_auto_bright':     self.config["no_auto_bright"],
                'gamma':              (1.0, self.config["gamma"]),
                'half_size':          self.config["half_size"],
                'four_color_rgb':     self.config["four_color_rgb"],
            }

            if self.config["use_camera_wb"]:
                postprocess_args['use_camera_wb'] = True
            elif self.config["use_auto_wb"]:
                postprocess_args['use_auto_wb'] = True
            else:
                postprocess_args['user_wb'] = self.config["user_wb"]

            # Postprocess into RGB
            rgb = raw.postprocess(**postprocess_args)

        # Normalize to float32 in 0.0-1.0 range depending on output_bps
        max_val = (2 ** self.config["output_bps"]) - 1
        rgb_float = rgb.astype(np.float32) / max_val

        # Add alpha channel (fully opaque)
        h, w, _ = rgb_float.shape
        alpha = np.ones((h, w, 1), dtype=np.float32)

        rgba = np.concatenate([rgb_float, alpha], axis=2)

        self.manager.pipeline.publish(self.pipeline_stage_out_id, rgba)
        dpg.configure_item(self.config_group, show=True)
        dpg.configure_item(self.busy_group, show=False)
