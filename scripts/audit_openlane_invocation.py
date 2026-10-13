#!/usr/bin/env python3
"""Bounded native OpenLane KLayout invocation audit; no production imports.

All persistent writes are confined to the audit directory and its two evidence
files. Public static source receipts must already be present. No API calls,
full flow, ALU trace, automatic retry, or modifications of retained controls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "runs/openlane_invocation_audit"
EVIDENCE = ROOT / "rtl2gdsagi_paper/evidence/openlane_invocation_audit.json"
REPORT = ROOT / "rtl2gdsagi_paper/evidence/OPENLANE_INVOCATION_AUDIT.md"
OLD = ROOT / "runs/external_fault_coverage/retained_native_v1"
NATIVE = OLD / "native_sources"
COMMIT = "ff5509f65b17bfa4068d5336495ab1718987ff69"
IMAGE = "ghcr.io/the-openroad-project/openlane@sha256:d7e2bdd21e757e3f0b15d6ea08c36d9a96653c31b4fb2fafd4de88c9b6a3f3fa"
PDK_BASE = Path("/home/vlsi/.volare/volare/sky130/versions")
PDK = PDK_BASE / "bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A"
PIN_PDK = PDK_BASE / "0fe599b2afb6708d281543108caf8310912f54af/sky130A"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identity(path):
    p = Path(path)
    return {"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size}


def writable(path):
    p = Path(path).absolute()
    if not (p.is_relative_to(RAW) or p in (EVIDENCE, REPORT)):
        raise ValueError("Outside authorized write scope: " + str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write(path, text):
    writable(path).write_text(text)


def write_json(path, value):
    write(path, json.dumps(value, indent=2) + "\n")


def tcl(value):
    s = str(value)
    if any(c in s for c in "{}\n"):
        raise ValueError(s)
    return "{" + s + "}"


def metrics(path):
    if not path.exists():
        return {"report_exists": False, "categories": None, "markers": None}
    root = ET.parse(path).getroot()
    cats = [{"name": c.findtext("name"), "description": c.findtext("description")}
            for c in root.findall("categories/category")]
    items = root.findall("items/item")
    counts = Counter((i.findtext("category") or "").strip("'") for i in items)
    return {"report_exists": True, "categories": len(cats), "markers": len(items),
            "distinct_name_description_pairs": len({(c["name"], c["description"]) for c in cats}),
            "category_inventory": cats, "markers_by_category": dict(sorted(counts.items())),
            "top_cell": root.findtext("top-cell"), "generator": root.findtext("generator")}


class Audit:
    def __init__(self, run_id, timeout):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("Unsafe run id")
        self.out = RAW / run_id
        self.out.mkdir(parents=True, exist_ok=False)
        self.timeout = timeout
        self.data = {
            "schema_version": 1, "status": "running", "started_utc": now(),
            "scope": "Independent synthetic checker controls and retained control replay only; no ALU trace or full flow.",
            "material_passport": {"origin_skill": "experiment-agent", "origin_mode": "run",
                                  "verification_status": "UNVERIFIED", "version_label": "openlane_invocation_audit_v1"},
            "delegation": {"requested_role": "ARS code_runner_agent", "execution": "inline",
                           "native_subagent_available": False, "independent_agent_judgement_claim": False},
            "classification_definitions": {
                "SUPPORTED": "Specified configuration executes the target rule and passes paired violating/clean controls; report versus rejection scope is explicit.",
                "NOTSUPPORTED": "Source and/or bounded controls establish that this invocation does not implement or activate the named obligation. Never a claim about all OpenLane configurations.",
                "NOTASSESSED": "No applicable execution, insufficient controls, or wider integration not exercised."},
            "image_reference": IMAGE, "openlane_commit": COMMIT,
            "script": identity(__file__), "run_directory": str(self.out),
            "invocation": {"argv": [sys.executable, *sys.argv], "cwd": str(ROOT)},
            "executions": [], "controls": [], "obligations": [], "source_confirmation": [],
            "full_flow": {"classification": "NOTASSESSED", "executed": False},
            "maintainer_endorsement": "None requested or claimed; static public maintainer-owned source/docs only.",
        }
        shutil.copyfile(__file__, writable(self.out / "runner_executed.py"))
        self.data["execution_script_snapshot"] = identity(self.out / "runner_executed.py")
        self.protected = sorted({p for base in (OLD, ROOT / "runs/external_fault_coverage/discovery")
                                 for p in base.rglob("*") if p.is_file()} |
                                {ROOT / "scripts/followup_openlane_fault_study.py"} |
                                {p for base in (PDK, PIN_PDK) for p in (
                                    base / "SOURCES", base / "libs.tech/openlane/config.tcl",
                                    base / "libs.tech/klayout/drc/sky130A.lydrc",
                                    base / "libs.tech/klayout/drc/sky130A_mr.drc")})
        self.before = [identity(p) for p in self.protected]
        write_json(self.out / "protected_before.json", self.before)
        self.checkpoint()

    def checkpoint(self):
        self.data["updated_utc"] = now()
        write_json(self.out / "checkpoint.json", self.data)

    def run(self, name, command):
        folder = self.out / "executions" / name
        folder.mkdir(parents=True, exist_ok=False)
        write_json(folder / "command.json", {"argv": command, "shell": shlex.join(command), "cwd": str(ROOT)})
        start = time.monotonic()
        print(json.dumps({"starting": name, "timeout_seconds": self.timeout}), flush=True)
        with (folder / "stdout").open("wb") as out, (folder / "stderr").open("wb") as err:
            proc = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err)
            write_json(folder / "process.json", {"pid": proc.pid, "started_utc": now()})
            timed_out = False
            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if elapsed >= self.timeout:
                    print(json.dumps({"hard_timeout": name, "action": "terminate audit container/process"}), flush=True)
                    timed_out = True
                    if command[:2] == ["docker", "run"]:
                        cleanup = ["docker", "rm", "-f", command[command.index("--name") + 1]]
                        write_json(folder / "timeout_cleanup.command.json", cleanup)
                        subprocess.run(cleanup, stdout=out, stderr=err, timeout=30)
                    proc.kill()
                    proc.wait()
                    break
                if elapsed and int(elapsed) % 30 == 0 and int(elapsed) > 0:
                    print(json.dumps({"alive": name, "pid": proc.pid, "elapsed_seconds": round(elapsed)}), flush=True)
                time.sleep(1)
        row = {"id": name, "argv": command, "exit_code": proc.returncode, "timed_out": timed_out,
               "elapsed_seconds": round(time.monotonic() - start, 3),
               "stdout": identity(folder / "stdout"), "stderr": identity(folder / "stderr")}
        write_json(folder / "result.json", row)
        self.data["executions"].append(row)
        self.checkpoint()
        print(json.dumps({"finished": name, "exit_code": proc.returncode}), flush=True)
        return row

    def docker(self, name, entry, args):
        # Only this run directory is writable on the host. Inputs remain read-only.
        command = ["docker", "run", "--rm", "--network", "none", "--read-only",
                   "--tmpfs", "/tmp:rw", "--name", f"ol-inv-audit-{name}-{os.getpid()}",
                   "-u", f"{os.getuid()}:{os.getgid()}",
                   "-v", f"{ROOT}:{ROOT}:ro", "-v", f"{self.out}:{self.out}:rw",
                   "-v", f"{PDK}:{PDK}:ro", "-v", f"{PIN_PDK}:{PIN_PDK}:ro",
                   "-w", str(self.out), "--entrypoint", entry, IMAGE, *map(str, args)]
        return self.run(name, command)

    def discover(self):
        row = self.run("image_identity", ["docker", "image", "inspect", IMAGE])
        if row["exit_code"] != 0:
            raise RuntimeError("Pinned local image unavailable; no automatic retry")
        meta = json.loads(Path(row["stdout"]["path"]).read_text())[0]
        if IMAGE not in meta["RepoDigests"]:
            raise RuntimeError("Image digest mismatch")
        self.data["image"] = {k: meta.get(k) for k in ("Id", "RepoDigests", "Created", "Architecture", "Os")}
        files = ["scripts/klayout/run_drc.sh", "scripts/tcl_commands/klayout.tcl", "configuration/general.tcl",
                 "flow.tcl", "dependencies/tool_metadata.yml"]
        command = ["sh", "-c", "klayout -v; tclsh <<'TCL'\nputs [info patchlevel]\nTCL\n"
                   "sha256sum /build/bin/klayout " + " ".join("/openlane/" + p for p in files)]
        self.docker("tool_and_native_versions", command[0], command[1:])
        versions = Path(self.data["executions"][-1]["stdout"]["path"]).read_text()
        public = RAW / "public_sources"
        mapping = dict(zip(files, ["openlane_run_drc.sh", "openlane_klayout.tcl", "openlane_general.tcl",
                                   "openlane_flow.tcl", "openlane_tool_metadata.yml"]))
        receipts = json.loads((public / "fetch_receipts.json").read_text())
        self.data["public_source_fetches"] = receipts
        for relative, name in mapping.items():
            h = sha(NATIVE / relative)
            match = h == sha(public / name) and h in versions
            self.data["source_confirmation"].append({"retained": identity(NATIVE / relative),
                "public": identity(public / name), "image_sha256_observed": h in versions,
                "byte_match": match, "url": next(r["url"] for r in receipts if Path(r["file"]).name == name)})
            if not match:
                raise RuntimeError("Native/public source mismatch: " + relative)
        legacy = PDK / "libs.tech/klayout/drc/sky130A.lydrc"
        public_legacy = public / "open_pdks_pinned_sky130.lydrc"
        self.data["legacy_deck_public_match"] = {
            "selected": identity(legacy), "pinned": identity(PIN_PDK / "libs.tech/klayout/drc/sky130A.lydrc"),
            "public": identity(public_legacy),
            "all_byte_identical": sha(legacy) == sha(public_legacy) == sha(PIN_PDK / "libs.tech/klayout/drc/sky130A.lydrc")}
        self.data["pdks"] = {"selected": str(PDK), "openlane_dependency_pin": str(PIN_PDK),
                             "inputs": [identity(p) for p in self.protected if p.is_relative_to(PDK_BASE)]}
        # Evaluate installed PDK configs without redefining any OpenLane proc.
        for label, pdk in (("selected", PDK), ("dependency_pin", PIN_PDK)):
            folder = self.out / "config_probes" / label
            folder.mkdir(parents=True)
            script = folder / "probe.tcl"
            write(script, "set ::env(PDK_ROOT) " + tcl(pdk.parent) + "\nset ::env(PDK) {sky130A}\n"
                  "source /openlane/configuration/general.tcl\nsource " + tcl(pdk / "libs.tech/openlane/config.tcl") + "\n"
                  "foreach key {RUN_KLAYOUT_DRC RUN_MAGIC_DRC PRIMARY_SIGNOFF_TOOL KLAYOUT_DRC_TECH_SCRIPT KLAYOUT_DRC_RUNSET KLAYOUT_DRC_OPTIONS} {\n"
                  " if {[info exists ::env($key)]} {puts \"$key=$::env($key)\"} else {puts \"$key=<UNSET>\"}\n}\n")
            run = self.docker("config_" + label, "tclsh", [script])
            if run["exit_code"] != 0:
                raise RuntimeError("Config evaluation failed; see retained output")
            config = dict(line.split("=", 1) for line in Path(run["stdout"]["path"]).read_text().splitlines() if "=" in line)
            self.data.setdefault("evaluated_config", {})[label] = config
        raw_options = self.data["evaluated_config"]["selected"]["KLAYOUT_DRC_OPTIONS"].split()
        opts = dict(zip(raw_options[::2], raw_options[1::2]))
        self.flags = {"feol": opts["feol"], "beol": opts["beol"], "offgrid": opts["offgrid"],
                      "seal": opts["seal"], "floating_met": opts["floating_metal"]}
        self.data["intended_pdk_options"] = {"raw": opts, "deck_runtime_variables": self.flags,
            "mapping": "PDK floating_metal maps to deck $floating_met; native pinned wrapper consumes neither options nor runset.",
            "stock_active_invocation": "No active stock KLayout DRC config: default RUN_KLAYOUT_DRC=0; PDK lacks the wrapper's KLAYOUT_DRC_TECH_SCRIPT.",
            "legacy_selection": "Explicit supported-interface override to a shipped compatible deck, not proven stock default deck selection."}
        self.checkpoint()

    def make_fixtures(self):
        folder = self.out / "fixtures"
        folder.mkdir()
        for retained, name in (("dirty", "metal_positive"), ("good", "metal_negative")):
            src = OLD / f"cases/controls_layouts/{retained}.gds"
            shutil.copyfile(src, writable(folder / (name + ".gds")))
        generator = folder / "make_controls.py"
        write(generator, "import pya\nfrom pathlib import Path\n"
              f"out = Path({str(folder)!r})\n"
              "for name, layer, box in [('poly_positive',66,(0,0,50,1000)),"
              "('poly_negative',66,(0,0,1000,1000)),"
              "('grid_positive',68,(1,0,1001,1000)),"
              "('grid_negative',68,(0,0,1000,1000))]:\n"
              " ly=pya.Layout(); ly.dbu=0.001; top=ly.create_cell('control')\n"
              " top.shapes(ly.layer(layer,20)).insert(pya.Box(*box))\n"
              " ly.write(str(out/(name+'.gds')))\n")
        row = self.docker("generate_controls", "klayout", ["-b", "-r", generator])
        if row["exit_code"] != 0:
            raise RuntimeError("Fixture generation failed; no automatic retry")
        self.data["fixtures"] = {p.stem: identity(p) for p in sorted(folder.glob("*.gds"))}
        self.data["fixture_design"] = {
            "metal": "Retained 68/20 0.05um square versus 1um square; positive violates m1.1 and m1.6.",
            "poly": "66/20 rectangle 0.05um by 1um versus 1um square; target poly.1a (minimum 0.15um).",
            "grid": "68/20 1um square shifted by 0.001um in x versus grid-aligned square; target m1_OFFGRID (0.005um grid).",
            "negative_scope": "Clean only for these executed deck configurations; isolated synthetic geometries, no circuit or tapeout claim."}
        self.adapter = self.out / "modern_pdk_options_adapter.drc"
        lines = ["# Audit-only compatibility adapter; original PDK deck is evaluated unchanged."]
        lines += [f"${k} = {json.dumps(v)}" for k, v in self.flags.items()]
        lines += ["$top_cell = 'control'", "$thr = '4'",
                  f"audit_deck = {json.dumps(str(PDK / 'libs.tech/klayout/drc/sky130A_mr.drc'))}",
                  "eval(File.read(audit_deck), binding, audit_deck)"]
        write(self.adapter, "\n".join(lines) + "\n")

    def harness(self, folder, deck, probe=False):
        setting = {"OPENLANE_ROOT": "/openlane", "SCRIPTS_DIR": "/openlane/scripts",
                   "RUN_DIR": str(folder), "CURRENT_INDEX": "0", "EXIT_ON_ERROR": "0",
                   "TERMINAL_OUTPUT": "/dev/null", "PRIMARY_SIGNOFF_TOOL": "klayout",
                   "signoff_logs": str(folder), "signoff_reports": str(folder),
                   "signoff_results": str(folder), "signoff_tmpfiles": str(folder)}
        if deck is not None:
            setting["KLAYOUT_DRC_TECH_SCRIPT"] = str(deck)
        script = folder / "harness.tcl"
        body = "\n".join(f"set ::env({k}) {tcl(v)}" for k, v in setting.items())
        if probe:
            body += "\nset ::env(PDK_ROOT) " + tcl(PDK.parent) + "\nset ::env(PDK) {sky130A}\n"
            body += "source /openlane/configuration/general.tcl\nsource " + tcl(PDK / "libs.tech/openlane/config.tcl")
            body += "\nputs \"STOCK_RUN_KLAYOUT_DRC=$::env(RUN_KLAYOUT_DRC)\""
        body += "\nset global_verbose_level 0\npackage require openlane\nputs {AUDIT_STAGE_BEGIN}\n"
        body += "if {[catch {run_klayout_drc -gds " + tcl(folder / "input.gds") + " -stage audit} message options]} {\n"
        body += " puts stderr $message\n if {[dict exists $options -errorinfo]} {puts stderr [dict get $options -errorinfo]}\n exit 1\n}\n"
        body += "puts {AUDIT_STAGE_END}\nexit 0\n"
        write(script, body)
        return script

    def control(self, config, fixture, deck, direct=False, probe=False):
        name = config + "_" + fixture
        folder = self.out / "cases" / name
        folder.mkdir(parents=True)
        original = self.out / "fixtures" / (fixture + ".gds")
        copied = folder / "input.gds"
        shutil.copyfile(original, writable(copied))
        trace = folder / "execve.trace"
        if direct:
            report = folder / "drc.lyrdb"
            args = ["klayout", "-b", "-r", str(deck), "-rd", f"input={copied}",
                    "-rd", f"report={report}", "-rd", "top_cell=control", "-rd", "thr=4"]
            for key, value in self.flags.items():
                args += ["-rd", f"{key}={value}"]
            mode = "external_tool_only_with_pdk_options"
        else:
            script = self.harness(folder, deck, probe)
            args = ["tclsh", str(script)]
            report = copied.with_suffix(".gds.lydrc")
            mode = "native_stage_compatibility_adapter" if deck == self.adapter else "native_stage_unmodified"
        row = self.docker(name, "strace", ["-f", "-s", "4096", "-e", "trace=execve", "-o", trace, *args])
        row.update(configuration=config, fixture=fixture, execution_mode=mode,
                   input=identity(original), copied_input=identity(copied),
                   deck=identity(deck) if deck else None,
                   execve_trace=identity(trace) if trace.exists() else None,
                   report=identity(report) if report.exists() else None, metrics=metrics(report))
        row["geometry_observation"] = (
            "NOTASSESSED_EXECUTION_FAILED" if row["exit_code"] != 0 or row["timed_out"] else
            "NOTASSESSED_NO_REPORT" if not report.exists() else
            "NOTSUPPORTED_INACTIVE_RULE_ENGINE" if row["metrics"]["categories"] == 0 else
            "MARKERS_PRESENT" if row["metrics"]["markers"] else "ZERO_MARKERS_ACTIVE_RULES")
        write_json(self.out / "executions" / name / "result.json", row)
        self.data["controls"].append(row)
        self.checkpoint()
        print(json.dumps({"control": name, "categories": row["metrics"]["categories"],
                          "markers": row["metrics"]["markers"], "observation": row["geometry_observation"]}), flush=True)

    def classify(self):
        lookup = {(r["configuration"], r["fixture"]): r for r in self.data["controls"]}
        for config in ("prior_modern_native", "legacy_native", "modern_direct_pdk_options", "modern_adapter_native"):
            for group, rule in (("metal", "m1.1"), ("metal", "m1.6"), ("poly", "poly.1a"), ("grid", "m1_OFFGRID")):
                a = lookup.get((config, group + "_positive"))
                b = lookup.get((config, group + "_negative"))
                status = "NOTASSESSED"
                reason = "Paired applicable executions absent or failed."
                if a and b and all(r["exit_code"] == 0 and r["metrics"]["report_exists"] for r in (a, b)):
                    inventory = {c["name"] for c in a["metrics"]["category_inventory"]}
                    hit = a["metrics"]["markers_by_category"].get(rule, 0)
                    if not inventory or rule not in inventory:
                        status = "NOTSUPPORTED"
                        reason = "Target category absent; rule group inactive in this invocation."
                    elif hit > 0 and b["metrics"]["markers"] == 0:
                        status = "SUPPORTED"
                        reason = "Target violation marked; paired clean control has zero markers with active categories."
                    else:
                        reason = "Active category lacks a successful discriminating control pair."
                self.data["obligations"].append({"configuration": config, "obligation": "report_" + rule,
                    "classification": status, "reason": reason,
                    "positive": a["id"] if a else None, "negative": b["id"] if b else None,
                    "enforced_scope": "Report geometry markers for supplied synthetic GDS only; no exit rejection."})
        self.data["obligations"].append({"configuration": "stock_selected_pdk_defaults",
            "obligation": "active_klayout_drc", "classification": "NOTSUPPORTED",
            "reason": "Evaluated stock config has RUN_KLAYOUT_DRC=0 and no KLAYOUT_DRC_TECH_SCRIPT; forced standalone stage probe skips with no report.",
            "evidence": "stock_config_forced_stage_probe_metal_positive"})
        for config in ("legacy_native", "modern_adapter_native"):
            a = lookup[(config, "metal_positive")]
            self.data["obligations"].append({"configuration": config, "obligation": "reject_nonzero_klayout_markers",
                "classification": "NOTSUPPORTED" if a["exit_code"] == 0 and (a["metrics"]["markers"] or 0) > 0 else "NOTASSESSED",
                "reason": "Native stage returns zero with violating marker report; no marker-count quit gate in native proc.",
                "evidence": a["id"]})
        for obligation in ("bind_consumed_gds_to_selected_candidate", "authenticate_approved_deck_digest",
                           "validate_expected_active_rule_inventory", "detect_omitted_feol_configuration",
                           "validate_streamout_layer_map_provenance", "bind_results_to_later_release_artifact"):
            self.data["obligations"].append({"configuration": "audited_run_klayout_drc_interface",
                "obligation": obligation, "classification": "NOTSUPPORTED",
                "reason": "Audited native stage accepts GDS and stage plus deck environment path; no implementation of this provenance/configuration obligation in proc or wrapper.",
                "scope_qualification": "Static interface finding; no claim about other stages or full OpenLane flow."})
        for obligation in ("all_feol_rules", "all_beol_rules", "seal_ring_detection", "floating_metal_detection",
                           "density_antenna_lvs_pdn", "default_magic_drc", "full_flow_comparative_fault_coverage"):
            self.data["obligations"].append({"configuration": "wider_scope", "obligation": obligation,
                "classification": "NOTASSESSED", "reason": "No matched controls/full-flow execution for this wider obligation."})
        self.data["prior_wrapper_diagnosis"] = {
            "cause": "Prior harness manually sets KLAYOUT_DRC_TECH_SCRIPT to modern sky130A_mr.drc; wrapper passes input/report only, leaving feol/beol/offgrid/seal/floating_met unset and false.",
            "config_incompatibility": "Both installed selected and dependency-pinned PDK configs define KLAYOUT_DRC_RUNSET and KLAYOUT_DRC_OPTIONS, not KLAYOUT_DRC_TECH_SCRIPT; pinned native code has no translator.",
            "stock_defaults": "RUN_KLAYOUT_DRC=0; RUN_MAGIC_DRC=1; PRIMARY_SIGNOFF_TOOL=magic. KLayout-only observations do not characterize default Magic DRC.",
            "prior_record_disposition": "Preserve old results; reinterpret zero-category stage observations as inactive/unassessed geometry, not active-engine DRCNotDetected.",
            "prior_enabled_control_difference": "Old direct control enables floating_met=true and omits seal; selected PDK options request floating_metal=0 and seal=1. These are different configurations."}
        after = [identity(p) for p in self.protected]
        write_json(self.out / "protected_after.json", after)
        self.data["preservation"] = {"before": identity(self.out / "protected_before.json"),
                                     "after": identity(self.out / "protected_after.json"),
                                     "file_count": len(after), "all_byte_identical": self.before == after}
        self.data["status"] = "completed"
        self.data["completed_utc"] = now()
        self.data["material_passport"]["verification_status"] = "EXECUTED_BOUNDED_CONTROLS"
        self.checkpoint()
        write_json(EVIDENCE, self.data)
        self.render()

    def render(self):
        d = self.data
        lines = ["# OpenLane invocation audit", "", "## Material Passport", "",
                 "- Origin Skill: ARS experiment-agent; code_runner_agent role", "- Origin Mode: run",
                 "- Origin Date: " + d["completed_utc"], "- Verification Status: EXECUTED_BOUNDED_CONTROLS",
                 "- Version Label: openlane_invocation_audit_v1",
                 "- Delegation: inline execution; native subagent dispatch unavailable. No independent-agent judgement claim.", "",
                 "## Result and intended invocation", "",
                 "Pinned OpenLane and retained native sources match the downloaded official commit bytes. "
                 "The stock KLayout DRC default is disabled (`RUN_KLAYOUT_DRC=0`); default Magic DRC remains outside this audit. "
                 "Both installed PDK configs name the modern `_mr.drc` runset and its options, but omit the pinned wrapper's "
                 "`KLAYOUT_DRC_TECH_SCRIPT`. The native wrapper forwards only input/report, with no rule flags or options translation. "
                 "There is no confirmed stock active deck/flag pairing for this combination.", "",
                 "The shipped legacy `sky130A.lydrc` is compatible with that wrapper and byte identical across both PDK versions "
                 "and public dependency-pinned source. Its built-in FEOL=false, BEOL=true, OFFGRID=true settings are exercised "
                 "using an explicit deck override. This is a demonstrated compatible configuration, not a proven default selection.", "",
                 "The selected PDK's intended modern options are `feol=1 beol=1 offgrid=1 seal=1 floating_metal=0`. "
                 "Direct runs map `floating_metal` to the deck variable `floating_met`. Native-stage adapter runs inject these "
                 "values in an audit-only adapter and evaluate the original deck unchanged. The adapter is not stock OpenLane.", "",
                 "## Actual control counts", "",
                 "Categories count emitted report categories, including those with zero markers; it is not a certified rule inventory. "
                 "Negative controls are nonempty synthetic geometry, clean only within the tested configurations.", "",
                 "| Configuration | Control | Exit | Categories | Markers | Marker categories |", "|---|---|---:|---:|---:|---|"]
        for r in d["controls"]:
            m = r["metrics"]
            detail = ", ".join(f"{k}: {v}" for k, v in m.get("markers_by_category", {}).items()) or "none"
            lines.append(f"| {r['configuration']} | {r['fixture']} | {r['exit_code']} | {m['categories']} | {m['markers']} | {detail} |")
        lines += ["", "## Obligations", "", "SUPPORTED means the exact target rule passed violating/clean controls. "
                  "NOTSUPPORTED identifies an inactive or absent obligation in the named interface/configuration. "
                  "NOTASSESSED marks wider or unexecuted coverage. Report detection and process rejection are separate.", "",
                  "| Configuration | Obligation | Classification |", "|---|---|---|"]
        lines += [f"| {r['configuration']} | {r['obligation']} | {r['classification']} |" for r in d["obligations"]]
        lines += ["", "## Why the prior wrapper disabled rules", "", d["prior_wrapper_diagnosis"]["cause"], "",
                  d["prior_wrapper_diagnosis"]["config_incompatibility"], "",
                  d["prior_wrapper_diagnosis"]["prior_enabled_control_difference"], "",
                  "Zero categories on a known violating control is an inactive-engine finding. The old study's `not_detected` "
                  "label is preserved in its original files, with this sidecar qualification; it cannot support an active-checker miss claim.", "",
                  "## Commands, identity, and preservation", "",
                  f"- Pinned image: `{IMAGE}`", "- KLayout version: 0.28.2 (actual version stdout retained).",
                  f"- Run directory: `{self.out}`", "- Exact argv, stdout, stderr, exit status, timings, hashes: `executions/*/command.json` and `result.json`.",
                  "- Actual child process arguments: `cases/*/execve.trace` captured with strace; no checker proc redefined.",
                  "- Report XMLs and per-category counts are retained; JSON includes full emitted category inventories.",
                  f"- Original input/source/control preservation: {d['preservation']['file_count']} files; byte identical = {d['preservation']['all_byte_identical']}.",
                  "- Containers use network=none; repository and both PDKs are read-only; only this run directory is writable.", "",
                  "## Public maintainer-owned confirmation", "",
                  "Confirmation is documentary and source-based. No maintainer was contacted; no personal endorsement is claimed.", ""]
        for r in d["source_confirmation"]:
            lines.append(f"- [{Path(r['public']['path']).name}]({r['url']}): public/retained/image bytes match; SHA256 `{r['public']['sha256']}`.")
        receipts = d["public_source_fetches"]
        for name in ("openlane_configuration.md", "open_pdks_pinned_config.tcl", "open_pdks_selected_config.tcl", "open_pdks_pinned_sky130.lydrc"):
            r = next(r for r in receipts if Path(r["file"]).name == name)
            lines.append(f"- [{name}]({r['url']}): downloaded public source; SHA256 `{r.get('sha256', 'unavailable')}`.")
        lines += ["", "## Enforced scope and limits", "",
                  "Supported geometry obligations apply only to supplied GDS under the named deck/options. "
                  "Native stage completion does not enforce zero markers. Candidate lineage, approved-deck authenticity, "
                  "expected active-rule inventory, map provenance, and later artifact binding are absent from this audited interface. "
                  "The adapter activates the selected PDK options but does not add those obligations or a marker rejection gate.", "",
                  "All-rule coverage, seal/floating-metal discriminating controls, default Magic DRC, LVS/PDN/antenna/density, "
                  "and full-flow comparative coverage are NOTASSESSED. No full RTL-to-GDS flow was executed and no signoff "
                  "or full-flow comparative claim follows. Old controls and study files are preserved.", ""]
        write(REPORT, "\n".join(lines))
        write(self.out / "OPENLANE_INVOCATION_AUDIT.md", "\n".join(lines))

    def execute(self):
        self.discover()
        self.make_fixtures()
        modern = PDK / "libs.tech/klayout/drc/sky130A_mr.drc"
        legacy = PDK / "libs.tech/klayout/drc/sky130A.lydrc"
        self.control("stock_config_forced_stage_probe", "metal_positive", None, probe=True)
        for group in ("metal", "poly", "grid"):
            for kind in ("positive", "negative"):
                fixture = group + "_" + kind
                for config, deck, direct in (("prior_modern_native", modern, False),
                                              ("legacy_native", legacy, False),
                                              ("modern_direct_pdk_options", modern, True),
                                              ("modern_adapter_native", self.adapter, False)):
                    self.control(config, fixture, deck, direct)
        self.classify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="controls_v1")
    parser.add_argument("--timeout", type=int, default=120, help="Hard bound per command/container in seconds")
    parser.add_argument("--summarize-existing", action="store_true", help="Reclassify retained audit controls without reexecuting tools")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    if args.summarize_existing:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
            parser.error("unsafe run id")
        audit = Audit.__new__(Audit)
        audit.out = RAW / args.run_id
        audit.data = json.loads((audit.out / "checkpoint.json").read_text())
        if audit.data["status"] != "completed":
            parser.error("only a completed audit may be summarized")
        audit.before = json.loads((audit.out / "protected_before.json").read_text())
        audit.protected = [Path(row["path"]) for row in audit.before]
        audit.data["obligations"] = []
        audit.data["analysis_script"] = identity(__file__)
        audit.data["analysis_invocation"] = {"argv": [sys.executable, *sys.argv], "cwd": str(ROOT)}
        audit.data["execution_script_snapshot"] = identity(audit.out / "runner_executed.py")
        audit.classify()
        return
    audit = Audit(args.run_id, args.timeout)
    try:
        audit.execute()
    except Exception as error:
        audit.data.update(status="incomplete", error=repr(error))
        audit.checkpoint()
        raise


if __name__ == "__main__":
    main()
