from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from .parsers import ArtifactUpdate
from .run_model import DictListModel


class ArtifactModel(DictListModel):
    """Lightweight metadata index for artifacts mentioned by process output."""

    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(
            [], parent,
            role_names=[
                "name", "time", "size", "artifactType", "path", "stage",
                "timestamp", "exists", "sizeBytes", "source",
            ],
        )

    count = Property(int, lambda self: len(self._rows), notify=countChanged)

    @Slot(object)
    def applyEvent(self, event: object) -> None:
        if not isinstance(event, ArtifactUpdate) or not event.path:
            return
        path = Path(event.path).expanduser()
        exists = path.exists()
        size_bytes = path.stat().st_size if exists and path.is_file() else -1
        row = {
            "name": path.name or event.path,
            "time": event.timestamp.astimezone().strftime("%H:%M:%S"),
            "size": self._format_size(size_bytes),
            "artifactType": event.artifact_type,
            "path": event.path,
            "stage": event.stage,
            "timestamp": event.timestamp.isoformat(),
            "exists": exists,
            "sizeBytes": size_bytes,
            "source": event.source,
        }
        existing = next((index for index, item in enumerate(self._rows) if item["path"] == event.path), None)
        if existing is None:
            self.append_row(row)
        else:
            self.update_row(existing, row)
        self.countChanged.emit()

    @Slot()
    def clear(self) -> None:
        if self._rows:
            self.clear_rows()
            self.countChanged.emit()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 0:
            return "—"
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return "—"
