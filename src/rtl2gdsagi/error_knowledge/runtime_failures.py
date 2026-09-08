from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..checks.tools import ToolRun


class RuntimeFailureClass(str, Enum):
    DESIGN_DATA_FAILURE = "design_data_failure"
    FLOW_CONFIGURATION_FAILURE = "flow_configuration_failure"
    TOOL_INVOCATION_FAILURE = "tool_invocation_failure"
    TOOL_RUNTIME_FAILURE = "tool_runtime_failure"
    TOOL_INSTALLATION_FAILURE = "tool_installation_failure"
    TOOL_VERSION_INCOMPATIBILITY = "tool_version_incompatibility"
    HOST_ENVIRONMENT_FAILURE = "host_environment_failure"


SALT = re.compile(r"lay::SaltDownloadManager::execute|SaltDownloadManager", re.I)
VERSION = re.compile(r"(?:Program Version:\s*|KLayout\s+)(KLayout\s+)?([^\n\r]+)", re.I)


@dataclass(frozen=True)
class RuntimeFailure:
    failure_class: RuntimeFailureClass
    executable: str
    version: str
    argv: tuple[str, ...]
    exit_status: int
    signal: int | None
    stack_signature: str | None
    output_tail: str
    environment_fingerprint: str
    health_probe_reproduced: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def classify_runtime_failure(run: ToolRun) -> RuntimeFailure | None:
    rc = int(run.returncode)
    signal = (-rc if rc < 0 else (rc - 128 if rc >= 128 else (11 if rc == 11 else None)))
    crashed = signal in {6, 7, 8, 9, 11} or run.timed_out
    if not crashed and rc not in {126, 127}:
        return None
    if rc == 127:
        cls = RuntimeFailureClass.TOOL_INSTALLATION_FAILURE
    elif run.timed_out:
        cls = RuntimeFailureClass.HOST_ENVIRONMENT_FAILURE
    else:
        cls = RuntimeFailureClass.TOOL_RUNTIME_FAILURE
    sig = "SaltDownloadManager" if SALT.search(run.combined) else (
        f"signal:{signal}" if signal else None)
    executable = run.argv[0] if run.argv else ""
    version_match = VERSION.search(run.combined)
    version = ("KLayout " + version_match.group(2).strip()
               if version_match else "unknown")
    env = f"{platform.system()}|{platform.release()}|{platform.machine()}|{os.getuid()}"
    return RuntimeFailure(
        failure_class=cls, executable=shutil.which(executable) or executable,
        version=version,
        argv=tuple(run.argv), exit_status=rc, signal=signal,
        stack_signature=sig, output_tail=run.tail(4000),
        environment_fingerprint=hashlib.sha256(env.encode()).hexdigest(),
    )
