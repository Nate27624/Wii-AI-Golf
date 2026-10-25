"""Offline inspect Felk swing bridge: thin CLI over shared cross-agent API.

Does not launch Dolphin, load savestates, call RPC or send controller input.
Only --prepare-legacy-trial explicitly requests a separate, no-overwrite copy.
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

# Public aliases retained for callers/tests using this script as a module.
from wii_ai_golf.shared.bridge_provenance import (  # noqa: E402
    DEFAULT_BRIDGE, ATOMIC, AUTOLOAD, NEUTRAL_V2, SWING_V1,
    inspect_bridge_file as inspect_bridge,
    audit_bridge_sources as audit_local_bridge,
    prepare_isolated_legacy_bridge as prepare_legacy_copy,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE,
                        help="Actual existing generated swing bridge")
    parser.add_argument("--prepare-legacy-trial", action="store_true",
                        help="Explicitly COPY verified pre-V2 backup to separate .py; NEVER launch Dolphin")
    parser.add_argument("--legacy-output", type=Path,
                        help="Alternative NEW .py path; only with --prepare-legacy-trial")
    args = parser.parse_args(argv)
    if args.legacy_output and not args.prepare_legacy_trial:
        parser.error("--legacy-output requires --prepare-legacy-trial")
    try:
        report = audit_local_bridge(args.bridge)
        if args.prepare_legacy_trial:
            copy = prepare_legacy_copy(args.bridge, destination=args.legacy_output)
            report["legacy_eval_copy"] = inspect_bridge(copy)
            report["optional_manual_full_start_example"] = (
                'py scripts/run_golf_experiment.py --send-live --bridge "'
                + str(copy.resolve())
                + '" --script collect_outcome_transition.py -- --send-live-swing'
            )
            report["manual_trial_note"] = (
                "Only after deciding to compare with the older bridge; close Dolphin first. "
                "This is an experimental protocol comparison, NOT a guaranteed swing or ball hit."
            )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Bridge audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
