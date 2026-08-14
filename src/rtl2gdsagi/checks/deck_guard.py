"""Deck integrity guard.

An agentic flow has a failure mode a human flow does not: when the model is
asked to "make DRC/LVS pass", the cheapest way to satisfy the checker is to
weaken the checker. A generated deck that unconditionally prints
``Netlists match`` passes any log-grepping result_check forever.

This is not hypothetical. A real SKY130-adjacent LVS runset on this machine
ends with::

    # KLayout's compare returns false here strictly due to top-level pin
    # mismatches (VDD/VSS global nets vs explicit pins).
    logger.info('INFO : Congratulations! Netlists match.')
    logger.info('INFO : (17,018 devices and nets verified successfully)')

There is no ``compare`` call gating those lines and the device count is a
literal, so the "pass" is a printf. The stock PDK deck, by contrast, does::

    if ! compare
      logger.error("ERROR : Netlists don't match")
      exit(1)
    else
      logger.info("INFO : Congratulations! Netlists match.")

So the discriminator is structural: a trustworthy deck both *calls* the
comparison and has a reachable failure branch. These checks run in
config_check, before the tool is invoked, and the deck's sha256 is recorded so
result_check can prove the deck that ran is the deck that was vetted.
"""

from __future__ import annotations

import hashlib

import re
from dataclasses import dataclass
from pathlib import Path

#: Strings that assert a passing verdict.
_VERDICT_PASS = re.compile(
    r"(netlists?\s+match|congratulations|lvs\s+clean|drc\s+clean|no\s+violations)",
    re.IGNORECASE,
)
#: Strings that assert a failing verdict, i.e. evidence a failure path exists.
_VERDICT_FAIL = re.compile(
    r"(don'?t\s+match|do\s+not\s+match|mismatch|not\s+clean|lvs\s+failed|drc\s+failed"
    r"|violations?\s+found)",
    re.IGNORECASE,
)
#: An executable comparison call (Ruby DSL `compare`, or an explicit exit).
_COMPARE_CALL = re.compile(r"^\s*(?:if\s*!?\s*|unless\s+|\w+\s*=\s*)?compare\b", re.MULTILINE)
_HARD_EXIT = re.compile(r"^\s*exit\s*\(\s*[1-9]", re.MULTILINE)


@dataclass(frozen=True)
class DeckAudit:
    path: Path
    kind: str  # "lvs" or "drc"
    has_compare: bool
    has_fail_branch: bool
    has_hard_exit: bool
    unconditional_pass_lines: tuple[int, ...]
    problems: tuple[str, ...]
    #: Content identity of the deck actually read, for the release candidate.
    sha256: str = ""
    #: Human label if this deck is on the approved list.
    approved_as: str = ""

    @property
    def trustworthy(self) -> bool:
        return not self.problems

    def summary(self) -> str:
        if self.trustworthy:
            return f"{self.kind.upper()} deck {self.path.name} has a reachable failure path"
        return f"{self.kind.upper()} deck {self.path.name} cannot be trusted: " + "; ".join(
            self.problems
        )


def _strip_comments(text: str) -> list[tuple[int, str]]:
    """Return (1-based lineno, code) for lines with comments removed.

    Ruby/TCL both use ``#``. Quoted ``#`` is rare in decks; treating it as a
    comment start only risks a false *positive* on the guard, never a false pass.
    """
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        code = raw.split("#", 1)[0]
        if code.strip():
            out.append((i, code))
    return out


#: Content hashes of decks whose behaviour is validated for this project.
#:
#: Trust comes from identity, not from inspection. The previous guard searched
#: the Ruby source for a `compare` call, a failure phrase and an `exit`, and
#: called a deck trustworthy when all three appeared *anywhere*. That is not a
#: reachability proof, and it accepts this:
#:
#:     if false
#:       if ! compare
#:         logger.error("Netlists don't match")
#:         exit(1)
#:       end
#:     end
#:     logger.info("Netlists match")
#:
#: Deciding reachability properly means interpreting Ruby, which a checker has
#: no business doing. Pinning the exact bytes of a deck that has been run
#: against known-good and known-bad designs is both stronger and honest about
#: what is actually known.
#:
#: From sky130A, volare bdc9412b3e468c102d01b7cf6337be06ec6e9c9a.
APPROVED_DECKS: dict[str, str] = {
    "9ac9ea80e91786510c2010f9f816a090d1879dbc22937b3280947be7cab2c890":
        "sky130A libs.tech/klayout/lvs/sky130.lvs (volare bdc9412b)",
    "ff4c0281ff485ae1c85f44d6d2695d43dd71422363edea8bc6c1b3dde6ef9470":
        "sky130A libs.tech/klayout/drc/sky130A_mr.drc (volare bdc9412b)",
}


def deck_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_deck(path: str | Path, *, kind: str = "lvs") -> DeckAudit:
    """Decide whether a deck's verdict may be treated as authoritative.

    Two independent conditions, the first carrying the weight:

    1. the deck's content hash is on the approved list;
    2. the lexical guard finds nothing obviously wrong.

    (2) alone can be fooled -- see APPROVED_DECKS -- so it is retained only as
    defence in depth, and never as the basis of trust.
    """
    p = Path(path)
    if not p.is_file():
        return DeckAudit(
            path=p, kind=kind, has_compare=False, has_fail_branch=False,
            has_hard_exit=False, unconditional_pass_lines=(),
            problems=(f"deck does not exist: {p}",),
        )

    text = p.read_text(encoding="utf-8", errors="replace")
    code_lines = _strip_comments(text)
    code = "\n".join(c for _, c in code_lines)

    has_compare = bool(_COMPARE_CALL.search(code))
    has_fail_branch = bool(_VERDICT_FAIL.search(code))
    has_hard_exit = bool(_HARD_EXIT.search(code))

    pass_lines = tuple(n for n, c in code_lines if _VERDICT_PASS.search(c))

    problems: list[str] = []
    digest = deck_sha256(p)
    if digest not in APPROVED_DECKS:
        problems.append(
            f"deck {p.name} (sha256 {digest[:12]}) is not an approved deck. Its "
            "verdict cannot be treated as authoritative: whether a deck really "
            "can fail is a property of its behaviour, and this project only "
            "knows that for decks it has validated. Approved: "
            + ", ".join(sorted(APPROVED_DECKS.values()))
        )
    if kind == "lvs" and not has_compare:
        problems.append(
            "no executable `compare` call found, so the netlist comparison never runs"
        )
    if pass_lines and not (has_fail_branch or has_hard_exit):
        problems.append(
            f"asserts a passing verdict at line(s) {', '.join(map(str, pass_lines))} "
            "but has no failure branch and no non-zero exit; the pass is unconditional"
        )
    return DeckAudit(
        path=p,
        kind=kind,
        has_compare=has_compare,
        has_fail_branch=has_fail_branch,
        has_hard_exit=has_hard_exit,
        unconditional_pass_lines=pass_lines,
        problems=tuple(problems),
        sha256=digest,
        approved_as=APPROVED_DECKS.get(digest, ""),
    )
