"""Exception hierarchy.

Stage-local failures derive from StageError. The runner catches those and feeds
them into the owning stage's fix loop. Anything else propagates and aborts the
run, because it means the orchestrator itself is misconfigured.
"""

from __future__ import annotations


class Rtl2GdsError(Exception):
    """Base for every error this package raises."""


class ConfigError(Rtl2GdsError):
    """Run configuration or CLI arguments are unusable. Not stage-local."""


class PDKError(Rtl2GdsError):
    """PDK root missing, or a required PDK file is absent. Not stage-local."""


class Escalated(Rtl2GdsError):
    """The flow stopped and is asking for a human. Not a crash.

    Raised for failure classes the taxonomy marks non-autonomous (a library
    integrity problem, an LEC mismatch, a functional RTL bug) and when a stage
    exhausts its budget with no deeper rollback target.
    """


class AgentError(Rtl2GdsError):
    """The Claude API call failed, or returned something unusable."""
