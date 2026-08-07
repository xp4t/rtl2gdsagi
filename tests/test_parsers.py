"""Unit tests for log parsers.

All tests are self-contained — they create temp log directories with
fake tool output and verify the parsed JSON schema.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parsers.lint_parser import LintParser
from parsers.synth_parser import SynthParser
from parsers.sta_parser import STAParser
from parsers.drc_parser import DRCParser
from parsers.lvs_parser import LVSParser
from parsers.sdc_parser import SDCParser


def _make_stage_result(exit_code: int = 0) -> MagicMock:
    sr = MagicMock()
    sr.exit_code = exit_code
    return sr


def _write_logs(log_dir: Path, stdout: str = "", stderr: str = "") -> None:
    (log_dir / "stdout.log").write_text(stdout)
    (log_dir / "stderr.log").write_text(stderr)


# ─────────────────────────────────────────────────────────────────────────────
# LintParser
# ─────────────────────────────────────────────────────────────────────────────

class TestLintParser:
    def test_clean_pass(self, tmp_path):
        _write_logs(tmp_path, stdout="Verilint: no issues found")
        r = LintParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["num_errors"] == 0
        assert r["num_warnings"] == 0
        assert r["stage"] == "lint"

    def test_warning_detection(self, tmp_path):
        stdout = "%Warning-UNUSED: alu.v:42:10: Signal is not used: _foo\n"
        _write_logs(tmp_path, stdout=stdout)
        r = LintParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "warn"
        assert r["num_warnings"] == 1
        assert r["warnings"][0]["code"] == "UNUSED"

    def test_error_detection(self, tmp_path):
        stdout = "%Error-NOTFOUND: alu.v:1:1: Cannot find module: foo\n"
        _write_logs(tmp_path, stdout=stdout)
        r = LintParser().parse(tmp_path, _make_stage_result(1))
        assert r["status"] == "fail"
        assert r["num_errors"] == 1

    def test_nonzero_exit_no_output_raises(self, tmp_path):
        # Non-zero exit + no recognisable output + >200 chars = raise
        long_garbage = "X" * 300
        _write_logs(tmp_path, stdout=long_garbage)
        with pytest.raises(RuntimeError, match="unrecognised log format"):
            LintParser().parse(tmp_path, _make_stage_result(1))


# ─────────────────────────────────────────────────────────────────────────────
# SynthParser
# ─────────────────────────────────────────────────────────────────────────────

_YOSYS_STATS = """
=== riscv_alu ===

   Number of wires:                245
   Number of cells:                198
     sky130_fd_sc_hd__buf_1          12
     sky130_fd_sc_hd__dfxtp_1        32

   Chip area for module '\\riscv_alu': 1245.678000
"""


class TestSynthParser:
    def test_basic_parse(self, tmp_path):
        _write_logs(tmp_path, stdout=_YOSYS_STATS)
        r = SynthParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["num_cells"] == 198
        assert r["num_wires"] == 245
        assert abs(r["area_um2"] - 1245.678) < 0.001

    def test_fail_exit_code(self, tmp_path):
        _write_logs(tmp_path, stdout=_YOSYS_STATS)
        r = SynthParser().parse(tmp_path, _make_stage_result(1))
        assert r["status"] == "fail"

    def test_empty_synth_raises(self, tmp_path):
        # exit=0 but no cell count and >200 chars of output = suspicious
        _write_logs(tmp_path, stdout="synthesis completed" + "X" * 300)
        with pytest.raises(RuntimeError, match="unrecognised log format"):
            SynthParser().parse(tmp_path, _make_stage_result(0))


# ─────────────────────────────────────────────────────────────────────────────
# STAParser
# ─────────────────────────────────────────────────────────────────────────────

_STA_PASS = """
Startpoint: operand_a[0] (input port clocked by clk)
Endpoint:   result_reg[0]/D
Path Group: clk
Path Type:  max

  ... (timing path detail omitted for brevity)
  slack (MET)                              4.92

