"""LOCAL-ONLY, OFFLINE candidate golf pin/start map-vector triage.

Imports canonical S002 source-chain gate from PR #151. No Dolphin, controller,
RPC, file uploads, ROM parsing, or speculative in-game coordinate claims.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.audit.golf_map_transform_candidates import audit_local_pair


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True,
                        help="Approved ignored Wii-AI-Golf-Data folder")
    parser.add_argument("--mem1", type=Path, required=True)
    parser.add_argument("--mem2", type=Path, required=True)
    parser.add_argument("--private-report", type=Path, required=True,
                        help="New -PRIVATE.json report, never upload")
    args = parser.parse_args(argv)
    try:
        safe = audit_local_pair(
            args.mem1, args.mem2, private_root=args.private_root,
            private_output=args.private_report)
    except (OSError, ValueError, TypeError, KeyError):
        print("Offline candidate map-vector audit stopped: wrong source gate, "
              "private bank format, or path; no addresses displayed.", file=sys.stderr)
        return 1
    print(json.dumps(safe, sort_keys=True, indent=2, allow_nan=False))
    print("Private candidate float report written locally; never upload it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
