from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QByteArray, QAbstractListModel, QModelIndex, QObject, Property, Signal, Qt


class DictListModel(QAbstractListModel):
    """Small dictionary-backed list model shared by static and live data."""

    def __init__(
        self,
        rows: list[dict] | None = None,
        parent: QObject | None = None,
        *,
        role_names: list[str] | None = None,
    ):
        super().__init__(parent)
        self._rows = rows or []
        keys = role_names or (list(self._rows[0].keys()) if self._rows else [])
        self._roles = {Qt.UserRole + index + 1: key for index, key in enumerate(keys)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        key = self._roles.get(role)
        return self._rows[index.row()].get(key) if key else None

    def roleNames(self):
        return {role: QByteArray(key.encode()) for role, key in self._roles.items()}

    def append_row(self, row: dict) -> None:
        unknown = set(row) - set(self._roles.values())
        if unknown:
            raise ValueError(f"Unknown model roles: {', '.join(sorted(unknown))}")
        index = len(self._rows)
        self.beginInsertRows(QModelIndex(), index, index)
        self._rows.append({key: row.get(key) for key in self._roles.values()})
        self.endInsertRows()

    def clear_rows(self) -> None:
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def update_row(self, row_index: int, values: dict) -> None:
        if not 0 <= row_index < len(self._rows):
            raise IndexError(row_index)
        unknown = set(values) - set(self._roles.values())
        if unknown:
            raise ValueError(f"Unknown model roles: {', '.join(sorted(unknown))}")
        changed_roles = [role for role, name in self._roles.items() if name in values]
        if not changed_roles:
            return
        self._rows[row_index].update(values)
        model_index = self.index(row_index, 0)
        self.dataChanged.emit(model_index, model_index, changed_roles)

    def replace_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = [
            {key: row.get(key) for key in self._roles.values()}
            for row in rows
        ]
        self.endResetModel()

    def rows_snapshot(self) -> list[dict]:
        """Return detached plain data suitable for non-Qt services."""

        return deepcopy(self._rows)


class RunState(QObject):
    changed = Signal()
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._base_values = {
            "project": "chipcore_cpu",
            "top_module": "chipcore_top",
            "branch_commit": "main / a1b2c3d",
            "run_id": "run_042",
        }
        self._execution_values = {
            "run_id": "run_042",
            "status": "Idle",
            "status_tone": "neutral",
            "elapsed": "00:00:00",
            "remaining": "—",
            "started": "—",
        }
        self._values = {**self._base_values, **self._execution_values}

    project = Property(str, lambda self: self._values["project"], notify=changed)
    topModule = Property(str, lambda self: self._values["top_module"], notify=changed)
    branchCommit = Property(str, lambda self: self._values["branch_commit"], notify=changed)
    runId = Property(str, lambda self: self._values["run_id"], notify=changed)
    status = Property(str, lambda self: self._values["status"], notify=changed)
    statusTone = Property(str, lambda self: self._values["status_tone"], notify=changed)
    elapsed = Property(str, lambda self: self._values["elapsed"], notify=changed)
    remaining = Property(str, lambda self: self._values["remaining"], notify=changed)
    started = Property(str, lambda self: self._values["started"], notify=changed)

    def apply_context(self, route: str) -> None:
        contexts = {
            "newRun": {"run_id": "—", "status": "—", "status_tone": "neutral", "elapsed": "—", "remaining": "—", "started": "—"},
            "checkpointRecovery": {"run_id": "run_041", "status": "Completed with issues", "status_tone": "review", "elapsed": "00:58:33", "remaining": "—", "started": "May 21 16:48:10"},
            "humanReview": {"run_id": "run_042", "status": "Escalated", "status_tone": "review", "elapsed": "00:38:54", "remaining": "00:13:21", "started": "May 22 08:11:03"},
            "strategySweep": {"run_id": "sweep_007", "status": "Completed", "status_tone": "pass", "elapsed": "03:16:29", "remaining": "—", "started": "May 22 05:12:41"},
            "retuneReview": {"run_id": "run_042", "status": "Running", "status_tone": "pass", "elapsed": "02:58:41", "remaining": "00:02:31", "started": "May 22 08:11:03"},
        }
        values = self._execution_values if route == "activeRun" else contexts.get(route, self._execution_values)
        self._values = {**self._base_values, **values}
        self.changed.emit()

    def apply_execution(
        self,
        *,
        status: str,
        status_tone: str,
        elapsed: str,
        started: str,
    ) -> None:
        self._execution_values.update({
            "status": status,
            "status_tone": status_tone,
            "elapsed": elapsed,
            "remaining": "—",
            "started": started,
        })
        self._values = {**self._base_values, **self._execution_values}
        self.changed.emit()

    def execution_snapshot(self) -> dict:
        return {**self._base_values, **self._execution_values}


class RunModel(DictListModel):
    def __init__(self, parent=None):
        rows = [
            ("run_039", "BASELINE", "Baseline implementation", "a1b2c3d", "May 21 09:14:22", "01:42:18", "Completed", "GDS Packaging", "+0.092", "-1.324", "12.38M", "125.7", "68.7%", "live"),
            ("run_040", "EXPERIMENT", "Low-power experiment", "d4e5f6a", "May 21 13:07:55", "01:35:42", "Completed", "GDS Packaging", "-0.015", "-3.842", "12.28M", "108.3", "66.1%", "review"),
            ("run_041", "RECOVERY", "Route recovery", "e7f8g9h", "May 21 16:48:10", "00:58:33", "Completed with issues", "Route", "+0.018", "-0.642", "12.41M", "122.1", "71.3%", "purple"),
            ("run_042", "CURRENT", "Current implementation", "a1b2c3d", "May 22 08:11:03", "02:47:16", "Running", "Power Plan & TAP", "—", "—", "—", "—", "—", "pass"),
        ]
        super().__init__([{
            "runId": a, "kind": b, "description": c, "commit": d, "started": e,
            "duration": f, "status": g, "terminal": h, "wns": i, "tns": j,
            "area": k, "power": l, "density": m, "tone": n,
        } for a, b, c, d, e, f, g, h, i, j, k, l, m, n in rows], parent)