wns 0.00
tns 0.00
violating paths 0
"""

_STA_FAIL = """
Startpoint: operand_a[31] (input port clocked by clk)
Endpoint:   result_reg[31]/D
Path Group: clk
Path Type:  max

  slack (VIOLATED)                        -0.42

wns -0.42
tns -1.26
violating paths 3
"""


class TestSTAParser:
    def test_timing_met(self, tmp_path):
        _write_logs(tmp_path, stdout=_STA_PASS)
        r = STAParser("post_synth_sta").parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["worst_setup_slack_ns"] == 0.0
        assert r["num_violating_paths"] == 0
        assert r["stage"] == "post_synth_sta"

    def test_timing_violated(self, tmp_path):
        _write_logs(tmp_path, stdout=_STA_FAIL)
        r = STAParser("post_synth_sta").parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "fail"
        assert r["worst_setup_slack_ns"] == -0.42
        assert r["num_violating_paths"] == 3
        assert len(r["top_violations"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# DRCParser
# ─────────────────────────────────────────────────────────────────────────────

_DRC_CLEAN = "Total DRC errors: 0\n"
_DRC_FAIL  = """
[ERROR] metal1 spacing violation at (100,200)-(110,210) (Count: 3)
[ERROR] poly.9 gate too close to well (Count: 1)
Total DRC errors: 4
"""


class TestDRCParser:
    def test_clean(self, tmp_path):
        _write_logs(tmp_path, stdout=_DRC_CLEAN)
        r = DRCParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["total_violations"] == 0

    def test_violations(self, tmp_path):
        _write_logs(tmp_path, stdout=_DRC_FAIL)
        r = DRCParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "fail"
        assert r["total_violations"] == 4
        assert len(r["violations"]) == 2

    def test_nonzero_exit_no_report_raises(self, tmp_path):
        _write_logs(tmp_path, stdout="")
        with pytest.raises(RuntimeError, match="unrecognised log format"):
            DRCParser().parse(tmp_path, _make_stage_result(1))


# ─────────────────────────────────────────────────────────────────────────────
# LVSParser
# ─────────────────────────────────────────────────────────────────────────────

_LVS_PASS = "Result: Circuits match uniquely.\n0 errors, 0 warnings.\n"
_LVS_FAIL = "Result: Netlists do not match.\n5 errors.\n"


class TestLVSParser:
    def test_match(self, tmp_path):
        _write_logs(tmp_path, stdout=_LVS_PASS)
        r = LVSParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["circuits_matched"] is True

    def test_mismatch(self, tmp_path):
        _write_logs(tmp_path, stdout=_LVS_FAIL)
        r = LVSParser().parse(tmp_path, _make_stage_result(1))
        assert r["status"] == "fail"
        assert r["circuits_matched"] is False


# ─────────────────────────────────────────────────────────────────────────────
# SDCParser
# ─────────────────────────────────────────────────────────────────────────────

_SDC_PASS = "[INFO] SDC check passed: 1 clocks, 6 paths constrained.\n"
_SDC_FAIL = "[ERROR] SDC check failed: missing constraints.\n"
_SDC_WARN = "[WARNING] No clock constraint found for pin CLK\n"


class TestSDCParser:
    def test_pass(self, tmp_path):
        _write_logs(tmp_path, stdout=_SDC_PASS)
        r = SDCParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "pass"
        assert r["num_clocks"] == 1

    def test_fail(self, tmp_path):
        _write_logs(tmp_path, stdout=_SDC_FAIL)
        r = SDCParser().parse(tmp_path, _make_stage_result(1))
        assert r["status"] == "fail"

    def test_warning(self, tmp_path):
        _write_logs(tmp_path, stdout=_SDC_WARN)
        r = SDCParser().parse(tmp_path, _make_stage_result(0))
        assert r["status"] == "warn"
        assert len(r["warnings"]) == 1
