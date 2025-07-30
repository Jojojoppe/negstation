import numpy as np

from .event_bus import EventBus


class ImagePipeline:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.stages = {}

    def add_stage(self, name: str, img: np.ndarray):
        self.stages[name] = img.astype(np.float32)
        # notify widgets of updated stage list and data
        self.bus.publish_deferred("pipeline_stages", list(self.stages.keys()))
        self.bus.publish_deferred("pipeline_stage", (name, self.stages[name]))

    def get_stage(self, name: str):
        return self.stages.get(name)
