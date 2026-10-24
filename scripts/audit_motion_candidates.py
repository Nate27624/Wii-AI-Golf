"""Offline audit of S002 sanitized golf motion-candidate reports (NO Dolphin)."""
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

from wii_ai_golf.audit.motion_candidates import audit_motion_report  # noqa: E402

MAX_INPUT_BYTES = 8 * 1024 * 1024


def read_report(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"input must be a JSON file <= {MAX_INPUT_BYTES} bytes")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("report must be a JSON object")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True,
                        help="S002 sanitized motion-discovery summary JSON")
    parser.add_argument("--baseline", type=Path,
                        help="optional earlier/idle summary for a bounded subset comparison")
    parser.add_argument("--out", type=Path,
                        help="optional new LOCAL JSON output; refuses overwrite")
    args = parser.parse_args(argv)
    if args.out is not None and args.out.resolve() in {
        args.input.resolve(), args.baseline.resolve() if args.baseline else None
    }:
        parser.error("--out cannot overwrite an input or baseline")
    try:
        result = audit_motion_report(read_report(args.input),
                                     read_report(args.baseline) if args.baseline else None)
        printed = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(printed)
        print(printed, end="")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"Motion candidate audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
