"""Offline/private-only source-verified golf object audit of paired MEM1+MEM2.

This runs NO Dolphin, controller, bridge, network or GitHub publication.
No raw words or pointers are printed. Both user-owned dumps stay local.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.golf_cross_bank_state import audit_local_pair


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", required=True, type=Path)
    p.add_argument("--mem1", required=True, type=Path)
    p.add_argument("--mem2", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path,
                   help="New local sanitized JSON; never overwrite")
    args = p.parse_args(argv)
    try:
        result = audit_local_pair(
            args.mem1, args.mem2, private_root=args.private_root,
            output=args.output)
    except (OSError, ValueError, TypeError, KeyError):
        print("Paired source-gated golf audit failed closed; inspect private "
              "file sizes, game revision, scene/mode and output path locally",
              file=sys.stderr)
        return 1
    print("Paired MEM1/MEM2 offline source audit succeeded; no upload.")
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
