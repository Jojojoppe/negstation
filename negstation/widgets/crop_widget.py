import dearpygui.dearpygui as dpg
import numpy as np
from .stage_viewer_widget import PipelineStageViewer


class CropWidget(PipelineStageViewer):
    name = "Crop Image"
    register = True
    has_pipeline_in = True
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger)
        self.crop_start = None  # (x, y)
        self.crop_end = None    # (x, y)
        self.crop_active = False

        self.manager.bus.subscribe("img_clicked", self.on_click)
        self.manager.bus.subscribe("img_dragged", self.on_drag)

    def create_pipeline_stage_content(self):
        super().create_pipeline_stage_content()

    # def on_full_res_pipeline_data(self, img):
        # pass

    def on_pipeline_data(self, img):
        if img is None:
            return
        self.img = img

        if self.crop_start and self.crop_end:
            x0, y0 = self.crop_start
            x1, y1 = self.crop_end
            x0, x1 = sorted((int(x0), int(x1)))
            y0, y1 = sorted((int(y0), int(y1)))

            x0 = max(0, min(x0, img.shape[1]-1))
            x1 = max(0, min(x1, img.shape[1]-1))
            y0 = max(0, min(y0, img.shape[0]-1))
            y1 = max(0, min(y1, img.shape[0]-1))

            cropped = img[y0:y1, x0:x1, :]
            self.publish_stage(cropped)
        else:
            self.publish_stage(img)

        self.needs_update = True

    def on_click(self, data):
        if data["obj"] is not self:
            return
        if data["button"] == "left":
            self.crop_start = data["pos"]
            self.crop_end = data["pos"]
            self.crop_active = True
            self.needs_update = True

    def on_drag(self, data):
        if data["obj"] is not self or not self.crop_active:
            return
        self.crop_end = data["pos"]
        self.needs_update = True

    def update_texture(self, img):
        super().update_texture(img)
        if self.crop_start and self.crop_end:
            # map image coords back to screen coords
            x0, y0 = self.crop_start
            x1, y1 = self.crop_end
            h, w, _ = self.img.shape
            img_x, img_y = self.image_position
            img_w, img_h = self.scaled_size

            p0 = (
                img_x + x0 / w * img_w,
                img_y + y0 / h * img_h
            )
            p1 = (
                img_x + x1 / w * img_w,
                img_y + y1 / h * img_h
            )

            dpg.draw_rectangle(pmin=p0, pmax=p1, color=(255, 255, 0, 255),
                            fill=(255, 255, 0, 50), thickness=2, parent=self.drawlist)
