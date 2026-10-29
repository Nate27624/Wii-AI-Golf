"""Single source of truth for *offline* Felk swing-bridge provenance.

All S001/S002/S003/S004/S005 agents and S000 lab can import these stdlib-only
functions. They inspect files, not live Dolphin state; bridge source identity
does NOT establish game recognition, ball contact, or a verified score.

Do not mistake marker classification for cryptographic authentication. sha256
allows a recorded experiment to be compared to another recorded bridge file.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BRIDGE = ROOT.parent / "tools" / "mcp_bridge_swing.py"
SWING_V1 = "# WII_AI_GOLF_SWING_TRACE_V1"
NEUTRAL_V2 = "# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2"
ATOMIC_A45 = "# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1"
ATOMIC = "# WII_AI_GOLF_ATOMIC_TRACE_V1"
AUTOLOAD = "# WII_AI_GOLF_STARTUP_STATE_V1"
MAX_SOURCE_BYTES = 2 * 1024 * 1024


def inspect_bridge_file(path: Path) -> dict[str, Any]:
    """Read-only bridge identity; all keys JSON-serializable.

    Classifications reflect source markers only, NOT what an already-running
    Dolphin process loaded. No network or memory write of any kind.
    """
    path = Path(path)
    result = {
        "exists": path.is_file(),
        "path": str(path.resolve()),
        "sha256": None,
        "bytes": None,
        "revision": "missing",
        "atomic_marker": False,
        "autoload_marker": False,
        "swing_v1_marker": False,
        "neutral_v2_marker": False,
        "atomic_a45_marker": False,
        "safe_for_isolated_legacy_copy": False,
    }
    if not path.is_file():
        return result
    size = path.stat().st_size
    if not 0 < size <= MAX_SOURCE_BYTES:
        result["revision"] = "too-large-or-empty"
        return result
    source = path.read_bytes()
    decoded = source.decode("utf-8")
    atomic = ATOMIC in decoded
    v1 = SWING_V1 in decoded
    v2 = NEUTRAL_V2 in decoded
    autoload = AUTOLOAD in decoded
    a45 = ATOMIC_A45 in decoded
    result.update({
        "sha256": hashlib.sha256(source).hexdigest(),
        "bytes": len(source),
        "atomic_marker": atomic,
        "autoload_marker": autoload,
        "swing_v1_marker": v1,
        "neutral_v2_marker": v2,
        "atomic_a45_marker": a45,
    })
    if atomic and v1 and a45 and not v2 and not autoload:
        result["revision"] = "V1-atomic-a45"
    elif atomic and v1 and v2:
        result["revision"] = "V2-neutral-button-only"
    elif atomic and v1 and not v2:
        result["revision"] = "V1-neutral-swing-calls"
        result["safe_for_isolated_legacy_copy"] = not autoload
    else:
        result["revision"] = "unknown-or-unexpected"
    return result


def audit_bridge_sources(current: Path = DEFAULT_BRIDGE) -> dict[str, Any]:
    """Read installed and prior bridge file identities, with no side effects."""
    current = Path(current)
    backup = current.with_name(current.name + ".before-neutral-v2.bak")
    active = inspect_bridge_file(current)
    historical = inspect_bridge_file(backup)
    return {
        "schema_version": 1,
        "type": "OFFLINE_BRIDGE_PROVENANCE",
        "current": active,
        "saved_pre_v2_backup": historical,
        "v1_isolated_trial_possible": bool(historical["safe_for_isolated_legacy_copy"]),
        "controlled_protocol_difference_detected": (
            active["revision"] == "V2-neutral-button-only"
            and historical["safe_for_isolated_legacy_copy"]
        ),
        "neutral_set_wiimote_swing_calls_89_frame_example": {
            "V1": 89, "V2": 35,
            "assumptions": (
                "12 idle-A, 15 backswing, 20 forward, 30 idle-A follow, "
                "12 release; illustrative source-level counts only"
            ),
        },
        "neutral_set_wiimote_swing_calls_122_frame_example": {
            "V1": 122, "V2": 35,
            "assumptions": (
                "45 idle-A, 15 backswing, 20 forward, 30 idle-A follow, "
                "12 release; illustrative source-level counts only"
            ),
        },
        "notes": [
            "Marker inspection is local source inspection; it does NOT prove what a running Dolphin actually loaded.",
            "Original successful S002 shots predated merged V2 change; no proof of V2 causation until controlled replay.",
            "Do not replace the active generated bridge and do not auto-start any live experiment.",
            "V1 only candidates from BEFORE-V2 backup, not an arbitrary stale bridge or a savestate autoload script.",
            "RPC completion proves trace dispatch, not club motion or ball contact.",
        ],
    }


def prepare_isolated_legacy_bridge(
    current: Path, *, destination: Path | None = None,
) -> Path:
    """Explicit local copy of a structurally identified old bridge, no resets.

    Must be requested by the operator (unlike read-only inspection). Never
    overwrite current V2, the backup, or an unrelated preexisting file.
    """
    current = Path(current)
    backup = current.with_name(current.name + ".before-neutral-v2.bak")
    previous = inspect_bridge_file(backup)
    if not previous["safe_for_isolated_legacy_copy"]:
        raise ValueError(
            "Pre-V2 backup missing/unknown/autoloading: cannot prepare a safe isolated V1 trial"
        )
    if not inspect_bridge_file(current)["swing_v1_marker"]:
        raise ValueError("Current bridge path is not an identified swing-enabled bridge")
    destination = (
        Path(destination) if destination is not None
        else current.with_name("mcp_bridge_swing_legacy_eval.py")
    )
    if destination.resolve() in {current.resolve(), backup.resolve()}:
        raise ValueError("Destination must differ from existing bridge and its backup")
    if destination.suffix.lower() != ".py":
        raise ValueError("Destination for the independent legacy trial must end with .py")
    source = backup.read_bytes()
    if destination.exists():
        if destination.read_bytes() != source:
            raise FileExistsError(
                "Legacy evaluation path exists with different bytes; refusing overwrite"
            )
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source)
    return destination


# Backwards-compatible names for the existing S001 audit CLI and its test suite.
inspect_bridge = inspect_bridge_file
audit_local_bridge = audit_bridge_sources
prepare_legacy_copy = prepare_isolated_legacy_bridge
