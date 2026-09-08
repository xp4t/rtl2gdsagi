"""Parsers turning raw tool output into structured metrics and verdicts.

Every parser here follows the same rule: **exit code 0 is not success**. The
report is read and the numbers are checked. Exit codes are used only as
corroborating evidence, and a disagreement between exit code and report content
is itself a failure rather than something to resolve in the tool's favour.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..stages import StageId
from ..taxonomy import FailureClass
from .verdict import Verdict, passed, qor_low
from .verdict import failed as failed_verdict


@dataclass
class ToolRun:
    """Result of one subprocess invocation."""

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_s: float = 0.0
    timed_out: bool = False

    @property
    def combined(self) -> str:
        return self.stdout + "\n" + self.stderr

    def tail(self, n: int = 4000) -> str:
        c = self.combined.strip()
        return c[-n:] if len(c) > n else c


def _runtime_failure(stage: StageId, run: ToolRun) -> Verdict | None:
    """Crash/OOM/timeout are environment problems, not design problems."""
    if run.timed_out:
        return failed_verdict(
            stage, FailureClass.TOOL_RUNTIME,
            f"{stage} timed out after {run.duration_s:.0f}s",
            evidence=run.tail(2000),
        )
    if run.returncode in (-9, 137):
        return failed_verdict(
            stage, FailureClass.TOOL_RUNTIME,
            f"{stage} was killed (likely out of memory)", evidence=run.tail(2000),
        )
    if run.returncode in (-11, 139):
        return failed_verdict(
            stage, FailureClass.TOOL_RUNTIME, f"{stage} segfaulted",
            evidence=run.tail(2000),
        )
    return None


# --------------------------------------------------------------- lint ------

_VERILATOR_ERR = re.compile(r"^%Error(?:-([A-Z0-9_]+))?:\s*(.*)$", re.MULTILINE)
_VERILATOR_WARN = re.compile(r"^%Warning-([A-Z0-9_]+):\s*(.*)$", re.MULTILINE)
_VERILATOR_SUMMARY = re.compile(r"Exiting due to \d+ warning", re.IGNORECASE)


def check_lint(run: ToolRun, *, fail_on_warning: bool = False) -> Verdict:
    stage = StageId.LINT
    if (v := _runtime_failure(stage, run)) is not None:
        return v

    # Verilator prints a trailing "%Error: Exiting due to N warning(s)" summary
    # when -Wall is fatal. That is a restatement of the warning count, not an
    # additional diagnostic, and counting it as an error turns a clean-but-noisy
    # lint into a hard failure.
    errors = [
        (code, msg) for code, msg in _VERILATOR_ERR.findall(run.combined)
        if not _VERILATOR_SUMMARY.match(msg)
    ]
    warnings = _VERILATOR_WARN.findall(run.combined)
    metrics = {
        "errors": len(errors),
        "warnings": len(warnings),
        "warning_codes": sorted({c for c, _ in warnings}),
    }

    if errors:
        codes = sorted({c or "GENERIC" for c, _ in errors})
        return failed_verdict(
            stage, FailureClass.RTL_SYNTAX,
            f"verilator reported {len(errors)} error(s): {', '.join(codes)}",
            evidence="\n".join(f"%Error-{c}: {m}" for c, m in errors[:40]),
            **metrics,
        )
    if fail_on_warning and warnings:
        return failed_verdict(
            stage, FailureClass.RTL_SYNTAX,
            f"verilator reported {len(warnings)} warning(s) and fail_on_warning is set",
            evidence="\n".join(f"%Warning-{c}: {m}" for c, m in warnings[:40]),
            **metrics,
        )
    if run.returncode != 0:
        return failed_verdict(
            stage, FailureClass.RTL_SYNTAX,
            f"verilator exited {run.returncode} without a parseable error",
            evidence=run.tail(), **metrics,
        )
    if warnings:
        return qor_low(
            stage, f"lint clean ({len(warnings)} warnings recorded)",
            evidence="\n".join(f"%Warning-{c}: {m}" for c, m in warnings[:20]),
            **metrics,
        )
    return passed(stage, "lint clean", **metrics)


# ---------------------------------------------------------------- sim ------

_SIM_FAIL = re.compile(
    r"(\$?(?:error|fatal)\b|assertion (?:failed|error)|\bFAILED\b|TEST FAILED|"
    r"ERROR:|Mismatch)", re.IGNORECASE)
_SIM_PASS = re.compile(
    r"(TEST(?:S)? PASSED|ALL TESTS PASSED|\bPASSED\b|SIMULATION PASSED|"
    r"\bOK\b\s*$)", re.IGNORECASE | re.MULTILINE)


def check_sim(run: ToolRun, *, testbench: str = "") -> Verdict:
    """Grade one simulation run.

    Three outcomes, because two would be wrong:

    * an explicit failure ($error/$fatal/assertion) is a functional bug, and
      those are escalated -- the agent may never "fix" RTL logic to silence one;
    * an explicit pass message is a pass;
    * a testbench that runs to completion without checking anything is neither.
      It is recorded as below-target rather than failed: it genuinely proves
      little, but failing a whole tapeout flow because someone's testbench does
      not print the word PASS would be absurd.
    """
    stage = StageId.SIM
    if (v := _runtime_failure(stage, run)) is not None:
        return v
    text = run.combined
    hits = [ln for ln in text.splitlines() if _SIM_FAIL.search(ln)]
    metrics = {"testbench": testbench, "failure_hits": len(hits)}

    if run.returncode != 0:
        return failed_verdict(
            stage, FailureClass.RTL_FUNCTIONAL,
            f"simulation of {testbench or 'testbench'} exited {run.returncode}",
            evidence=run.tail(2000), escalate=True, **metrics,
        )
    if hits:
        return failed_verdict(
            stage, FailureClass.RTL_FUNCTIONAL,
            f"simulation of {testbench or 'testbench'} reported "
            f"{len(hits)} failure message(s)",
            evidence="\n".join(hits[:40])[:2000],
            escalate=True,  # a functional bug is a human's call
            **metrics,
        )
    if _SIM_PASS.search(text):
        return passed(stage, f"{testbench or 'testbench'} passed", **metrics)

    return qor_low(
        stage,
        f"{testbench or 'testbench'} ran to completion with no errors, but "
        "printed no pass/fail result -- it is not self-checking, so it "
        "demonstrates the design elaborates and runs, not that it is correct",
        evidence=run.tail(1200), **metrics,
    )


# ---------------------------------------------------------- synthesis ------

_YOSYS_ERR = re.compile(r"^ERROR:\s*(.*)$", re.MULTILINE)
_YOSYS_LATCH = re.compile(r"(?<!no )latch inferred|inferring latch", re.IGNORECASE)
# Yosys prints its statistics in two different shapes, and the one you get
# depends on the design:
#
#     Number of cells:               929      <- design with submodules
#            22  292.781 cells                <- single flat module
#           939 8.56E+03 cells                <- same, area in scientific form
#
# Only matching the first means the simplest possible design -- one module,
# which is exactly what someone writes first -- reports zero cells and fails.
# The area column switches to scientific notation once it gets large, so it is
# matched loosely; only the count is actually read from these lines.
_YOSYS_CELLS_LABELLED = re.compile(r"^\s*Number of cells:\s+(\d+)", re.MULTILINE)
_YOSYS_CELLS_COMPACT = re.compile(
    r"^\s+(\d+)\s+[\d.eE+-]+\s+cells\s*$", re.MULTILINE)
_YOSYS_AREA = re.compile(r"Chip area for (?:top )?module.*?:\s*([0-9.]+)", re.IGNORECASE)
#: A row of the per-cell-type table, in either shape:
#:     <count> <area> <cellname>   or   <cellname>   <count>
_YOSYS_CELL_ROW_COMPACT = re.compile(
    r"^\s+(\d+)\s+[\d.eE+-]+\s+(\S+)\s*$", re.MULTILINE)
_YOSYS_CELL_ROW_LABELLED = re.compile(r"^\s+(\$\S+)\s+(\d+)\s*$", re.MULTILINE)


def _yosys_cell_count(text: str) -> int:
    if m := _YOSYS_CELLS_LABELLED.search(text):
        return int(m.group(1))
    hits = _YOSYS_CELLS_COMPACT.findall(text)
    return int(hits[-1]) if hits else 0


def _yosys_unmapped(text: str) -> dict[str, int]:
    """Cell types Yosys could not map to the standard-cell library.

    These keep their internal ``$``-prefixed names, and shipping them means the
    netlist contains logic no foundry cell implements.
    """
    out: dict[str, int] = {}
    for count, name in _YOSYS_CELL_ROW_COMPACT.findall(text):
        if name.startswith("$") and name != "$_TECHMAP_":
            out[name] = out.get(name, 0) + int(count)
    for name, count in _YOSYS_CELL_ROW_LABELLED.findall(text):
        if name != "$_TECHMAP_":
            out[name] = out.get(name, 0) + int(count)
    return out


def check_synthesis(
    run: ToolRun, netlist: Path | None, *, min_cells: int = 1, area_budget: float | None = None
) -> Verdict:
    stage = StageId.SYNTHESIS
    if (v := _runtime_failure(stage, run)) is not None:
        return v

    errors = _YOSYS_ERR.findall(run.combined)
    if errors:
        cls = (
            FailureClass.ELABORATION
            if any(re.search(r"module|parameter|width|port", e, re.I) for e in errors)
            else FailureClass.SYNTH_ERROR
        )
        return failed_verdict(
            stage, cls, f"yosys reported {len(errors)} error(s)",
            evidence="\n".join(errors[:20]),
        )
    if run.returncode != 0:
        return failed_verdict(
            stage, FailureClass.SYNTH_ERROR, f"yosys exited {run.returncode}",
            evidence=run.tail(),
        )
    if netlist is None or not Path(netlist).is_file() or Path(netlist).stat().st_size == 0:
        return failed_verdict(
            stage, FailureClass.SYNTH_ERROR,
            "yosys exited cleanly but wrote no netlist",
            evidence=run.tail(),
        )

    cells = _yosys_cell_count(run.combined)
    area = float(m.group(1)) if (m := _YOSYS_AREA.search(run.combined)) else None
    unmapped = _yosys_unmapped(run.combined)
    latches = bool(_YOSYS_LATCH.search(run.combined))

    metrics: dict[str, Any] = {
        "cells": cells, "area_um2": area, "unmapped": unmapped, "latches_inferred": latches,
    }

    if cells < min_cells:
        return failed_verdict(
            stage, FailureClass.SYNTH_ERROR,
            f"netlist has {cells} cells, expected at least {min_cells}",
            evidence=run.tail(2000), **metrics,
        )
    if unmapped:
        return failed_verdict(
            stage, FailureClass.SYNTH_ERROR,
            f"{sum(unmapped.values())} cells remain unmapped: {sorted(unmapped)[:6]}",
            evidence=run.tail(2000), **metrics,
        )
    if latches:
        return failed_verdict(
            stage, FailureClass.SYNTH_ERROR,
            "unintended latches were inferred during synthesis",
            evidence="\n".join(
                ln for ln in run.combined.splitlines() if _YOSYS_LATCH.search(ln)
            )[:1500],
            **metrics,
        )
    if area_budget is not None and area is not None and area > area_budget:
        return qor_low(
            stage, f"synthesis clean but area {area:.0f}um2 exceeds budget {area_budget:.0f}um2",
            evidence=f"area={area} budget={area_budget}", **metrics,
        )
    return passed(stage, f"synthesis clean: {cells} cells"
                  + (f", {area:.0f}um2" if area else ""), **metrics)


# ---------------------------------------------------------------- LEC ------

# EQY, not Yosys equiv_*: the latter cannot prove a mapped netlist against a
# real standard-cell library because the cells are blackboxes.
#
# EQY distinguishes two very different outcomes, and so must we:
#
#   "...: partitions not equivalent"  -> the netlist really does differ
#   "...: equivalence unknown"        -> the prover ran out of depth/time
#
# Reporting the second as the first would tell someone their design is broken
# when in fact the checker gave up. That is the worst possible error message,
# so the two are graded separately and worded differently.
_EQY_DONE = re.compile(r"DONE \((PASS|FAIL|UNKNOWN|ERROR)[,)]", re.IGNORECASE)
_EQY_EQUIV = re.compile(r"Successfully proved designs equivalent", re.IGNORECASE)
# EQY announces a proved partition twice, in two different shapes:
#     run: Proved equivalence of partition 'register.o_data' using strategy 'sat'
#     Successfully proved equivalence of partition register.o_data
# Only the first was matched, and case-sensitively, so a log containing just
# the second scored zero proved partitions. Both are accepted and the names are
# de-duplicated by the caller, so a partition reported twice still counts once.
_EQY_PROVED = re.compile(
    r"(?:Successfully )?proved equivalence of partition '?([^'\s]+)'?",
    re.IGNORECASE)
_EQY_NOT_EQUIV = re.compile(
    r"Could not prove equivalence of partition '([^']+)'[^:]*:\s*partitions not equivalent",
    re.IGNORECASE)
_EQY_UNKNOWN = re.compile(
    r"Could not prove equivalence of partition '([^']+)'[^:]*:\s*equivalence unknown",
    re.IGNORECASE)
_EQY_ERROR = re.compile(r"^ERROR:\s*(.*)$", re.MULTILINE)


def check_lec(run: ToolRun, stage: StageId) -> Verdict:
    """Verdict for a formal equivalence run."""
    if (v := _runtime_failure(stage, run)) is not None:
        return v

    text = run.combined
    proved = sorted(set(_EQY_PROVED.findall(text)))
    mismatched = sorted(set(_EQY_NOT_EQUIV.findall(text)))
    unknown = sorted(set(_EQY_UNKNOWN.findall(text)))

    # Every terminal marker, not the first.
    #
    # `_EQY_DONE.search()` returned the earliest `DONE (...)`, so a log reading
    # "DONE (PASS)" and later "DONE (FAIL)" was certified on the strength of
    # the first one. A proof that disagrees with itself is not a proof, and
    # which end of the log you read should not decide the answer.
    outcomes = [o.upper() for o in _EQY_DONE.findall(text)]
    outcome = outcomes[-1] if outcomes else None
    errors = sorted(set(_EQY_ERROR.findall(text)))

    metrics: dict[str, Any] = {
        "partitions_proved": len(proved),
        "partitions_not_equivalent": len(mismatched),
        "partitions_unknown": len(unknown),
        "eqy_outcome": outcome,
        "eqy_terminal_results": len(outcomes),
        "eqy_errors": len(errors),
    }

    # Contradictory terminal markers are themselves disqualifying, whichever
    # way they point.
    if len(set(outcomes)) > 1:
        return failed_verdict(
            stage, FailureClass.LEC_MISMATCH,
            f"the prover reported {len(outcomes)} terminal results that do not "
            f"agree ({', '.join(outcomes)}); refusing to pick one",
            evidence=run.tail(2500), **metrics,
        )
    # An explicit error is weighed *before* any claim of success, not after.
    #
    # An error on its own is an environment/configuration problem and is
    # classified as such further down -- the run never started, which is not a
    # statement about the design. An error accompanied by a claim of
    # equivalence is a different thing entirely: the log contradicts itself,
    # and that must not be resolved in favour of the happier line.
    if errors and (outcome == "PASS" or _EQY_EQUIV.search(text)):
        return failed_verdict(
            stage, FailureClass.LEC_MISMATCH,
            f"the prover claims equivalence but also reported "
            f"{len(errors)} explicit error(s) (e.g. {errors[0][:120]}); a proof "
            "cannot rest on a run that errored, whatever it printed afterwards",
            evidence=run.tail(2500), **metrics,
        )

    # Every one of these has to hold before equivalence may be claimed.
    #
    # This used to be `outcome == "PASS" or ...`, which short-circuited past
    # the contradiction checks: a log containing both "DONE (PASS)" and a
    # mismatched partition was certified equivalent, as was one where the
    # prover exited nonzero, and as was one that proved *nothing at all*
    # (0 partitions is not a proof, it is an empty run).
    claims_pass = outcome == "PASS" or bool(_EQY_EQUIV.search(text))
    if claims_pass:
        blockers: list[str] = []
        if run.returncode != 0:
            blockers.append(f"the prover exited {run.returncode}")
        if mismatched:
            blockers.append(
                f"{len(mismatched)} partition(s) reported not equivalent "
                f"({', '.join(mismatched[:3])})"
            )
        if unknown:
            blockers.append(
                f"{len(unknown)} partition(s) came back unknown "
                f"({', '.join(unknown[:3])})"
            )
        if not proved:
            blockers.append("no partition was actually proved")
        if blockers:
            return failed_verdict(
                stage, FailureClass.LEC_MISMATCH,
                "the equivalence log claims a pass but contradicts itself: "
                + "; ".join(blockers)
                + ". Refusing to certify equivalence on contradictory evidence.",
                evidence=run.tail(2500), **metrics,
            )
        return passed(
            stage, f"formally equivalent ({len(proved)} partition(s) proved)", **metrics
        )

    # A reported counterexample.
    #
    # KNOWN LIMITATION, and the reason this does not simply say "your netlist is
    # wrong": the RTL-versus-netlist comparison in this flow reports a mismatch
    # on the *sequential* partition of even a plain 8-bit counter that is
    # certainly correct. Evidence that the fault is in the comparison and not in
    # the design: comparing the netlist against itself proves cleanly, including
    # sequential partitions; combinational partitions always prove; and it is
    # unaffected by reset style, init attributes, or setundef/hilomap.
    #
    # Until that is understood, the flow may not accuse a design of being wrong.
    # It still blocks -- unverified is unverified, and signoff refuses to
    # certify -- but the wording reflects what is actually known.
    if mismatched:
        return failed_verdict(
            stage, FailureClass.LEC_MISMATCH,
            f"equivalence NOT established for {len(mismatched)} partition(s) "
            f"(e.g. {', '.join(mismatched[:3])}): the prover reported a "
            "counterexample. Note that this flow currently reports a "
            "counterexample for sequential logic even on designs known to be "
            "correct, so treat this as unverified rather than as proof of a "
            "bug, and check the trace before changing your RTL.",
            evidence=run.tail(3000), escalate=True, **metrics,
        )

    # The prover could not decide. Still blocks -- equivalence is unproven, and
    # signoff may not assume it -- but this is a checker limitation, not
    # evidence of a broken design, and the message says so.
    if unknown:
        return failed_verdict(
            stage, FailureClass.LEC_MISMATCH,
            f"equivalence could not be proved for {len(unknown)} partition(s) "
            f"(e.g. {', '.join(unknown[:3])}): the prover reached its limit "
            "without finding either a proof or a counterexample. This is not "
            "evidence that the netlist is wrong. Raise lec.induction_steps, or "
            "install an SMT solver so a stronger strategy is available.",
            evidence=run.tail(3000), escalate=True, **metrics,
        )

    if errs := _EQY_ERROR.findall(text):
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            f"the equivalence run could not start: {errs[0][:200]}",
            evidence=run.tail(2500), **metrics,
        )

    return failed_verdict(
        stage, FailureClass.LEC_MISMATCH,
        "the equivalence check produced no verdict; refusing to assume the "
        "netlist matches the RTL",
        evidence=run.tail(2500), escalate=True, **metrics,
    )


# ---------------------------------------------------------------- STA ------

_SLACK_RE = {
    "setup_wns": re.compile(r"^setup_wns\s+(-?[\d.eE+]+|INF)", re.MULTILINE),
    "setup_tns": re.compile(r"^setup_tns\s+(-?[\d.eE+]+|INF)", re.MULTILINE),
    "hold_wns": re.compile(r"^hold_wns\s+(-?[\d.eE+]+|INF)", re.MULTILINE),
    "hold_tns": re.compile(r"^hold_tns\s+(-?[\d.eE+]+|INF)", re.MULTILINE),
}
_STA_ERR = re.compile(r"^(Error|ERROR):\s*(.*)$", re.MULTILINE)
#: A SPEF that failed to parse is announced as a *warning* and the analysis
#: continues -- with no parasitics. OpenROAD then prints timing numbers
#: identical to the no-parasitic run, and nothing in the log says the words
#: "error". A signoff that reads a SPEF must prove the SPEF was actually read.
#:
#: P0-R1: matching only STA-0179 and a loose "spef ... failed" phrase missed
#: the family OpenROAD actually emits when a syntactically valid SPEF does not
#: match the design. A forged SPEF whose 35 *D_NET records all describe one
#: real net parses fine and produces `STA-0175` connectivity warnings; the run
#: still exits zero with plausible positive slack, and this checker passed it.
#:
#: The codes are enumerated deliberately rather than matching every OpenROAD
#: warning: a blanket "any [WARNING ...] fails" rule would be a different kind
#: of dishonesty, and would fail on warnings that say nothing about parasitics.
PARASITIC_DIAGNOSTIC_CODES = ("STA-0172", "STA-0174", "STA-0175", "STA-0179")

_STA_SPEF_PROBLEM = re.compile(
    r"\[(?:WARNING|ERROR)\s+(?:" + "|".join(PARASITIC_DIAGNOSTIC_CODES) + r")\]|"
    r"(?:spef|SPEF)[^\n]{0,80}(?:syntax error|cannot|failed|not found|unexpected)",
    re.IGNORECASE)
#: Emitted by the signoff STA script immediately after read_spef. A successful
#: read_spef is silent, so this marker is the only positive evidence that the
#: parasitics were actually consumed rather than skipped.
SPEF_ANNOTATED_MARKER = "RTL2GDSAGI_SPEF_ANNOTATED"

#: Quantitative annotation proof, emitted by the signoff STA script.
#:
#: The bare marker above only proves control flow reached the line after
#: `read_spef` -- it is equally present when the SPEF annotated nothing. This
#: one carries `report_parasitic_annotation`'s own counts, so the gate can
#: require that the timing engine consumed RC for a meaningful share of the
#: design rather than merely that the file was opened.
SPEF_COVERAGE_MARKER = "RTL2GDSAGI_SPEF_COVERAGE"

#: `report_parasitic_annotation`'s own output in the pinned OpenSTA build:
#:     Found 0 unannotated drivers.
#:     Found 0 partially unannotated drivers.
#: Parsed straight from the tool rather than re-echoed by our script, so the
#: number cannot be manufactured by the Tcl we generate.
_STA_UNANNOTATED = re.compile(
    r"Found\s+(\d+)\s+unannotated\s+drivers?\.", re.IGNORECASE)
_STA_PARTIAL_UNANNOTATED = re.compile(
    r"Found\s+(\d+)\s+partially\s+unannotated\s+drivers?\.", re.IGNORECASE)

#: Written into the antenna report by the antenna stage's own Tcl.
#:
#: `check_antennas` writes an empty report when the design is clean, and an
#: empty artifact cannot be bound as gate evidence -- which is how a fully
#: passing run still had its candidate refused at signoff. The marker carries
#: the check's return value, so a clean antenna result is a positive record
#: rather than an absent one.
ANTENNA_COMPLETE_MARKER = "RTL2GDSAGI_ANTENNA_COMPLETE"
_STA_SPEF_READ = re.compile(re.escape(SPEF_ANNOTATED_MARKER))
# A missing clock definition is a genuine constraint gap: every path in the
# design goes unchecked. Unconstrained *endpoints* are weaker evidence -- an
# output tied to a constant has no timing arc and is legitimately unconstrained
# -- so the two are graded differently rather than lumped together.
_NO_CLOCKS = re.compile(
    r"(no clocks defined|There are \d+ unclocked register)", re.IGNORECASE)
_UNCONSTRAINED = re.compile(
    r"There are (\d+) unconstrained endpoints", re.IGNORECASE)
_ENDPOINT_LINE = re.compile(r"^\s{2,}(\S+)\s*$", re.MULTILINE)


def _num(text: str, key: str) -> float | None:
    m = _SLACK_RE[key].search(text)
    if not m:
        return None
    raw = m.group(1)
    if raw.upper() == "INF":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def check_sta(
    run: ToolRun,
    stage: StageId,
    *,
    guardband: float = 0.0,
    expect_parasitics: bool = False,
) -> Verdict:
    """Shared by all three STA invocations; the gate type differs, not the parse."""
    if (v := _runtime_failure(stage, run)) is not None:
        return v

    errs = _STA_ERR.findall(run.combined)
    if errs:
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            f"OpenSTA reported {len(errs)} error(s)",
            evidence="\n".join(f"{a}: {b}" for a, b in errs[:20]),
        )
    if run.returncode != 0:
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG, f"OpenSTA exited {run.returncode}",
            evidence=run.tail(),
        )

    # Parasitic annotation has to be proven, not assumed from the presence of
    # numbers. A malformed SPEF produces a warning, zero annotation, and a
    # perfectly plausible timing report -- the same numbers as the analysis
    # with no interconnect at all.
    if expect_parasitics:
        if not _STA_SPEF_READ.search(run.combined):
            return failed_verdict(
                stage, FailureClass.EXTRACTION,
                "this analysis is supposed to use extracted parasitics, but "
                "the log carries no annotation marker; either read_spef never "
                "ran or it aborted, and the timing then describes a design "
                "with no interconnect",
                evidence=run.tail(2500),
            )
        if (sp := _STA_SPEF_PROBLEM.search(run.combined)):
            return failed_verdict(
                stage, FailureClass.EXTRACTION,
                "the SPEF did not parse cleanly or did not match the design "
                f"({sp.group(0)[:120].strip()}), so the reported timing is not "
                "annotated timing -- the numbers will match the no-parasitic "
                "analysis and mean nothing about the routed design",
                evidence=run.tail(3000),
            )

        # Quantitative annotation proof. A syntactically valid SPEF that
        # describes the wrong nets parses without complaint and annotates
        # almost nothing; the timing engine's own count is what distinguishes
        # that from a real annotation.
        um = _STA_UNANNOTATED.search(run.combined)
        pm = _STA_PARTIAL_UNANNOTATED.search(run.combined)
        if um is None or pm is None:
            return failed_verdict(
                stage, FailureClass.EXTRACTION,
                "the log carries no parasitic-annotation report, so there is "
                "no evidence the timing engine consumed RC for this design; "
                "reaching the line after read_spef is not annotation",
                evidence=run.tail(2500),
            )
        unannotated, partial = int(um.group(1)), int(pm.group(1))
        if unannotated or partial:
            return failed_verdict(
                stage, FailureClass.EXTRACTION,
                f"parasitic annotation is incomplete: {unannotated} "
                f"unannotated and {partial} partially unannotated driver(s). "
                "The SPEF parsed, but the timing engine found no RC for part "
                "of the design, so this slack is partly no-parasitic slack",
                evidence=run.tail(3000),
                unannotated_drivers=unannotated,
                partially_unannotated_drivers=partial,
            )

    m: dict[str, Any] = {k: _num(run.combined, k) for k in _SLACK_RE}
    if expect_parasitics:
        um2 = _STA_UNANNOTATED.search(run.combined)
        pm2 = _STA_PARTIAL_UNANNOTATED.search(run.combined)
        m["unannotated_drivers"] = int(um2.group(1)) if um2 else None
        m["partially_unannotated_drivers"] = int(pm2.group(1)) if pm2 else None
    no_clocks = bool(_NO_CLOCKS.search(run.combined))
    um = _UNCONSTRAINED.search(run.combined)
    unconstrained = int(um.group(1)) if um else 0
    m["unconstrained_endpoints"] = unconstrained  # type: ignore[assignment]
    m["no_clocks"] = no_clocks  # type: ignore[assignment]

    if all(
        v is None for k, v in m.items()
        if k not in ("unconstrained_endpoints", "no_clocks")
    ):
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            "STA produced no slack numbers; the report is unusable",
            evidence=run.tail(2500), **m,
        )
    if no_clocks:
        return failed_verdict(
            stage, FailureClass.SDC,
            "the design has undefined clocks or unclocked registers, so timing "
            "was never actually checked on those paths",
            evidence=_path_excerpt(run.combined, "check_setup", 1500), **m,
        )

    setup = m["setup_wns"]
    hold = m["hold_wns"]

    # A guardband is a *margin you must clear*, not an allowance.
    #
    # This was `limit = -abs(guardband)`, which inverted the meaning: a
    # guardband of 5ns accepted a hold slack of -4ns. Since the field is
    # model-writable, that made "propose a bigger guardband" a way to make
    # failing timing pass. It now only ever raises the bar, and a non-finite
    # value is rejected outright rather than silently defeating every
    # comparison (NaN compares False against everything).
    if not math.isfinite(guardband):
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            f"sta.slack_guardband_ns is {guardband}, which is not a finite "
            "number; refusing to compare timing against it",
            evidence=run.tail(1000), **m,
        )
    limit = abs(guardband)

    def _bad(slack: float | None) -> bool:
        """Slack fails unless it is a real number at or above the guardband."""
        return slack is None or not math.isfinite(slack) or slack < limit

    # Which metrics each stage must actually have. A missing number used to
    # skip its own check (`hold is not None and hold < limit`), so a signoff
    # report containing only setup passed the hold gate by omission.
    required: tuple[str, ...] = ()
    if stage is StageId.STA_POSTCTS:
        required = ("hold_wns",)
    elif stage is StageId.STA_SIGNOFF:
        required = ("setup_wns", "hold_wns")
    absent = [k for k in required if m.get(k) is None]
    if absent:
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            f"{stage} reported no {', '.join(absent)}; a timing gate cannot "
            "pass on a report that never states the number it gates on",
            evidence=run.tail(2500), **m,
        )
    nonfinite = [k for k in required
                 if isinstance(m.get(k), float) and not math.isfinite(m[k])]
    if nonfinite:
        return failed_verdict(
            stage, FailureClass.TCL_CONFIG,
            f"{stage} reported a non-finite value for {', '.join(nonfinite)}",
            evidence=run.tail(2500), **m,
        )

    # Post-CTS is the hold gate; signoff checks both.
    if stage is StageId.STA_POSTCTS and _bad(hold):
        return failed_verdict(
            stage, FailureClass.HOLD,
            f"hold WNS {hold:.4f}ns is below the {limit:.4f}ns guardband after CTS",
            evidence=_path_excerpt(run.combined, "hold"), **m,
        )
    if stage is StageId.STA_SIGNOFF:
        if _bad(hold):
            return failed_verdict(
                stage, FailureClass.HOLD,
                f"signoff hold WNS {hold:.4f}ns is below the "
                f"{limit:.4f}ns guardband",
                evidence=_path_excerpt(run.combined, "hold"), **m,
            )
        if _bad(setup):
            return failed_verdict(
                stage, FailureClass.SETUP,
                f"signoff setup WNS {setup:.4f}ns is below the "
                f"{limit:.4f}ns guardband",
                evidence=_path_excerpt(run.combined, "setup"), **m,
            )
    if stage is StageId.STA_PRE and setup is not None and setup < limit:
        # Advisory: recorded and fed to the optimizer, never blocks (review 4.9).
        return qor_low(
            stage,
            f"pre-layout setup WNS {setup:.4f}ns is negative (advisory estimate; "
            "not blocking, real timing is decided at signoff)",
            evidence=_path_excerpt(run.combined, "setup"), **m,
        )

    parts = []
    if setup is not None:
        parts.append(f"setup WNS {setup:.4f}ns")
    if hold is not None:
        parts.append(f"hold WNS {hold:.4f}ns")
    summary = "timing met: " + ", ".join(parts) if parts else "timing met"

    if unconstrained:
        # An unconstrained endpoint is a path timing never looked at.
        #
        # This used to return `qor_below_target` with ok=True on the assumption
        # that such endpoints are constant-driven and therefore have no timing
        # arc. That assumption was never checked against anything: a report
        # saying "99 unconstrained endpoints" produced a passing signoff, and
        # the 99 could equally have been real paths left unconstrained by an
        # incomplete SDC. "Probably benign" is not evidence.
        #
        # At the gates that decide the design, it now fails closed. Pre-layout
        # stays advisory because it is explicitly not authoritative.
        if stage in (StageId.STA_POSTCTS, StageId.STA_SIGNOFF):
            return failed_verdict(
                stage, FailureClass.SDC,
                f"{summary}, but {unconstrained} endpoint(s) are unconstrained "
                "-- those paths were never timed, so this report does not show "
                "the design meets timing. Constrain them, or record them as "
                "intentionally untimed in the design's timing intent.",
                evidence=_path_excerpt(run.combined, "check_setup", 1500), **m,
            )
        return qor_low(
            stage,
            f"{summary}, but {unconstrained} endpoint(s) are unconstrained",
            evidence=_path_excerpt(run.combined, "check_setup", 1200), **m,
        )
    return passed(stage, summary, **m)


def _path_excerpt(text: str, which: str, limit: int = 2500) -> str:
    """Pull the relevant report section so the agent sees the critical path."""
    marker = f"=== {which} ==="
    i = text.find(marker)
    if i < 0:
        return text[-limit:]
    return text[i : i + limit]


# ----------------------------------------------------------- OpenROAD ------

_OR_ERR = re.compile(r"^\[ERROR\s+([A-Z]{3}-\d+)\]\s*(.*)$", re.MULTILINE)
_OR_WARN = re.compile(r"^\[WARNING\s+([A-Z]{3}-\d+)\]", re.MULTILINE)
_OR_AREA = re.compile(r"Design area\s+([\d.]+)\s*u\^2\s+([\d.]+)%", re.IGNORECASE)
# Global placement prints one of these per Nesterov iteration:
#     [NesterovSolve] Iter: 70 overflow: 0.138467 HPWL: 384610
# There is no "Total overflow" line anywhere in a real log, so the previous
# pattern matched nothing and the congestion gate never ran. Like the routing
# violation count this is a *converging series* -- the first iteration is
# always high (0.65 on the register design, against a 0.02 limit) -- so the
# terminal value is the result and a plain search() would condemn every design.
_OR_OVERFLOW = re.compile(r"^\[NesterovSolve\].*?overflow:\s*([\d.]+)",
                          re.IGNORECASE | re.MULTILINE)
#: The authoritative terminal value, and proof the solver actually converged:
#:     [NesterovSolve] Finished with Overflow: 0.099774
#: Its absence after a series of iterations means global placement ran out of
#: iterations rather than settling, which is the case actually worth flagging.
_OR_OVERFLOW_FINAL = re.compile(r"Finished with Overflow:\s*([\d.]+)",
                                re.IGNORECASE)
# OpenROAD writes this as "[INFO DRT-0199]   Number of violations = 900." --
# with an '=', not a colon. The original pattern required a digit straight
# after whitespace, so it matched *nothing* in a real routing log: the count
# was never recorded and routing passed with no violation evidence at all.
#
# The router prints one of these per optimisation iteration (900, 739, 764,
# 104, 38, 0 on the OV7670 design), so a single search() would latch onto the
# first, worst, intermediate number. Every count is collected and only the
# terminal one decides -- see _route_violations.
_OR_DRC_VIOL = re.compile(
    r"(?:total\s+)?number\s+of\s+violations?\s*[:=]\s*(\d+)", re.IGNORECASE)
#: The router says so explicitly when it finishes. Without this line the last
#: count seen is from an aborted run and means nothing.
_OR_ROUTE_DONE = re.compile(r"DRT-0198\]|Complete detail routing", re.IGNORECASE)
# `report_clock_skew` prints a table, never a "Worst clock skew:" line -- the
# old pattern was invented and matched nothing, so clock_skew_ns was never
# recorded on any run. The real shape is:
#
#     Clock i_pclk
#     Latency      CRPR       Skew
#     _1661_/CLK ^
#        0.38
#     _1662_/CLK ^
#        0.31      0.00       0.07      <- latency, CRPR, skew
#
# and on a design where STA finds no launch/capture pair it prints
# "No launch/capture paths found." instead, in which case there is no skew to
# report and none is invented.
_OR_SKEW_ROW = re.compile(r"^\s+-?[\d.]+\s+-?[\d.]+\s+(-?[\d.]+)\s*$", re.MULTILINE)
_OR_SKEW_NO_PATHS = re.compile(r"No launch/capture paths found", re.IGNORECASE)
# OpenROAD's real output is "[INFO ANT-0002] Found 1 net violations." and
# "[INFO ANT-0001] Found 1 pin violations." -- not the phrasing a reasonable
# person would guess. A regex that misses it scores zero violations while the
# word "antenna" still appears in the log, so a naive "did it mention antenna?"
# guard passes a design that genuinely violates the rule.
_OR_ANTENNA_NETS = re.compile(r"ANT-0002\]\s*Found\s+(\d+)\s+net", re.IGNORECASE)
_OR_ANTENNA_PINS = re.compile(r"ANT-0001\]\s*Found\s+(\d+)\s+pin", re.IGNORECASE)
_OR_ANTENNA_RAN = re.compile(r"ANT-000\d\]|check_antennas", re.IGNORECASE)
_OR_PLACE_FAIL = re.compile(r"(detailed placement failed|placement failed|overlap)", re.I)


#: Artifact keys whose file may legitimately be zero bytes. An empty DRC or
#: congestion report is the *good* outcome -- it means nothing was found. An
#: empty DEF, netlist or SPEF never is.
_REPORT_KEYS = frozenset({
    "route_drc", "congestion_report", "antenna_report", "pdn_report",
    "drc_report", "lvs_report", "cts_report",
})


def is_report_key(key: str) -> bool:
    return key in _REPORT_KEYS or key.endswith(("_report", "_rpt", "_drc"))


def check_openroad(
    run: ToolRun,
    stage: StageId,
    *,
    outputs: dict[str, Path] | None = None,
    overflow_limit: float = 0.02,
) -> Verdict:
    """Verdict for any OpenROAD-driven stage."""
    if (v := _runtime_failure(stage, run)) is not None:
        return v

    outputs = outputs or {}
    errs = _OR_ERR.findall(run.combined)
    metrics: dict[str, Any] = {"warnings": len(_OR_WARN.findall(run.combined))}

    _CLASS = {
        StageId.FLOORPLAN: FailureClass.FLOORPLAN,
        StageId.PDN: FailureClass.PDN,
        StageId.PLACEMENT: FailureClass.PLACEMENT,
        StageId.CTS: FailureClass.CTS,
        StageId.ROUTING: FailureClass.ROUTING,
        StageId.EXTRACTION: FailureClass.EXTRACTION,
        StageId.ANTENNA: FailureClass.ANTENNA,
    }
    cls = _CLASS.get(stage, FailureClass.TOOL_RUNTIME)

    if errs:
        codes = [c for c, _ in errs]
        # A DRT/ODB error about an off-grid or missing library shape is a
        # library-integrity problem, not something to retune (review 9.4).
        if any(re.search(r"offgrid|not found in the library|LEF", m, re.I) for _, m in errs):
            cls = FailureClass.LIBRARY
        return failed_verdict(
            stage, cls, f"OpenROAD reported {len(errs)} error(s): {', '.join(codes[:5])}",
            evidence="\n".join(f"[ERROR {c}] {m}" for c, m in errs[:20]),
            escalate=cls is FailureClass.LIBRARY, **metrics,
        )
    if run.returncode != 0:
        return failed_verdict(
            stage, cls, f"OpenROAD exited {run.returncode}", evidence=run.tail(), **metrics,
        )

    for key, path in outputs.items():
        p = Path(path)
        if not p.is_file():
            return failed_verdict(
                stage, cls, f"{stage} exited cleanly but {key} was not written ({p.name})",
                evidence=run.tail(2000), **metrics,
            )
        # A report may legitimately be empty -- an empty routing-DRC or
        # congestion report means nothing was found, which is the *good*
        # outcome. Design databases may not: an empty DEF, netlist or SPEF is
        # always a failure.
        if p.stat().st_size == 0 and not is_report_key(key):
            return failed_verdict(
                stage, cls, f"{stage} wrote an empty {key} ({p.name})",
                evidence=run.tail(2000), **metrics,
            )

    if (m := _OR_AREA.search(run.combined)):
        metrics["area_um2"] = float(m.group(1))
        metrics["utilization_pct"] = float(m.group(2))

    if stage is StageId.PLACEMENT:
        if _OR_PLACE_FAIL.search(run.combined):
            return failed_verdict(
                stage, FailureClass.PLACEMENT, "detailed placement is not legal",
                evidence=run.tail(2000), **metrics,
            )
        iters = [float(x) for x in _OR_OVERFLOW.findall(run.combined)]
        final = _OR_OVERFLOW_FINAL.search(run.combined)
        if iters or final:
            converged = final is not None
            ov = float(final.group(1)) if final else iters[-1]
            metrics["overflow"] = ov
            metrics["overflow_iterations"] = len(iters)
            metrics["overflow_converged"] = converged
            if not converged:
                return qor_low(
                    stage,
                    f"global placement stopped at overflow {ov:.4f} without "
                    "converging (no 'Finished with Overflow' line); it ran out "
                    "of iterations rather than settling",
                    evidence=run.tail(2500), **metrics,
                )
            if ov > overflow_limit:
                # Soft: catch routability here, far cheaper than a failed route.
                return qor_low(
                    stage,
                    f"placement legal but global-route overflow {ov:.4f} exceeds "
                    f"{overflow_limit:.4f}; routing is at risk",
                    evidence=run.tail(2500), **metrics,
                )
    if stage is StageId.CTS:
        skews = [abs(float(x)) for x in _OR_SKEW_ROW.findall(run.combined)]
        if skews:
            # Worst across every clock in the report.
            metrics["clock_skew_ns"] = max(skews)
            metrics["clock_skew_rows"] = len(skews)
        elif _OR_SKEW_NO_PATHS.search(run.combined):
            # Recorded as absent rather than as zero: "no paths to compare"
            # is not "perfect skew", and a 0.0 here would read as the latter.
            metrics["clock_skew_ns"] = None
            metrics["clock_skew_note"] = "no launch/capture paths to compare"
    if stage is StageId.ROUTING:
        counts = [int(x) for x in _OR_DRC_VIOL.findall(run.combined)]
        metrics["route_violation_iterations"] = len(counts)
        if not _OR_ROUTE_DONE.search(run.combined):
            return failed_verdict(
                stage, FailureClass.ROUTING,
                "detailed routing never reported completion; the log has no "
                "'Complete detail routing', so any violation count in it is "
                "from an unfinished route",
                evidence=run.tail(2500), **metrics,
            )
        if not counts:
            # Fail closed. Silence is not zero: the original pattern could not
            # match OpenROAD's real syntax, so it read no count and passed.
            return failed_verdict(
                stage, FailureClass.ROUTING,
                "detailed routing reported no violation count; refusing to "
                "infer a clean route from the absence of a number",
                evidence=run.tail(2500), **metrics,
            )
        n = counts[-1]
        metrics["route_violations"] = n
        if n:
            return failed_verdict(
                stage, FailureClass.ROUTING,
                f"detailed routing left {n} violation(s)",
                evidence=run.tail(2500), **metrics,
            )
    if stage is StageId.ANTENNA:
        nets_all = _OR_ANTENNA_NETS.findall(run.combined)
        pins_all = _OR_ANTENNA_PINS.findall(run.combined)
        if not nets_all and not pins_all:
            # No explicit count anywhere: the check did not report a result, so
            # there is nothing to call clean. Never infer a pass from silence.
            return failed_verdict(
                stage, FailureClass.ANTENNA,
                "the antenna check reported no violation count; refusing to "
                "infer a pass from the absence of a number",
                evidence=run.tail(2000), **metrics,
            )
        # Both halves are required. Treating a missing side as zero turned a
        # one-sided report into a clean result, and check_antennas always
        # reports both when it actually runs.
        if not nets_all or not pins_all:
            missing = "net" if not nets_all else "pin"
            return failed_verdict(
                stage, FailureClass.ANTENNA,
                f"the antenna check reported no {missing} violation count; a "
                "one-sided result cannot be read as clean",
                evidence=run.tail(2000), **metrics,
            )
        # The stage may run check_antennas more than once (repair, then
        # re-check). Taking the first match let an early 0/0 hide a later 4/5,
        # so the *worst* count over the whole log decides.
        nets = max(int(x) for x in nets_all)
        pins = max(int(x) for x in pins_all)
        metrics["antenna_net_violations"] = nets
        metrics["antenna_pin_violations"] = pins
        metrics["antenna_results"] = min(len(nets_all), len(pins_all))
        if nets or pins:
            return failed_verdict(
                stage, FailureClass.ANTENNA,
                f"antenna violations: {nets} net(s), {pins} pin(s)",
                evidence=run.tail(2500), **metrics,
            )

    return passed(stage, f"{stage} completed", **metrics)
