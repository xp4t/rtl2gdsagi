from PySide6.QtCore import QModelIndex, Property, QTime, Signal, Slot

from .run_model import DictListModel


class LogModel(DictListModel):
    countChanged = Signal()

    def __init__(self, parent=None, max_rows: int = 5000):
        super().__init__(
            [],
            parent,
            role_names=["time", "level", "scope", "message"],
        )
        self._max_rows = max_rows

    count = Property(int, lambda self: len(self._rows), notify=countChanged)

    @Slot(str, str, str)
    def appendProcessOutput(self, stream: str, stage: str, message: str) -> None:
        if not message:
            return
        scope = stage.upper().replace(" ", "_") if stage else "FLOW"
        self.append_row({
            "time": QTime.currentTime().toString("HH:mm:ss"),
            "level": "ERROR" if stream == "stderr" else "INFO",
            "scope": scope,
            "message": message,
        })
        if len(self._rows) > self._max_rows:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self._rows.pop(0)
            self.endRemoveRows()
        self.countChanged.emit()

    @Slot()
    def clear(self) -> None:
        if self._rows:
            self.clear_rows()
            self.countChanged.emit()
