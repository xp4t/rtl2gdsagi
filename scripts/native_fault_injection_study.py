#!/usr/bin/env python3
"""Native false-pass fixtures plus production parser and lineage evaluation.

This controlled comparator counts zero DRC markers or an LVS match message
without checking rule coverage or consumed candidate identity. It is not a
comparison against a named external EDA flow.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rtl2gdsagi.artifacts import Artifact, sha256_file
from rtl2gdsagi.checks.deck_guard import audit_deck
from rtl2gdsagi.checks.klayout_drc import parse_drc_report
from rtl2gdsagi.checks.klayout_lvs import parse_lvs_report
from rtl2gdsagi.checks.pdn import check_pdn_def
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.evidence import GateEvidence
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.pdk import PDKConfig
from rtl2gdsagi.runner import Orchestrator
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import RunState

IMAGE = "ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69"
BASE = ROOT / "runs/signoff_final_v5"
PDK_ROOT = Path("/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A")
OUT = ROOT / "runs/native_fault_injection"

def execute(script: Path, folder: Path, extra: list[str] | None = None):
    cmd = ["docker", "run", "--rm", "-u", "1000:1000", "-v", f"{ROOT}:{ROOT}",
           "-v", f"{PDK_ROOT}:{PDK_ROOT}:ro", "-w", str(folder),
           "--entrypoint", "klayout", IMAGE, "-b", "-r", str(script), *(extra or [])]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    (folder / (script.stem + ".native.log")).write_text(result.stdout + result.stderr)
    (folder / (script.stem + ".command.json")).write_text(json.dumps(cmd, indent=2) + "\n")
    return result

def drc(gds: Path, top: str, folder: Path, deck: Path):
    report = folder / "drc.lyrdb"
    args = ["-rd", f"input={gds}", "-rd", f"top_cell={top}", "-rd", f"report={report}",
            "-rd", "thr=4", "-rd", "feol=true", "-rd", "beol=true", "-rd",
            "offgrid=true", "-rd", "floating_met=true"]
    run = execute(deck, folder, args)
    raw = ET.parse(report).getroot() if report.exists() else None
    count = len(raw.findall("items/item")) if raw is not None else None
    naive = run.returncode == 0 and count == 0
    return run, report, naive, count

def load(design: str):
    folder = BASE / design
    state = RunState.load(folder)
    bundle = json.loads((folder / "signoff.json").read_text())
    cand = ReleaseCandidateManifest(**bundle["release_candidate"])
    records = json.loads((folder / "gate_evidence.json").read_text())["gates"]
    assert bundle["clean"]
    return state, cand, GateEvidence(**records["drc"])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-run", type=Path, default=ROOT / "runs/alu8_drc_api_repeat_v3")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    pdk = PDKConfig.discover("sky130A", root=PDK_ROOT)
    approved_deck = pdk.drc_deck_path
    rows = []
    def record(attack, rep, design, naive, problems, **metrics):
        row = dict(attack=attack, replicate=rep, design=design,
                   naive_clean=naive, blocked=bool(problems), reasons=list(problems), **metrics)
        rows.append(row)
        print(json.dumps({k:row[k] for k in ("attack","replicate","naive_clean","blocked")}), flush=True)

    for rep, design in enumerate(("register", "alu8", "fifo_buf"), 1):
        state, candidate, gate = load(design)
        gds = state.artifacts.get("final_gds").path
        # A same-top, physically different, clean ALU layout is actually fed to
        # native DRC. The zero-marker report has no GDS digest of its own.
        folder=OUT/f"stale_{rep}"; folder.mkdir(exist_ok=True)
        astate, acandidate, agate = load("alu8")
        stale=ROOT/"runs/alu8_timing_api_v4/stages/15_gdsout/alu8.gds"
        native, report, naive, count=drc(stale,"alu8",folder,approved_deck)
        actual=Artifact.capture("final_gds",stale,"injected_input")
        consumed={**agate.consumed,"final_gds":actual.sha256}
        produced={**agate.produced,"drc_report":sha256_file(report)}
        changed=replace(agate,consumed=consumed,produced=produced,
                        report_sha256=sha256_file(report),
                        metrics={**agate.metrics,"checked_gds_sha256":actual.sha256})
        problems=changed.problems_against(manifest_artifacts=acandidate.artifacts,
                                         ledger=astate.artifacts)
        judge=object.__new__(Orchestrator)
        judge.cfg=SimpleNamespace(top="alu8",pdk=pdk)
        judge.ledger=astate.artifacts
        ctx=SimpleNamespace(work_dir=folder,out=lambda key:str(report))
        verdict=judge._judge_drc(ToolRun(argv=native.args,returncode=native.returncode,
                                       stdout=native.stdout,stderr=native.stderr),ctx)
        assert not verdict.ok, "the production DRC judge must block the native stale input"
        problems.append(verdict.summary)
        assert any("final_gds" in p for p in problems)
        record("stale_gds_fed_to_drc",rep,"alu8",naive,problems,
               native_exit=native.returncode,drc_markers=count,
               consumed_gds_sha256=actual.sha256,selected_gds_sha256=astate.artifacts.get("final_gds").sha256)

        # Disable all FEOL checks in a copy of the real deck and execute it.
        folder=OUT/f"rules_{rep}"; folder.mkdir(exist_ok=True)
        deck=folder/"missing_feol.drc"
        text,n=re.subn(r"(FEOL\s*=\s*)true",r"\1false",approved_deck.read_text())
        assert n>0; deck.write_text(text)
        native,report,naive,count=drc(gds,design,folder,deck)
        audit=audit_deck(deck,kind="drc")
        parsed=parse_drc_report(report,expected_top=design,deck_sha256=sha256_file(approved_deck))
        record("drc_deck_missing_feol_rules",rep,design,naive,[*audit.problems,*parsed.problems],
               native_exit=native.returncode,drc_markers=count,categories=parsed.declared_categories)

        # Native LVS prints a match and writes a database-shaped file without
        # performing compare. The production parser requires cross-references.
        folder=OUT/f"lvs_{rep}"; folder.mkdir(exist_ok=True)
        deck=folder/"no_compare.rb"; report=folder/"lvs.lvsdb"
        deck.write_text(f'File.write({json.dumps(str(report))}, "#%lvsdb-klayout\\nJ(\\n W({design})\\n)\\n")\nputs "Congratulations! Netlists match."\n')
        native=execute(deck,folder)
        audit=audit_deck(deck,kind="lvs")
        parsed=parse_lvs_report(report,log_text=native.stdout+native.stderr,
                               exit_code=native.returncode,expected_top=design,
                               deck_trustworthy=audit.trustworthy)
        naive=native.returncode==0 and "Netlists match" in native.stdout
        record("lvs_no_real_compare",rep,design,naive,[*audit.problems,*parsed.problems],
               native_exit=native.returncode,xref_circuits=parsed.xref_circuits)

        folder=OUT/f"pdn_{rep}"; folder.mkdir(exist_ok=True)
        pdn=folder/"missing_connection.def"; text=state.artifacts.get("pdn_def").path.read_text()
        start=text.index("SPECIALNETS"); end=text.index("END SPECIALNETS",start)
        section,n=re.subn(r"\s+NEW\s+met[1-5]\s+\d+\s+\+\s+SHAPE\s+\w+\s+\([^)]*\)\s+via\S+","",text[start:end])
        assert n>0; pdn.write_text(text[:start]+section+text[end:])
        checked=check_pdn_def(pdn)
        record("missing_pdn_via_connection",rep,design,pdn.stat().st_size>0,
               checked.problems,removed_via_entries=n,remaining_vias=checked.via_count,
               baseline="cached_green_stage_plus_nonempty_DEF")

        # Omitting map_file yields real GDS with default, incorrect routing
        # layer numbers. Native DRC can still report zero on standard cells.
        folder=OUT/f"map_{rep}"; folder.mkdir(exist_ok=True)
        script=folder/"gdsout_nomap.py"; wrong=folder/f"{design}.gds"
        original=BASE/design/"stages/15_gdsout/gdsout.py"
        text=re.sub(r"^cfg.map_file = .*\n","",original.read_text(),flags=re.M)
        text=text.replace(str(gds),str(wrong)); script.write_text(text)
        native_stream=execute(script,folder)
        native,report,naive,count=drc(wrong,design,folder,approved_deck)
        judge=object.__new__(Orchestrator); judge.cfg=SimpleNamespace(top=design,pdk=pdk)
        outputs={"final_gds":wrong,"gds_summary":folder/"gds_summary.json"}
        ctx=SimpleNamespace(out=lambda key: str(outputs[key]))
        verdict=judge._judge_gds(ToolRun(argv=native_stream.args,returncode=native_stream.returncode,
                                       stdout=native_stream.stdout,stderr=native_stream.stderr),ctx)
        record("missing_layer_map_streamout",rep,design,naive,
               [] if verdict.ok else [verdict.summary],native_stream_exit=native_stream.returncode,
               native_drc_exit=native.returncode,drc_markers=count)

    repair=args.repair_run.resolve()
    state=RunState.load(repair)
    signoff=json.loads((repair/"signoff.json").read_text()); assert signoff["clean"]
    candidate=ReleaseCandidateManifest(**signoff["release_candidate"])
    gates=json.loads((repair/"gate_evidence.json").read_text())["gates"]
    gate=GateEvidence(**gates["drc"])
    assert signoff["certification"]["repair_verifications"]
    for rep,foreign in enumerate((ROOT/"runs/alu8_timing_api_v4/stages/15_gdsout/alu8.gds",
                                 BASE/"register/stages/15_gdsout/register.gds",
                                 BASE/"fifo_buf/stages/15_gdsout/fifo_buf.gds"),1):
        artifacts={k:dict(v) for k,v in candidate.artifacts.items()}
        artifacts["final_gds"].update(path=str(foreign),sha256=sha256_file(foreign),size=foreign.stat().st_size)
        rebound=replace(candidate,artifacts=artifacts)
        problems=gate.problems_against(manifest_artifacts=rebound.artifacts,ledger=state.artifacts)
        assert any("final_gds" in p for p in problems)
        record("artifact_swap_after_verified_repair",rep,"alu8",True,problems,
               baseline="accept_model_fix_then_reuse_prior_clean_DRC_LVS",repair_run=str(repair.relative_to(ROOT)))
    from run_signoff_benchmark import source_identity
    result={"source_sha256":source_identity(),"native_tool_image":IMAGE,"replicates_per_attack":3,"attack_classes":6,
            "naive_clean":sum(r["naive_clean"] for r in rows),
            "candidate_blocked":sum(r["blocked"] for r in rows),"results":rows}
    (ROOT/"rtl2gdsagi_paper/evidence/native_fault_injection.json").write_text(json.dumps(result,indent=2)+"\n")
    assert len(rows)==18 and all(r["naive_clean"] and r["blocked"] for r in rows),result

if __name__=="__main__": main()
