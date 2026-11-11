"""One local-only cohort read of existing S002 outcome RAW-PRIVATE captures.

All raw bytes and absolute runtime addresses stay under Wii-AI-Golf-Data.
No Dolphin, network, controller commands, Git operations or publisher.
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
PRIVATE_DIR = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.environment_cohort import MAX_FILES, summarize_environment_cohort
from wii_ai_golf.audit.environment_state_candidate import audit_environment_snapshots

RAW_NAME = re.compile(r"outcome-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}-RAW-PRIVATE\.jsonl\Z")
MAX_RAW_FILE_BYTES = 8_000_000


def audit_local_directory(path: Path) -> dict:
    """No partial successes: malformed captures invalidate the whole cohort."""
    if path.is_symlink() or not path.is_dir() or path.resolve() != PRIVATE_DIR.resolve():
        raise ValueError("Capture directory must be the canonical private root")
    candidates = sorted(p for p in path.iterdir()
                        if p.name.startswith("outcome-") and p.name.endswith("-RAW-PRIVATE.jsonl"))
    if any(not RAW_NAME.fullmatch(p.name) for p in candidates):
        raise ValueError("Invalid legacy outcome capture name; no silent file filtering")
    files = candidates
    if not 2 <= len(files) <= MAX_FILES:
        raise ValueError("Need 2 to 64 prior private outcome captures")
    reports = []
    for file in files:
        if (file.is_symlink() or not file.is_file()
            or not 0 < file.stat().st_size <= MAX_RAW_FILE_BYTES):
            raise ValueError("Private capture failed file safety")
        rows = []
        with file.open(encoding="utf-8") as stream:
            for line in stream:
                if len(rows) >= 100:
                    raise ValueError("Capture exceeds bounded snapshot count")
                rows.append(json.loads(line))
        reports.append(audit_environment_snapshots(rows))
    return summarize_environment_cohort(reports)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=PRIVATE_DIR,
                        help="Canonical local private captures directory")
    args = parser.parse_args(argv)
    try:
        report = audit_local_directory(args.directory)
        filename = ("env-cohort-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
                    + uuid.uuid4().hex[:8] + "-summary.json")
        with (PRIVATE_DIR / filename).open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        print("Local sanitized cohort summary saved; no upload or game action.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        # Do not leak captured file names, absolute pointers or raw bytes in errors.
        print("Environment cohort stopped: unsupported/inconsistent private captures.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
