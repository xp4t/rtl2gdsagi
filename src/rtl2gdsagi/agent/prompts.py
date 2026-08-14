"""Prompt construction.

The model is given already-computed facts and asked for a diagnosis plus a
bounded config delta. It is never asked for TCL, and it is never asked whether
a stage passed -- that question is answered before it is ever called.

The schema for the relevant IR section is injected verbatim, with ranges and
choices, so the model proposes values the renderer can actually accept.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..ir import describe_section
from ..taxonomy import TAXONOMY, lookup

if TYPE_CHECKING:
    from .client import DiagnosisRequest

SYSTEM_PROMPT = """\
You are the diagnostic engine of an autonomous RTL-to-GDSII flow. A stage has \
failed. Deterministic code has already parsed the tool's reports and decided \
that it failed; your job is root-cause analysis and a bounded remediation \
proposal, not verdict-setting.

Rules you operate under, all enforced by the orchestrator regardless of what \
you return:

1. You never write TCL, Tcl, shell, or any tool syntax. Your only write surface \
   is a JSON `config_delta` addressing declared schema fields. A deterministic \
   renderer turns those values into scripts.
2. You cannot waive, filter, skip or downgrade any DRC, LVS, antenna, timing or \
   equivalence violation. No such field exists in the schema. Proposing one is \
   rejected.
3. You never propose changes to RTL functional logic in response to a timing, \
   DRC, congestion or other physical problem. Hold violations in particular are \
   a clock-tree or constraint problem, never an RTL problem.
4. You never propose editing PDK files, standard-cell libraries, LEF/Liberty \
   files, or DRC/LVS decks. These are immutable ground truth. A failure that \
   implicates them is an escalation, not a fix.
5. Prefer the shallowest rollback consistent with the evidence. Rolling back \
   further than the evidence supports wastes a full physical-implementation \
   cycle; not rolling back far enough wastes several.
6. If the evidence does not support a confident root cause, say so with low \
   confidence and set "escalate": true. Confident escalation is a correct \
   outcome, not a failure. Do not invent a plausible-sounding fix to appear \
   useful.

Respond with exactly one JSON object in a ```json fenced block, and nothing else:

{
  "failure_class": "<one of the taxonomy classes>",
  "implicated_stage": "<stage name, or null if not a design problem>",
  "confidence": <float 0.0-1.0>,
  "evidence": "<the specific numbers/messages that led you here>",
  "reasoning": "<why this stage and not an adjacent one>",
  "config_delta": {"<section>": {"<field>": <value>}},
  "escalate": <true|false>
}
"""


def _taxonomy_digest() -> str:
    rows = []
    for e in TAXONOMY:
        stage = e.responsible_stage.value if e.responsible_stage else "-"
        esc = f" (escalates to {e.escalate_to.value})" if e.escalate_to else ""
        rows.append(
            f"  {e.failure.value:<18} -> {stage:<12}{esc}  [{e.resolution.value}]"
        )
    return "\n".join(rows)


def build_diagnosis_prompt(req: "DiagnosisRequest") -> str:
    parts: list[str] = []

    parts.append(f"# Failed stage: {req.stage}")
    parts.append(f"attempt {req.attempt} of {req.retry_limit}")
    parts.append("")
    parts.append("## What the deterministic checker concluded")
    parts.append(req.summary)
    if req.failure_class_hint is not None:
        entry = lookup(req.failure_class_hint)
        parts.append("")
        parts.append(
            f"Its provisional classification is `{req.failure_class_hint.value}` "
            f"(evidence source: {entry.evidence}). Confirm or correct this."
        )
        if entry.forbids:
            parts.append(
                "For this class you must NOT propose changes to: "
                + ", ".join(entry.forbids)
            )
        if entry.notes:
            parts.append(f"Domain note: {entry.notes}")

    parts.append("")
    parts.append("## Parsed metrics")
    parts.append("```json")
    parts.append(json.dumps(req.metrics, indent=2, default=str)[:3000])
    parts.append("```")

    if req.evidence:
        parts.append("")
        parts.append("## Tool evidence")
        parts.append("```")
        parts.append(req.evidence[:6000])
        parts.append("```")

    if req.action_space:
        sections = ", ".join(f"`{s}`" for s in sorted(req.action_space))
        parts.append("")
        parts.append(f"## Your authorised write surface: {sections}")
        parts.append(
            "This is generated from the same authorization table the validator "
            "enforces. Every field listed here is one your proposal may set; "
            "any field or section NOT listed will be rejected. Values outside "
            "the stated range or choices are rejected before rendering."
        )
        parts.append("```json")
        parts.append(json.dumps(req.action_space, indent=2, default=str))
        parts.append("```")
        parts.append("")
        parts.append("Current values of those fields:")
        parts.append("```json")
        parts.append(json.dumps(req.current_config, indent=2, default=str))
        parts.append("```")

    if req.tried_configs:
        parts.append("")
        parts.append("## Already tried and failed")
        parts.append(
            "Do not propose any of these again; identical configurations are "
            "refused by the orchestrator."
        )
        parts.append("```json")
        parts.append(json.dumps(req.tried_configs[-6:], indent=2, default=str)[:2500])
        parts.append("```")

    if req.history:
        parts.append("")
        parts.append("## Earlier stage results (for delta analysis)")
        parts.append(
            "Compare the same critical path or metric across checkpoints where "
            "relevant: a path already near-critical before placement implicates "
            "synthesis, while one that only became critical after routing "
            "implicates placement."
        )
        parts.append("```json")
        parts.append(json.dumps(req.history[-10:], indent=2, default=str)[:3000])
        parts.append("```")

    parts.append("")
    parts.append("## PDK context")
    parts.append("```json")
    parts.append(json.dumps(req.pdk_context, indent=2, default=str)[:2000])
    parts.append("```")

    parts.append("")
    parts.append("## Failure class -> responsible stage table")
    parts.append("```")
    parts.append(_taxonomy_digest())
    parts.append("```")

    parts.append("")
    parts.append(
        "Diagnose the root cause and propose a bounded config_delta. If the "
        "correct action is to escalate to a human, set escalate true and leave "
        "config_delta empty."
    )
    return "\n".join(parts)


def build_sdc_prompt(facts: dict, pdk_context: dict, current: dict) -> str:
    """Initial SDC-generation prompt (values only; the renderer writes the SDC)."""
    return "\n".join(
        [
            "# Generate timing constraints",
            "",
            "The user does not hand-write SDC. Propose constraint *values*; a "
            "deterministic renderer emits the SDC file itself.",
            "",
            "## Design facts from characterization",
            "```json",
            json.dumps(facts, indent=2, default=str)[:3000],
            "```",
            "",
            "## Schema you may write: section `sdc`",
            "```json",
            json.dumps(describe_section("sdc"), indent=2, default=str),
            "```",
            "",
            "Current values:",
            "```json",
            json.dumps(current, indent=2, default=str),
            "```",
            "",
            "## PDK context",
            "```json",
            json.dumps(pdk_context, indent=2, default=str)[:1500],
            "```",
            "",
            'Respond with the same JSON object format, using failure_class '
            '"sdc" and config_delta {"sdc": {...}}.',
        ]
    )
