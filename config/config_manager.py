"""YAML-based config manager with:

* Per-stage allowed param ranges (LLM suggestions validated before applying)
* Clamp / reject out-of-range values
* Generates the OpenLane2 JSON config file for each run attempt
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


class ConfigManager:
    """Loads the design YAML config and validates LLM param_updates."""

    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        self._raw = self._load(self.config_path)
        self.defaults: dict[str, Any] = self._raw.get("defaults", {})
        self.param_ranges: dict[str, dict] = self._raw.get("param_ranges", {})
        self.design: dict[str, Any] = self._raw.get("design", {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_and_apply(
        self,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate *updates* against param_ranges; clamp or reject.

        Returns the validated (possibly clamped) subset of *updates*.
        """
        validated: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in self.param_ranges:
                log.warning(
                    "Config: param '%s' not in param_ranges — rejecting LLM suggestion",
                    key,
                )
                continue
            spec = self.param_ranges[key]
            validated[key] = self._validate_value(key, value, spec)
        return validated

    def generate_run_config(
        self,
        overrides: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Merge defaults + overrides → write JSON for OpenLane2."""
        merged = {**self.defaults, **overrides}
        # Always include required design fields
        merged["DESIGN_NAME"] = self.design.get("top_module", merged.get("DESIGN_NAME"))
        merged["VERILOG_FILES"] = self.design.get("rtl_files", merged.get("VERILOG_FILES", []))
        merged["CLOCK_PORT"]   = self.design.get("clock_port", merged.get("CLOCK_PORT", "clk"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(merged, indent=2))
        log.debug("Wrote run config: %s", output_path)
        return output_path

    def get_sweep_variants(
        self,
        stage: str,
    ) -> list[dict[str, Any]]:
        """Return a list of param override dicts for strategy sweep."""
        sweeps = self._raw.get("sweeps", {}).get(stage, [])
        return sweeps  # list of {param: value, ...}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Config must be a YAML mapping, got: {type(data)}")
        return data

    @staticmethod
    def _validate_value(key: str, value: Any, spec: dict) -> Any:
        """Clamp numeric values; reject wrong types."""
        expected_type = spec.get("type", "any")

        # Type coercion / validation
        if expected_type == "int":
            try:
                value = int(value)
            except (TypeError, ValueError):
                log.warning("Param '%s': expected int, got %r — skipping", key, value)
                return spec.get("default", value)
        elif expected_type == "float":
            try:
                value = float(value)
            except (TypeError, ValueError):
                log.warning("Param '%s': expected float, got %r — skipping", key, value)
                return spec.get("default", value)
        elif expected_type == "bool":
            if not isinstance(value, bool):
                log.warning("Param '%s': expected bool, got %r — coercing", key, value)
                value = bool(value)

        # Range clamping
        if "min" in spec and value < spec["min"]:
            log.warning(
                "Param '%s': value %r below min %r — clamping",
                key, value, spec["min"],
            )
            value = spec["min"]
        if "max" in spec and value > spec["max"]:
            log.warning(
                "Param '%s': value %r above max %r — clamping",
                key, value, spec["max"],
            )
            value = spec["max"]

        # Enum validation
        if "enum" in spec and value not in spec["enum"]:
            log.warning(
                "Param '%s': value %r not in enum %r — using default",
                key, value, spec["enum"],
            )
            value = spec.get("default", spec["enum"][0])

        return value
