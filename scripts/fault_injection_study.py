#!/usr/bin/env python3
"""Post-signoff mutation study against cached-status and candidate-bound checks."""
from __future__ import annotations
import csv, hashlib, json, shutil, sys, tempfile
from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rtl2gdsagi.artifacts import Artifact, sha256_file
from rtl2gdsagi.checks.deck_guard import audit_deck
from rtl2gdsagi.checks.klayout_drc import parse_drc_report
from rtl2gdsagi.checks.pdn import check_pdn_def
from rtl2gdsagi.evidence import GateEvidence
from rtl2gdsagi.manifest import ReleaseCandidateManifest
from rtl2gdsagi.stages import StageId
from rtl2gdsagi.state import RunState

MAIN = ROOT / "runs/signoff_final_v5"
REPAIR = ROOT / "runs/alu8_api_closure_v1"
OUTPUT = ROOT / "rtl2gdsagi_paper/evidence/fault_injection.json"
DESIGNS = ("register", "alu8", "fifo_buf")


def loaded(run_dir: Path):
    state = RunState.load(run_dir)
    signoff = json.loads((run_dir / "signoff.json").read_text())
    gates_raw = json.loads((run_dir / "gate_evidence.json").read_text())["gates"]
    gates = {StageId(k): GateEvidence(**v) for k, v in gates_raw.items()}
    candidate = ReleaseCandidateManifest(**signoff["release_candidate"])
    assert signoff["clean"] and state.status.value == "ok"
    assert all(s.status.value == "ok" for s in state.stages.values())
    return state, signoff, gates, candidate


def naive_cached_clean(run_dir: Path) -> bool:
    """The explicit weak baseline: reuse green stage flags and zero DRC count."""
    state, signoff, gates, _ = loaded(run_dir)
    drc = gates[StageId.DRC].metrics
    return (state.status.value == "ok" and signoff["clean"]
            and all(s.status.value == "ok" for s in state.stages.values())
            and drc.get("total_violations") == 0
            and gates[StageId.LVS].verdict == "pass")


def clone_artifacts(run_dir: Path, keys: tuple[str, ...], target: Path):
    state, signoff, gates, candidate = loaded(run_dir)
    arts = {k: dict(v) for k, v in candidate.artifacts.items()}
    ledger = state.artifacts
    for key in keys:
        source = ledger.get(key).path
        clone = target / f"{key}{source.suffix}"
        if source.is_dir():
            shutil.copytree(source, clone)
        else:
            shutil.copy2(source, clone)
        arts[key]["path"] = str(clone)
        ledger.put(replace(ledger.get(key), path=clone))
    return state, signoff, gates, replace(candidate, artifacts=arts), ledger


def record(name: str, repetition: int, design: str, blocked: bool, reason: str):
    return {"attack": name, "replicate": repetition, "design": design,
            "naive_cached_verdict": "CLEAN", "candidate_gate_verdict": "BLOCKED" if blocked else "CLEAN",
            "blocked": blocked, "reason": reason}


