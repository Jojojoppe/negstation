import numpy as np

from .event_bus import EventBus


class ImagePipeline:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.stages = []
        self.stagedata = {}

    def register_stage(self, name: str):
        self.stages.append(name)
        self.stagedata[name] = None
        self.bus.publish_deferred("pipeline_stages", self.stages)
        return len(self.stages) - 1

    def rename_stage(self, id: int, name: str):
        if id >= 0 and id < len(self.stages):
            self.stages[id] = name
            self.bus.publish_deferred("pipeline_stages", self.stages)

    def publish(self, id: int, img: np.ndarray):
        self.stagedata[id] = img.astype(np.float32)
        self.bus.publish_deferred("pipeline_stage", (id, self.stagedata[id]))

    def get_stage_data(self, id: int):
        if id >= 0 and id < len(self.stages):
            return self.stagedata[id]
        else:
            return None

    def get_stage_name(self, id:int):
        if id >= 0 and id < len(self.stages):
            return self.stages[id] 
        else:
            return None
        
    def republish_stages(self):
        self.bus.publish_deferred("pipeline_stages", self.stages)