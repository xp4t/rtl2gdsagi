"""KLayout LVS report (.lvsdb) parsing.

An LVS verdict is assembled from three independent signals and they must agree:

* the tool's **exit code** (the stock SKY130 deck does ``exit(1)`` on mismatch),
* the **log** verdict line,
* the **.lvsdb** itself -- does it actually contain a cross-reference section,
  i.e. did a comparison run at all.

Any disagreement is a failure. In particular a log that claims a match while
the exit code is non-zero, or while the database holds no cross-reference, is
treated as a hardcoded pass rather than a result. See
:mod:`rtl2gdsagi.checks.deck_guard` for why that specific shape is guarded.

The .lvsdb is KLayout's own bracketed format, not XML::

    #%lvsdb-klayout
    J(
     W(top)                      <- top cell
     U(0.001)                    <- database unit
     L(l9 '1/0') ...             <- layers
     H(W B('...') C(top) X(...)) <- log entries, W=warning E=error
     X(AND201 ... Z( ... ))      <- circuit cross-reference
    )

Only the structure needed for a verdict is scanned; the geometry is left alone,
because these files run to tens of megabytes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..artifacts import Artifact

#: Conditions recorded at severity W whose own text says they are errors.
_MUST_CONNECT_RE = re.compile(
    r"must-connect|must be connected further up", re.IGNORECASE)

_MAGIC = "#%lvsdb-klayout"
_TOP_RE = re.compile(r"^\s*W\(([^)]*)\)", re.MULTILINE)
_XREF_RE = re.compile(r"^\s*X\(", re.MULTILINE)
_LOGENTRY_RE = re.compile(r"^\s*H\(([A-Z])\s", re.MULTILINE)
_LOGBODY_RE = re.compile(r"B\('((?:[^'\\]|\\.){0,400})'")

_LOG_MATCH_RE = re.compile(r"netlists?\s+match|congratulations", re.IGNORECASE)
_LOG_MISMATCH_RE = re.compile(
    r"netlists?\s+don'?t\s+match|netlists?\s+do\s+not\s+match|ERROR\s*:", re.IGNORECASE
)

_SEVERITY = {"E": "error", "W": "warning", "I": "info"}


@dataclass(frozen=True)
class LVSResult:
    report_path: Path
    top_cell: str
    exit_code: int | None
    #: Number of X(...) circuit cross-reference entries in the database.
    xref_circuits: int
    #: Counts by severity letter, e.g. {"warning": 20359}.
    severity_counts: dict[str, int]
    #: Distinct log bodies with their counts, most frequent first.
    message_counts: dict[str, int]
    log_claims_match: bool
    log_claims_mismatch: bool
    checked_gds: Artifact | None = None
    deck_trustworthy: bool | None = None
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def errors(self) -> int:
        return self.severity_counts.get("error", 0)

    @property
    def warnings(self) -> int:
        return self.severity_counts.get("warning", 0)

    @property
    def clean(self) -> bool:
        return not self.problems

    def summary(self) -> str:
        if self.clean:
            return (
                f"LVS clean: netlists match on {self.top_cell!r} "
                f"({self.xref_circuits} circuits cross-referenced, {self.warnings} warnings)"
            )
        return "LVS FAILED: " + "; ".join(self.problems)

    def top_messages(self, n: int = 8) -> list[tuple[str, int]]:
        return sorted(self.message_counts.items(), key=lambda kv: -kv[1])[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_path": str(self.report_path),
            "top_cell": self.top_cell,
            "exit_code": self.exit_code,
            "xref_circuits": self.xref_circuits,
            "severity_counts": dict(self.severity_counts),
            "log_claims_match": self.log_claims_match,
            "log_claims_mismatch": self.log_claims_mismatch,
            "deck_trustworthy": self.deck_trustworthy,
            "checked_gds": self.checked_gds.to_dict() if self.checked_gds else None,
            "clean": self.clean,
            "problems": list(self.problems),
            "top_messages": self.top_messages(),
        }

    def digest(self, limit: int = 8) -> str:
        lines = [
            f"top cell: {self.top_cell}",
            f"exit code: {self.exit_code}",
            f"circuits cross-referenced: {self.xref_circuits}",
            f"errors: {self.errors}  warnings: {self.warnings}",
        ]
        if self.problems:
            lines.append("")
            lines.append("problems:")
            lines.extend(f"  - {p}" for p in self.problems)
        if self.message_counts:
            lines.append("")
            lines.append("most frequent messages:")
            for msg, n in self.top_messages(limit):
                lines.append(f"  {n:>7}  {msg[:160]}")
        return "\n".join(lines)


def _completeness_problems(text: str) -> list[str]:
    """Structural completeness of a KLayout LVS database.

    The format is a single balanced S-expression whose atoms may contain
    quoted strings (``L(l5 '64/20')``) and comments are not used. Counting
    parentheses outside quotes therefore decides completeness exactly:

    * a truncated file leaves unclosed groups;
    * a complete one returns to depth zero and ends on the closing paren of
      its single top-level ``J(`` block.
    """
    depth = 0
    in_quote = False
    closed_top = False
    for ch in text:
        if in_quote:
            if ch == "'":
                in_quote = False
            continue
        if ch == "'":
            in_quote = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                closed_top = True
            elif depth < 0:
                return ["the LVS database has unbalanced parentheses "
                        "(more closing than opening); it is corrupt"]
    if in_quote:
        return ["the LVS database ends inside a quoted string; it is truncated"]
    if depth > 0:
        return [
            f"the LVS database is incomplete: {depth} unclosed group(s) at "
            "end of file. A truncated database describes only the circuits it "
            "happens to contain and cannot support a match verdict."
        ]
    if not closed_top:
        return ["the LVS database contains no complete top-level block"]
    return []


def parse_lvs_report(
    path: str | Path,
    *,
    log_text: str = "",
    exit_code: int | None = None,
    expected_top: str | None = None,
    checked_gds: Artifact | None = None,
    deck_trustworthy: bool | None = None,
) -> LVSResult:
    """Parse a ``.lvsdb`` and reconcile it against the log and exit code."""
    p = Path(path)
    problems: list[str] = []

    log_match = bool(_LOG_MATCH_RE.search(log_text))
    log_mismatch = bool(_LOG_MISMATCH_RE.search(log_text))

    if not p.is_file():
        return LVSResult(
            report_path=p, top_cell="", exit_code=exit_code, xref_circuits=0,
            severity_counts={}, message_counts={}, log_claims_match=log_match,
            log_claims_mismatch=log_mismatch, checked_gds=checked_gds,
            deck_trustworthy=deck_trustworthy,
            problems=(f"LVS report was not written: {p}",),
        )

    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.lstrip().startswith(_MAGIC):
        problems.append(
            f"LVS report does not start with {_MAGIC!r}; it is not a KLayout LVS database"
        )

    m = _TOP_RE.search(text)
    top_cell = (m.group(1).strip() if m else "")
    xref_circuits = len(_XREF_RE.findall(text))

    # The database has to be *complete*, not merely start correctly.
    #
    # Truncating the real 199,053-byte register database to 30,955 bytes -- 15%
    # of it, cut just after the first cross-reference -- previously came back
    # clean with one cross-referenced circuit. Every existing check was
    # satisfied by the surviving prefix: magic, a top cell, one `X(`, a clean
    # exit and a matching log. Nothing asked whether the rest of the
    # comparison was there.
    #
    # A KLayout LVS database is one balanced S-expression, so a truncated file
    # always ends with unclosed parentheses. That makes completeness exact and
    # cheap to check, and it is the property that matters: a partial file
    # cannot testify about the circuits it does not contain.
    problems.extend(_completeness_problems(text))

    severity_counts: dict[str, int] = {}
    for letter in _LOGENTRY_RE.findall(text):
        key = _SEVERITY.get(letter, letter)
        severity_counts[key] = severity_counts.get(key, 0) + 1

    message_counts: dict[str, int] = {}
    for body in _LOGBODY_RE.findall(text):
        msg = body.strip()
        message_counts[msg] = message_counts.get(msg, 0) + 1

    # --- reconcile the three signals ------------------------------------
    if exit_code not in (None, 0):
        problems.append(f"LVS tool exited {exit_code}")
    if log_mismatch:
        problems.append("log reports a netlist mismatch")
    if xref_circuits == 0:
        problems.append(
            "the LVS database contains no circuit cross-reference, so no netlist "
            "comparison actually ran"
        )
    if severity_counts.get("error"):
        problems.append(f"{severity_counts['error']} error entries in the LVS database")

    # Some conditions are recorded at severity W and are still errors.
    #
    # The register run carried three of these, verbatim:
    #
    #   "Must-connect subnets of VGND of circuit sky130_fd_sc_hd__clkbuf_1 must
    #    be connected further up in the hierarchy - this is an error at chip
    #    top level."
    #
    # The severity letter says warning; the message says error at top level,
    # and top level is exactly what was being certified. Blocking on the
    # message class rather than on the severity letter is deliberately narrow:
    # this is not "all warnings now fail", which would be its own kind of
    # dishonesty, but a named condition whose own text states it is fatal
    # where we are applying it.
    must_connect = sum(
        n for msg, n in message_counts.items()
        if _MUST_CONNECT_RE.search(msg)
    )
    if must_connect:
        problems.append(
            f"{must_connect} must-connect power/ground subnet(s) are not "
            "connected at top level. KLayout records these at severity W, but "
            "the message itself says this is an error at chip top level -- "
            "which is the level being signed off. Unresolved PG connectivity "
            "is the one defect class LVS exists to catch."
        )
    if deck_trustworthy is False:
        problems.append(
            "the LVS deck has no reachable failure path, so its verdict is not evidence"
        )
    if log_match and exit_code not in (None, 0):
        problems.append(
            "log claims the netlists match but the tool exited non-zero; "
            "treating the log verdict as unreliable"
        )
    if log_match and xref_circuits == 0:
        problems.append(
            "log claims the netlists match but no comparison is recorded in the "
            "database; this is a hardcoded pass, not a result"
        )
    if not log_match and exit_code == 0 and not log_mismatch:
        problems.append(
            "log records no explicit match verdict; refusing to infer a pass from exit code 0"
        )
    if expected_top and top_cell and top_cell != expected_top:
        problems.append(
            f"LVS database is for top cell {top_cell!r} but the design top is {expected_top!r}"
        )
    if not top_cell:
        problems.append("LVS database does not name a top cell")

    return LVSResult(
        report_path=p,
        top_cell=top_cell,
        exit_code=exit_code,
        xref_circuits=xref_circuits,
        severity_counts=severity_counts,
        message_counts=message_counts,
        log_claims_match=log_match,
        log_claims_mismatch=log_mismatch,
        checked_gds=checked_gds,
        deck_trustworthy=deck_trustworthy,
        problems=tuple(problems),
    )
