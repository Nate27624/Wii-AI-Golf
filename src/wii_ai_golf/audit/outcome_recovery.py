"""Offline salvage and manual result parsing for private golf capture files.

Never reads Dolphin, sends controls or writes game memory. A recovery summary
cannot retroactively know the discarded live swing-dispatch metadata or restore
a missed result-screen moment.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

from wii_ai_golf.audit.outcome_transition import rank_outcome_candidates

_DISTANCE = re.compile(
    r"^\s*(?P<value>(?:\d+(?:\.\d*)?|\.\d+))\s*"
    r"(?P<unit>ft|feet|foot|yd|yds|yard|yards|m|meter|meters)?\s*$",
    re.IGNORECASE,
)
_UNITS = {
    "ft": "ft", "feet": "ft", "foot": "ft",
    "yd": "yd", "yds": "yd", "yard": "yd", "yards": "yd",
    "m": "m", "meter": "m", "meters": "m",
}
_MAX_BYTES = 6 * 1024 * 1024
_MAX_SAMPLES = 60


def parse_displayed_distance(value: str) -> tuple[float | None, str | None]:
    """Accept '100.0ft', '2.1 ft', '3 yards', '2.1', or blank.

    The game display unit must be preserved; this does not convert between
    units or invent a score. Returns (None, None) for no visible number.
    """
    if not isinstance(value, str):
        raise ValueError("distance label must be text")
    value = value.strip()
    if not value:
        return None, None
    found = _DISTANCE.fullmatch(value)
    if not found:
        raise ValueError("Use a nonnegative number, optionally followed by ft, yd, or m (e.g. 100.0ft)")
    number = float(found.group("value"))
    if not math.isfinite(number) or number < 0:
        raise ValueError("Displayed distance must be finite and nonnegative")
    raw_unit = found.group("unit")
    return number, _UNITS[raw_unit.lower()] if raw_unit else None


def exploratory_ranking_target(
    distance: float | None, *, displayed_unit: str | None, green: str,
) -> float | None:
    """Exclude fixed off-green 100-foot penalty from raw RAM numeric matching.

    The HUD label is retained as human evidence in the summary. None here
    means NO numeric target; it does not erase the category or verify physics.
    No other displayed number becomes a physical distance or true score.
    """
    if green == "no" and displayed_unit == "ft" and distance == 100.0:
        return None
    return distance


def recover_outcome_summary(
    path: Path, *, contact: str, green: str, distance_text: str,
    unit: str = "unknown",
) -> dict[str, Any]:
    """Rank an existing private raw JSONL without requiring another live shot."""
    if contact not in ("yes", "no", "unknown") or green not in ("yes", "no", "unknown"):
        raise ValueError("Contact/green must each be yes, no, or unknown")
    distance, suffix_unit = parse_displayed_distance(distance_text)
    if unit not in ("ft", "yd", "m", "unknown"):
        raise ValueError("Unit must be ft, yd, m, or unknown")
    if suffix_unit and unit != "unknown" and suffix_unit != unit:
        raise ValueError("Conflicting unit flags and distance suffix")
    display_unit = ("not-visible" if distance is None else (suffix_unit or unit))
    if not path.is_file() or path.stat().st_size > _MAX_BYTES:
        raise ValueError("Raw JSONL must exist and be at most 6 MiB")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as src:
        for line in src:
            if len(rows) >= _MAX_SAMPLES:
                raise ValueError("Too many raw snapshots for a single shot")
            record = json.loads(line)
            if not isinstance(record, dict) or record.get("phase") not in ("pre", "post", "settled"):
                raise ValueError("Expected only phase-labelled private snapshot records")
            if record.get("source") not in (
                "Felk-read-only-US-Rev1-unverified-golf-windows", None
            ):
                raise ValueError("Unexpected raw snapshot source")
            rows.append(record)
    ranked = rank_outcome_candidates(
        rows, human_distance=exploratory_ranking_target(
            distance, displayed_unit=display_unit, green=green))
    return {
        "schema_version": 1,
        "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
        "source": "offline-recovery-from-private-local-raw-capture",
        "raw_data_created": True,
        "human_observation": {
            "contact_human": contact, "finished_on_green_human": green,
            "displayed_distance_human": distance, "displayed_unit_human": display_unit,
            "game_distance_verified_by_memory": False,
        },
        "known_good_swing_request": {
            "preset": None, "follow_through_frames": None,
            "generated_trace_frames": None, "trace_sha256": None,
            "a_button_only_prime_requests": None, "a_button_prime_applied": None,
        },
        "swing_dispatch": {
            "state": "not_recoverable_from_snapshot_only",
            "applied_frames": None,
        },
        "candidate_ranking": ranked,
        "recovery": {
            "method": "rank-existing-private-phase-snapshots",
            "sample_count": len(rows), "live_dispatch_metadata_recovered": False,
            "screen_state_at_capture_verified": False,
            "warning": "Recovery cannot recreate missing RAM frames or the live swing trace.",
        },
        "warning": "Manual labels and RAM addresses are exploratory; not verified ball XYZ or game score.",
    }
