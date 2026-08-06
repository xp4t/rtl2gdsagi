"""Unit tests for ConfigManager."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from config.config_manager import ConfigManager


MINIMAL_CONFIG = """
design:
  top_module: test_top
  rtl_files:
    - test.v
  clock_port: clk
  pdk: sky130hd

defaults:
  CLOCK_PERIOD: 10.0
  FP_CORE_UTIL: 45
  PL_TARGET_DENSITY: 0.55

param_ranges:
  CLOCK_PERIOD:
    type: float
    min: 2.0
    max: 100.0
    default: 10.0
  FP_CORE_UTIL:
    type: int
    min: 20
    max: 75
    default: 45
  PL_TARGET_DENSITY:
    type: float
    min: 0.30
    max: 0.85
    default: 0.55

sweeps:
  synthesis:
    - {SYNTH_STRATEGY: 0}
    - {SYNTH_STRATEGY: 1}
"""


@pytest.fixture
def cfg_path(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(MINIMAL_CONFIG)
    return str(p)


def test_load(cfg_path):
    cm = ConfigManager(cfg_path)
    assert cm.design["top_module"] == "test_top"
    assert cm.defaults["CLOCK_PERIOD"] == 10.0


def test_validate_clamp_min(cfg_path):
    cm = ConfigManager(cfg_path)
    validated = cm.validate_and_apply({"CLOCK_PERIOD": 0.5})  # below min=2.0
    assert validated["CLOCK_PERIOD"] == 2.0  # clamped


def test_validate_clamp_max(cfg_path):
    cm = ConfigManager(cfg_path)
    validated = cm.validate_and_apply({"FP_CORE_UTIL": 99})  # above max=75
    assert validated["FP_CORE_UTIL"] == 75


def test_validate_reject_unknown(cfg_path):
    cm = ConfigManager(cfg_path)
    # FAKE_PARAM is not in param_ranges — should be silently rejected
    validated = cm.validate_and_apply({"FAKE_PARAM": "value"})
    assert "FAKE_PARAM" not in validated


def test_validate_type_coercion(cfg_path):
    cm = ConfigManager(cfg_path)
    # Pass string "45" for an int param
    validated = cm.validate_and_apply({"FP_CORE_UTIL": "55"})
    assert validated["FP_CORE_UTIL"] == 55
    assert isinstance(validated["FP_CORE_UTIL"], int)


def test_generate_run_config(cfg_path, tmp_path):
    cm = ConfigManager(cfg_path)
    out = tmp_path / "run_config.json"
    cm.generate_run_config({"CLOCK_PERIOD": 8.0}, out)
    data = json.loads(out.read_text())
    assert data["CLOCK_PERIOD"] == 8.0
    assert data["FP_CORE_UTIL"] == 45  # from defaults
    assert data["DESIGN_NAME"] == "test_top"


def test_sweep_variants(cfg_path):
    cm = ConfigManager(cfg_path)
    variants = cm.get_sweep_variants("synthesis")
    assert len(variants) == 2
    assert variants[0]["SYNTH_STRATEGY"] == 0
