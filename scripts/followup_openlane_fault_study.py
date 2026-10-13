#!/usr/bin/env python3
"""Bounded OpenLane coverage of six retained, author-constructed fault classes.

No rtl2gdsagi production imports. Original artifacts and the PDK are mounted
read-only; only this study's raw directory is writable. Results are checkpointed
after each execution. The retained replicates are observations, not independent
comparisons. No process success is called CLEAN.
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
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "runs/external_fault_coverage"
EVIDENCE = ROOT / "rtl2gdsagi_paper/evidence/external_fault_coverage.json"
TAG = "ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69"
IMAGE = "ghcr.io/the-openroad-project/openlane@sha256:d7e2bdd21e757e3f0b15d6ea08c36d9a96653c31b4fb2fafd4de88c9b6a3f3fa"
PDK = Path("/home/vlsi/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A")
BASE = ROOT / "runs/signoff_final_v5"
FIXTURES = ROOT / "runs/native_fault_injection"
DESIGNS = ("register", "alu8", "fifo_buf")
ATTACKS = (
    "stale_gds_fed_to_drc", "drc_deck_missing_feol_rules",
    "lvs_no_real_compare", "missing_pdn_via_connection",
    "missing_layer_map_streamout", "artifact_swap_after_verified_repair",
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identity(path):
    p = Path(path)
    return {"path": str(p), "sha256": digest(p), "bytes": p.stat().st_size}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    tmp.replace(path)


def tcl(value):
    # All paths are controlled local paths. Braces keep Tcl from evaluating them.
    value = str(value)
    if "{" in value or "}" in value or "\n" in value:
        raise ValueError(value)
    return "{" + value + "}"


def xml_counts(path):
    if not Path(path).exists():
        return {"report_exists": False}
    root = ET.parse(path).getroot()
    signatures = [(c.findtext("name"), c.findtext("description")) for c in root.findall("categories/category")]
    return {"report_exists": True, "markers": len(root.findall("items/item")),
            "categories": len(root.findall("categories/category")),
            "distinct_category_name_description_pairs": len(set(signatures)),
            "top_cell": root.findtext("top-cell")}


class Study:
    def __init__(self, run_id, timeout):
        self.out = RAW / run_id
        self.out.mkdir(parents=True, exist_ok=False)
        self.timeout = timeout
        self.result = {
            "schema_version": 1, "status": "running", "started_utc": self.now(),
            "raw_directory": str(self.out), "script": identity(__file__),
            "question": "Which native OpenLane checks detect each retained fault class, under explicit inputs?",
            "unit_of_analysis": "six author-constructed detection-coverage classes",
            "replicate_warning": "Three retained observations per class; stale observations reuse the same GDS. Not 18 independent comparisons.",
            "scope": "Isolated stage and report checker execution; no full RTL-to-GDS flow or full signoff certification.",
            "status_definitions": {
                "detected": "Applicable checker ran and produced fault evidence; matched controls and qualifications are recorded.",
                "not_detected": "Applicable checker ran on the fault input without indicating the target fault.",
                "not_checked": "Obligation not executed or not supported by the native interface; never inferred from exit zero.",
            },
            "full_flow": {"result": "not_checked", "support": "not_executed", "reason": "Stage/checker-only study; original flow was not rerun."},
            "executions": [], "controls": [], "coverage": [], "limitations": [],
            "script_invocations": [{"argv": [sys.executable, *sys.argv], "cwd": str(ROOT)}],
        }
        self.checkpoint()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def checkpoint(self):
        self.result["updated_utc"] = self.now()
        write_json(self.out / "checkpoint.json", self.result)
        write_json(EVIDENCE, self.result)

    def host(self, name, command, binary=False):
        folder = self.out / "executions" / name
        folder.mkdir(parents=True, exist_ok=False)
        write_json(folder / "command.json", {"argv": command, "shell": shlex.join(command), "cwd": str(ROOT)})
        start = time.monotonic()
        rc = None
        timed_out = False
        with (folder / "stdout").open("wb") as stdout, (folder / "stderr").open("wb") as stderr:
            try:
                p = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=self.timeout)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                # Docker client timeout does not guarantee container termination.
                if command[:2] == ["docker", "run"] and "--name" in command:
                    cname = command[command.index("--name") + 1]
                    cleanup = ["docker", "rm", "-f", cname]
                    write_json(folder / "timeout_cleanup.command.json", cleanup)
                    subprocess.run(cleanup, stdout=stdout, stderr=stderr, timeout=30)
        run = {"id": name, "argv": command, "command_file": str(folder / "command.json"),
               "stdout": identity(folder / "stdout"), "stderr": identity(folder / "stderr"),
               "exit_code": rc, "timed_out": timed_out, "elapsed_seconds": round(time.monotonic() - start, 3)}
        if not binary:
            run["stdout_tail"] = (folder / "stdout").read_text(errors="replace")[-1800:]
            run["stderr_tail"] = (folder / "stderr").read_text(errors="replace")[-1800:]
        write_json(folder / "result.json", run)
        self.result["executions"].append(run)
        self.checkpoint()
        print(json.dumps({"execution": name, "exit_code": rc, "timed_out": timed_out}), flush=True)
        return run

    def docker(self, name, entrypoint, args, inputs=(), code=(), mode="stage_only"):
        command = ["docker", "run", "--rm", "--network", "none", "--name", "external-fault-" + name.replace("_", "-") + "-" + str(os.getpid()),
                   "-u", f"{os.getuid()}:{os.getgid()}", "-v", f"{ROOT}:{ROOT}:ro",
                   "-v", f"{RAW}:{RAW}:rw", "-v", f"{PDK}:{PDK}:ro",
                   "-w", str(self.out), "--entrypoint", entrypoint, IMAGE, *map(str, args)]
        run = self.host(name, command)
        run.update({"execution_mode": mode, "inputs": [identity(p) for p in inputs],
                    "native_code_paths": list(code)})
        self.checkpoint()
        return run

    def folder(self, name):
        folder = self.out / "cases" / name
        folder.mkdir(parents=True, exist_ok=False)
        return folder

    def harness(self, folder, invocation, env=None):
        # Use the real OpenLane package, utilities, timer, error policy and checkers.
        # No checker/helper proc is redefined. Catch only maps Tcl exceptions to OS exit status.
        setting = {"OPENLANE_ROOT": "/openlane", "SCRIPTS_DIR": "/openlane/scripts",
                   "RUN_DIR": str(folder), "CURRENT_INDEX": "0", "EXIT_ON_ERROR": "0",
                   "TERMINAL_OUTPUT": "/dev/null", "PRIMARY_SIGNOFF_TOOL": "klayout",
                   "signoff_logs": str(folder), "signoff_reports": str(folder),
                   "signoff_results": str(folder), "signoff_tmpfiles": str(folder),
                   "floorplan_logs": str(folder), "KLAYOUT_XOR_THREADS": "4",
                   "KLAYOUT_XOR_IGNORE_LAYERS": "", "QUIT_ON_XOR_ERROR": "1"}
        setting.update(env or {})
        script = folder / "harness.tcl"
        script.write_text("\n".join(f"set ::env({key}) {tcl(value)}" for key, value in setting.items()) +
                          "\nset global_verbose_level 0\npackage require openlane\n" +
                          "puts {HARNESS_CHECK_BEGIN}\n" +
                          "if {[catch {\n" + invocation + "\n} message options]} {\n" +
                          " puts stderr $message\n if {[dict exists $options -errorinfo]} {puts stderr [dict get $options -errorinfo]}\n exit 1\n}\n" +
                          "puts {HARNESS_CHECK_END}\nexit 0\n")
        return script

    def discover(self):
        inspection = self.host("image_identity", ["docker", "image", "inspect", TAG])
        data = json.loads(Path(inspection["stdout"]["path"]).read_text())[0]
        expected = json.loads((ROOT / "rtl2gdsagi_paper/evidence/experiment_manifest.json").read_text())["environment"]
        if data["Id"] != expected["container_id"] or IMAGE not in data["RepoDigests"]:
            raise RuntimeError("Pinned image does not match retained evidence")
        self.result["image"] = {"tag": TAG, "execution_reference": IMAGE, "id": data["Id"],
                                "repo_digests": data["RepoDigests"], "recorded_evidence_matches": True,
                                "git_commit_from_tag": "ff5509f65b17bfa4068d5336495ab1718987ff69",
                                "git_commit_verification": "No .git directory in image; tag is not independently verified by git. Exact archived code hashes and image digest establish executed identity."}
        archive = self.host("native_source_archive", ["docker", "run", "--rm", "--network", "none", "--entrypoint", "tar", IMAGE, "-C", "/openlane", "-cf", "-", "scripts", "configuration", "dependencies/tool_metadata.yml", "flow.tcl"], binary=True)
        discovery = self.out / "native_sources"
        discovery.mkdir()
        with tarfile.open(archive["stdout"]["path"]) as tar:
            # The archive is created directly from the pinned image, with known relative roots.
            for member in tar.getmembers():
                dest = (discovery / member.name).resolve()
                if not dest.is_relative_to(discovery.resolve()) or member.issym() or member.islnk():
                    raise ValueError("Unexpected archive member " + member.name)
            tar.extractall(discovery)
        self.result["native_code_identity"] = [identity(p) for p in sorted(discovery.rglob("*")) if p.is_file()]
        self.docker("tool_versions", "bash", ["-lc", "openroad -version; klayout -v; netgen -batch quit; tclsh <<< 'puts [info patchlevel]'"], mode="discovery")
        pdks = [PDK / "libs.tech/klayout/drc/sky130A_mr.drc", PDK / "libs.tech/klayout/tech/sky130A.map",
                PDK / "libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef", PDK / "libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef",
                PDK / "libs.tech/netgen/sky130A_setup.tcl"]
        self.result["pdk"] = {"root": str(PDK), "files": [identity(p) for p in pdks]}
        native = json.loads((ROOT / "rtl2gdsagi_paper/evidence/native_fault_injection.json").read_text())
        self.result["retained_study_identity"] = identity(ROOT / "rtl2gdsagi_paper/evidence/native_fault_injection.json")
        self.result["retained_source_sha256"] = native["source_sha256"]
        self.result["retained_observations"] = native["results"]
        self.checkpoint()

    def drc(self, name, gds, deck, enabled=False, top=None):
        folder = self.folder(name)
        # The actual stage writes next to its input; use a byte-identical copy to preserve originals.
        copied = folder / "input.gds"
        shutil.copyfile(gds, copied)
        if enabled:
            report = folder / "drc.lyrdb"
            args = ["-b", "-r", deck, "-rd", f"input={copied}", "-rd", f"report={report}"]
            for key, value in {"top_cell": top, "thr": "4", "feol": "true", "beol": "true", "offgrid": "true", "floating_met": "true"}.items():
                if value is not None:
                    args += ["-rd", f"{key}={value}"]
            run = self.docker(name, "klayout", args, [gds, copied, deck], [str(deck)], "external_tool_only")
        else:
            script = self.harness(folder, f"run_klayout_drc -gds {tcl(copied)} -stage fixture",
                                  {"KLAYOUT_DRC_TECH_SCRIPT": str(deck)})
            run = self.docker(name, "tclsh", [script], [gds, copied, deck, script],
                              ["/openlane/scripts/tcl_commands/klayout.tcl::run_klayout_drc", "/openlane/scripts/klayout/run_drc.sh"])
            report = copied.with_suffix(".gds.lydrc")
        run["report"] = identity(report) if report.exists() else None
        run["metrics"] = xml_counts(report)
        run["result"] = "not_checked" if run["exit_code"] != 0 or not report.exists() else ("detected" if run["metrics"]["markers"] else "not_detected")
        run["result_scope"] = "Geometry DRC markers only; no candidate lineage, deck approval, rule-inventory or layer-map enforcement."
        run["rule_flags_explicitly_enabled"] = enabled
        self.checkpoint()
        return run

    def xor(self, name, a, b):
        folder = self.folder(name)
        script = self.harness(folder, f"run_klayout_gds_xor -layout1 {tcl(a)} -layout2 {tcl(b)}", {"DESIGN_NAME": "fixture"})
        run = self.docker(name, "tclsh", [script], [a, b, script],
                          ["/openlane/scripts/tcl_commands/klayout.tcl::run_klayout_gds_xor", "/openlane/scripts/klayout/xor.drc", "/openlane/scripts/tcl_commands/checkers.tcl::quit_on_xor_error"])
        report = folder / "1-xor.rpt"
        match = re.search(r"Total XOR differences = (\d+)", report.read_text()) if report.exists() else None
        run["differences"] = int(match.group(1)) if match else None
        run["report"] = identity(report) if report.exists() else None
        run["result"] = ("detected" if run["differences"] and run["exit_code"] == 1 else
                         "not_detected" if run["differences"] == 0 and run["exit_code"] == 0 else "not_checked")
        run["result_scope"] = "Explicitly supplied reference versus fault GDS; native XOR is ordinarily Magic-versus-KLayout consistency, not lineage enforcement."
        self.checkpoint()
        return run

    def pdn(self, name, def_file):
        folder = self.folder(name)
        tech = PDK / "libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
        cells = PDK / "libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
        liberty = PDK / "libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        script = folder / "check_pdn.tcl"
        script.write_text(f"read_liberty {tcl(liberty)}\nread_lef {tcl(tech)}\nread_lef {tcl(cells)}\nread_def {tcl(def_file)}\n" +
                          "set failure 0\nforeach net {VPWR VGND} {\n puts \"NATIVE_PDN_CHECK_BEGIN $net\"\n" +
                          " if {[catch {check_power_grid -net $net} message options]} {\n set failure 1\n puts stderr $message\n" +
                          " puts \"NATIVE_PDN_CHECK_REJECTED $net\"\n } else {puts \"NATIVE_PDN_CHECK_RETURNED $net\"}\n}\nexit $failure\n")
        run = self.docker(name, "openroad", ["-exit", "-no_init", script], [def_file, liberty, tech, cells, script],
                          ["/openlane/scripts/openroad/pdn.tcl::check_power_grid", "OpenROAD native check_power_grid"], "stage_checker_only")
        text = Path(run["stdout"]["path"]).read_text() + Path(run["stderr"]["path"]).read_text()
        run["checks_reached"] = [net for net in ("VPWR", "VGND") if f"NATIVE_PDN_CHECK_BEGIN {net}" in text]
        run["checks_rejected"] = [net for net in ("VPWR", "VGND") if f"NATIVE_PDN_CHECK_REJECTED {net}" in text]
        run["result"] = ("detected" if run["checks_rejected"] and "PSM-0069" in text else "not_detected" if not run["checks_rejected"] else "not_checked") if len(run["checks_reached"]) == 2 else "not_checked"
        # Feed the actual native checker output to OpenLane's actual log gate.
        native_log = folder / "1-pdn.log"
        native_log.write_text(text)
        gate_script = self.harness(folder, "quit_on_unconnected_pdn_nodes", {"CURRENT_INDEX": "1"})
        gate = self.docker(name + "_log_gate", "tclsh", [gate_script], [native_log, gate_script],
                           ["/openlane/scripts/tcl_commands/checkers.tcl::quit_on_unconnected_pdn_nodes"], "report_only")
        gate["result"] = "detected" if gate["exit_code"] == 1 and "PDN generation failed" in Path(gate["stdout"]["path"]).read_text() else "not_detected" if gate["exit_code"] == 0 else "not_checked"
        run["log_gate_execution"] = gate["id"]
        self.checkpoint()
        return run

    def controls(self):
        folder = self.folder("controls_layouts")
        script = folder / "make_controls.py"
        script.write_text("import pya\n" +
                          "for name, size in [('good',1000),('different',2000),('dirty',50)]:\n" +
                          " ly=pya.Layout(); ly.dbu=0.001; top=ly.create_cell('control')\n" +
                          " top.shapes(ly.layer(68,20)).insert(pya.Box(0,0,size,size))\n" +
                          f" ly.write({str(folder)!r}+'/'+name+'.gds')\n")
        self.docker("make_control_layouts", "klayout", ["-b", "-r", script], [script], mode="control_generation")
        positive = self.xor("control_xor_positive", folder / "good.gds", folder / "different.gds")
        negative = self.xor("control_xor_negative", folder / "good.gds", folder / "good.gds")
        self.result["controls"].append({"checker": "run_klayout_gds_xor + quit_on_xor_error", "positive": positive["id"], "negative": negative["id"],
                                         "positive_result": positive["result"], "negative_result": negative["result"]})
        deck = PDK / "libs.tech/klayout/drc/sky130A_mr.drc"
        enabled = self.drc("control_drc_positive_enabled", folder / "dirty.gds", deck, True, "control")
        default = self.drc("control_drc_positive_stage_default", folder / "dirty.gds", deck)
        self.result["controls"].append({"checker": "KLayout DRC", "positive_enabled_engine": enabled["id"], "positive_stage_default": default["id"],
                                         "enabled_result": enabled["result"], "stage_default_result": default["result"],
                                         "qualification": "The PDK needs runtime rule flags. OpenLane's unmodified run_drc.sh does not pass them. Stage completion is not a marker-rejecting gate."})
        self.lvs_controls("device")

    def lvs_controls(self, prefix):
        # Distinct files avoid Netgen's same-netlist refusal; actual primitive devices
        # avoid flattening an empty subcircuit into a vacuous 'Not checked' result.
        folder = self.folder(prefix + "_lvs_inputs")
        for name, device in (("a", "R1 A B 1000"), ("b", "C1 A B 1p"), ("a_copy", "R1 A B 1000")):
            (folder / f"{name}.spice").write_text(".subckt control A B\n" + device + "\n.ends control\n")
        (folder / "setup.tcl").write_text("# Use native Netgen defaults.\n")
        for name, schematic in (("positive", "b"), ("negative", "a_copy")):
            execution_name = prefix + "_control_lvs_" + name
            lvsfolder = self.folder(execution_name)
            a = folder / "a.spice"
            b = folder / f"{schematic}.spice"
            env = {"DESIGN_NAME": "control", "EXT_NETLIST": str(a), "CURRENT_POWERED_NETLIST": str(b),
                   "NETGEN_SETUP_FILE": str(folder / "setup.tcl"), "LVS_INSERT_POWER_PINS": "0",
                   "MAGIC_EXT_USE_GDS": "0", "QUIT_ON_LVS_ERROR": "1"}
            harness = self.harness(lvsfolder, f"run_lvs {tcl(a)}", env)
            run = self.docker(execution_name, "tclsh", [harness], [a, b, folder / "setup.tcl", harness],
                              ["/openlane/scripts/tcl_commands/lvs.tcl::run_lvs", "/openlane/scripts/count_lvs.py", "/openlane/scripts/tcl_commands/checkers.tcl::quit_on_lvs_error"])
            report = lvsfolder / "1-control.lvs.rpt"
            match = re.search(r"Total errors = (\d+)", report.read_text()) if report.exists() else None
            run["total_errors"] = int(match.group(1)) if match else None
            run["result"] = "detected" if run["total_errors"] and run["exit_code"] == 1 else "not_detected" if run["total_errors"] == 0 and run["exit_code"] == 0 else "not_checked"
            self.result["controls"].append({"checker": "run_lvs / count_lvs / quit_on_lvs_error", "type": name, "execution": run["id"], "result": run["result"], "qualification": "Native Netgen comparison on explicit small SPICE inputs; does not validate KLayout LVS database support."})
            self.checkpoint()

    def complete_existing(self):
        """Preserve all initial attempts, fix checker prerequisites and finalize."""
        self.result["status"] = "running_supplement"
        self.result["supplement_script"] = identity(__file__)
        shutil.copyfile(__file__, self.out / "study_script.supplement.py")
        for run in self.result["executions"]:
            if run["id"] in {"control_lvs_positive", "control_lvs_negative"}:
                run["result"] = "not_checked"
                run["qualification"] = "Invalid initial control: empty leaf flattened away or same-file comparison refused. Native logs preserved; not a successful positive or negative control."
            if run["id"].startswith("pdn_") and "PSM-0079" in run.get("stdout_tail", ""):
                run["result"] = "not_checked"
                run["support"] = "missing_prerequisite"
                run["qualification"] = "Initial harness omitted Liberty; voltage prerequisite failed before connectivity analysis. Supplement loads the same typical Liberty as native OpenLane read_libs."
        for control in self.result["controls"]:
            if control.get("execution") in {"control_lvs_positive", "control_lvs_negative"}:
                control["result"] = "not_checked"
                control["qualification"] = "Invalid initial control; retained for audit. Replaced by primitive device controls."
            if control.get("type") == "paired_untouched_DEF":
                control["fault_result"] = control["baseline_result"] = "not_checked"
                control["qualification"] = "Initial attempt omitted Liberty; no connectivity result."
        self.checkpoint()
        self.lvs_controls("device")
        paired = []
        runs = []
        for rep, design in enumerate(DESIGNS, 1):
            fault = self.pdn(f"pdn_{rep}_fault_with_liberty", FIXTURES / f"pdn_{rep}/missing_connection.def")
            control = self.pdn(f"pdn_{rep}_baseline_with_liberty", BASE / design / f"stages/08_pdn/{design}.pdn.def")
            runs += [fault, control]
            paired.append({"checker": "check_power_grid", "design": design, "fault_execution": fault["id"], "fault_result": fault["result"], "baseline_execution": control["id"], "baseline_result": control["result"]})
            self.result["controls"].append({"type": "paired_untouched_DEF_with_native_Liberty", **paired[-1]})
            self.checkpoint()
        row = next(r for r in self.result["coverage"] if r["fault_class"] == ATTACKS[3])
        row["execution_ids"] += [r["id"] for r in runs]
        row["execution_modes"] = ["report_only", "stage_checker_only"]
        row["auxiliary_checks"] = paired
        row["result"] = "detected" if all(p["fault_result"] == "detected" and p["baseline_result"] == "not_detected" for p in paired) else "not_checked"
        row["reason"] = "Native post-pdngen check_power_grid commands run on retained DEFs with the native typical-Liberty prerequisite. Paired untouched DEF results bound attribution; initial missing-Liberty attempts are not_checked. Native log gates also run."
        self.result["supplement_reason"] = "Initial checker controls exposed missing prerequisites; only bounded device controls and PDN checks were added. Existing attempts remain in the audit record."
        self.result.pop("error", None)
        self.finish()

    def summarize(self):
        """Enrich completed evidence from preserved native output; no new check runs."""
        self.result["analysis_script"] = identity(__file__)
        shutil.copyfile(__file__, self.out / "study_script.final.py")
        h = hashlib.sha256()
        for p in sorted((ROOT / "src").rglob("*.py")):
            h.update(str(p.relative_to(ROOT)).encode() + b"\0")
            h.update(p.read_bytes())
        self.result["current_source_sha256"] = h.hexdigest()
        self.result["current_source_matches_retained_study"] = h.hexdigest() == self.result["retained_source_sha256"]
        by_id = {e["id"]: e for e in self.result["executions"]}
        for run in self.result["executions"]:
            if run.get("report") and "metrics" in run:
                run["metrics"] = xml_counts(run["report"]["path"])
            if run["id"].startswith("pdn_") and "with_liberty" not in run["id"]:
                run["result"] = "not_checked"
                run["support"] = "missing_prerequisite"
                run["qualification"] = "Initial missing-Liberty attempt did not exercise connectivity. Even a returned log gate is not a successful connectivity check."
        for row in self.result["coverage"]:
            row["positive_control_executions"] = []
            row["negative_control_executions"] = []
            if row["fault_class"] in {ATTACKS[0], ATTACKS[1], ATTACKS[4]}:
                row["positive_control_executions"] += ["control_drc_positive_enabled", "control_drc_positive_stage_default"]
                row["control_qualification"] = "Enabled engine finds 4 markers; unmodified OpenLane stage declares zero rule categories and finds none. This is a limitation of this specific deck/wrapper combination, not evidence of general stage reliability."
            if row["fault_class"] == ATTACKS[2]:
                row["positive_control_executions"] = ["device_control_lvs_positive"]
                row["negative_control_executions"] = ["device_control_lvs_negative"]
            if row["fault_class"] == ATTACKS[3]:
                row["positive_control_executions"] = [f"pdn_{i}_fault_with_liberty" for i in range(1, 4)]
                row["negative_control_executions"] = [f"pdn_{i}_baseline_with_liberty" for i in range(1, 4)]
                row["control_qualification"] = "Paired native controls use each unchanged original DEF versus its retained missing-via DEF; not additional independently constructed PDN faults."
                for item in row["unsupported_obligations"]:
                    if "regeneration" in item["obligation"]:
                        item["support"] = "not_executed"
                        item["reason"] = "Rerunning pdngen would generate a new grid rather than inspect the retained post-generation mutation."
            for aux in row["auxiliary_checks"]:
                if aux.get("checker") == "reference XOR":
                    aux["positive_control_execution"] = "control_xor_positive"
                    aux["negative_control_execution"] = "control_xor_negative"
                    aux["differences"] = by_id[aux["execution"]]["differences"]
            if row["fault_class"] == ATTACKS[4]:
                row["auxiliary_checks"].append({"checker": "streamout required-map CLI", "result": by_id["map_missing_required_option"]["result"],
                                                "execution": "map_missing_required_option", "qualification": "Native CLI prevents omission of --lym before generating GDS; retained wrongly mapped GDS was not an input to this check."})
        row = next(r for r in self.result["coverage"] if r["fault_class"] == ATTACKS[1])
        row["inventory_observation"] = {"fault_raw_categories": [by_id[f"rules_{i}_enabled"]["metrics"]["categories"] for i in range(1, 4)],
                                         "approved_raw_categories": [by_id[f"rules_{i}_approved_enabled_control"]["metrics"]["categories"] for i in range(1, 4)],
                                         "fault_distinct_name_description_pairs": [by_id[f"rules_{i}_enabled"]["metrics"]["distinct_category_name_description_pairs"] for i in range(1, 4)],
                                         "approved_distinct_name_description_pairs": [by_id[f"rules_{i}_approved_enabled_control"]["metrics"]["distinct_category_name_description_pairs"] for i in range(1, 4)],
                                         "qualification": "Counts observed by follow-up analysis of native reports; OpenLane did not enforce this inventory comparison. Exact repeated name/description pairs counted once only for the distinct-pair metric."}
        repair = ROOT / "runs/alu8_drc_api_repeat_v3"
        signoff = json.loads((repair / "signoff.json").read_text())
        gate = json.loads((repair / "gate_evidence.json").read_text())["gates"]["drc"]
        row = next(r for r in self.result["coverage"] if r["fault_class"] == ATTACKS[5])
        row["retained_cached_evidence"] = {"candidate_manifest": identity(repair / "signoff.json"), "gate_ledger": identity(repair / "gate_evidence.json"),
                                            "cached_drc_gate_consumed": gate["consumed"], "selected_candidate_final_gds": signoff["release_candidate"]["artifacts"]["final_gds"],
                                            "injected_references": [identity(p) for p in (ROOT / "runs/alu8_timing_api_v4/stages/15_gdsout/alu8.gds", BASE / "register/stages/15_gdsout/register.gds", BASE / "fifo_buf/stages/15_gdsout/fifo_buf.gds")],
                                            "native_cached_lineage_check": "not_checked", "qualification": "Read retained metadata only; no native checker for this ledger interface found. Explicit-reference XOR is a separate executed comparison."}
        self.result["execution_mode_counts"] = dict(Counter(e.get("execution_mode", "host_discovery") for e in self.result["executions"]))
        # Verify receipts and control claims against actual native outputs.
        checks = []
        for run in self.result["executions"]:
            for field in ("stdout", "stderr"):
                assert digest(run[field]["path"]) == run[field]["sha256"], (run["id"], field)
            assert json.loads((self.out / "executions" / run["id"] / "command.json").read_text())["argv"] == run["argv"]
            for input_record in run.get("inputs", []):
                assert digest(input_record["path"]) == input_record["sha256"], input_record["path"]
        checks.append("All exact argv, raw stdout/stderr hashes and consumed input hashes verified")
        assert by_id["control_xor_positive"]["differences"] > 0 and by_id["control_xor_positive"]["exit_code"] == 1
        assert by_id["control_xor_negative"]["differences"] == 0 and by_id["control_xor_negative"]["exit_code"] == 0
        assert by_id["device_control_lvs_positive"]["total_errors"] == 4 and by_id["device_control_lvs_positive"]["exit_code"] == 1
        assert by_id["device_control_lvs_negative"]["total_errors"] == 0 and by_id["device_control_lvs_negative"]["exit_code"] == 0
        for i in range(1, 4):
            assert by_id[f"pdn_{i}_fault_with_liberty"]["checks_rejected"] == ["VPWR", "VGND"]
            assert by_id[f"pdn_{i}_fault_with_liberty_log_gate"]["result"] == "detected"
            assert by_id[f"pdn_{i}_baseline_with_liberty"]["checks_rejected"] == []
            assert by_id[f"pdn_{i}_baseline_with_liberty_log_gate"]["result"] == "not_detected"
        checks.append("Native XOR, Netgen LVS and PDN positive/negative controls agree with their native outputs")
        initial = json.loads((self.out / "original_inputs_before.json").read_text())
        changed = [p for p, value in initial.items() if digest(p) != value]
        self.result["original_artifacts_preserved"]["changed_paths_at_finalization"] = changed
        document_changes = [p for p in changed if Path(p).is_relative_to(ROOT / "rtl2gdsagi_paper") and Path(p).suffix in {".tex", ".bib", ".md"}]
        protected_changes = [p for p in changed if p not in document_changes]
        self.result["original_artifacts_preserved"]["concurrent_document_changes_observed"] = document_changes
        self.result["original_artifacts_preserved"]["protected_source_or_input_changes"] = protected_changes
        self.result["original_artifacts_preserved"]["qualification"] = "The study writes only its script and new evidence/raw paths. Concurrent manuscript integration is observed, not overwritten or counted as fixture mutation."
        assert not protected_changes, protected_changes
        assert self.result["current_source_matches_retained_study"]
        checks.append(f"{len(initial) - len(changed)} watched files remain unchanged; {len(document_changes)} concurrent document changes observed; source and retained experiment inputs unchanged; source identity matches af31... retained cohort")
        self.result["verification"] = {"result": "verified_receipts_and_bounded_controls", "checks": checks}
        self.finish()

    def add_row(self, attack, result, runs, reason, unsupported=(), auxiliary=()):
        self.result["coverage"].append({"fault_class": attack, "result": result, "reason": reason,
                                        "retained_observations": 3, "execution_ids": [r["id"] for r in runs],
                                        "execution_modes": sorted(set(r["execution_mode"] for r in runs)),
                                        "auxiliary_checks": list(auxiliary),
                                        "unsupported_obligations": [{"obligation": x, "result": "not_checked", "support": "unsupported"} for x in unsupported],
                                        "full_flow": {"result": "not_checked", "support": "not_executed"}})
        self.checkpoint()
        print(json.dumps({"class": attack, "result": result}), flush=True)

    def cases(self):
        deck = PDK / "libs.tech/klayout/drc/sky130A_mr.drc"
        stale = ROOT / "runs/alu8_timing_api_v4/stages/15_gdsout/alu8.gds"
        selected = BASE / "alu8/stages/15_gdsout/alu8.gds"
        runs = []
        for rep in range(1, 4):
            runs += [self.drc(f"stale_{rep}_stage", stale, deck), self.drc(f"stale_{rep}_enabled", stale, deck, True, "alu8")]
        xor = self.xor("stale_reference_xor", selected, stale)
        self.add_row(ATTACKS[0], self.all_no_detection(runs), runs,
                     "DRC inspected the stale input but has no selected-candidate identity argument. Reused identical stale GDS is not three independent faults.",
                     ["Bind DRC-consumed GDS digest to selected release candidate"],
                     [{"checker": "reference XOR", "result": xor["result"], "execution": xor["id"], "qualification": "Explicit selected reference added by this follow-up; geometric difference detection is not lineage enforcement."}])
        runs = []
        for rep, design in enumerate(DESIGNS, 1):
            gds = BASE / design / f"stages/15_gdsout/{design}.gds"
            modified = FIXTURES / f"rules_{rep}/missing_feol.drc"
            runs += [self.drc(f"rules_{rep}_stage", gds, modified), self.drc(f"rules_{rep}_enabled", gds, modified, True, design),
                     self.drc(f"rules_{rep}_approved_enabled_control", gds, deck, True, design)]
        self.add_row(ATTACKS[1], self.all_no_detection(runs[:2] + runs[3:5] + runs[6:8]), runs,
                     "Fault decks execute without rejection. Enabled native reports expose smaller rule inventories, but OpenLane does not compare them with an approved inventory.",
                     ["Approve deck identity and require FEOL rule inventory"])
        runs = []
        for rep in range(1, 4):
            report = FIXTURES / f"lvs_{rep}/lvs.lvsdb"
            log = FIXTURES / f"lvs_{rep}/no_compare.native.log"
            parse = self.docker(f"lvs_{rep}_count_report", "python3", ["/openlane/scripts/count_lvs.py", "-f", report], [report], ["/openlane/scripts/count_lvs.py"], "report_only")
            parse["result"] = "not_checked"
            parse["support"] = "incompatible_input"
            parse["qualification"] = "KLayout .lvsdb is not Netgen JSON. Parser error is format rejection, not evidence of detecting absent comparison."
            folder = self.folder(f"lvs_{rep}_report_gate")
            harness = self.harness(folder, f"quit_on_lvs_error -rpt {tcl(report)} -log {tcl(log)}")
            gate = self.docker(f"lvs_{rep}_report_gate", "tclsh", [harness], [report, log, harness],
                               ["/openlane/scripts/tcl_commands/checkers.tcl::quit_on_lvs_error"], "report_only")
            gate["result"] = "not_checked"
            gate["support"] = "incompatible_input"
            gate["qualification"] = "Retained KLayout database has no Netgen 'Total errors = 0' summary. Rejection cannot establish whether a comparison occurred."
            runs += [parse, gate]
        self.add_row(ATTACKS[2], "not_checked", runs,
                     "Actual Netgen report parser and gate reject incompatible retained KLayout reports. No native OpenLane KLayout LVS-database checker was found; native Netgen controls are separate.",
                     ["Verify real compare/xrefs in a KLayout .lvsdb", "Execute OpenLane LVS stage using only the no-compare .rb/.lvsdb fixture"])
        runs = []
        paired = []
        for rep, design in enumerate(DESIGNS, 1):
            fault = self.pdn(f"pdn_{rep}_fault", FIXTURES / f"pdn_{rep}/missing_connection.def")
            control = self.pdn(f"pdn_{rep}_baseline", BASE / design / f"stages/08_pdn/{design}.pdn.def")
            runs += [fault, control]
            paired.append({"design": design, "fault_execution": fault["id"], "fault_result": fault["result"], "baseline_execution": control["id"], "baseline_result": control["result"]})
            self.result["controls"].append({"checker": "check_power_grid + quit_on_unconnected_pdn_nodes", "type": "paired_untouched_DEF", **paired[-1]})
        status = "detected" if all(p["fault_result"] == "detected" and p["baseline_result"] == "not_detected" for p in paired) else "not_checked"
        self.add_row(ATTACKS[3], status, runs,
                     "Execute the same check_power_grid commands used after OpenLane pdngen on existing DEFs, without regenerating/healing the injected grid. Native log gate also runs. Any baseline rejection limits attribution.",
                     ["Full PDN regeneration flow on mutated inputs"], paired)
        runs = []
        aux = []
        for rep, design in enumerate(DESIGNS, 1):
            wrong = FIXTURES / f"map_{rep}/{design}.gds"
            good = BASE / design / f"stages/15_gdsout/{design}.gds"
            runs += [self.drc(f"map_{rep}_stage", wrong, deck), self.drc(f"map_{rep}_enabled", wrong, deck, True, design)]
            xor = self.xor(f"map_{rep}_reference_xor", good, wrong)
            aux.append({"checker": "reference XOR", "result": xor["result"], "execution": xor["id"], "qualification": "Requires an explicitly supplied correctly mapped reference GDS."})
        # Invoke OpenLane's own streamout CLI without its required layer map option.
        folder = self.folder("map_missing_required_option")
        native_stream = self.docker("map_missing_required_option", "python3",
                                  ["/openlane/scripts/klayout/stream_out.py", "--output", folder / "unused.gds",
                                   "--lyt", PDK / "libs.tech/klayout/tech/sky130A.lyt", "--lyp", PDK / "libs.tech/klayout/tech/sky130A.lyp",
                                   "--top", "register", BASE / "register/stages/12_routing/register.routed.def"],
                                  [BASE / "register/stages/12_routing/register.routed.def"], ["/openlane/scripts/klayout/stream_out.py"], "stage_interface_only")
        native_stream["result"] = "detected" if native_stream["exit_code"] == 2 and "Missing option" in Path(native_stream["stderr"]["path"]).read_text() and "--lym" in Path(native_stream["stderr"]["path"]).read_text() else "not_checked"
        native_stream["qualification"] = "Configuration omission is rejected by native CLI before streamout; no retained faulty GDS was consumed. This is prevention, not inspection of retained GDS."
        runs.append(native_stream)
        self.add_row(ATTACKS[4], self.all_no_detection(runs[:-1]), runs,
                     "Existing wrongly mapped GDS is not rejected by DRC. OpenLane streamout requires --lym; explicit reference XOR can detect the retained physical difference.",
                     ["Retroactively validate SKY130 layer-map semantics in an existing GDS without a reference"], aux)
        repair = ROOT / "runs/alu8_drc_api_repeat_v3/stages/15_gdsout/alu8.gds"
        foreigners = [stale, BASE / "register/stages/15_gdsout/register.gds", BASE / "fifo_buf/stages/15_gdsout/fifo_buf.gds"]
        runs = [self.xor(f"swap_{i}_reference_xor", repair, foreign) for i, foreign in enumerate(foreigners, 1)]
        self.add_row(ATTACKS[5], "not_checked", runs,
                     "The retained attack changes release-candidate references after cached verification. No OpenLane candidate/repair ledger exists in this checker interface. Newly run explicit-reference XOR detects geometry differences but does not test reuse of cached evidence.",
                     ["Bind cached DRC/LVS and verified repair to subsequently selected artifact"],
                     [{"checker": "reference XOR", "result": run["result"], "execution": run["id"]} for run in runs])

    @staticmethod
    def all_no_detection(runs):
        return "not_detected" if all(r["result"] == "not_detected" for r in runs) else "not_checked"

    def finish(self):
        self.result["limitations"] = [
            "Six constructed classes only; no sampling-based estimate of general OpenLane reliability or superiority.",
            "Retained designs were generated outside OpenLane. Isolated stages/checkers run with explicit compatible inputs; no full-flow execution.",
            "Unmodified run_klayout_drc passes no rule flags to this PDK deck; enabled engine runs are labeled external_tool_only.",
            "OpenLane KLayout DRC stage reports completion and copies a marker report; it does not reject marker count or validate rule inventory here.",
            "KLayout no-compare reports are incompatible with Netgen JSON/summary inputs. Format rejection is not credited as semantic detection.",
            "XOR is an optional explicit-reference comparison normally used for two streamouts. Reference selection and lineage enforcement are outside its coverage.",
            "PDN check_power_grid is extracted from the native post-pdngen checker callsite, not a rerun of pdngen. Both power and ground checks and the native log gate are recorded.",
            "Each run has a hard timeout; error or timeout never establishes a passing check. No unavailable obligation is called CLEAN.",
        ]
        self.result["status"] = "completed"
        self.result["finished_utc"] = self.now()
        self.result["coverage_counts"] = dict(Counter(row["result"] for row in self.result["coverage"]))
        assert len(self.result["coverage"]) == 6
        for execution in self.result["executions"]:
            write_json(self.out / "executions" / execution["id"] / "result.json", execution)
        self.checkpoint()
        lines = ["# Bounded native OpenLane fault coverage", "", "Six author-constructed classes. Retained observations are not independent comparisons.", "",
                 "| Fault class | Native target obligation | Auxiliary reference check | Full flow |", "|---|---|---|---|"]
        for row in self.result["coverage"]:
            auxiliary = "; ".join(f"{a.get('checker', a.get('design'))}: {a.get('result', a.get('fault_result'))}" for a in row["auxiliary_checks"]) or "none"
            lines.append(f"| {row['fault_class']} | {row['result']} | {auxiliary} | not_checked |")
        lines += ["", "## Limits", "", *["- " + x for x in self.result["limitations"]], "", "## Evidence", "", f"- JSON: {EVIDENCE}", f"- Raw directory: {self.out}", "- Every execution directory contains exact argv, stdout, stderr, elapsed time, exit code and timeout state.", ""]
        (self.out / "coverage.md").write_text("\n".join(lines))
        inventory = [identity(p) for p in sorted(self.out.rglob("*")) if p.is_file() and p.name not in {"checkpoint.json", "raw_manifest.json"}]
        write_json(self.out / "raw_manifest.json", inventory)


def preserve_inventory():
    # Hash inputs only: concurrent unrelated experiments are explicitly excluded.
    roots = [ROOT / "src", FIXTURES, BASE, ROOT / "runs/alu8_drc_api_repeat_v3", ROOT / "runs/alu8_timing_api_v4"]
    files = [p for root in roots for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files += [ROOT / "scripts/native_fault_injection_study.py", ROOT / "rtl2gdsagi_paper/evidence/native_fault_injection.json", ROOT / "rtl2gdsagi_paper/evidence/experiment_manifest.json"]
    # Track manuscript source and existing paper evidence without scanning growing live runs.
    files += [p for p in (ROOT / "rtl2gdsagi_paper").rglob("*") if p.is_file() and p.suffix in {".tex", ".bib", ".md"}]
    return {str(p): digest(p) for p in sorted(set(files))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ"))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--complete-existing-run", help="Add corrected native checker controls/prerequisites to an existing run; preserve all original attempts")
    parser.add_argument("--summarize-existing-run", help="Verify receipts and enrich coverage from existing native outputs; execute no new native checks")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("--run-id must be a single safe path component")
    existing = args.complete_existing_run or args.summarize_existing_run
    if existing:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", existing):
            parser.error("existing run must be a safe single path component")
        study = Study.__new__(Study)
        study.out = RAW / existing
        study.timeout = args.timeout
        study.result = json.loads((study.out / "checkpoint.json").read_text())
        study.result.setdefault("script_invocations", []).append({"argv": [sys.executable, *sys.argv], "cwd": str(ROOT)})
        if args.complete_existing_run:
            study.complete_existing()
        else:
            study.summarize()
        return
    study = Study(args.run_id, args.timeout)
    shutil.copyfile(__file__, study.out / "study_script.initial.py")
    before = preserve_inventory()
    write_json(study.out / "original_inputs_before.json", before)
    try:
        study.discover()
        study.controls()
        study.cases()
        after = preserve_inventory()
        changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
        write_json(study.out / "original_inputs_after.json", after)
        study.result["original_artifacts_preserved"] = {"files_hashed": len(before), "changed_paths": changed,
                                                       "read_only_container_mounts": True, "concurrently_running_unrelated_cohort_excluded": True}
        if changed:
            raise RuntimeError("An original watched input changed: " + repr(changed))
        study.finish()
    except Exception as exc:
        study.result["status"] = "incomplete"
        study.result["error"] = repr(exc)
        for attack in ATTACKS:
            if not any(row["fault_class"] == attack for row in study.result["coverage"]):
                study.add_row(attack, "not_checked", [], "Execution did not complete: " + repr(exc))
        study.checkpoint()
        raise
    print(json.dumps({"evidence": str(EVIDENCE), "raw": str(study.out), "coverage_counts": study.result["coverage_counts"]}), flush=True)


if __name__ == "__main__":
    main()
