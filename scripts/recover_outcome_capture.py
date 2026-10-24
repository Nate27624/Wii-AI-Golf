"""Offline recover a missing candidates JSON after a completed RAW-PRIVATE capture.

This does NOT launch Dolphin or issue controller inputs. Human observations
come from CLI arguments; the original score screen cannot be reconstructed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
_SRC = str(ROOT / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)
from wii_ai_golf.audit.outcome_recovery import recover_outcome_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True,
                        help="Existing PRIVATE outcome-...-RAW-PRIVATE.jsonl; never upload")
    parser.add_argument("--contact", choices=("yes", "no", "unknown"), required=True)
    parser.add_argument("--green", choices=("yes", "no", "unknown"), required=True)
    parser.add_argument("--distance", default="",
                        help='Exact screen text e.g. "100.0ft"; blank if not shown')
    parser.add_argument("--unit", choices=("ft", "yd", "m", "unknown"), default="unknown",
                        help="Only needed when distance text lacks units")
    parser.add_argument("--out", type=Path,
                        help="New local candidates summary JSON; exclusive creation, no overwrites")
    args = parser.parse_args(argv)
    raw = args.raw.resolve()
    if args.out is None:
        suffix = "-RAW-PRIVATE.jsonl"
        if not raw.name.endswith(suffix):
            parser.error("Unrecognized raw filename; provide --out explicitly")
        out = raw.with_name(raw.name[:-len(suffix)] + "-candidates.json")
    else:
        out = args.out.resolve()
    if out == raw:
        parser.error("Cannot overwrite the original raw file")
    try:
        # Check destination before processing; never delete/replace an old run.
        if out.exists():
            raise FileExistsError(f"Refusing to overwrite existing summary: {out}")
        summary = recover_outcome_summary(raw, contact=args.contact, green=args.green,
                                          distance_text=args.distance, unit=args.unit)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Offline outcome recovery failed: {exc}", file=sys.stderr)
        return 1
    print("Recovered sanitized candidate summary:", out)
    print("RAM fields with persistent changes:",
          summary["candidate_ranking"]["all_phase_stable_change_count"])
    print("Previous swing dispatch details were not saved; memory score remains unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
