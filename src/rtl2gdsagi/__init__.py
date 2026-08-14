"""rtl2gdsagi -- agentic RTL-to-GDSII orchestrator.

Each stage owns its own fix loop. There is deliberately no shared cross-stage
error handler: diagnosis is always local to the stage that failed, because the
context needed to repair a Yosys script has nothing in common with what is
needed to repair a routing script or a DRC deck invocation.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .errors import AgentError, ConfigError, Escalated, PDKError, Rtl2GdsError
from .pdk import PDKConfig
from .stages import STAGE_ORDER, STAGES, Gate, StageId, StageSpec, Tool, get_stage

__all__ = [
    "__version__",
    "AgentError",
    "ConfigError",
    "Escalated",
    "PDKConfig",
    "PDKError",
    "Rtl2GdsError",
    "STAGES",
    "STAGE_ORDER",
    "StageId",
    "StageSpec",
    "Gate",
    "Tool",
    "get_stage",
]
