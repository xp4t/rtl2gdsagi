#!/usr/bin/env python3
"""Regenerate paper metrics, tables, and timing figure from verified live runs."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    script = Path(__file__).resolve().parent.parent / "scripts/extract_signoff_metrics.py"
    runpy.run_path(str(script), run_name="__main__")
