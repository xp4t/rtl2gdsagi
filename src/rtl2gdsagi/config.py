"""Run configuration: CLI args + config file + env, merged.

Precedence, highest first: explicit CLI flag > config file > environment >
built-in default.

Per-stage overrides live under ``stages:`` in the config file and currently
cover the retry limit and the parallel fix-candidate count, e.g.::

    retry_limit: 3
    stages:
      routing:
        retry_limit: 5      # slow and flaky, allow more attempts
      drc_lvs:
        retry_limit: 1      # violations are real; don't let it churn
        fix_candidates: 1
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .pdk import PDKConfig
from .stages import STAGE_ORDER, StageId, parse_stage

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_RETRY_LIMIT = 3
DEFAULT_FIX_CANDIDATES = 3
DEFAULT_RUN_ROOT = Path("runs")
REPAIR_POLICIES = frozenset({"ask", "auto", "manual"})
KLAYOUT_BACKENDS = frozenset({"native", "native_isolated", "container"})

#: Env var holding the API key. Never read into a config field, never logged.
API_KEY_ENV = "ANTHROPIC_API_KEY"
#: Env var overriding the model string.
MODEL_ENV = "RTL2GDSAGI_MODEL"

_PDK_OVERRIDE_KEYS = (
    "liberty", "tech_lef", "cell_lef", "drc_deck", "lvs_deck",
    "netgen_setup", "openlane_config", "cell_verilog",
)


@dataclass(frozen=True)
class StageOverrides:
    retry_limit: int | None = None
    fix_candidates: int | None = None
    timeout_s: int | None = None


@dataclass(frozen=True)
class RunConfig:
    """Everything one pipeline run needs, fully resolved."""

    rtl_dir: Path
    top: str
    pdk: PDKConfig

    retry_limit: int = DEFAULT_RETRY_LIMIT
    fix_candidates: int = DEFAULT_FIX_CANDIDATES
    timeout_s: int = 3600
    model: str = DEFAULT_MODEL
    run_root: Path = DEFAULT_RUN_ROOT
    resume_from: StageId | None = None
    stage_overrides: dict[StageId, StageOverrides] = field(default_factory=dict)

    #: When true the runner uses the mock tool invoker and mock agent. Phase-1
    #: development and the whole test suite run this way.
    mock_tools: bool = False
    #: Starting IR values from the config file's ``ir:`` section, e.g.
    #: ``{"floorplan": {"core_utilization": 0.35}}``. Applied after the
    #: characterization-derived defaults, so what the user writes wins.
    ir_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Stages the user explicitly asked to skip. Recorded in the signoff
    #: bundle, and a skipped signoff gate always fails signoff -- this is for
    #: measuring the rest of the flow, never for getting a clean result.
    skip_stages: frozenset[StageId] = frozenset()
    #: Known repairs ask in a TTY, execute directly in auto mode, and stop in
    #: manual mode.  ``ask`` resolves to manual when stdin is not a TTY.
    repair_policy: str = "ask"
    klayout_backend: str = "native"

    def __post_init__(self) -> None:
        # Absolute, because tools are invoked with cwd set to a stage
        # directory: a relative path from the config file would not resolve.
        object.__setattr__(self, "rtl_dir", Path(self.rtl_dir).expanduser().resolve())
        object.__setattr__(self, "run_root", Path(self.run_root).expanduser().resolve())
        if self.retry_limit < 1:
            raise ConfigError(f"retry_limit must be >= 1, got {self.retry_limit}")
        if self.fix_candidates < 1:
            raise ConfigError(f"fix_candidates must be >= 1, got {self.fix_candidates}")
        if not self.top:
            raise ConfigError("top module name is required")
        if self.repair_policy not in REPAIR_POLICIES:
            raise ConfigError(f"repair_policy must be one of {sorted(REPAIR_POLICIES)}")
        if self.klayout_backend not in KLAYOUT_BACKENDS:
            raise ConfigError(f"klayout_backend must be one of {sorted(KLAYOUT_BACKENDS)}")

    # ---- per-stage resolution -------------------------------------------

    def retry_limit_for(self, stage: StageId | str) -> int:
        return self._resolve(stage, "retry_limit", self.retry_limit)

    def fix_candidates_for(self, stage: StageId | str) -> int:
        return self._resolve(stage, "fix_candidates", self.fix_candidates)

    def timeout_for(self, stage: StageId | str) -> int:
        return self._resolve(stage, "timeout_s", self.timeout_s)

    def _resolve(self, stage: StageId | str, attr: str, default: int) -> int:
        key = StageId(stage) if not isinstance(stage, StageId) else stage
        ov = self.stage_overrides.get(key)
        if ov is not None:
            val = getattr(ov, attr)
            if val is not None:
                return int(val)
        return default

    # ---- loading ---------------------------------------------------------

    @staticmethod
    def load_file(path: str | os.PathLike[str]) -> dict[str, Any]:
        """Read a YAML (or JSON, which YAML is a superset of) config file."""
        p = Path(path).expanduser()
        if not p.is_file():
            raise ConfigError(f"config file not found: {p}")
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"config file {p} is not valid YAML/JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"config file {p} must contain a mapping at the top level")
        return data

    @classmethod
    def build(
        cls,
        *,
        rtl_dir: str | os.PathLike[str] | None = None,
        top: str | None = None,
        pdk_name: str | None = None,
        pdk_root: str | os.PathLike[str] | None = None,
        retry_limit: int | None = None,
        fix_candidates: int | None = None,
        model: str | None = None,
        run_root: str | os.PathLike[str] | None = None,
        resume_from: str | None = None,
        config_path: str | os.PathLike[str] | None = None,
        mock_tools: bool | None = None,
        skip_stages: list[str] | None = None,
        repair_policy: str | None = None,
        klayout_backend: str | None = None,
    ) -> "RunConfig":
        """Merge config file, environment and explicit arguments."""
        fileconf: dict[str, Any] = cls.load_file(config_path) if config_path else {}

        def pick(cli: Any, key: str, env: str | None, default: Any) -> Any:
            if cli is not None:
                return cli
            if key in fileconf and fileconf[key] is not None:
                return fileconf[key]
            if env and os.environ.get(env):
                return os.environ[env]
            return default

        # rtl may be spelled "rtl" or "rtl_dir" in the file.
        rtl_val = rtl_dir if rtl_dir is not None else fileconf.get("rtl", fileconf.get("rtl_dir"))
        if rtl_val is None:
            raise ConfigError("no RTL directory given: pass --rtl or set 'rtl' in the config file")
        top_val = top if top is not None else fileconf.get("top")
        if not top_val:
            raise ConfigError("no top module given: pass --top or set 'top' in the config file")

        pdk_section = fileconf.get("pdk") or {}
        if isinstance(pdk_section, str):
            # Shorthand:  pdk: sky130A
            pdk_section = {"name": pdk_section}
        if not isinstance(pdk_section, dict):
            raise ConfigError("config key 'pdk' must be a mapping or a PDK name string")

        overrides = {k: pdk_section[k] for k in _PDK_OVERRIDE_KEYS if pdk_section.get(k)}
        pdk = PDKConfig.discover(
            name=pdk_name or pdk_section.get("name") or "sky130A",
            root=pdk_root if pdk_root is not None else pdk_section.get("root"),
            **overrides,
        )
        if pdk_section.get("std_cell_lib") or pdk_section.get("corner"):
            pdk = replace(
                pdk,
                std_cell_lib=pdk_section.get("std_cell_lib", pdk.std_cell_lib),
                corner=pdk_section.get("corner", pdk.corner),
            )
        fillers = pdk_section.get("filler_prefixes")
        if fillers is not None:
            if isinstance(fillers, str):
                fillers = [fillers]
            if not isinstance(fillers, list) or not all(isinstance(f, str) for f in fillers):
                raise ConfigError(
                    "config key 'pdk.filler_prefixes' must be a string or list of strings"
                )
            pdk = replace(pdk, filler_prefixes=tuple(fillers))

        stage_overrides = cls._parse_stage_overrides(fileconf.get("stages") or {})
        ir_overrides = cls._parse_ir_overrides(fileconf.get("ir") or {})

        resume_val = resume_from if resume_from is not None else fileconf.get("resume_from")

        return cls(
            rtl_dir=Path(rtl_val),
            top=str(top_val),
            pdk=pdk,
            retry_limit=int(pick(retry_limit, "retry_limit", None, DEFAULT_RETRY_LIMIT)),
            fix_candidates=int(
                pick(fix_candidates, "fix_candidates", None, DEFAULT_FIX_CANDIDATES)
            ),
            timeout_s=int(fileconf.get("timeout_s") or 3600),
            model=str(pick(model, "model", MODEL_ENV, DEFAULT_MODEL)),
            run_root=Path(pick(run_root, "run_root", None, DEFAULT_RUN_ROOT)),
            resume_from=parse_stage(str(resume_val)) if resume_val else None,
            stage_overrides=stage_overrides,
            mock_tools=bool(
                mock_tools if mock_tools is not None else fileconf.get("mock_tools", False)
            ),
            ir_overrides=ir_overrides,
            skip_stages=frozenset(
                parse_stage(str(x))
                for x in (skip_stages or fileconf.get("skip_stages") or [])
            ),
            repair_policy=str(pick(repair_policy, "repair_policy", None, "ask")),
            klayout_backend=str(pick(klayout_backend, "klayout_backend", None, "native")),
        )

    @staticmethod
    def _parse_ir_overrides(raw: Any) -> dict[str, dict[str, Any]]:
        """Validate the ``ir:`` section against the schema at load time.

        Checked here rather than at first use so a typo in the config file is
        reported immediately, with the list of valid fields, instead of halfway
        through a run.
        """
        from .ir import SCHEMA, IR

        if not isinstance(raw, dict):
            raise ConfigError("config key 'ir' must be a mapping of section -> settings")
        probe = IR()
        out: dict[str, dict[str, Any]] = {}
        for section, values in raw.items():
            if section not in SCHEMA:
                raise ConfigError(
                    f"ir.{section} is not a known section; valid: "
                    + ", ".join(sorted(SCHEMA))
                )
            if not isinstance(values, dict):
                raise ConfigError(f"ir.{section} must be a mapping")
            probe.update(section, values, agent=False)  # raises on a bad field
            out[section] = dict(values)
        return out

    @staticmethod
    def _parse_stage_overrides(raw: Any) -> dict[StageId, StageOverrides]:
        if not isinstance(raw, dict):
            raise ConfigError("config key 'stages' must be a mapping of stage name -> settings")
        out: dict[StageId, StageOverrides] = {}
        for name, settings in raw.items():
            stage = parse_stage(str(name))
            if settings is None:
                continue
            if not isinstance(settings, dict):
                raise ConfigError(f"stages.{name} must be a mapping, got {type(settings).__name__}")
            unknown = set(settings) - {"retry_limit", "fix_candidates", "timeout_s"}
            if unknown:
                raise ConfigError(
                    f"stages.{name} has unknown keys: {', '.join(sorted(unknown))}; "
                    "supported: retry_limit, fix_candidates, timeout_s"
                )
            ov = StageOverrides(
                retry_limit=_pos_int(settings.get("retry_limit"), f"stages.{name}.retry_limit"),
                fix_candidates=_pos_int(
                    settings.get("fix_candidates"), f"stages.{name}.fix_candidates"
                ),
                timeout_s=_pos_int(settings.get("timeout_s"), f"stages.{name}.timeout_s"),
            )
            out[stage] = ov
        return out

    # ---- reporting -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialisable form for run_state.json. Contains no secrets."""
        return {
            "rtl_dir": str(self.rtl_dir),
            "top": self.top,
            "pdk": self.pdk.to_dict(),
            "retry_limit": self.retry_limit,
            "fix_candidates": self.fix_candidates,
            "model": self.model,
            "mock_tools": self.mock_tools,
            "resume_from": self.resume_from.value if self.resume_from else None,
            "effective_retry_limits": {
                s.value: self.retry_limit_for(s) for s in STAGE_ORDER
            },
            "ir_overrides": self.ir_overrides,
            "skip_stages": sorted(s.value for s in self.skip_stages),
            "repair_policy": self.repair_policy,
            "klayout_backend": self.klayout_backend,
        }


def _pos_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ConfigError(f"{label} must be an integer, got {value!r}") from None
    if n < 1:
        raise ConfigError(f"{label} must be >= 1, got {n}")
    return n
