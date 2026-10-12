#!/usr/bin/env python3
"""Validate retained signoff evidence and generate CSV, JSON and paper assets."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rtl2gdsagi.evidence import GateEvidence, certification_id, lineage_problems
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import RunState


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(run_dir: Path) -> dict:
    state = RunState.load(run_dir)
    bundle = json.loads((run_dir / "signoff.json").read_text())
    evidence = json.loads((run_dir / "gate_evidence.json").read_text())
    candidate = ReleaseCandidateManifest(**bundle["release_candidate"])
    records = {StageId(k): GateEvidence(**v) for k, v in evidence["gates"].items()}
    problems = candidate.verify(state.artifacts) + lineage_problems(records)
    for record in records.values():
        problems += record.problems_against(manifest_artifacts=candidate.artifacts, ledger=state.artifacts)
    assert not problems, (run_dir, problems)
    assert state.status.value == "ok" and all(s.status.value == "ok" for s in state.stages.values())
    assert bundle["clean"] and not bundle["problems"] and bundle["certification"]["full_certification"]
    assert candidate.candidate_id == evidence["candidate_id"] == bundle["candidate_id"]
    assert certification_id(candidate.candidate_id, records) == evidence["certification_id"]

    events = [json.loads(line) for line in (run_dir / "run.jsonl").read_text().splitlines()]
    def metric(stage: str) -> dict:
        checks = [e for e in events if e.get("event") == "result_check" and e.get("stage") == stage]
        assert checks and checks[-1]["ok"], (stage, checks)
        return checks[-1]
    routed = state.artifacts.get("routed_def").path.read_text()
    units = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", routed)[1])
    coords = [int(x) for x in re.search(r"DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", routed).groups()]
    route_log = (run_dir / "stages/12_routing/attempt_01.log").read_text()
    # Use the latest attempt log after an IR repair, rather than an old route.
    route_logs = sorted((run_dir / "stages/12_routing").glob("attempt_*.log"))
    route_log = route_logs[-1].read_text()
    lengths = re.findall(r"^Total wire length = ([\d.]+) um\.", route_log, re.MULTILINE)
    assert lengths, "router wire-length measurement missing"
    calls = [e for e in events if e.get("event") == "api_call" and e.get("model") != "scripted"]
    row = {
        "design": bundle["top"], "run_dir": str(run_dir.relative_to(ROOT)), "run_id": state.run_id,
        "stages_passed": len(state.stages), "clean": bundle["clean"],
        "synthesis_cells": metric("synthesis")["cells"],
        "synthesis_area_um2": metric("synthesis")["area_um2"],
        "die_area_um2": (coords[2] - coords[0]) * (coords[3] - coords[1]) / units**2,
        "routed_components": int(re.search(r"^COMPONENTS (\d+)", routed, re.MULTILINE)[1]),
        "wire_length_um": float(lengths[-1]),
        "setup_wns_ns": metric("sta_signoff")["setup_wns"],
        "hold_wns_ns": metric("sta_signoff")["hold_wns"],
        "setup_tns_ns": metric("sta_signoff")["setup_tns"],
        "hold_tns_ns": metric("sta_signoff")["hold_tns"],
        "spef_nets": metric("extraction")["spef_net_count"],
        "spef_coverage": metric("extraction")["coverage"],
        "route_violations": metric("routing")["route_violations"],
        "drc_violations": metric("drc")["total_violations"],
        "initial_drc_violations": [e for e in events if e.get("event") == "result_check" and e.get("stage") == "drc"][0]["total_violations"],
        "drc_categories": metric("drc")["declared_categories"],
        "lvs_match": records[StageId.LVS].verdict == "pass",
        "lec_synthesis_partitions": metric("lec_synth")["partitions_proved"],
        "lec_route_partitions": metric("lec_route")["partitions_proved"],
        "antenna_net_violations": metric("antenna")["antenna_net_violations"],
        "antenna_pin_violations": metric("antenna")["antenna_pin_violations"],
        "authoritative_testbenches": metric("sim")["authoritative_passed"],
        "gds_bytes": state.artifacts.get("final_gds").path.stat().st_size,
        "elapsed_s": state.ended_at - state.started_at,
        "model_calls": len(calls),
        "provider_model": calls[0]["model"] if calls else "disabled",
        "model_input_tokens": sum(e["input_tokens"] for e in calls),
        "model_output_tokens": sum(e["output_tokens"] for e in calls),
        "candidate_id": candidate.candidate_id, "certification_id": evidence["certification_id"],
        "gds_sha256": sha(state.artifacts.get("final_gds").path),
        "signoff_sha256": sha(run_dir / "signoff.json"),
        "gate_evidence_sha256": sha(run_dir / "gate_evidence.json"),
        "run_log_sha256": sha(run_dir / "run.jsonl"),
        "timing_checkpoints": {s: {k: metric(s)[k] for k in ("setup_wns", "hold_wns")} for s in ("sta_pre", "sta_postcts", "sta_signoff")},
        "repair_verifications": bundle["certification"]["repair_verifications"],
        "tools": candidate.tools,
        "timing_parameters": bundle["ir"]["sdc"],
        "physical_parameters": {k: bundle["ir"][k] for k in ("floorplan", "placement", "cts", "routing")},
    }
    for gate in (StageId.DRC, StageId.LVS):
        assert records[gate].consumed["final_gds"] == row["gds_sha256"]
    return row


def tables(rows: list[dict], generated: Path) -> None:
    heading = "\\begin{table}[htbp]\\centering\\small\\setlength{\\tabcolsep}{4pt}\n"
    a = [heading, "\\caption{Measured implementation results. Cell area is the synthesis-library area; die area comes from routed DEF. Timing uses extracted parasitics.}\\label{tab:qor}\n",
         "\\begin{tabular}{@{}lrrrrr@{}}\\toprule\nDesign & Cells & Cell area & Die area & Setup slack & Hold slack \\\\\n",
         " & & ($\\mu$m$^2$) & ($\\mu$m$^2$) & (ns) & (ns) \\\\\n\\midrule\n"]
    b = [heading, "\\caption{Native verification and execution outcomes. Every design passed all 21 stages, both equivalence boundaries, LVS, and its authoritative testbench.}\\label{tab:gates}\n",
         "\\begin{tabular}{@{}lrrrrr@{}}\\toprule\nDesign & Route/DRC & Antenna & SPEF nets & GDS & Runtime \\\\\n",
         " & violations & net/pin & & (KiB) & (s) \\\\\n\\midrule\n"]
    for r in rows:
        name = r["design"].replace("_", "\\_")
        a.append(f"{name} & {r['synthesis_cells']} & {r['synthesis_area_um2']:.2f} & {r['die_area_um2']:.2f} & {r['setup_wns_ns']:.3f} & {r['hold_wns_ns']:.3f} \\\\\n")
        b.append(f"{name} & {r['route_violations']}/{r['drc_violations']} & {r['antenna_net_violations']}/{r['antenna_pin_violations']} & {r['spef_nets']} & {r['gds_bytes']/1024:.1f} & {r['elapsed_s']:.1f} \\\\\n")
    for text, name in ((a, "qor_table.tex"), (b, "signoff_table.tex")):
        text.append("\\bottomrule\\end{tabular}\\end{table}\n")
        (generated / name).write_text("".join(text))


def plot(rows: list[dict], destination: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(4.8, 2.6), sharex=True)
    stages = ("sta_pre", "sta_postcts", "sta_signoff")
    colors = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#333333")
    for r, color in zip(rows, colors):
        for ax, kind in zip(axes, ("setup", "hold")):
            ax.plot(range(3), [r["timing_checkpoints"][s][kind + "_wns"] for s in stages], marker="o", markersize=3, color=color, label=r["design"])
    for ax, label in zip(axes, ("Setup WNS (ns)", "Hold WNS (ns)")):
        ax.set_ylabel(label); ax.set_xticks(range(3), ("Pre-layout", "Post-CTS", "Post-route"))
        ax.grid(axis="y", color="0.88", linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=7,
               frameon=False, columnspacing=1.2, handlelength=1.5)
    fig.tight_layout(rect=(0, 0.18, 1, 1), pad=0.7)
    fig.savefig(destination, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=ROOT / "rtl2gdsagi_paper/evidence/experiment_manifest.json")
    p.add_argument("--paper-dir", type=Path, default=ROOT / "rtl2gdsagi_paper")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_signoff_benchmark import source_identity
    # The retained physical runs were produced from one internally consistent
    # source snapshot. Later corrective edits (including rollback re-registration
    # of PDK evidence) are recorded separately; do not silently relabel those
    # old runs as if they had used today's source.
    current_source_sha256 = source_identity()
    assert manifest.get("consistent_source", True), "source changed during selected run batch"
    for batch_path in manifest.get("batch_manifests", []):
        batch = json.loads((ROOT / batch_path).read_text())
        assert batch["consistent_source"] and batch["source_sha256"] == manifest["source_sha256"], batch_path
    expected_controls = {"counter_grouped": "PASS", "shift_grouped": "PASS", "counter_mutant": "FAIL"}
    for key, expected in expected_controls.items():
        marker = ROOT / manifest["formal_controls"][key]
        assert marker.is_file() and marker.name == expected
        assert f"DONE ({expected}, rc=" in (marker.parent / "logfile.txt").read_text()
    rows = [extract(ROOT / r["run_dir"]) for r in manifest["selected_runs"]]
    repair_run = extract(ROOT / manifest["repair_run"])
    assert len(rows) >= 5 and len({r["design"] for r in rows}) == len(rows)
    suite_path = args.paper_dir / "evidence/pytest_final_release.xml"
    suite = ET.parse(suite_path).getroot().find("testsuite")
    counts = {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    assert counts["failures"] == counts["errors"] == 0
    generated = args.paper_dir / "generated"; generated.mkdir(exist_ok=True)
    metrics = {"manifest": manifest, "runs": rows, "repair_run": repair_run,
               "tests": counts, "pytest_sha256": sha(suite_path),
               "current_source_sha256": current_source_sha256,
               "source_matches_extraction": manifest["source_sha256"] == current_source_sha256}
    (args.paper_dir / "evidence/live_results.json").write_text(json.dumps(metrics, indent=2) + "\n")
    scalar_keys = [k for k in rows[0] if k not in ("timing_checkpoints", "repair_verifications", "tools", "timing_parameters", "physical_parameters")]
    with (args.paper_dir / "evidence/signoff_metrics.csv").open("w") as fh:
        writer = csv.DictWriter(fh, fieldnames=scalar_keys);writer.writeheader()
        writer.writerows({k: r[k] for k in scalar_keys} for r in rows)
    alu = repair_run
    repair = next(r for r in alu["repair_verifications"] if r["stage"] == "drc")
    assert repair["rtl_identity_preserved"] and repair["repair_verified"]
    macros = {"DesignCount": len(rows), "StageCount": rows[0]["stages_passed"], "TestPasses": counts["passed"], "TestSkipped": counts["skipped"],
              "CellMin": min(r["synthesis_cells"] for r in rows), "CellMax": max(r["synthesis_cells"] for r in rows),
              "SetupMin": f"{min(r['setup_wns_ns'] for r in rows):.3f}", "HoldMin": f"{min(r['hold_wns_ns'] for r in rows):.3f}",
              "RuleCount": min(r["drc_categories"] for r in rows),
              "ModelCalls": repair_run["model_calls"],
              "ModelInputTokens": repair_run["model_input_tokens"], "ModelOutputTokens": repair_run["model_output_tokens"],
              "SourceShort": manifest["source_sha256"][:12], "InitialAluDRC": alu["initial_drc_violations"],
              "PaddingBefore": repair["previous_values"]["placement.padding_sites"],
              "PaddingAfter": repair["new_values"]["placement.padding_sites"],
              "ClockPeriod": rows[0]["timing_parameters"]["default_clock_period_ns"],
              "ClockUncertainty": rows[0]["timing_parameters"]["clock_uncertainty_ns"],
              "OutputLoad": rows[0]["timing_parameters"]["output_load_pf"],
              "RepairRuntime": f"{repair_run['elapsed_s']:.1f}"}
    macros["RepairModel"] = repair_run["provider_model"]
    (generated / "live_results.tex").write_text("% Generated from validated signoff bundles.\n" + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items()))
    tables(rows, generated)
    figures = args.paper_dir / "figures";figures.mkdir(exist_ok=True)
    plot(rows, figures / "timing_checkpoints.pdf")
    print(json.dumps({r['design']: {k: r[k] for k in ('clean', 'synthesis_cells', 'setup_wns_ns', 'hold_wns_ns', 'drc_violations', 'elapsed_s')} for r in rows}, indent=2))


if __name__ == "__main__":
    main()
