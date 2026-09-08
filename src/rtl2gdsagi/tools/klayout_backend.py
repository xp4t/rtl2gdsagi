from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..checks import gds as gdsread
from ..checks.tools import ToolRun
from ..stages import Tool
from .invoker import DEFAULT_OPENLANE_IMAGE, ToolInvoker


@dataclass(frozen=True)
class ProbeResult:
    backend: str
    healthy: bool
    run: ToolRun
    output_gds: Path
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"backend": self.backend, "healthy": self.healthy,
                "argv": self.run.argv, "returncode": self.run.returncode,
                "output_gds": str(self.output_gds), "reason": self.reason,
                "output_tail": self.run.tail(2000)}


class KLayoutBackend:
    name = "native"

    def argv(self, base: list[str], *, cwd: Path, run_dir: Path, pdk_root: Path) -> list[str]:
        return list(base)

    def env(self, *, run_dir: Path) -> dict[str, str]:
        return {}


class NativeKLayoutBackend(KLayoutBackend):
    def __init__(self, *, executable: str = "klayout", isolated: bool = False) -> None:
        self.executable, self.isolated = executable, isolated
        self.name = "native_isolated" if isolated else "native"

    def argv(self, base: list[str], **_: Any) -> list[str]:
        rest = list(base[1:])
        if self.isolated and "-nc" not in rest:
            rest.insert(0, "-nc")
        return [self.executable, *rest]

    def env(self, *, run_dir: Path) -> dict[str, str]:
        if not self.isolated:
            return {}
        home = run_dir / "runtime" / "klayout-home"
        config = run_dir / "runtime" / "klayout-xdg-config"
        cache = run_dir / "runtime" / "klayout-xdg-cache"
        for path in (home, config, cache):
            path.mkdir(parents=True, exist_ok=True)
        return {"HOME": str(home), "XDG_CONFIG_HOME": str(config), "XDG_CACHE_HOME": str(cache)}


class ContainerKLayoutBackend(KLayoutBackend):
    name = "container"

    def __init__(self, image: str = DEFAULT_OPENLANE_IMAGE) -> None:
        self.image = image

    def argv(self, base: list[str], *, cwd: Path, run_dir: Path, pdk_root: Path) -> list[str]:
        return ["docker", "run", "--rm", "-u", f"{os.getuid()}:{os.getgid()}",
                "-v", f"{run_dir.resolve()}:{run_dir.resolve()}",
                "-v", f"{pdk_root.resolve()}:{pdk_root.resolve()}:ro",
                "-w", str(cwd.resolve()), "--entrypoint", "klayout", self.image,
                *base[1:]]


class KLayoutRuntimeManager:
    def __init__(self, *, invoker: ToolInvoker, run_dir: Path, pdk_root: Path,
                 image: str = DEFAULT_OPENLANE_IMAGE) -> None:
        self.invoker, self.run_dir, self.pdk_root = invoker, Path(run_dir), Path(pdk_root)
        self.image = image
        self.backend: KLayoutBackend = NativeKLayoutBackend()

    def set_backend(self, name: str) -> None:
        if name == "native":
            self.backend = NativeKLayoutBackend()
        elif name == "native_isolated":
            self.backend = NativeKLayoutBackend(isolated=True)
        elif name == "container":
            self.backend = ContainerKLayoutBackend(self.image)
        else:
            raise ValueError(f"unknown KLayout backend {name}")

    def effective_argv(self, base: list[str], cwd: Path) -> list[str]:
        return self.backend.argv(base, cwd=cwd, run_dir=self.run_dir, pdk_root=self.pdk_root)

    def effective_env(self) -> dict[str, str]:
        return self.backend.env(run_dir=self.run_dir)

    def probe(self, backend: KLayoutBackend) -> ProbeResult:
        root = self.run_dir / "runtime" / "klayout-probes" / backend.name
        root.mkdir(parents=True, exist_ok=True)
        out = root / "health.gds"
        script = root / "health.py"
        script.write_text(
            "import pya\nlayout=pya.Layout()\nlayout.dbu=0.001\n"
            "top=layout.create_cell('RTL2GDSAGI_HEALTH')\n"
            "top.shapes(layout.layer(1,0)).insert(pya.Box(0,0,1000,1000))\n"
            f"layout.write({str(out)!r})\n", encoding="utf-8")
        if out.exists():
            out.unlink()
        base = ["klayout", "-b", "-r", str(script)]
        argv = backend.argv(base, cwd=root, run_dir=self.run_dir, pdk_root=self.pdk_root)
        try:
            run = self.invoker.run(Tool.KLAYOUT, argv, cwd=root, timeout_s=60,
                                   env=backend.env(run_dir=self.run_dir),
                                   log_path=root / "probe.log")
        except TypeError:
            run = self.invoker.run(Tool.KLAYOUT, argv, cwd=root, timeout_s=60,
                                   env=backend.env(run_dir=self.run_dir))
        healthy, reason = False, "probe did not produce a valid GDS"
        if run.returncode == 0 and out.is_file() and out.stat().st_size:
            try:
                info = gdsread.read_gds(out)
                healthy = info.cell("RTL2GDSAGI_HEALTH") is not None and not info.cell("RTL2GDSAGI_HEALTH").is_empty
                reason = "minimal layout was written and parsed" if healthy else reason
            except gdsread.GDSError as exc:
                reason = f"probe GDS is invalid: {exc}"
        elif run.returncode != 0:
            reason = f"health probe exited {run.returncode}"
        result = ProbeResult(backend.name, healthy, run, out, reason)
        (root / "probe.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    def repair_candidates(self) -> list[KLayoutBackend]:
        candidates: list[KLayoutBackend] = [NativeKLayoutBackend(isolated=True)]
        for name in ("klayout_app", "klayout-bin"):
            path = shutil.which(name)
            if path:
                candidates.append(NativeKLayoutBackend(executable=path, isolated=True))
        if shutil.which("docker"):
            candidates.append(ContainerKLayoutBackend(self.image))
        return candidates
