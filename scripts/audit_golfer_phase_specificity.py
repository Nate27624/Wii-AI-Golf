"""Offline S002 candidate-golfer control specificity: private input, typed public output.

Use on a locally retained golfer-*-RAW-PRIVATE.jsonl capture from PR #129.
Never put RAW-PRIVATE in Git. Automatic upload is attempted ONLY when the
canonical S000 public_observation kind is reviewed and installed.
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
from wii_ai_golf.audit.golfer_phase_specificity import analyze

CAPTURES = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
NAME = re.compile(r"golfer-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}-RAW-PRIVATE\.jsonl\Z")
MAX_RAW_BYTES = 4_000_000


def load_private(path: Path):
    if not path.is_file() or not NAME.fullmatch(path.name):
        raise ValueError("Expected local S002 golfer RAW-PRIVATE JSONL filename")
    if path.stat().st_size > MAX_RAW_BYTES:
        raise ValueError("Private input exceeds bounded study limit")
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if len(rows) >= 60:
                raise ValueError("Too many private snapshots")
            rows.append(json.loads(line))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path,
                        help="Existing S002 golfer-*-RAW-PRIVATE.jsonl (kept local)")
    parser.add_argument("--no-upload", action="store_true",
                        help="Keep even the sanitized report local")
    args = parser.parse_args(argv)
    try:
        rows = load_private(args.input)
        run_id = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
                  + uuid.uuid4().hex[:8])
        report = analyze(rows, run_id=run_id)
        CAPTURES.mkdir(parents=True, exist_ok=True)
        output = CAPTURES / ("golfer-controls-" + run_id + "-summary.json")
        with output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
        print("Local sanitized summary:", output, flush=True)
        if not args.no_upload:
            try:
                # No fallback uploader; fail closed if S000 has not yet
                # explicitly approved this observation kind.
                from wii_ai_golf.shared.public_observation import public_observation
                checked = public_observation(report)
                from research_cli import publish_summary
                print("GitHub sanitized observation:", publish_summary(checked), flush=True)
            except (ImportError, RuntimeError, OSError, ValueError) as exc:
                print("Auto-upload NOT approved or failed; local report retained. "
                      "S000 typed schema integration needed: " + str(exc),
                      file=sys.stderr)
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("Golfer control audit stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
