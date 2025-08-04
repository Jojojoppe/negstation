import dearpygui.dearpygui as dpg
import numpy as np
import time
from scipy.ndimage import rotate

from .stage_viewer_widget import PipelineStageViewer


class FramingWidget(PipelineStageViewer):
    name = "Framing"
    register = True
    has_pipeline_in = True
    has_pipeline_out = True

    def __init__(self, manager, logger):
        super().__init__(manager, logger)

        # Rotation line endpoints (canvas coords)
        self.rot_start = None   # (x, y)
        self.rot_end = None     # (x, y)
        self.angle = 0.0        # computed deskew angle

        # Throttle publishing to a few Hz
        self._last_pub_time = 0.0
        self._publish_interval = 0.5  # seconds

        self.manager.bus.subscribe("img_clicked", self.on_click)
        self.manager.bus.subscribe("img_dragged", self.on_drag)
        self.manager.bus.subscribe("img_scrolled", self.on_scroll)

    def create_pipeline_stage_content(self):
        super().create_pipeline_stage_content()

    def on_pipeline_data(self, img):
        if img is None:
            return
        self.img = img.copy()
        self._publish_rotated_and_cropped()
        self.needs_update = True

    def update_texture(self, img):
        super().update_texture(img)
        # Draw rotation guide if active
        if self.rot_start and self.rot_end:
            p0 = self._pos_to_canvas(self.rot_start)
            p1 = self._pos_to_canvas(self.rot_end)
            dpg.draw_line(p1=p0, p2=p1, color=(
                255, 255, 0, 255), thickness=2, parent=self.drawlist)

    def on_click(self, data):
        if data.get("obj") is not self:
            return
        x, y = data.get("pos")
        button = data.get("button")
        if button == "right":
            self.rot_start = (x, y)
            self.rot_end = (x, y)
        self.needs_update = True

    def on_drag(self, data):
        if data.get("obj") is not self:
            return
        x, y = data.get("pos")
        button = data.get("button")
        if button == "right":
            self.rot_end = (x, y)
        # Update angle on rotation drag
        if self.rot_start and self.rot_end:
            dx = self.rot_end[0] - self.rot_start[0]
            dy = self.rot_end[1] - self.rot_start[1]
            self.angle = np.degrees(np.arctan2(dy, dx))
        # Throttle publishes
        now = time.time()
        if now - self._last_pub_time >= self._publish_interval:
            self._publish_rotated_and_cropped()
            self._last_pub_time = now
        self.needs_update = True

    def on_scroll(self, data):
        print(data)

    def _publish_rotated_and_cropped(self):
        w, h, _ = self.img.shape
        out = self.rotate_and_crop(self.img, self.angle, (0, 0, w, h))
        self.publish_stage(out)

    def _pos_to_canvas(self, img_pos):
        x, y = img_pos
        ix, iy = self.image_position
        iw, ih = self.img.shape[1], self.img.shape[0]
        sw, sh = self.scaled_size
        return (ix + x / iw * sw, iy + y / ih * sh)

    def rotate_and_crop(
        self,
        img: np.ndarray,
        angle: float,
        rect: tuple[int, int, int, int],
        cval: float = 0.0
    ) -> np.ndarray:
        h, w = img.shape[:2]
        x, y, cw, ch = rect
        rotated = np.empty_like(img)
        for c in range(img.shape[2]):
            rotated[..., c] = rotate(
                img[..., c],
                angle,
                reshape=False,
                order=1,              # bilinear interpolation
                mode='constant',
                cval=cval,
                prefilter=False
            )
        x0 = max(0, min(int(x), w - 1))
        y0 = max(0, min(int(y), h - 1))
        x1 = max(0, min(int(x + cw), w))
        y1 = max(0, min(int(y + ch), h))
        return rotated[y0:y1, x0:x1]
