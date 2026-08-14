"""Claude client.

Two hard boundaries hold here:

* The model's response is parsed into a :class:`~rtl2gdsagi.taxonomy.Diagnosis`
  containing a **schema-bounded IR delta**. It never returns TCL, and there is
  no code path from a model response to a Verdict.
* The API key is read from ``ANTHROPIC_API_KEY`` at call time and never stored
  on a config object, never logged, and never written to the run directory.

Every call is recorded to the run log with token counts, and the full prompt and
response are written to per-attempt files under the stage directory so a
diagnosis can always be audited after the fact (review 14.2).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..errors import AgentError
from ..ir import SCHEMA, SchemaViolation
from ..stages import StageId
from ..taxonomy import Diagnosis, FailureClass

DEFAULT_MODEL = "claude-opus-4-8"
API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "RTL2GDSAGI_MODEL"

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass(frozen=True)
class CallAudit:
    """Immutable record of what the model was actually shown and returned.

    The benchmark previously recorded the literal string
    `"<prompt recorded by agent>"`, which is not research evidence: a reviewer
    could not establish what the model saw. These hashes are computed at call
    time, before any remediation outcome is known, so they cannot be
    retrofitted to a result.

    `provider` and `model` identify the endpoint. No credential is recorded --
    the key is read from the environment at call time and never stored.
    """

    provider: str = ""
    model: str = ""
    system_prompt_sha256: str = ""
    user_prompt_sha256: str = ""
    evidence_payload_sha256: str = ""
    response_sha256: str = ""
    #: Kept for local research review; never contains a credential.
    system_prompt: str = ""
    user_prompt: str = ""
    response_text: str = ""
    synthetic_transport: bool = False

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        d = {
            "provider": self.provider,
            "model": self.model,
            "system_prompt_sha256": self.system_prompt_sha256,
            "user_prompt_sha256": self.user_prompt_sha256,
            "evidence_payload_sha256": self.evidence_payload_sha256,
            "response_sha256": self.response_sha256,
            "synthetic_transport": self.synthetic_transport,
        }
        if include_text:
            d["system_prompt"] = self.system_prompt
            d["user_prompt"] = self.user_prompt
            d["response_text"] = self.response_text
        return d


def _sha(text: str) -> str:
    import hashlib

    return hashlib.sha256((text or "").encode()).hexdigest()


@dataclass
class AgentResponse:
    diagnosis: Diagnosis
    raw: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    #: Populated by agents that actually call a model.
    audit: "CallAudit | None" = None


class Agent(Protocol):
    def diagnose(self, request: "DiagnosisRequest") -> AgentResponse: ...


@dataclass
class DiagnosisRequest:
    """Everything the model is allowed to see. All of it is already-computed."""

    stage: StageId
    failure_class_hint: FailureClass | None
    summary: str
    evidence: str
    metrics: dict[str, Any]
    ir_section: str | None
    current_config: dict[str, Any]
    pdk_context: dict[str, Any]
    attempt: int
    retry_limit: int
    #: Fingerprints already tried and failed, so it does not repeat itself.
    tried_configs: list[dict[str, Any]] = field(default_factory=list)
    #: Facts from characterization plus prior-stage metrics, for delta analysis.
    history: list[dict[str, Any]] = field(default_factory=list)
    #: The exact write surface this failure class authorises, section -> field
    #: -> schema. Built by `safety.authorized_action_space` -- the same data the
    #: validator enforces, so the prompt cannot advertise a field that would be
    #: rejected or withhold one that would be accepted.
    action_space: dict[str, dict[str, Any]] = field(default_factory=dict)


def resolve_model(explicit: str | None = None) -> str:
    return explicit or os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def api_key_present() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


class ClaudeAgent:
    """Real Anthropic-backed agent."""

    def __init__(
        self,
        model: str | None = None,
        *,
        max_tokens: int = 2048,
        timeout_s: float = 120.0,
    ) -> None:
        self.model = resolve_model(model)
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        key = os.environ.get(API_KEY_ENV)
        if not key:
            raise AgentError(
                f"{API_KEY_ENV} is not set. The orchestrator reads the key from the "
                "environment at call time and never stores it."
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise AgentError("the 'anthropic' package is not installed") from exc
        self._client = anthropic.Anthropic(api_key=key, timeout=self.timeout_s)
        return self._client

    def diagnose(self, request: DiagnosisRequest) -> AgentResponse:
        from .prompts import build_diagnosis_prompt, SYSTEM_PROMPT

        client = self._ensure_client()
        user = build_diagnosis_prompt(request)
        try:
            msg = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # network, auth, rate limit
            raise AgentError(f"Claude API call failed: {exc}") from exc

        text = "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )
        diag = parse_diagnosis(text, request)
        usage = getattr(msg, "usage", None)
        return AgentResponse(
            diagnosis=diag,
            raw=text,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            model=self.model,
            audit=CallAudit(
                provider="anthropic",
                model=self.model,
                system_prompt_sha256=_sha(SYSTEM_PROMPT),
                user_prompt_sha256=_sha(user),
                evidence_payload_sha256=_sha(request.evidence),
                response_sha256=_sha(text),
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user,
                response_text=text,
                synthetic_transport=getattr(self, "synthetic_transport", False),
            ),
        )


def parse_diagnosis(text: str, request: DiagnosisRequest) -> Diagnosis:
    """Parse and validate a model response into a Diagnosis.

    Anything the schema rejects is an AgentError, not a silently-dropped field:
    a proposal that cannot be represented must fail loudly so the orchestrator
    can retry or escalate rather than apply a half-understood change.
    """
    blob = _extract_json(text)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise AgentError(f"model response was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AgentError("model response JSON must be an object")

    raw_class = str(data.get("failure_class", "")).strip()
    try:
        failure = FailureClass(raw_class)
    except ValueError:
        raise AgentError(
            f"model returned unknown failure_class {raw_class!r}; expected one of: "
            + ", ".join(f.value for f in FailureClass)
        ) from None

    stage_raw = data.get("implicated_stage")
    implicated: StageId | None = None
    if stage_raw:
        try:
            implicated = StageId(str(stage_raw))
        except ValueError:
            raise AgentError(f"model returned unknown stage {stage_raw!r}") from None

    delta = data.get("config_delta") or {}
    if not isinstance(delta, dict):
        raise AgentError("config_delta must be an object mapping section -> fields")
    for section, vals in delta.items():
        if section not in SCHEMA:
            raise SchemaViolation(
                f"config_delta names unknown section {section!r}; the agent may only "
                "configure: " + ", ".join(sorted(SCHEMA))
            )
        if not isinstance(vals, dict):
            raise SchemaViolation(f"config_delta.{section} must be an object")

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        raise AgentError("confidence must be a number in [0, 1]") from None

    return Diagnosis(
        failure=failure,
        evidence=str(data.get("evidence", request.summary))[:4000],
        implicated_stage=implicated,
        confidence=confidence,
        reasoning=str(data.get("reasoning", ""))[:4000],
        config_delta=delta,
        escalated=bool(data.get("escalate", False)),
    )


def _extract_json(text: str) -> str:
    m = _JSON_BLOCK.search(text)
    if m:
        return m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise AgentError(f"no JSON object found in model response: {text[:300]!r}")


@dataclass
class ScriptedAgent:
    """Deterministic agent for tests and for --no-api runs."""

    diagnoses: list[Diagnosis] = field(default_factory=list)
    calls: list[DiagnosisRequest] = field(default_factory=list)
    #: Used when the queue is empty: propose nothing, low confidence.
    fallback: Diagnosis | None = None

    def diagnose(self, request: DiagnosisRequest) -> AgentResponse:
        self.calls.append(request)
        if self.diagnoses:
            diag = self.diagnoses.pop(0)
        elif self.fallback is not None:
            diag = self.fallback
        else:
            diag = Diagnosis(
                failure=request.failure_class_hint or FailureClass.TOOL_RUNTIME,
                evidence=request.evidence[:500],
                implicated_stage=request.stage,
                confidence=0.0,
                reasoning="scripted agent: no proposal",
            )
        return AgentResponse(diagnosis=diag, raw="<scripted>", model="scripted")


def write_audit(
    stage_dir: Path, attempt: int, *, prompt: str, response: str, meta: dict[str, Any]
) -> Path:
    """Persist a full API exchange so any diagnosis can be audited later."""
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"attempt_{attempt:02d}_api.json"
    path.write_text(
        json.dumps(
            {"meta": meta, "prompt": prompt, "response": response},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return path
