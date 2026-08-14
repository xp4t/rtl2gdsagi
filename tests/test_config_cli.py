"""Config merging, per-stage overrides, state persistence and the CLI."""

from __future__ import annotations

import json
import pytest

from rtl2gdsagi.cli import main
from rtl2gdsagi.config import RunConfig
from rtl2gdsagi.errors import ConfigError
from rtl2gdsagi.stages import STAGE_ORDER, StageId
from rtl2gdsagi.state import RunState, StageStatus, new_run_id


# ---- config ---------------------------------------------------------------

def test_per_stage_retry_override(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\nretry_limit: 3\n"
        f"pdk:\n  name: sky130A\n  root: {fake_pdk.root}\n"
        "stages:\n  routing: {retry_limit: 5}\n  drc: {retry_limit: 1}\n",
        encoding="utf-8",
    )
    cfg = RunConfig.build(config_path=cfgfile)
    assert cfg.retry_limit_for(StageId.SYNTHESIS) == 3   # global default
    assert cfg.retry_limit_for(StageId.ROUTING) == 5     # overridden
    assert cfg.retry_limit_for(StageId.DRC) == 1


def test_cli_flag_beats_config_file(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\nretry_limit: 3\n"
        f"pdk:\n  root: {fake_pdk.root}\n", encoding="utf-8",
    )
    cfg = RunConfig.build(config_path=cfgfile, retry_limit=9)
    assert cfg.retry_limit == 9


