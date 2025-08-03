import numpy as np

from .event_bus import EventBus


class ImagePipeline:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.id_counter = 0
        self.stages = {}
        self.stagedata = {}
        self.stagedata_full = {}

    def load_stages(self, stages:dict):
        self.stages = stages
        self.stagedata.clear()
        self.stagedata_full.clear()
        self.id_counter = len(stages)
        for id, stage in self.stages.items():
            print(id, stage)
            self.stagedata[id] = None
            self.stagedata_full[id] = None

    def register_stage(self, name: str):
        self.stages[self.id_counter] = name
        self.stagedata[self.id_counter] = None
        self.stagedata_full[self.id_counter] = None
        self.bus.publish_deferred("pipeline_stages", self.stages)
        self.id_counter += 1
        return self.id_counter-1

    def rename_stage(self, id: int, name: str):
        if id in self.stages:
            self.stages[id] = name
            self.bus.publish_deferred("pipeline_stages", self.stages)

    def publish(self, id: int, img: np.ndarray, full_res=False):
        if img is None:
            return
        if full_res:
            self.stagedata_full[id] = img.astype(np.float32)
            self.bus.publish_deferred(
                "pipeline_stage_full", (id, self.stagedata_full[id]))
        else:
            self.stagedata[id] = img.astype(np.float32)
            self.bus.publish_deferred(
                "pipeline_stage", (id, self.stagedata[id]))

    def get_stage_data(self, id: int):
        if id in self.stagedata:
            return self.stagedata[id]
        else:
            return None
        
    def get_stage_data_full(self, id: int):
        if id in self.stagedata_full:
            return self.stagedata_full[id]
        else:
            return None

    def get_stage_name(self, id: int):
        if id in self.stages:
            return self.stages[id]
        else:
            return None

    def republish_stages(self):
        self.bus.publish_deferred("pipeline_stages", self.stages)

    def remove_stage(self, id: int):
        del self.stages[id]
        del self.stagedata[id]
        self.republish_stages()
