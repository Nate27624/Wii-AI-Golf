"""Offline compare two or more private-or-sanitized outcome-...-candidates.json files.

Run after the full fresh-boot capture sessions have completed; no live Dolphin.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

from wii_ai_golf.audit.outcome_compare import compare_outcome_runs

MAX_FILE_BYTES = 8 * 1024 * 1024


def read_summary(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"summary must exist and be at most {MAX_FILE_BYTES} bytes")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("expected JSON object")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, type=Path,
                        help="at least two outcome-...-candidates.json summaries")
    parser.add_argument("--out", type=Path, help="exclusive-create offline comparison JSON output")
    args = parser.parse_args(argv)
    if len(args.input) < 2 or len(args.input) > 25:
        parser.error("--input requires 2..25 files")
    paths = [x.resolve() for x in args.input]
    if len(set(paths)) < len(paths):
        parser.error("same report was supplied more than once")
    if args.out and args.out.resolve() in paths:
        parser.error("output must not be any input file")
    try:
        result = compare_outcome_runs([read_summary(x) for x in args.input])
        data = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(data)
        print(data, end="")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Outcome comparison failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