def test_unknown_stage_in_config_is_rejected(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\npdk: {{root: {fake_pdk.root}}}\n"
        "stages:\n  polishing: {retry_limit: 2}\n", encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown stage"):
        RunConfig.build(config_path=cfgfile)


def test_unknown_stage_key_is_rejected(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\npdk: {{root: {fake_pdk.root}}}\n"
        "stages:\n  routing: {retries: 2}\n", encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown keys"):
        RunConfig.build(config_path=cfgfile)


def test_missing_top_is_an_error(design, fake_pdk):
    with pytest.raises(ConfigError, match="top module"):
        RunConfig.build(rtl_dir=design, pdk_root=fake_pdk.root)


def test_zero_retry_limit_is_rejected(design, fake_pdk):
    with pytest.raises(ConfigError, match="retry_limit"):
        RunConfig(rtl_dir=design, top="widget", pdk=fake_pdk, retry_limit=0)


def test_config_dict_contains_no_secret(cfg, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-appear")
    blob = json.dumps(cfg.to_dict())
    assert "sk-ant" not in blob


def test_effective_retry_limits_are_recorded(cfg):
    d = cfg.to_dict()
    assert set(d["effective_retry_limits"]) == {s.value for s in STAGE_ORDER}


# ---- state persistence ----------------------------------------------------

def test_state_roundtrip(tmp_path):
    st = RunState(run_id=new_run_id(), run_dir=tmp_path, config={"top": "widget"})
    st.stage(StageId.SYNTHESIS).status = StageStatus.OK
    st.stage(StageId.SYNTHESIS).attempts = 2
    st.stage(StageId.ROUTING).status = StageStatus.FAILED
    st.stage(StageId.ROUTING).last_error = "12 violations"
    st.save()

    back = RunState.load(tmp_path)
    assert back.run_id == st.run_id
    assert back.stage(StageId.SYNTHESIS).attempts == 2
    assert back.stage(StageId.ROUTING).last_error == "12 violations"
    assert back.failed_stage() is StageId.ROUTING


def test_save_is_atomic_and_leaves_no_partial_file(tmp_path):
    st = RunState(run_id="x", run_dir=tmp_path)
    for _ in range(20):
        st.save()
    assert json.loads(st.path.read_text())["run_id"] == "x"
    assert not list(tmp_path.glob("*.tmp"))


def test_newer_state_version_is_refused(tmp_path):
    st = RunState(run_id="x", run_dir=tmp_path)
    st.save()
    data = json.loads(st.path.read_text())
    data["version"] = 999
    st.path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="newer rtl2gdsagi"):
        RunState.load(tmp_path)


def test_first_incomplete_drives_resume(tmp_path):
    st = RunState(run_id="x", run_dir=tmp_path)
    for sid in (StageId.CHARACTERIZE, StageId.LINT, StageId.SIM, StageId.SDC):
        st.stage(sid).status = StageStatus.OK
    assert st.first_incomplete() is StageId.SYNTHESIS


# ---- CLI ------------------------------------------------------------------

def test_stages_command(capsys):
    assert main(["stages"]) == 0
    out = capsys.readouterr().out
    for s in ("lint", "sta_signoff", "drc", "lvs", "antenna", "signoff"):
        assert s in out
    assert "advisory" in out


def test_taxonomy_command(capsys):
    assert main(["taxonomy"]) == 0
    out = capsys.readouterr().out
    assert "congestion" in out and "escalate" in out


def test_schema_command_lists_only_bounded_fields(capsys):
    assert main(["schema", "drc"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data["drc"]) <= {"threads", "deep_mode"}


def test_schema_rejects_unknown_section(capsys):
    assert main(["schema", "nonsense"]) == 2


def test_status_command_on_a_real_run(cfg, toolchain, capsys):
    from rtl2gdsagi.runner import Orchestrator
    from rtl2gdsagi.agent.client import ScriptedAgent

    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.invoker = toolchain(orch)
    orch.run()
    capsys.readouterr()

    assert main(["status", str(orch.run_dir)]) == 0
    out = capsys.readouterr().out
    assert "signoff" in out and "ok" in out


def test_run_without_api_key_and_without_no_api_is_a_usage_error(
    design, fake_pdk, monkeypatch, capsys
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code = main([
        "run", "--rtl", str(design), "--top", "widget",
        "--pdk-root", str(fake_pdk.root),
    ])
    assert code == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_unknown_resume_stage_is_rejected(design, fake_pdk, capsys):
    code = main([
        "run", "--rtl", str(design), "--top", "widget",
        "--pdk-root", str(fake_pdk.root), "--no-api",
        "--resume-from", "polishing",
    ])
    assert code == 2


# ---- relative paths -------------------------------------------------------

def test_config_paths_are_made_absolute(design, fake_pdk, tmp_path, monkeypatch):
    """Tools run with cwd set to a stage directory.

    A relative path taken straight from the config file resolves against the
    stage directory instead of where the user ran the command, and the tool
    reports 'No such file or directory' for a file that plainly exists.
    """
    monkeypatch.chdir(design.parent)
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design.name}\npdk: {{root: {fake_pdk.root}}}\n",
        encoding="utf-8",
    )
    cfg = RunConfig.build(config_path=cfgfile)
    assert cfg.rtl_dir.is_absolute()
    assert cfg.rtl_dir == design.resolve()
    assert cfg.run_root.is_absolute()


def test_testbench_discovery_returns_absolute_paths(cfg, tmp_path):
    """Same reason: these are handed to iverilog, which runs elsewhere."""
    from rtl2gdsagi.agent.client import ScriptedAgent
    from rtl2gdsagi.runner import Orchestrator

    tb = tmp_path / "benches"
    tb.mkdir()
    (tb / "widget_tb.v").write_text("module widget_tb; endmodule\n", encoding="utf-8")

    orch = Orchestrator(cfg, agent=ScriptedAgent())
    orch.ir.update("sim", {"testbench_dir": str(tb)}, agent=False)
    found = orch._testbenches()
    assert found and all(p.is_absolute() for p in found)


def test_ir_section_values_are_validated_when_the_file_loads(
    design, fake_pdk, tmp_path
):
    """A typo should be reported immediately, not 20 minutes into a run."""
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\npdk: {{root: {fake_pdk.root}}}\n"
        "ir:\n  floorplan: {core_utilisation: 0.4}\n",   # British spelling typo
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="not a field in the schema"):
        RunConfig.build(config_path=cfgfile)


def test_ir_section_cannot_introduce_a_check_waiver(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\npdk: {{root: {fake_pdk.root}}}\n"
        "ir:\n  drc: {waive_violations: true}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="not a field in the schema"):
        RunConfig.build(config_path=cfgfile)


def test_ir_overrides_reach_the_run(cfg, toolchain):
    from dataclasses import replace
    from rtl2gdsagi.agent.client import ScriptedAgent
    from rtl2gdsagi.runner import Orchestrator

    cfg2 = replace(cfg, ir_overrides={"floorplan": {"core_utilization": 0.31}})
    orch = Orchestrator(cfg2, agent=ScriptedAgent())
    orch.invoker = toolchain(orch)
    orch.prepare()
    # Beats the value characterization would otherwise have chosen.
    assert orch.ir.get("floorplan", "core_utilization") == pytest.approx(0.31)


# ---- shipped examples -----------------------------------------------------

def test_shipped_examples_have_valid_configs():
    """A broken example is worse than no example: it is the first thing anyone
    runs, and it decides whether they trust the tool at all."""
    from pathlib import Path as _P

    root = _P(__file__).resolve().parent.parent
    examples = sorted((root / "examples").glob("*/*.yaml"))
    assert examples, "no example configs found"

    for cfgfile in examples:
        raw = RunConfig.load_file(cfgfile)
        assert raw.get("top"), f"{cfgfile.name} has no top module"
        rtl = root / raw["rtl"]
        assert rtl.is_dir(), f"{cfgfile.name} points at a missing RTL dir: {rtl}"
        assert list(rtl.glob("*.v")), f"{rtl} contains no Verilog"

        tb_dir = (raw.get("ir") or {}).get("sim", {}).get("testbench_dir")
        if tb_dir:
            assert (root / tb_dir).is_dir(), f"{cfgfile.name}: missing {tb_dir}"


def test_shipped_examples_declare_only_real_schema_fields(monkeypatch):
    """Catches an example drifting out of sync with the schema."""
    from pathlib import Path as _P
    from rtl2gdsagi.ir import IR

    root = _P(__file__).resolve().parent.parent
    for cfgfile in sorted((root / "examples").glob("*/*.yaml")):
        raw = RunConfig.load_file(cfgfile)
        probe = IR()
        for section, values in (raw.get("ir") or {}).items():
            probe.update(section, values, agent=False)   # raises if invalid


def test_example_testbenches_are_self_checking():
    """A testbench that prints no verdict proves the design elaborates and
    nothing more. The shipped ones must set a better example than that."""
    from pathlib import Path as _P

    root = _P(__file__).resolve().parent.parent
    benches = sorted((root / "examples").glob("*/tb/*_tb.v"))
    assert benches
    for tb in benches:
        text = tb.read_text(encoding="utf-8")
        assert "TEST PASSED" in text, f"{tb.name} never reports success"
        assert "FAILED" in text, f"{tb.name} never reports failure"


# ---- filler selection -----------------------------------------------------

def test_filler_prefixes_default_includes_decap(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\n"
        f"pdk:\n  name: sky130A\n  root: {fake_pdk.root}\n",
        encoding="utf-8",
    )
    cells = RunConfig.build(config_path=cfgfile).pdk.filler_cells()
    assert any("fill_" in c for c in cells)
    assert any("decap_" in c for c in cells)


def test_filler_prefixes_override_narrows_filler_set(design, fake_pdk, tmp_path):
    """A cell that is DRC-legal in isolation can still cause spacing
    violations once the filler placer abuts it against its neighbours, so
    which cells are used as filler has to be selectable per design."""
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\n"
        f"pdk:\n  name: sky130A\n  root: {fake_pdk.root}\n"
        "  filler_prefixes: [fill]\n",
        encoding="utf-8",
    )
    cfg = RunConfig.build(config_path=cfgfile)
    assert cfg.pdk.filler_prefixes == ("fill",)
    cells = cfg.pdk.filler_cells()
    assert cells, "expected fill cells to still be discovered"
    assert all("decap" not in c for c in cells)


def test_filler_prefixes_rejects_non_string_entries(design, fake_pdk, tmp_path):
    cfgfile = tmp_path / "run.yaml"
    cfgfile.write_text(
        f"top: widget\nrtl: {design}\n"
        f"pdk:\n  name: sky130A\n  root: {fake_pdk.root}\n"
        "  filler_prefixes: [1, 2]\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="filler_prefixes"):
        RunConfig.build(config_path=cfgfile)
