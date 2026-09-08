from __future__ import annotations

from pathlib import Path

from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.error_knowledge.runtime_failures import (
    RuntimeFailureClass, classify_runtime_failure,
)
from rtl2gdsagi.tools.klayout_backend import (
    ContainerKLayoutBackend, KLayoutRuntimeManager, NativeKLayoutBackend,
)
from rtl2gdsagi.tools.invoker import DEFAULT_OPENLANE_IMAGE
from rtl2gdsagi.stages import Tool
from conftest import make_gds


def test_klayout_sigsegv_is_runtime_not_design_data():
    run = ToolRun(["klayout", "-b"], 139,
                  "Program Version: KLayout 0.26.2\nlay::SaltDownloadManager::execute(...)\n", "")
    failure = classify_runtime_failure(run)
    assert failure.failure_class is RuntimeFailureClass.TOOL_RUNTIME_FAILURE
    assert failure.signal == 11
    assert failure.stack_signature == "SaltDownloadManager"
    assert failure.version == "KLayout 0.26.2"


def test_exit_11_is_also_treated_as_sigsegv_for_observed_host_shape():
    failure = classify_runtime_failure(ToolRun(["klayout"], 11, "SaltDownloadManager", ""))
    assert failure.signal == 11 and failure.stack_signature == "SaltDownloadManager"


class ProbeInvoker:
    def available(self, _tool):
        return True

    def run(self, tool, argv, *, cwd, timeout_s=60, env=None, log_path=None):
        assert tool is Tool.KLAYOUT
        if argv[0] == "klayout" and "-nc" not in argv:
            return ToolRun(argv, 139, "SaltDownloadManager", "")
        script = Path(argv[-1])
        text = script.read_text()
        output = Path(text.split("layout.write(", 1)[1].split(")", 1)[0].strip("'\""))
        make_gds(output, "RTL2GDSAGI_HEALTH")
        return ToolRun(argv, 0, "probe ok", "")


def test_unhealthy_native_backend_falls_back_to_health_probed_isolation(tmp_path):
    pdk = tmp_path / "pdk"; pdk.mkdir()
    manager = KLayoutRuntimeManager(invoker=ProbeInvoker(), run_dir=tmp_path / "run",
                                    pdk_root=pdk)
    native = manager.probe(NativeKLayoutBackend())
    isolated = manager.probe(NativeKLayoutBackend(isolated=True))
    assert not native.healthy
    assert isolated.healthy
    manager.set_backend("native_isolated")
    argv = manager.effective_argv(["klayout", "-b", "-r", "gdsout.py"], tmp_path)
    assert argv[:3] == ["klayout", "-nc", "-b"]


def test_container_backend_preserves_run_and_pdk_mounts(tmp_path):
    run, pdk, cwd = tmp_path / "run", tmp_path / "pdk", tmp_path / "run/stage"
    for path in (run, pdk, cwd): path.mkdir(parents=True, exist_ok=True)
    backend = ContainerKLayoutBackend(DEFAULT_OPENLANE_IMAGE)
    argv = backend.argv(["klayout", "-b", "-r", str(cwd / "x.py")], cwd=cwd,
                        run_dir=run, pdk_root=pdk)
    assert argv[0:3] == ["docker", "run", "--rm"]
    assert f"{run.resolve()}:{run.resolve()}" in argv
    assert f"{pdk.resolve()}:{pdk.resolve()}:ro" in argv
    assert argv[-3:] == ["-b", "-r", str(cwd / "x.py")]
