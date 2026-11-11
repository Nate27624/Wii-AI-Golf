"""Offline-only interpretation of an ALREADY CAPTURED private S002 golfer audit.

NEVER starts Dolphin, sends inputs, changes RAM or uploads results.
Do not share the -RAW-PRIVATE.jsonl; the output is a local sanitized
temporal pattern classification pending S000 privacy approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.modeling.golfer_temporal_private import analyze_files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True,
                    help="Existing local golfer-*-RAW-PRIVATE.jsonl")
    ap.add_argument("--summary", type=Path, required=True,
                    help="Matching S002 golfer-*-summary.json")
    ap.add_argument("--output", type=Path,
                    help="New local sanitized report, never overwrite")
    a = ap.parse_args(argv)
    name = a.input.name
    if not name.endswith("-RAW-PRIVATE.jsonl"):
        ap.error("Expected S002 private golf capture name")
    output = a.output or a.input.with_name(
        name[:-len("-RAW-PRIVATE.jsonl")] + "-temporal-summary.json")
    try:
        result = analyze_files(a.input, a.summary, output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("S003 temporal analysis FAILED CLOSED: "
              + type(exc).__name__ + "; inspect local input/schema",
              file=sys.stderr)
        return 1
    print("Local sanitized temporal report saved; no GitHub upload.")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
