"""Private offline phase/cochange cohort of existing source-gated S002 captures.

Never launches Dolphin, writes controller input, or publishes private RAM.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.environment_phase_joint import (
    MAX_CAPTURES, summarize_phase_joint_cohort)

NAME = re.compile(r"outcome-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}-RAW-PRIVATE\.jsonl\Z")
MAX_BYTES = 8_000_000
MAX_ROWS = 100


def audit_directory(directory: Path) -> dict:
    if (directory.is_symlink() or not directory.is_dir()
            or directory.resolve() != CAPTURES.resolve()):
        raise ValueError("Not the canonical private capture directory")
    candidate_files = sorted(
        p for p in directory.iterdir()
        if p.name.startswith("outcome-") and p.name.endswith("-RAW-PRIVATE.jsonl"))
    if any(not NAME.fullmatch(p.name) for p in candidate_files):
        raise ValueError("Unrecognized capture filename")
    if not 2 <= len(candidate_files) <= MAX_CAPTURES:
        raise ValueError("Expected 2..64 existing captures")
    captures = []
    for path in candidate_files:
        if (path.is_symlink() or not path.is_file()
                or not 0 < path.stat().st_size <= MAX_BYTES):
            raise ValueError("Capture file failed private format gate")
        rows = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if len(rows) >= MAX_ROWS:
                    raise ValueError("Too many capture snapshots")
                rows.append(json.loads(line))
        captures.append(rows)
    return summarize_phase_joint_cohort(captures)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, default=CAPTURES,
                   help="Canonical ignored private capture directory")
    args = p.parse_args(argv)
    try:
        report = audit_directory(args.directory)
        output = CAPTURES / (
            "env-joint-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            + uuid.uuid4().hex[:8] + "-summary.json")
        with output.open("x", encoding="utf-8") as dest:
            json.dump(report, dest, indent=2, sort_keys=True, allow_nan=False)
            dest.write("\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        print("Local-only sanitized cochange summary saved, no uploads.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        # Do not echo private paths, in-game addresses or raw pointer values.
        print("Offline phase-cochange study stopped: unsupported or inconsistent private data.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
