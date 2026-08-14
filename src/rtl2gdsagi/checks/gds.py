"""Minimal GDSII structure reader -- no external dependencies.

Only the record layer is decoded: structure names, element counts and the
reference graph. That is enough to answer the questions ``gdsout`` must answer
before ``drc_lvs`` is allowed to run:

* Was exactly one GDS written, and does it contain the expected top cell?
* Is that top cell non-empty?
* **Does every referenced cell actually exist inside this file?**

The last one matters most. A pre-merge layout references standard cells that
live in the PDK GDS rather than in the file itself, so its SREF/AREF names
dangle. A properly merged stream-out resolves them all. Detecting dangling
references is therefore a direct structural test for "this is not the final
merged GDS" -- which is exactly the condition that let a clean-looking DRC run
check pre-merge macros and hide thousands of real violations.

GDSII layout: a flat sequence of records, each
``[uint16 length][uint8 record type][uint8 data type][payload]``, length
inclusive of the 4-byte header.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Record types we care about.
_HEADER = 0x00
_BGNLIB = 0x01
_LIBNAME = 0x02
_UNITS = 0x03
_ENDLIB = 0x04
_BGNSTR = 0x05
_STRNAME = 0x06
_ENDSTR = 0x07
_BOUNDARY = 0x08
_PATH = 0x09
_SREF = 0x0A
_AREF = 0x0B
_TEXT = 0x0C
_LAYER = 0x0D
_DATATYPE = 0x0E
_SNAME = 0x12

_ELEMENT_TYPES = {_BOUNDARY, _PATH, _SREF, _AREF, _TEXT}


class GDSError(Exception):
    """The file is not parseable as GDSII."""


@dataclass
class GDSCell:
    name: str
    elements: int = 0
    #: Names this cell instantiates, with instance counts.
    references: dict[str, int] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return self.elements == 0


@dataclass
class GDSInfo:
    path: Path
    libname: str
    cells: dict[str, GDSCell]
    #: Names referenced by some cell but not defined in this file.
    unresolved_references: dict[str, int]
    total_elements: int
    #: (layer, datatype) -> shape count, across the whole file.
    layers: dict[tuple[int, int], int] = field(default_factory=dict)

    def cell(self, name: str) -> GDSCell | None:
        return self.cells.get(name)

    def root_cells(self) -> list[str]:
        """Cells nobody references -- the candidate top cells."""
        referenced = {n for c in self.cells.values() for n in c.references}
        return sorted(n for n in self.cells if n not in referenced)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "libname": self.libname,
            "cell_count": len(self.cells),
            "total_elements": self.total_elements,
            "layers": {f"{l}/{d}": n for (l, d), n in sorted(self.layers.items())},
            "root_cells": self.root_cells(),
            "unresolved_references": dict(
                sorted(self.unresolved_references.items(), key=lambda kv: -kv[1])
            ),
        }


def read_gds(path: str | Path) -> GDSInfo:
    """Scan a GDSII file's record stream.

    Raises :class:`GDSError` for a missing, empty, truncated or non-GDS file.
    """
    p = Path(path)
    if not p.is_file():
        raise GDSError(f"GDS file does not exist: {p}")
    data = p.read_bytes()
    if not data:
        raise GDSError(f"GDS file is empty: {p}")

    cells: dict[str, GDSCell] = {}
    libname = ""
    current: GDSCell | None = None
    pending_ref: str | None = None
    pending_layer: int | None = None
    layer_counts: dict[tuple[int, int], int] = {}
    total_elements = 0
    saw_header = False
    saw_endlib = False

    pos, size = 0, len(data)
    while pos + 4 <= size:
        (length, rectype, _datatype) = struct.unpack_from(">HBB", data, pos)
        if length < 4:
            raise GDSError(
                f"{p.name}: invalid record length {length} at byte {pos}; file is corrupt"
            )
        if pos + length > size:
            raise GDSError(
                f"{p.name}: record at byte {pos} runs past end of file "
                f"(needs {length}, has {size - pos}); file is truncated"
            )
        payload = data[pos + 4 : pos + length]

        if rectype == _HEADER:
            saw_header = True
        elif rectype == _LIBNAME:
            libname = _ascii(payload)
        elif rectype == _BGNSTR:
            current = None
        elif rectype == _STRNAME:
            name = _ascii(payload)
            current = cells.setdefault(name, GDSCell(name=name))
        elif rectype == _ENDSTR:
            current = None
        elif rectype in _ELEMENT_TYPES:
            total_elements += 1
            if current is not None:
                current.elements += 1
            pending_ref = None if rectype not in (_SREF, _AREF) else ""
            pending_layer = None
        elif rectype == _LAYER and len(payload) >= 2:
            pending_layer = struct.unpack(">h", payload[:2])[0]
        elif rectype == _DATATYPE and len(payload) >= 2 and pending_layer is not None:
            key = (pending_layer, struct.unpack(">h", payload[:2])[0])
            layer_counts[key] = layer_counts.get(key, 0) + 1
            pending_layer = None
        elif rectype == _SNAME:
            if pending_ref is not None and current is not None:
                ref = _ascii(payload)
                current.references[ref] = current.references.get(ref, 0) + 1
                pending_ref = None
        elif rectype == _ENDLIB:
            saw_endlib = True

        pos += length

    if not saw_header:
        raise GDSError(f"{p.name}: no GDSII HEADER record; this is not a GDS file")
    if not saw_endlib:
        raise GDSError(f"{p.name}: no ENDLIB record; the stream-out did not finish")
    if not cells:
        raise GDSError(f"{p.name}: contains no structures")

    unresolved: dict[str, int] = {}
    for c in cells.values():
        for ref, n in c.references.items():
            if ref not in cells:
                unresolved[ref] = unresolved.get(ref, 0) + n

    return GDSInfo(
        path=p,
        libname=libname,
        cells=cells,
        unresolved_references=unresolved,
        total_elements=total_elements,
        layers=layer_counts,
    )


def _ascii(payload: bytes) -> str:
    return payload.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
