#!/usr/bin/env python3
"""Execute distinct bundled designs and retain commands and source identity."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def source_identity() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").rglob("*.py")):
        h.update(str(p.relative_to(ROOT)).encode() + b"\0")
        h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--pdk-root", type=Path, required=True)
    parser.add_argument("--eda-bin", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--designs", nargs="+", default=["register", "mux4to1", "alu8", "counter", "shift_reg"])
    args = parser.parse_args()
    if len(set(args.designs)) != len(args.designs):
        parser.error("designs must be distinct")
    out = args.run_root.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    if args.eda_bin:
        env["PATH"] = str(args.eda_bin.resolve()) + os.pathsep + env.get("PATH", "")
    manifest = {"source_sha256": source_identity(), "started_at": time.time(), "designs": {}, "commands": {}}
    for design in args.designs:
        config = ROOT / "examples" / design / f"{design}.yaml"
        if not config.is_file():
            parser.error(f"missing design config: {config}")
        if (out / design / "run_state.json").exists():
            parser.error(f"refusing to overwrite retained run: {out / design}")
        manifest["commands"][design] = [sys.executable, "-m", "rtl2gdsagi.cli", "run", "--config", str(config), "--pdk-root", str(args.pdk_root.resolve()), "--no-api", "--klayout-backend", "container", "--run-dir", str(out / design)]
    (out / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def execute(design: str) -> tuple[str, dict]:
        print(f"starting {design}", flush=True)
        start = time.time()
        with (out / f"{design}.console.log").open("w") as fh:
            result = subprocess.run(manifest["commands"][design], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
        row = {"exit_code": result.returncode, "elapsed_s": round(time.time() - start, 3), "run_dir": str(out / design)}
        state_path = out / design / "run_state.json"
        if state_path.is_file():
            state = json.loads(state_path.read_text())
            row.update(status=state["status"], run_id=state["run_id"], completed_stages=sum(s["status"] == "ok" for s in state["stages"].values()))
        print(f"finished {design}: {row}", flush=True)
        return design, row

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(execute, d) for d in args.designs]
        for future in as_completed(futures):
            design, row = future.result()
            manifest["designs"][design] = row
            (out / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    manifest.update(ended_at=time.time(), consistent_source=manifest["source_sha256"] == source_identity())
    (out / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0 if manifest["consistent_source"] and all(r["exit_code"] == 0 for r in manifest["designs"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
