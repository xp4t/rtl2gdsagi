from .run_model import DictListModel


class PipelineModel(DictListModel):
    def __init__(self, parent=None):
        self._approved_names = [
            ("IMPORT\nRTL", "pass"), ("ELABORATE\nDESIGN", "pass"),
            ("SYNTHESIS\nLOGIC", "pass"), ("STA\nPRE-CTS", "pass"),
            ("FLOORPLAN", "pass"), ("POWER PLAN\n& TAP", "pass"),
            ("PLACE", "active"), ("CTS", "pending"),
            ("POST-CTS\nSTA", "review"), ("ROUTE", "pending"),
            ("SIGNOFF\nSTA", "pending"), ("DRC", "pending"),
            ("LVS", "pending"), ("GDS\nPACKAGING", "pending"),
        ]
        super().__init__([
            {"number": index + 1, "name": name, "status": status}
            for index, (name, status) in enumerate(self._approved_names)
        ], parent)

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = "".join(character for character in value.lower() if character.isalnum())
        return {"placement": "place", "routing": "route"}.get(normalized, normalized)

    def apply_execution(self, stage: str, status: str, stage_number: int = 0) -> None:
        if 1 <= stage_number <= len(self._rows):
            stage_index = stage_number - 1
        else:
            stage_index = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if self._normalize(row["name"]) == self._normalize(stage)
                ),
                -1,
            )
        for index in range(len(self._rows)):
            if stage_index < 0:
                value = "pending"
            elif index < stage_index:
                value = "pass"
            elif index > stage_index:
                value = "pending"
            elif status == "Completed":
                value = "pass"
            elif status == "Failed":
                value = "fail"
            elif status == "Cancelled":
                value = "review"
            else:
                value = "active"
            if self._rows[index]["status"] != value:
                self.update_row(index, {"status": value})

    def apply_context(self, route: str) -> None:
        if route == "activeRun":
            return
        for index, (_, status) in enumerate(self._approved_names):
            if self._rows[index]["status"] != status:
                self.update_row(index, {"status": status})
