"""Locally inspect EXISTING S002 outcome RAW-PRIVATE captures for environment candidates.

Never invokes Dolphin, controller RPC, GitHub, or any publisher.
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
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.environment_state_candidate import audit_environment_snapshots

RAW_NAME = re.compile(r"outcome-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}-RAW-PRIVATE\\.jsonl\\Z")
MAX_BYTES = 8_000_000


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True,
                        help="Existing local outcome-...-RAW-PRIVATE.jsonl capture")
    args = parser.parse_args(argv)
    try:
        path = args.input
        if not RAW_NAME.fullmatch(path.name) or not path.is_file():
            raise ValueError("Unsupported private capture filename")
        size = path.stat().st_size
        if not 0 < size <= MAX_BYTES:
            raise ValueError("Private capture exceeds study bound")
        rows = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if len(rows) >= 100:
                    raise ValueError("Too many snapshots")
                rows.append(json.loads(line))
        report = audit_environment_snapshots(rows)
        stem = "env-candidates-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
        output = path.with_name(stem + uuid.uuid4().hex[:8] + "-summary.json")
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
        print("Local candidate summary saved. No publication or game action.", flush=True)
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        # Never echo a private path or raw bytes via third-party exception messages.
        print("Environment audit stopped: unsupported or inconsistent private capture.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
