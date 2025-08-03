import dearpygui.dearpygui as dpg
import rawpy
import numpy as np
import ast
from PIL import Image

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
        self.img = None
        self.img_full = None
        self.rawconfig = {
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

        self.demosaic_combo_tag    = dpg.generate_uuid()
        self.color_space_combo_tag = dpg.generate_uuid()
        self.output_bps_combo_tag  = dpg.generate_uuid()
        self.use_cam_wb_tag        = dpg.generate_uuid()
        self.auto_wb_tag           = dpg.generate_uuid()
        self.wb_r_slider_tag       = dpg.generate_uuid()
        self.wb_g_slider_tag       = dpg.generate_uuid()
        self.wb_b_slider_tag       = dpg.generate_uuid()
        self.bright_slider_tag     = dpg.generate_uuid()
        self.no_auto_bright_tag    = dpg.generate_uuid()
        self.gamma_slider_tag      = dpg.generate_uuid()
        self.half_size_tag         = dpg.generate_uuid()
        self.four_color_tag        = dpg.generate_uuid()

        self.manager.bus.subscribe(
            "process_full_res", self._on_process_full_res, True)

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
            # -- Open / Reprocess buttons --
            with dpg.group(horizontal=True):
                dpg.add_button(label="Open File...", callback=self._on_open_file)
                dpg.add_button(label="Reprocess",  callback=self._process_and_publish)

            # -- Demosaic combo --
            dpg.add_combo(
                label="Demosaic",
                items=[alg.name for alg in rawpy.DemosaicAlgorithm],
                default_value=self.rawconfig["demosaic_algorithm"].name,
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "demosaic_algorithm", rawpy.DemosaicAlgorithm[a]
                ),
                tag=self.demosaic_combo_tag
            )

            # -- Color space combo --
            dpg.add_combo(
                label="Color Space",
                items=[cs.name for cs in rawpy.ColorSpace],
                default_value=self.rawconfig["output_color"].name,
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "output_color", rawpy.ColorSpace[a]
                ),
                tag=self.color_space_combo_tag
            )

            # -- Bits per sample --
            dpg.add_combo(
                label="Output Bits",
                items=["8","16"],
                default_value=str(self.rawconfig["output_bps"]),
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "output_bps", int(a)
                ),
                tag=self.output_bps_combo_tag
            )

            # -- Checkboxes & sliders --
            dpg.add_checkbox(
                label="Use Camera WB",
                default_value=self.rawconfig["use_camera_wb"],
                callback=lambda s,a,u: self.rawconfig.__setitem__("use_camera_wb", a),
                tag=self.use_cam_wb_tag
            )
            dpg.add_checkbox(
                label="Auto WB",
                default_value=self.rawconfig["use_auto_wb"],
                callback=lambda s,a,u: self.rawconfig.__setitem__("use_auto_wb", a),
                tag=self.auto_wb_tag
            )
            dpg.add_slider_float(
                label="Manual WB R Gain",
                default_value=self.rawconfig["user_wb"][0],
                min_value=0.1, max_value=4.0,
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "user_wb", (a, self.rawconfig["user_wb"][1],
                                self.rawconfig["user_wb"][2], self.rawconfig["user_wb"][3])
                ),
                tag=self.wb_r_slider_tag
            )
            dpg.add_slider_float(
                label="Manual WB G Gain",
                default_value=self.rawconfig["user_wb"][1],
                min_value=0.1, max_value=4.0,
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "user_wb", (self.rawconfig["user_wb"][0], a,
                                self.rawconfig["user_wb"][2], self.rawconfig["user_wb"][3])
                ),
                tag=self.wb_g_slider_tag
            )
            dpg.add_slider_float(
                label="Manual WB B Gain",
                default_value=self.rawconfig["user_wb"][2],
                min_value=0.1, max_value=4.0,
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "user_wb", (self.rawconfig["user_wb"][0],
                                self.rawconfig["user_wb"][1], a,
                                self.rawconfig["user_wb"][3])
                ),
                tag=self.wb_b_slider_tag
            )
            dpg.add_slider_float(
                label="Bright",
                default_value=self.rawconfig["bright"],
                min_value=0.1, max_value=4.0,
                callback=lambda s,a,u: self.rawconfig.__setitem__("bright", a),
                tag=self.bright_slider_tag
            )
            dpg.add_checkbox(
                label="No Auto Bright",
                default_value=self.rawconfig["no_auto_bright"],
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "no_auto_bright", a
                ),
                tag=self.no_auto_bright_tag
            )
            dpg.add_slider_float(
                label="Gamma",
                default_value=self.rawconfig["gamma"],
                min_value=0.1, max_value=3.0,
                callback=lambda s,a,u: self.rawconfig.__setitem__("gamma", a),
                tag=self.gamma_slider_tag
            )
            dpg.add_checkbox(
                label="Half-size",
                default_value=self.rawconfig["half_size"],
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "half_size", a
                ),
                tag=self.half_size_tag
            )
            dpg.add_checkbox(
                label="4-color RGB",
                default_value=self.rawconfig["four_color_rgb"],
                callback=lambda s,a,u: self.rawconfig.__setitem__(
                    "four_color_rgb", a
                ),
                tag=self.four_color_tag
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
                'demosaic_algorithm': self.rawconfig["demosaic_algorithm"],
                'output_color':       self.rawconfig["output_color"],
                'output_bps':         self.rawconfig["output_bps"],
                'bright':             self.rawconfig["bright"],
                'no_auto_bright':     self.rawconfig["no_auto_bright"],
                'gamma':              (1.0, self.rawconfig["gamma"]),
                'half_size':          self.rawconfig["half_size"],
                'four_color_rgb':     self.rawconfig["four_color_rgb"],
            }

            if self.rawconfig["use_camera_wb"]:
                postprocess_args['use_camera_wb'] = True
            elif self.rawconfig["use_auto_wb"]:
                postprocess_args['use_auto_wb'] = True
            else:
                postprocess_args['user_wb'] = self.rawconfig["user_wb"]

            # Postprocess into RGB
            rgb = raw.postprocess(**postprocess_args)

        # Normalize to float32 in 0.0-1.0 range depending on output_bps
        max_val = (2 ** self.rawconfig["output_bps"]) - 1
        rgb_float = rgb.astype(np.float32) / max_val

        # Add alpha channel (fully opaque)
        h, w, _ = rgb_float.shape
        alpha = np.ones((h, w, 1), dtype=np.float32)

        rgba = np.concatenate([rgb_float, alpha], axis=2)

        # scale for small version
        max_dim = 500
        scale = min(1.0, max_dim / w, max_dim / h)
        if scale < 1.0:
            # convert to 0–255 uint8, resize with PIL, back to float32 [0–1]
            pil = Image.fromarray((rgba * 255).astype(np.uint8), mode="RGBA")
            new_w, new_h = int(w * scale), int(h * scale)
            pil = pil.resize((new_w, new_h), Image.LANCZOS)
            rgba_small = np.asarray(pil).astype(np.float32) / 255.0
            w_small, h_small = new_w, new_h

        self.img_full = rgba
        self.img = rgba_small

        self.manager.pipeline.publish(self.pipeline_stage_out_id, rgba_small)
        dpg.configure_item(self.config_group, show=True)
        dpg.configure_item(self.busy_group, show=False)

    def _on_process_full_res(self, data):
        if self.img_full is None:
            return
        self.manager.pipeline.publish(
            self.pipeline_stage_out_id, self.img_full, True)
        
    def get_config(self):
        config = super().get_config()
        config["raw_config"] = { k:str(v) for k, v in self.rawconfig.items() }
        return config

    def set_config(self, config):
        super().set_config(config)
        raw_cfg = config.get("raw_config", {})
        if raw_cfg:
            # parse each back into Python types
            for k, v in raw_cfg.items():
                if k == "demosaic_algorithm":
                    # "DemosaicAlgorithm.AHD" → "AHD"
                    name = v.split(".", 1)[1]
                    self.rawconfig[k] = rawpy.DemosaicAlgorithm[name]
                elif k == "output_color":
                    name = v.split(".", 1)[1]
                    self.rawconfig[k] = rawpy.ColorSpace[name]
                elif k == "output_bps":
                    self.rawconfig[k] = int(v)
                elif k in ("use_camera_wb","use_auto_wb",
                           "no_auto_bright","half_size","four_color_rgb"):
                    self.rawconfig[k] = (v == "True")
                elif k in ("bright","gamma"):
                    self.rawconfig[k] = float(v)
                elif k == "user_wb":
                    self.rawconfig[k] = tuple(ast.literal_eval(v))

            # now that rawconfig is back to real types, update the UI
            self._update_raw_ui()

    def _update_raw_ui(self):
        """Push current self.rawconfig values back into all controls."""
        # combos want the enum.name or string
        dpg.set_value(self.demosaic_combo_tag,    self.rawconfig["demosaic_algorithm"].name)
        dpg.set_value(self.color_space_combo_tag,  self.rawconfig["output_color"].name)
        dpg.set_value(self.output_bps_combo_tag,   str(self.rawconfig["output_bps"]))

        # checkboxes & sliders
        dpg.set_value(self.use_cam_wb_tag,         self.rawconfig["use_camera_wb"])
        dpg.set_value(self.auto_wb_tag,            self.rawconfig["use_auto_wb"])
        dpg.set_value(self.wb_r_slider_tag,        self.rawconfig["user_wb"][0])
        dpg.set_value(self.wb_g_slider_tag,        self.rawconfig["user_wb"][1])
        dpg.set_value(self.wb_b_slider_tag,        self.rawconfig["user_wb"][2])
        dpg.set_value(self.bright_slider_tag,      self.rawconfig["bright"])
        dpg.set_value(self.no_auto_bright_tag,     self.rawconfig["no_auto_bright"])
        dpg.set_value(self.gamma_slider_tag,       self.rawconfig["gamma"])
        dpg.set_value(self.half_size_tag,          self.rawconfig["half_size"])
        dpg.set_value(self.four_color_tag,         self.rawconfig["four_color_rgb"])