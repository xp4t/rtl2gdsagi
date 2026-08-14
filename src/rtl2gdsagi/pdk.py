"""The one PDK config object.

A single instance is built at run start and handed to every stage that needs
process data: synthesis (liberty for `abc`), sta (timing libs), all four
OpenLane stages, gdsout, and drc_lvs. Not just sta.

Path resolution follows the open_pdks/volare layout by default, but every
resolved path can be overridden explicitly in the run config, so a
non-SKY130 PDK with a different tree (e.g. a custom SCL process) is a config
change rather than a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import PDKError

DEFAULT_PDK_NAME = "sky130A"
DEFAULT_STD_CELL_LIB = "sky130_fd_sc_hd"
DEFAULT_CORNER = "tt_025C_1v80"

# Searched in order when no --pdk-root/config path is given.
_ROOT_CANDIDATES = (
    "~/.volare/{name}",
    "~/.ciel/{name}",
    "~/pdk/{name}",
    "/usr/local/share/pdk/{name}",
    "/opt/pdk/{name}",
)


@dataclass(frozen=True)
class PDKConfig:
    """Resolved process design kit.

    Attributes marked "override" default to None and are then derived from
    ``root`` using the open_pdks layout.
    """

    root: Path
    name: str = DEFAULT_PDK_NAME
    std_cell_lib: str = DEFAULT_STD_CELL_LIB
    corner: str = DEFAULT_CORNER

    # Explicit overrides.
    liberty: Path | None = None
    tech_lef: Path | None = None
    cell_lef: Path | None = None
    drc_deck: Path | None = None
    lvs_deck: Path | None = None
    netgen_setup: Path | None = None
    openlane_config: Path | None = None
    cell_verilog: Path | None = None
    # Filler/decap cell name prefixes used to fill row gaps. Overridable
    # because a cell that is legal on its own can still produce spacing
    # violations once the filler placer abuts it against its neighbours.
    filler_prefixes: tuple[str, ...] = ("fill", "decap")

    def __post_init__(self) -> None:
        # Accept str for root/overrides at construction; normalise to Path.
        # resolve(): PDK installs are commonly symlinks (volare/ciel keep a
        # versioned tree and link the current one). Rendered scripts and docker
        # bind-mounts must both use the real path or the container sees a
        # dangling link.
        object.__setattr__(self, "root", Path(self.root).expanduser().resolve())
        for name in (
            "liberty", "tech_lef", "cell_lef", "drc_deck", "lvs_deck",
            "netgen_setup", "openlane_config", "cell_verilog",
        ):
            v = getattr(self, name)
            if v is not None and not isinstance(v, Path):
                object.__setattr__(self, name, Path(v).expanduser())

    # ---- construction ----------------------------------------------------

    @classmethod
    def discover(
        cls,
        name: str = DEFAULT_PDK_NAME,
        root: str | os.PathLike[str] | None = None,
        **overrides: object,
    ) -> "PDKConfig":
        """Build a PDKConfig, locating ``root`` if not given.

        Order: explicit ``root`` > ``$PDK_ROOT/<name>`` > known install paths.
        """
        resolved: Path | None = None
        if root is not None:
            resolved = Path(root).expanduser()
            # Accept either .../sky130A or the parent containing it.
            if not (resolved / "libs.ref").is_dir() and (resolved / name / "libs.ref").is_dir():
                resolved = resolved / name
        else:
            env = os.environ.get("PDK_ROOT")
            if env:
                cand = Path(env).expanduser()
                resolved = cand / name if (cand / name).is_dir() else cand
            else:
                for tpl in _ROOT_CANDIDATES:
                    cand = Path(tpl.format(name=name)).expanduser()
                    if cand.is_dir():
                        resolved = cand
                        break

        if resolved is None:
            raise PDKError(
                f"could not locate PDK {name!r}. Pass --pdk-root, set $PDK_ROOT, "
                f"or install to one of: "
                + ", ".join(t.format(name=name) for t in _ROOT_CANDIDATES)
            )
        if not resolved.is_dir():
            raise PDKError(f"PDK root does not exist: {resolved}")

        clean = {k: (Path(v).expanduser() if v is not None else None)  # type: ignore[arg-type]
                 for k, v in overrides.items()}
        return cls(name=name, root=resolved, **clean)  # type: ignore[arg-type]

    # ---- derived paths ---------------------------------------------------

    @property
    def _ref(self) -> Path:
        return self.root / "libs.ref" / self.std_cell_lib

    @property
    def _tech(self) -> Path:
        return self.root / "libs.tech"

    @property
    def liberty_path(self) -> Path:
        if self.liberty is not None:
            return self.liberty
        return self._ref / "lib" / f"{self.std_cell_lib}__{self.corner}.lib"

    @property
    def tech_lef_path(self) -> Path:
        if self.tech_lef is not None:
            return self.tech_lef
        return self._ref / "techlef" / f"{self.std_cell_lib}__nom.tlef"

    @property
    def cell_lef_path(self) -> Path:
        if self.cell_lef is not None:
            return self.cell_lef
        return self._ref / "lef" / f"{self.std_cell_lib}.lef"

    @property
    def cell_verilog_path(self) -> Path:
        if self.cell_verilog is not None:
            return self.cell_verilog
        return self._ref / "verilog" / f"{self.std_cell_lib}.v"

    @property
    def drc_deck_path(self) -> Path:
        if self.drc_deck is not None:
            return self.drc_deck
        return self._tech / "klayout" / "drc" / f"{self.name}_mr.drc"

    @property
    def lvs_deck_path(self) -> Path:
        if self.lvs_deck is not None:
            return self.lvs_deck
        # sky130A and sky130B share one runset name.
        return self._tech / "klayout" / "lvs" / f"{self.name.rstrip('AB')}.lvs"

    @property
    def netgen_setup_path(self) -> Path:
        if self.netgen_setup is not None:
            return self.netgen_setup
        return self._tech / "netgen" / f"{self.name}_setup.tcl"

    @property
    def openlane_config_path(self) -> Path:
        if self.openlane_config is not None:
            return self.openlane_config
        return self._tech / "openlane" / "config.tcl"

    def liberty_for_corner(self, corner: str) -> Path:
        """Liberty for a named corner, e.g. ``ss_100C_1v60``.

        Falls back to the configured default corner rather than raising, so a
        signoff run listing a corner this PDK does not ship degrades to a
        single-corner analysis instead of failing to render at all. The caller
        sees the substitution because the rendered path differs.
        """
        cand = self._ref / "lib" / f"{self.std_cell_lib}__{corner}.lib"
        if cand.exists() or corner == self.corner:
            return cand
        return self.liberty_path

    def openrcx_rules(self, corner: str = "nom") -> Path:
        """OpenRCX extraction rules for a process corner."""
        if corner not in ("min", "nom", "max"):
            corner = "nom"
        return (
            self._tech / "openlane"
            / f"rules.openrcx.{self.name}.{corner}.spef_extractor"
        )

    def clock_buffers(self, limit: int = 6) -> list[str]:
        """Clock buffer cells, discovered from the cell LEF.

        Read from the PDK rather than hardcoded so a different process works
        without a code change. CTS refuses to run without an explicit buffer
        list (CTS-0055), so an empty result here is worth surfacing.
        """
        lef = self.cell_lef_path
        if not lef.is_file():
            return []
        names: list[str] = []
        for line in lef.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("MACRO ") and "clkbuf" in line:
                names.append(line.split(None, 1)[1].strip())
        # Prefer mid-strength drives; the extremes are rarely good CTS choices.
        names.sort(key=lambda n: (len(n), n))
        return names[:limit]

    def _macros_matching(self, needle: str) -> list[str]:
        lef = self.cell_lef_path
        if not lef.is_file():
            return []
        names = [
            line.split(None, 1)[1].strip()
            for line in lef.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip().startswith("MACRO ") and needle in line
        ]
        names.sort(key=lambda n: (len(n), n))
        return names

    def formal_cell_models(self) -> list[Path]:
        """Behavioural Verilog for the cells, for formal equivalence.

        Returned in dependency order (primitives first). These use Verilog UDPs
        and cannot be read by Yosys directly; they are fed through
        ``formal_pdk_proc.py`` first.
        """
        vdir = self._ref / "verilog"
        if not vdir.is_dir():
            return []
        prims = vdir / "primitives.v"
        cells = vdir / f"{self.std_cell_lib}.v"
        return [p for p in (prims, cells) if p.is_file()]

    def tap_cells(self) -> list[str]:
        """Well-tap cells. Without these the nwell has no tie-down and the
        layout fails nwell.* DRC even though placement and routing are clean."""
        return self._macros_matching("tapvpwrvgnd") or self._macros_matching("tap")

    @property
    def layer_map_path(self) -> Path:
        """LEF/DEF layer map: DEF layer names -> real GDS layer numbers.

        Without it KLayout invents sequential layer numbers for everything it
        reads from the DEF, so routing and pins land nowhere near the layers
        the DRC and LVS decks inspect.
        """
        return self._tech / "klayout" / "tech" / f"{self.name}.map"

    def mapped_layers(self) -> set[tuple[int, int]]:
        """Every (layer, datatype) the PDK's layer map names, of any purpose."""
        path = self.layer_map_path
        if not path.is_file():
            return set()
        out: set[tuple[int, int]] = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit():
                out.add((int(parts[-2]), int(parts[-1])))
        return out

    def routing_layers(self) -> set[tuple[int, int]]:
        """(layer, datatype) pairs the layer map assigns to routed nets.

        These are the ``NET``/``SPNET`` rows -- the layers a routed design must
        have geometry on. Checking for their *presence* is what catches a
        stream-out that ignored the layer map: cell-internal layers come from
        the cell GDS and are correct either way, so only the DEF-derived
        routing reveals the problem.

        Empty if the PDK ships no map, in which case the check is skipped
        rather than guessed at.
        """
        path = self.layer_map_path
        if not path.is_file():
            return set()
        out: set[tuple[int, int]] = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) < 4 or not (parts[-1].isdigit() and parts[-2].isdigit()):
                continue
            if "NET" in parts[1].upper():
                out.add((int(parts[-2]), int(parts[-1])))
        return out

    @property
    def cell_cdl_path(self) -> Path:
        """Cell-level SPICE (CDL). The LVS reference side is built from this.

        The PDK also ships ``spice/<lib>.spice``, describing the same cells
        with the same pin order, and it is **not** usable here. It writes
        transistors as subcircuit calls (``X0 VGND A Y VNB
        sky130_fd_pr__nfet_01v8 w=... l=...``), and KLayout's SPICE reader only
        turns those into devices if the deck's reader delegate declares them as
        such -- the SKY130 deck's does not. The cells come back with correct
        nets and pins and **no devices at all**, so every net mismatches in
        both directions and the report looks like a connectivity disaster.

        The CDL's ``M``-form cards do create real devices. Their model names
        need qualifying to match the deck's device classes -- see
        :attr:`device_model_prefix`.
        """
        return self._ref / "cdl" / f"{self.std_cell_lib}.cdl"

    @property
    def device_model_prefix(self) -> str:
        """Namespace the LVS deck gives its extracted device classes.

        The deck extracts into classes named for the primitive library
        (``extract_devices(mos4("sky130_fd_pr__nfet_01v8"), ...)``) while the
        CDL names the same transistor ``nfet_01v8``. Unqualified, no device
        matches anything and every cell fails to compare with its pins and
        topology looking perfectly correct.

        Discovered from the PDK's own primitive library directory rather than
        hardcoded, so it holds for processes that namespace theirs differently.
        Empty if there is no such library, in which case names are left alone.
        """
        for d in sorted((self.root / "libs.ref").glob("*_fd_pr")):
            if d.is_dir():
                return f"{d.name}__"
        return ""

    def filler_cells(self) -> list[str]:
        """Filler and decap cells, widest first.

        These fill the gaps left between placed cells in a row. Without them
        the nwell is a row of islands instead of a continuous strip, and the
        layout fails nwell minimum-width and minimum-spacing DRC even though
        placement and routing are perfectly legal.
        """
        cells: list[str] = []
        for prefix in self.filler_prefixes:
            cells += self._macros_matching(prefix)
        # Widest first: the placer fills large gaps before small ones.
        def width_key(name: str) -> int:
            tail = name.rsplit("_", 1)[-1]
            return -int(tail) if tail.isdigit() else 0
        return sorted(cells, key=width_key)

    def antenna_diodes(self) -> list[str]:
        """Antenna diode cells, discovered from the cell LEF."""
        lef = self.cell_lef_path
        if not lef.is_file():
            return []
        names = [
            line.split(None, 1)[1].strip()
            for line in lef.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip().startswith("MACRO ") and "diode" in line
        ]
        names.sort(key=lambda n: (len(n), n))
        return names

    def cell_gds(self) -> list[Path]:
        """Standard-cell GDS files that must be merged at streamout."""
        gds_dir = self._ref / "gds"
        if not gds_dir.is_dir():
            return []
        return sorted(gds_dir.glob("*.gds"))

    def timing_libs(self) -> list[Path]:
        """Every corner liberty available for the selected std cell library."""
        lib_dir = self._ref / "lib"
        if not lib_dir.is_dir():
            return []
        return sorted(lib_dir.glob(f"{self.std_cell_lib}__*.lib"))

    # ---- validation ------------------------------------------------------

    def missing(self, *, need: tuple[str, ...] = ()) -> list[str]:
        """Return human-readable descriptions of required paths that are absent.

        ``need`` names attributes to check; empty means the common core.
        """
        checks = need or ("liberty_path", "tech_lef_path", "cell_lef_path")
        out: list[str] = []
        for attr in checks:
            p = getattr(self, attr)
            if not Path(p).exists():
                out.append(f"{attr}={p}")
        return out

    def validate(self, *, need: tuple[str, ...] = ()) -> None:
        gone = self.missing(need=need)
        if gone:
            raise PDKError(
                f"PDK {self.name} at {self.root} is missing required files: " + "; ".join(gone)
            )

    # ---- prompt context --------------------------------------------------

    def prompt_context(self) -> dict[str, object]:
        """Compact, factual PDK description injected into config-generation prompts.

        Only paths that exist are marked available, so the model is never told
        to reference a file that is not on disk.
        """

        def entry(p: Path) -> dict[str, object]:
            return {"path": str(p), "exists": Path(p).exists()}

        return {
            "pdk_name": self.name,
            "pdk_root": str(self.root),
            "std_cell_library": self.std_cell_lib,
            "timing_corner": self.corner,
            "liberty": entry(self.liberty_path),
            "tech_lef": entry(self.tech_lef_path),
            "cell_lef": entry(self.cell_lef_path),
            "cell_verilog": entry(self.cell_verilog_path),
            "klayout_drc_deck": entry(self.drc_deck_path),
            "klayout_lvs_deck": entry(self.lvs_deck_path),
            "netgen_setup": entry(self.netgen_setup_path),
            "openlane_pdk_config": entry(self.openlane_config_path),
            "available_corners": [p.stem.split("__", 1)[-1] for p in self.timing_libs()],
        }

    def to_dict(self) -> dict[str, object]:
        """Serialisable form recorded in run_state.json."""
        return {
            "name": self.name,
            "root": str(self.root),
            "std_cell_lib": self.std_cell_lib,
            "corner": self.corner,
        }
