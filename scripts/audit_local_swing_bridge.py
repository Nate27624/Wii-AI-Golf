"""OFFLINE local bridge audit: inspect S001 legacy vs neutral-button-only V2.

Never starts Dolphin, loads a savestate, connects to RPC, sends controller
input, or reads private RAM. An optional explicit --prepare-legacy-trial
creates a SEPARATE .py copy from a validated backup (never overwrites V2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = ROOT.parent / "tools" / "mcp_bridge_swing.py"
SWING_V1 = "# WII_AI_GOLF_SWING_TRACE_V1"
NEUTRAL_V2 = "# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2"
ATOMIC = "# WII_AI_GOLF_ATOMIC_TRACE_V1"
AUTOLOAD = "# WII_AI_GOLF_STARTUP_STATE_V1"
LIMIT = 2 * 1024 * 1024


def inspect_bridge(path: Path) -> dict:
    """Identify markers of a local generated bridge; this is not a live ping."""
    path = Path(path)
    result = {"exists": path.is_file(), "path": str(path.resolve()),
              "sha256": None, "bytes": None, "revision": "missing",
              "atomic_marker": False, "autoload_marker": False,
              "swing_v1_marker": False, "neutral_v2_marker": False,
              "safe_for_isolated_legacy_copy": False}
    if not path.is_file():
        return result
    if not 0 < path.stat().st_size <= LIMIT:
        result["revision"] = "too-large-or-empty"
        return result
    raw = path.read_bytes()
    content = raw.decode("utf-8")
    v1, v2 = SWING_V1 in content, NEUTRAL_V2 in content
    atomic, boot = ATOMIC in content, AUTOLOAD in content
    result.update({"sha256": hashlib.sha256(raw).hexdigest(),
                   "bytes": len(raw), "atomic_marker": atomic,
                   "autoload_marker": boot, "swing_v1_marker": v1,
                   "neutral_v2_marker": v2})
    if atomic and v1 and v2:
        result["revision"] = "V2-neutral-button-only"
    elif atomic and v1 and not v2:
        result["revision"] = "V1-neutral-swing-calls"
        result["safe_for_isolated_legacy_copy"] = not boot
    else:
        result["revision"] = "unknown-or-unexpected"
    return result


def audit_local_bridge(current: Path = DEFAULT_BRIDGE) -> dict:
    """Snapshot filesystem provenance, not a claim of game-side recognition."""
    current = Path(current)
    backup = current.with_name(current.name + ".before-neutral-v2.bak")
    installed = inspect_bridge(current)
    prior = inspect_bridge(backup)
    protocol_changed = (
        installed["revision"] == "V2-neutral-button-only"
        and prior["safe_for_isolated_legacy_copy"]
    )
    return {
        "schema_version": 1, "type": "OFFLINE_BRIDGE_PROVENANCE",
        "current": installed, "saved_pre_v2_backup": prior,
        "v1_isolated_trial_possible": bool(prior["safe_for_isolated_legacy_copy"]),
        "controlled_protocol_difference_detected": protocol_changed,
        "neutral_set_wiimote_swing_calls_89_frame_example": {
            "V1": 89, "V2": 35,
            "assumptions": "12 idle-A, 15 backswing, 20 forward, 30 idle-A follow, 12 release; illustrative source-level counts only",
        },
        "neutral_set_wiimote_swing_calls_122_frame_example": {
            "V1": 122, "V2": 35,
            "assumptions": "45 idle-A, 15 backswing, 20 forward, 30 idle-A follow, 12 release; illustrative source-level counts only",
        },
        "notes": [
            "Marker inspection is local source inspection; it does NOT prove what a running Dolphin actually loaded.",
            "Original successful S002 shots predated merged V2 change; no proof of V2 causation until controlled replay.",
            "Do not replace the active generated bridge and do not auto-start any live experiment.",
            "V1 only candidates from BEFORE-V2 backup, not an arbitrary stale bridge or a savestate autoload script.",
            "RPC completion proves trace dispatch, not club motion or ball contact.",
        ],
    }


def prepare_legacy_copy(current: Path, *, destination: Path | None = None) -> Path:
    """Explicit opt-in: create isolated Python script; no mutation of current."""
    current = Path(current)
    backup = current.with_name(current.name + ".before-neutral-v2.bak")
    report = inspect_bridge(backup)
    if not report["safe_for_isolated_legacy_copy"]:
        raise ValueError("Pre-V2 backup missing/unknown/autoloading: cannot prepare a safe isolated V1 trial")
    if not inspect_bridge(current)["swing_v1_marker"]:
        raise ValueError("Current bridge path is not an identified swing-enabled bridge")
    destination = (Path(destination) if destination is not None
                   else current.with_name("mcp_bridge_swing_legacy_eval.py"))
    # Do not overwrite current/backup/savestate, even with an arbitrary path.
    if destination.resolve() in {current.resolve(), backup.resolve()}:
        raise ValueError("Destination must differ from existing bridge and its backup")
    if destination.suffix.lower() != ".py":
        raise ValueError("Destination for the independent legacy trial must end with .py")
    source = backup.read_bytes()
    if destination.exists():
        if destination.read_bytes() != source:
            raise FileExistsError("Legacy evaluation path exists with different bytes; refusing overwrite")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE,
                        help="Actual existing generated bridge, defaults to sibling tools/mcp_bridge_swing.py")
    parser.add_argument("--prepare-legacy-trial", action="store_true",
                        help="Explicitly COPY verified pre-V2 backup to separate .py; NEVER launch Dolphin")
    parser.add_argument("--legacy-output", type=Path,
                        help="Alternative NEW .py path; only used with --prepare-legacy-trial")
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
