#!/usr/bin/env python3
"""Generate rtl2gdsagi's offline OpenROAD message catalog.

The parser follows OpenROAD's ``etc/find_messages.py`` logger-call grammar.
It deliberately reads source, rather than scraping rendered documentation, so
severity, source location and the canonical format string remain available.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

CALL = re.compile(
    r"(?:->|\.)(?P<severity>info|warn|fileWarn|error|fileError|critical)\s*"
    r"\(\s*(?:utl::)?(?P<tool>[A-Z]{3})\s*,\s*(?P<code>\d+)\s*,\s*"
    r'(?P<message>"(?:[^"\\]|\\.)*"(?:\s*"(?:[^"\\]|\\.)*")*)',
    re.MULTILINE,
)
TCL_CALL = re.compile(
    r'(?P<severity>info|warn|error|critical)\s+(?P<tool>[A-Z]{3}|"[A-Z]{3}")\s+'
    r'(?P<code>\d+)\s+(?P<message>"(?:[^"\\]|\\.)*")', re.MULTILINE,
)
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".yy", ".ll", ".i", ".tcl"}


def _message(raw: str) -> str:
    # Join adjacent C++ string literals without confusing an escaped quote
    # (``\"{}\"``) for the end of a literal.
    pieces = re.findall(r'"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    return "".join(pieces).replace('\\"', '"').replace("\\n", "\n")


def scan(root: Path) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rx = TCL_CALL if path.suffix == ".tcl" else CALL
        for match in rx.finditer(text):
            tool = match.group("tool").strip('"')
            code = int(match.group("code"))
            canonical_id = f"{tool}-{code:04d}"
            severity = match.group("severity").lower()
            severity = {"filewarn": "WARN", "warn": "WARN", "fileerror": "ERROR",
                        "error": "ERROR", "critical": "CRITICAL", "info": "INFO"}[severity]
            # Runtime intelligence is intentionally a failure catalog.  INFO
            # IDs are not gates and upstream currently reuses a few of them.
            if severity == "INFO":
                continue
            rel = path.relative_to(root.parent).as_posix()
            line = text.count("\n", 0, match.start()) + 1
            doc = root / tool.lower() / "doc" / "messages" / f"{code}.md"
            record = {
                "id": canonical_id, "tool": tool, "code": code,
                "severity": severity, "message": _message(match.group("message")),
                "source_file": rel, "source_line": line,
                "documentation": doc.read_text(encoding="utf-8").strip() if doc.is_file() else "",
            }
            if canonical_id in found:
                old = found[canonical_id]
                if any(old[k] != record[k] for k in ("severity", "message", "source_file", "source_line")):
                    raise SystemExit(f"duplicate OpenROAD ID {canonical_id}: {old} / {record}")
            found[canonical_id] = record
    return [found[key] for key in sorted(found)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True,
                        help="OpenROAD checkout root (contains src/)")
    parser.add_argument("--output", type=Path,
                        default=Path("src/rtl2gdsagi/resources/openroad_messages.json"))
    args = parser.parse_args()
    source = args.source.resolve()
    revision = "unknown"
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        pass
    messages = scan(source / "src")
    payload = {
        "schema_version": 1,
        "upstream": "https://github.com/The-OpenROAD-Project/OpenROAD",
        "revision": revision,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "generator": "scripts/update_openroad_messages.py",
        "messages": messages,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts = {s: sum(m["severity"] == s for m in messages) for s in ("ERROR", "WARN", "CRITICAL", "INFO")}
    print(f"wrote {len(messages)} messages to {args.output}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
