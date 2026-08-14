"""Subprocess invocation, with a mock implementation for tests.

The orchestrator only ever talks to a ToolInvoker, so the entire state machine
can be exercised without a single real EDA run -- which is how the retry,
rollback and escalation logic gets tested deterministically.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from ..checks.tools import ToolRun
from ..stages import Tool

#: OpenLane container used for OpenROAD stages when no native binary exists.
DEFAULT_OPENLANE_IMAGE = (
    "ghcr.io/the-openroad-project/openlane:"
    "ff5509f65b17bfa4068d5336495ab1718987ff69"
)


class ToolInvoker(Protocol):
    def run(
        self,
        tool: Tool,
        argv: list[str],
        *,
        cwd: Path,
        timeout_s: int = 3600,
        env: dict[str, str] | None = None,
        log_path: Path | None = None,
    ) -> ToolRun: ...

    def available(self, tool: Tool) -> bool: ...


@dataclass
class RealInvoker:
    """Runs the actual binaries.

    OpenROAD is reached through the OpenLane container because no native
    openroad binary is installed on this host; the PDK and run directory are
    bind-mounted so paths inside the rendered scripts stay valid.
    """

    openlane_image: str = DEFAULT_OPENLANE_IMAGE
    pdk_root: Path | None = None
    #: Whole run directory, mounted so a stage can read upstream stages'
    #: artifacts. Mounting only the stage cwd makes the netlist from an
    #: earlier stage invisible inside the container.
    run_dir: Path | None = None
    use_docker_for_openroad: bool = True
    extra_mounts: tuple[tuple[Path, Path], ...] = ()

    _BINARY = {
        Tool.VERILATOR: "verilator",
        Tool.IVERILOG: "iverilog",
        Tool.YOSYS: "yosys",
        Tool.EQY: "eqy",
        Tool.OPENSTA: "sta",
        Tool.KLAYOUT: "klayout",
        Tool.OPENROAD: "openroad",
    }

    @staticmethod
    def _search_path() -> str:
        """PATH with this interpreter's bin directory in front.

        Tools installed alongside rtl2gdsagi in a virtualenv (sby, z3) must be
        findable even when the venv was never activated -- and they are looked
        up by *other* tools, not by us: eqy spawns sby, which spawns the solver.
        Without this, `.venv/bin/rtl2gdsagi` works but its LEC stage cannot find
        its own solver.
        """
        own_bin = str(Path(sys.executable).parent)
        current = os.environ.get("PATH", "")
        parts = current.split(os.pathsep) if current else []
        if own_bin not in parts:
            parts.insert(0, own_bin)
        return os.pathsep.join(parts)

    def available(self, tool: Tool) -> bool:
        if tool is Tool.NONE:
            return True
        path = self._search_path()
        if tool is Tool.OPENROAD:
            if shutil.which("openroad", path=path):
                return True
            return self.use_docker_for_openroad and shutil.which("docker") is not None
        return shutil.which(self._BINARY[tool], path=path) is not None

    def run(
        self,
        tool: Tool,
        argv: list[str],
        *,
        cwd: Path,
        timeout_s: int = 3600,
        env: dict[str, str] | None = None,
        log_path: Path | None = None,
    ) -> ToolRun:
        cwd = Path(cwd)
        cwd.mkdir(parents=True, exist_ok=True)
        full_env = {**os.environ, "PATH": self._search_path(), **(env or {})}

        if tool is Tool.OPENROAD and not shutil.which("openroad"):
            argv = self._dockerize(argv, cwd)

        started = time.monotonic()
        # Stream to a file rather than buffering in memory: detailed routing can
        # run for tens of minutes, and capture_output means nothing is visible
        # until it exits. With a file, `tail -f` works while the stage runs.
        sink = log_path or (cwd / "tool.live.log")
        try:
            with open(sink, "w", encoding="utf-8") as fh:
                proc = subprocess.run(
                    argv,
                    cwd=str(cwd),
                    env=full_env,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout_s,
                    check=False,
                )
            text = Path(sink).read_text(encoding="utf-8", errors="replace")
            return ToolRun(
                argv=argv,
                returncode=proc.returncode,
                stdout=text,
                stderr="",
                duration_s=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired:
            partial = ""
            if Path(sink).is_file():
                partial = Path(sink).read_text(encoding="utf-8", errors="replace")
            return ToolRun(
                argv=argv, returncode=124, stdout=partial, stderr="",
                duration_s=time.monotonic() - started, timed_out=True,
            )
        except FileNotFoundError as exc:
            return ToolRun(
                argv=argv, returncode=127, stdout="",
                stderr=f"tool not found: {exc}", duration_s=time.monotonic() - started,
            )

    def _dockerize(self, argv: list[str], cwd: Path) -> list[str]:
        base = Path(self.run_dir).resolve() if self.run_dir else cwd.resolve()
        mounts: list[str] = ["-v", f"{base}:{base}"]
        if not str(cwd.resolve()).startswith(str(base)):
            mounts += ["-v", f"{cwd.resolve()}:{cwd.resolve()}"]
        if self.pdk_root is not None:
            p = Path(self.pdk_root).resolve()
            mounts += ["-v", f"{p}:{p}:ro"]
        for src, dst in self.extra_mounts:
            mounts += ["-v", f"{Path(src).resolve()}:{dst}"]
        return [
            "docker", "run", "--rm",
            "-u", f"{os.getuid()}:{os.getgid()}",
            *mounts,
            "-w", str(cwd.resolve()),
            "--entrypoint", "openroad",
            self.openlane_image,
            *argv[1:],
        ]


Responder = Callable[[Tool, list[str], Path], ToolRun]


@dataclass
class MockInvoker:
    """Scripted invoker for tests.

    ``responses`` maps a tool to a queue of ToolRun results, or to a callable
    for dynamic behaviour (e.g. fail twice, then succeed).
    """

    responses: dict[Tool, list[ToolRun] | Responder] = field(default_factory=dict)
    default: ToolRun | None = None
    calls: list[tuple[Tool, list[str]]] = field(default_factory=list)
    #: Files each invocation should create, so result_check has something to read.
    side_effects: dict[Tool, Callable[[Path], None]] = field(default_factory=dict)

    def available(self, tool: Tool) -> bool:
        return True

    def run(
        self,
        tool: Tool,
        argv: list[str],
        *,
        cwd: Path,
        timeout_s: int = 3600,
        env: dict[str, str] | None = None,
        log_path: Path | None = None,
    ) -> ToolRun:
        self.calls.append((tool, list(argv)))
        if (fx := self.side_effects.get(tool)) is not None:
            fx(Path(cwd))

        spec = self.responses.get(tool)
        if callable(spec):
            return spec(tool, argv, Path(cwd))
        if isinstance(spec, list) and spec:
            return spec.pop(0)
        if self.default is not None:
            return self.default
        return ToolRun(argv=argv, returncode=0, stdout="", stderr="")

    def call_count(self, tool: Tool | None = None) -> int:
        if tool is None:
            return len(self.calls)
        return sum(1 for t, _ in self.calls if t is tool)
