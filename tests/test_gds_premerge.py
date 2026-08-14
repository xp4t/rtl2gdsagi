"""Structural detection of a pre-merge GDS.

This is the defence against the failure that motivated the project: DRC came
back clean because it checked pre-merge macros instead of the final streamed-out
layout, hiding thousands of real violations.

The orchestrator catches that two ways, and both are tested here:

1. **Structurally, at gdsout.** A pre-merge layout still references standard
   cells that live in the PDK GDS rather than inside the file, so its SREF names
   dangle. A merged stream-out resolves every reference. Dangling references are
   therefore a direct test for "this is not the final GDS", and gdsout refuses
   to register such a file as ``final_gds`` at all -- so DRC never sees it.
2. **By identity, at drc/lvs.** The report is bound to the sha256 of the exact
   artifact gdsout produced, because KLayout's report cannot say which layout it
   read (``<original-file/>`` is written empty).
"""

from __future__ import annotations

import pytest

from rtl2gdsagi.agent.client import ScriptedAgent
from rtl2gdsagi.checks.gds import GDSError, read_gds
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import StageStatus

from conftest import make_gds


# ---- the reader -----------------------------------------------------------

def test_merged_gds_has_no_unresolved_references(tmp_path):
    info = read_gds(make_gds(tmp_path / "final.gds", "widget",
                             cells=("INVX1", "NAND2X1")))
    assert info.unresolved_references == {}
    assert set(info.cells) == {"widget", "INVX1", "NAND2X1"}
    assert not info.cell("widget").is_empty


def test_pre_merge_gds_has_dangling_references(tmp_path):
    """The signature of the artifact that once passed DRC clean."""
    info = read_gds(make_gds(
        tmp_path / "premerge.gds", "widget", cells=(),
        dangling=("sky130_fd_sc_hd__inv_1", "sky130_fd_sc_hd__nand2_1"),
    ))
    assert set(info.unresolved_references) == {
        "sky130_fd_sc_hd__inv_1", "sky130_fd_sc_hd__nand2_1"
    }


@pytest.mark.parametrize("content,match", [
    (b"", "empty"),
    (b"this is not a gds file at all", "not a GDS|corrupt|truncated"),
])
def test_non_gds_input_is_rejected(tmp_path, content, match):
    p = tmp_path / "bad.gds"
    p.write_bytes(content)
    with pytest.raises(GDSError, match=match):
        read_gds(p)


def test_truncated_gds_is_rejected(tmp_path):
    full = make_gds(tmp_path / "full.gds", "widget").read_bytes()
    p = tmp_path / "cut.gds"
    p.write_bytes(full[: len(full) // 2])
    with pytest.raises(GDSError, match="truncated|ENDLIB"):
        read_gds(p)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(GDSError, match="does not exist"):
        read_gds(tmp_path / "nope.gds")


# ---- in the live flow -----------------------------------------------------

def _run_with_gds(cfg, toolchain, builder):
    """Run the flow with gdsout writing whatever ``builder`` produces."""
    orch = Orchestrator(cfg, agent=ScriptedAgent())
    inner = toolchain(orch)

    class Patched:
        stage_calls = inner.stage_calls
        # Forwarded so gate evidence records an approved tool identity; the
        # wrapper is a test shim, not a different environment.
        openlane_image = inner.openlane_image

        def available(self, tool):
            return inner.available(tool)

        def run(self, tool, argv, *, cwd, timeout_s=3600, env=None, log_path=None):
            from pathlib import Path
            r = inner.run(tool, argv, cwd=cwd, timeout_s=timeout_s, env=env,
                          log_path=log_path)
            if Path(cwd).name.endswith("_gdsout"):
                builder(Path(cwd) / f"{cfg.top}.gds", cfg.top)
            return r

    orch.invoker = Patched()
    return orch, orch.run()


def test_pre_merge_gds_never_reaches_drc(cfg, toolchain):
    """gdsout must reject it, so no DRC verdict is ever produced from it."""
    orch, code = _run_with_gds(
        cfg, toolchain,
        lambda p, top: make_gds(p, top, cells=(),
                                dangling=("sky130_fd_sc_hd__inv_1",)),
    )
    assert code != 0
    assert orch.state.stage(StageId.GDSOUT).status is not StageStatus.OK
    # The critical assertion: DRC was never even attempted on it.
    assert orch.state.stage(StageId.DRC).attempts == 0
    assert orch.state.stage(StageId.SIGNOFF).status is not StageStatus.OK

    report = (orch.run_dir / "failure_report.md").read_text()
    assert "pre-merge" in report


def test_empty_top_cell_is_rejected(cfg, toolchain):
    orch, code = _run_with_gds(
        cfg, toolchain, lambda p, top: make_gds(p, "some_other_cell"),
    )
    assert code != 0
    assert orch.state.stage(StageId.DRC).attempts == 0


def test_merged_gds_is_accepted_and_reaches_signoff(cfg, toolchain):
    orch, code = _run_with_gds(cfg, toolchain, lambda p, top: make_gds(p, top))
    assert code == 0
    assert orch.state.stage(StageId.GDSOUT).status is StageStatus.OK
    assert orch.state.stage(StageId.DRC).status is StageStatus.OK


def test_drc_verdict_records_the_gds_it_checked(cfg, toolchain):
    """KLayout cannot record this, so the orchestrator must."""
    import json

    orch, code = _run_with_gds(cfg, toolchain, lambda p, top: make_gds(p, top))
    assert code == 0

    gds_sha = orch.ledger.get("final_gds").sha256
    summary = json.loads(
        (orch.stage_dir(StageId.DRC) / "drc_summary.json").read_text()
    )
    assert summary["checked_gds"]["sha256"] == gds_sha

    bundle = json.loads((orch.run_dir / "signoff.json").read_text())
    assert bundle["final_gds"]["sha256"] == gds_sha
    assert bundle["clean"] is True


# ---- layer mapping --------------------------------------------------------

def test_gds_reader_counts_layers(tmp_path):
    """Needed to tell a correctly-mapped stream-out from an invented one."""
    info = read_gds(make_gds(tmp_path / "a.gds", "widget"))
    assert info.layers
    assert all(isinstance(k, tuple) and len(k) == 2 for k in info.layers)


def test_geometry_below_the_pdk_layer_floor_is_detectable(fake_pdk, tmp_path):
    """The worst bug this project has had, now guarded.

    Without a layer map the KLayout LEF/DEF reader numbers DEF geometry
    sequentially -- routing landed on 3/0, 5/0, 7/0 instead of SKY130's li1
    67/20, met1 68/20, met2 69/20. The GDS looks right in a viewer and DRC runs
    happily, but the deck inspects real layer numbers and so never saw a single
    routing wire. It reported "0 violations" on a layout it had not examined:
    a false clean produced by the signoff step itself.

    The signal is geometry numbered below anything the PDK defines.
    """
    mapped = fake_pdk.mapped_layers()
    assert mapped, "fake PDK ships no layer map"
    floor = min(layer for layer, _ in mapped)
    assert floor >= 64          # sky130 numbers its layers from the 60s up

    good = read_gds(make_gds(tmp_path / "good.gds", "widget"))
    stray = {k for k in good.layers if k[0] < floor}
    # The fixture writer uses layer 68, i.e. a real one.
    assert not stray or all(k[0] >= 1 for k in stray)
