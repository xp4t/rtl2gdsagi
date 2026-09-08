from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures" / "validation" / "shift_register"


def test_inferred_shift_register_behavior_fixture(tmp_path):
    """Checks only reset/shift behavior directly stated by the fixture RTL."""
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        pytest.skip("iverilog/vvp unavailable")
    image = tmp_path / "shift_register_tb.vvp"
    build = subprocess.run(
        ["iverilog", "-g2012", "-s", "shift_register_tb", "-o", str(image),
         str(FIX / "shift_register_tb.v"), str(FIX / "shift_register.v")],
        text=True, capture_output=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    sim = subprocess.run(["vvp", str(image)], text=True, capture_output=True)
    assert sim.returncode == 0, sim.stdout + sim.stderr
    assert "PASS shift_register inferred behavior" in sim.stdout
    assert "FAIL" not in sim.stdout
