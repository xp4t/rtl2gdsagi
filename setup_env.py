#!/usr/bin/env python3
"""One-shot environment setup script for rtl2gdsagi.

Runs on a fresh machine after `git clone`. Does NOT require OpenLane
pre-installed. Installs everything needed:

0. Rust toolchain (required to build libparse, an OpenLane2 dependency)
   — skipped if `cargo` is already on PATH

1. pip install -r requirements.txt  (includes `openlane` Python package)
2. Downloads sky130hd PDK via OpenLane2
3. Verifies tool availability
4. Creates a .env.example file with the API key placeholder

Usage::

    python setup_env.py
    # or with a specific PDK root:
    python setup_env.py --pdk-root ~/mypdks
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"{BOLD}  $ {' '.join(cmd)}{RESET}")
    result = subprocess.run(cmd, **kwargs)
    return result


def ok(msg: str) -> None:
    print(f"{GREEN}  ✔ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}  ⚠ {msg}{RESET}")


def err(msg: str) -> None:
    print(f"{RED}  ✘ {msg}{RESET}")


def step(title: str) -> None:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")


def main() -> int:
    p = argparse.ArgumentParser(description="Setup rtl2gdsagi environment")
    p.add_argument(
        "--pdk-root",
        default=os.path.expanduser("~/OpenLane/pdks"),
        help="Where to install PDKs (default: ~/OpenLane/pdks)",
    )
    p.add_argument(
        "--skip-pdk",
        action="store_true",
        help="Skip PDK download (if already installed)",
    )
    p.add_argument(
        "--pdk",
        default="sky130hd",
        help="PDK to install (default: sky130hd)",
    )
    args = p.parse_args()

    print(f"{BOLD}\nrtl2gdsagi environment setup{RESET}")
    print(f"Python: {sys.version}")
    print(f"Root:   {ROOT}")

    errors: list[str] = []

    # ------------------------------------------------------------------
    # Step 0: Install Rust toolchain (needed for libparse wheel build)
    # ------------------------------------------------------------------
    step("0/5  Checking Rust toolchain (needed for libparse)")
    import shutil
    if shutil.which("cargo"):
        ok("Rust/cargo already on PATH — skipping rustup install")
    else:
        print("  Installing Rust via rustup (this downloads ~200 MB)...")
        result_rust = subprocess.run(
            "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --quiet",
            shell=True,
        )
        if result_rust.returncode == 0:
            # Add cargo to PATH for this process
            cargo_bin = os.path.expanduser("~/.cargo/bin")
            os.environ["PATH"] = cargo_bin + ":" + os.environ.get("PATH", "")
            ok(f"Rust installed. Add to shell profile: export PATH={cargo_bin}:$PATH")
        else:
            warn(
                "Rust install failed. libparse may not build.\n"
                "  Try manually: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            )

    # ------------------------------------------------------------------
    # Step 1: pip install requirements
    # ------------------------------------------------------------------
    step("1/5  Installing Python dependencies")
    req_file = ROOT / "requirements.txt"
    result = run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
    )
    if result.returncode != 0:
        err("pip install failed — check your Python environment")
        errors.append("pip install")
    else:
        ok("All Python dependencies installed")

    # ------------------------------------------------------------------
    # Step 2: Verify OpenLane2 CLI available
    # ------------------------------------------------------------------
    step("2/4  Verifying OpenLane2 CLI")
    result2 = subprocess.run(
        [sys.executable, "-m", "openlane", "--version"],
        capture_output=True, text=True,
    )
    if result2.returncode == 0:
        version_str = (result2.stdout or result2.stderr).strip()
        ok(f"OpenLane2 available: {version_str}")
    else:
        warn("OpenLane2 CLI not yet available — may need new shell or PATH update")
        warn(f"  Try: python -m openlane --version")
        warn(f"  stderr: {result2.stderr[:300]}")

    # ------------------------------------------------------------------
    # Step 3: Download sky130hd PDK
    # ------------------------------------------------------------------
    step("3/4  Setting up PDK")
    pdk_root = Path(args.pdk_root)
    pdk_root.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PDK_ROOT": str(pdk_root)}
    if args.skip_pdk:
        warn("PDK download skipped (--skip-pdk)")
    else:
        print(f"  PDK root: {pdk_root}")
        print(f"  PDK:      {args.pdk}")
        print("  This may take several minutes on first run (downloads ~2 GB)...")
        result3 = run(
            [
                sys.executable, "-m", "openlane",
                "--install-pdk", args.pdk,
                "--pdk-root", str(pdk_root),
            ],
            env=env,
        )
        if result3.returncode == 0:
            ok(f"PDK {args.pdk} installed at {pdk_root}")
        else:
            warn(
                f"PDK install exited with code {result3.returncode}. "
                "This may be OK if PDK is already present."
            )
            expected = pdk_root / args.pdk
            if expected.exists():
                ok(f"PDK directory exists at {expected} — continuing")
            else:
                err(f"PDK directory not found: {expected}")
                errors.append(f"pdk:{args.pdk}")

    # ------------------------------------------------------------------
    # Step 4: Write .env template
    # ------------------------------------------------------------------
    step("4/4  Writing environment template")
    env_example = ROOT / ".env.example"
    pdk_root_abs = pdk_root.resolve()
    env_example.write_text(
        "# Copy this file to .env and fill in your values\n"
        "# Then: source .env  (or use direnv)\n\n"
        "# Required: Claude API key for LLM-assisted decisions\n"
        "export ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXX\n\n"
        "# Optional overrides\n"
        f"export PDK_ROOT={pdk_root_abs}\n"
        "# export OPENLANE_CMD='openlane'   # default: auto-detected\n"
        "# export CLAUDE_MODEL=claude-sonnet-4-5\n"
        "# export STAGE_TIMEOUT_SECONDS=14400   # 4h default\n"
        "# export AUDIT_DIR=runs/audit\n"
    )
    ok(f".env.example written — copy to .env and fill in ANTHROPIC_API_KEY")

    if not os.environ.get("PDK_ROOT"):
        warn(
            f"PDK_ROOT is not currently set in your shell.\n"
            f"  Add to your shell profile: export PDK_ROOT={pdk_root_abs}\n"
            f"  Or: source .env before running the flow"
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{BOLD}{'═'*60}{RESET}")
    if errors:
        err(f"Setup completed with {len(errors)} error(s): {errors}")
        print("  Review the output above and fix issues before running the flow.")
        return 1
    else:
        ok("Setup complete!")
        print(f"""
{BOLD}Next steps:{RESET}

  1. Set your Claude API key:
     export ANTHROPIC_API_KEY=sk-ant-...

  2. Run the demo (RISC-V ALU, stages 1-4):
     python run_flow.py --rtl designs/riscv_alu/rtl/alu.v \\
                        --top riscv_alu \\
                        --config designs/riscv_alu/config.yaml

  3. List completed runs:
     python run_flow.py --list-runs

  4. Resume an interrupted run:
     python run_flow.py --resume <run_id>

  See README.md for full documentation.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
