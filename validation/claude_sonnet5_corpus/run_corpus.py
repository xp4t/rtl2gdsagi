#!/usr/bin/env python3
"""Portable driver for the isolated rtl2gdsagi validation corpus."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITE = Path(__file__).resolve().parent
CLI = ROOT / ".venv" / "bin" / "rtl2gdsagi"
YOSYS = ROOT / ".venv" / "bin" / "yosys"


def cases(selected: list[str]) -> list[Path]:
    found = sorted(p for p in SUITE.glob("[0-9][0-9]_*") if p.is_dir())
    if selected:
        wanted = set(selected)
        found = [p for p in found if p.name in wanted]
    return found


def run(argv: list[str], *, cwd: Path = ROOT) -> None:
    print("+", " ".join(argv), flush=True)
    subprocess.run(argv, cwd=cwd, check=True)


def preflight(case_dirs: list[Path]) -> None:
    build = SUITE / "build"
    build.mkdir(exist_ok=True)
    for case in case_dirs:
        top = next(line.split(":", 1)[1].strip() for line in
                   (case / "run.yaml").read_text().splitlines() if line.startswith("top:"))
        rtl = [str(p) for p in sorted((case / "golden").glob("*.v"))]
        tb = next((case / "tb").glob("*_tb.v"))
        run(["verilator", "--lint-only", "--language", "1800-2017", "-Wall",
             "--top-module", top, *rtl])
        run([str(YOSYS), "-q", "-p",
             f"read_verilog -sv {' '.join(rtl)}; hierarchy -check -top {top}; "
             f"synth -top {top}; check"])
        image = build / f"{case.name}.vvp"
        run(["iverilog", "-g2012", "-o", str(image), *rtl, str(tb)])
        run(["vvp", str(image)])


def live(case_dirs: list[Path], pdk_root: str | None, dry_run: bool) -> None:
    for case in case_dirs:
        argv = [str(CLI), "run", "--config", str(case / "run.yaml"),
                "--model", "claude-sonnet-5", "--repair-policy", "auto"]
        if pdk_root:
            argv += ["--pdk-root", pdk_root]
        if dry_run:
            argv += ["--dry-run", "--no-api"]
        run(argv)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "dry-run", "live"))
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--pdk-root")
    args = parser.parse_args()
    selected = cases(args.case)
    if not selected:
        parser.error("no matching cases")
    if args.mode == "preflight":
        preflight(selected)
    else:
        live(selected, args.pdk_root, args.mode == "dry-run")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)

