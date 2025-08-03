import dearpygui.dearpygui as dpg
import numpy as np
from .pipeline_stage_widget import PipelineStageWidget


class PipelineStageViewer(PipelineStageWidget):
    name = "View Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = False

    def __init__(self, manager, logger):
        super().__init__(manager, logger, default_stage_in="pipeline_out")
        self.texture_tag = dpg.generate_uuid()
        self.drawlist = None
        self.img = None
        self.registry = manager.texture_registry
        self.needs_update = False
        self.canvas_handler = None
        self.scaled_size = (0, 0)
        self.image_position = (0, 0)

        self.manager.bus.subscribe("mouse_dragged", self._on_mouse_drag, False)

    def create_pipeline_stage_content(self):
        # Create an empty dynamic texture
        dpg.add_dynamic_texture(
            1, 1, [0, 0, 0, 0], tag=self.texture_tag, parent=self.registry
        )

        # Add drawlist
        with dpg.drawlist(width=-1, height=-1) as self.drawlist:
            pass

        # Register click handler
        with dpg.item_handler_registry() as self.canvas_handler:
            dpg.add_item_clicked_handler(callback=self.on_canvas_click)
        dpg.bind_item_handler_registry(self.drawlist, self.canvas_handler)

    def on_canvas_click(self, sender, app_data, user_data):
        mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
        canvas_x, canvas_y = dpg.get_item_rect_min(self.drawlist)
        local_x = mouse_x - canvas_x
        local_y = mouse_y - canvas_y

        img_x, img_y = self.image_position
        img_w, img_h = self.scaled_size

        if (
            local_x >= img_x
            and local_x < img_x + img_w
            and local_y >= img_y
            and local_y < img_y + img_h
        ):
            # calculate the image coordinate
            x = int((local_x - img_x) * self.img.shape[1] / img_w)
            y = int((local_y - img_y) * self.img.shape[0] / img_h)
            self.manager.bus.publish_deferred(
                "img_clicked",
                {
                    "stage_id": self.pipeline_stage_in_id,
                    "pos": (x, y),
                    "button": (
                        "right"
                        if app_data[0] == 0
                        else ("left" if app_data[0] == 1 else ("middle"))
                    ),
                },
            )

    def _on_mouse_drag(self, data):
        mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
        canvas_x, canvas_y = dpg.get_item_rect_min(self.drawlist)
        local_x = mouse_x - canvas_x
        local_y = mouse_y - canvas_y

        img_x, img_y = self.image_position
        img_w, img_h = self.scaled_size

        if (
            local_x >= img_x
            and local_x < img_x + img_w
            and local_y >= img_y
            and local_y < img_y + img_h
        ):
            # calculate the image coordinate
            x = int((local_x - img_x) * self.img.shape[1] / img_w)
            y = int((local_y - img_y) * self.img.shape[0] / img_h)
            self.manager.bus.publish_deferred(
                "img_dragged",
                {
                    "stage_id": self.pipeline_stage_in_id,
                    "pos": (x, y),
                    "button": data['button'],
                    "delta": data['delta']
                },
            )

    def on_resize(self, width, height):
        self.needs_update = True

    def on_pipeline_data(self, img):
        if img is None:
            return
        self.img = img
        self.needs_update = True

    def on_full_res_pipeline_data(self, img):
        pass

    def update_texture(self, img: np.ndarray):
        if img is None:
            return

        h, w, _ = img.shape
        flat = img.flatten().tolist()

        # Replace texture
        if dpg.does_item_exist(self.texture_tag):
            dpg.delete_item(self.texture_tag)
        dpg.add_dynamic_texture(
            width=w,
            height=h,
            default_value=flat,
            tag=self.texture_tag,
            parent=self.registry,
        )

        win_w, win_h = self.window_width, self.window_height
        scale = min(win_w / w, win_h / h)
        disp_w = int(w * scale)
        disp_h = int(h * scale)

        x_off = (win_w - disp_w) / 2
        y_off = (win_h - disp_h) / 2

        self.scaled_size = (disp_w, disp_h)
        self.image_position = (x_off, y_off)

        # Clear old drawings
        dpg.delete_item(self.drawlist, children_only=True)

        # Draw image
        dpg.draw_image(
            self.texture_tag,
            pmin=(x_off, y_off),
            pmax=(x_off + disp_w, y_off + disp_h),
            uv_min=(0, 0),
            uv_max=(1, 1),
            parent=self.drawlist,
        )

        # Resize drawlist
        dpg.configure_item(self.drawlist, width=win_w, height=win_h)

    def update(self):
        if self.needs_update:
            self.needs_update = False
            self.update_texture(self.img)