def run_study() -> list[dict]:
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="rtl2gdsagi-faults-") as tmp:
        root = Path(tmp)
        # Three independent certified candidates per attack; mutations happen
        # only in temporary copies and never alter the retained signoff bundle.
        for index, design in enumerate(DESIGNS, 1):
            run = MAIN / design
            assert naive_cached_clean(run)
            folder = root / f"r{index}"; folder.mkdir()
            state, signoff, gates, candidate, ledger = clone_artifacts(run, ("final_gds",), folder)
            gds = Path(candidate.artifacts["final_gds"]["path"])
            blob = bytearray(gds.read_bytes()); blob[100] ^= 0x01; gds.write_bytes(blob)
            problems = candidate.verify(ledger)
            results.append(record("stale_gds_after_drc", index, design, bool(problems), "; ".join(problems[:2])))

            folder = root / f"c{index}"; folder.mkdir()
            state, signoff, gates, candidate, ledger = clone_artifacts(run, ("drc_report",), folder)
            report = Path(candidate.artifacts["drc_report"]["path"])
            tree = ET.parse(report); categories = tree.getroot().find("categories")
            assert categories is not None and len(categories) > 2
            categories.remove(list(categories)[0]); tree.write(report, encoding="utf-8", xml_declaration=True)
            deck_hash = ledger.get("drc_deck").sha256
            parsed = parse_drc_report(report, expected_top=signoff["top"], deck_sha256=deck_hash)
            problems = candidate.verify(ledger)
            blocked = not parsed.clean or bool(problems)
            results.append(record("missing_drc_rule_category", index, design, blocked,
                                  "; ".join([*parsed.problems, *problems][:3])))

            folder = root / f"p{index}"; folder.mkdir()
            state, signoff, gates, candidate, ledger = clone_artifacts(run, ("pdn_def",), folder)
            pdn = Path(candidate.artifacts["pdn_def"]["path"])
            text = pdn.read_text(); start = text.index("SPECIALNETS"); end = text.index("END SPECIALNETS", start)
            section = text[start:end]
            import re
            section, removed = re.subn(r"\s+NEW\s+met[1-5]\s+\d+\s+\+\s+SHAPE\s+\w+\s+\([^)]*\)\s+via\S+", "", section)
            assert removed > 0
            pdn.write_text(text[:start] + section + text[end:])
            checked = check_pdn_def(pdn)
            problems = candidate.verify(ledger)
            blocked = not checked.ok or bool(problems)
            results.append(record("missing_pdn_via_connection", index, design, blocked,
                                  "; ".join([*checked.problems, *problems][:3])))

            folder = root / f"m{index}"; folder.mkdir()
            state, signoff, gates, candidate, ledger = clone_artifacts(run, ("layer_map",), folder)
            layer_map = Path(candidate.artifacts["layer_map"]["path"]); layer_map.unlink()
            problems = candidate.verify(ledger)
            results.append(record("missing_layer_map", index, design, bool(problems), "; ".join(problems[:2])))

            folder = root / f"l{index}"; folder.mkdir()
            state, signoff, gates, candidate, ledger = clone_artifacts(run, ("lvs_deck",), folder)
            deck = Path(candidate.artifacts["lvs_deck"]["path"])
            deck.write_text('logger.info("Congratulations! Netlists match.")\n')
            audited = audit_deck(deck, kind="lvs")
            problems = candidate.verify(ledger)
            blocked = not audited.trustworthy or bool(problems)
            results.append(record("lvs_without_compare", index, design, blocked,
                                  "; ".join([*audited.problems, *problems][:3])))

        # Replace a repaired ALU candidate's GDS with another valid run's GDS,
        # while retaining the ALU DRC/LVS records. Exercise three distinct
        # foreign candidates and leave all source bundles untouched.
        state, signoff, gates, candidate = loaded(REPAIR)
        for index, design in enumerate(DESIGNS, 1):
            foreign_state, foreign_signoff, _, _ = loaded(MAIN / design)
            arts = {k: dict(v) for k, v in candidate.artifacts.items()}
            foreign = foreign_state.artifacts.get("final_gds")
            arts["final_gds"].update(sha256=foreign.sha256, path=str(foreign.path), size=foreign.size)
            changed = replace(candidate, artifacts=arts)
            problems = gates[StageId.DRC].problems_against(
                manifest_artifacts=changed.artifacts, ledger=state.artifacts)
            history = [{"stage": "drc", "metrics": gates[StageId.DRC].metrics}]
            problems += changed.gate_binding_problems(history)
            results.append(record("foreign_gds_swapped_after_repair", index, design,
                                  bool(problems), "; ".join(problems[:3])))
    return results


def main() -> None:
    rows = run_study()
    assert len(rows) == 18
    assert all(r["blocked"] for r in rows), [r for r in rows if not r["blocked"]]
    OUTPUT.write_text(json.dumps({"replicates_per_attack": 3,
        "attack_count": 6, "naive_cached_clean_count": len(rows),
        "candidate_blocked_count": sum(r["blocked"] for r in rows),
        "false_clean_prevented": sum(r["blocked"] for r in rows),
        "results": rows}, indent=2) + "\n")
    csv_path = OUTPUT.with_suffix(".csv")
    with csv_path.open("w") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(json.dumps({"rows": len(rows), "naive_clean": len(rows),
                      "candidate_blocked": sum(r["blocked"] for r in rows),
                      "by_attack": {n: sum(r["blocked"] for r in rows if r["attack"] == n)
                                    for n in sorted({r["attack"] for r in rows})}}, indent=2))

if __name__ == "__main__":
    main()
