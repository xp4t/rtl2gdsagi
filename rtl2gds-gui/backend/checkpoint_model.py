from .run_model import DictListModel


class CheckpointModel(DictListModel):
    def __init__(self, parent=None):
        super().__init__([
            {"stage": "Floorplan", "timestamp": "May 21 16:51:03", "size": "142 MB", "health": "Healthy"},
            {"stage": "Power Plan & TAP", "timestamp": "May 21 16:53:22", "size": "186 MB", "health": "Healthy"},
            {"stage": "Place", "timestamp": "May 21 16:55:47", "size": "512 MB", "health": "Healthy"},
            {"stage": "CTS", "timestamp": "May 21 16:56:38", "size": "98 MB", "health": "Healthy"},
            {"stage": "Post-CTS STA", "timestamp": "May 21 16:56:55", "size": "64 MB", "health": "Healthy"},
            {"stage": "Route (failed)", "timestamp": "May 21 16:57:22", "size": "1.2 GB", "health": "Recoverable"},
        ], parent)
