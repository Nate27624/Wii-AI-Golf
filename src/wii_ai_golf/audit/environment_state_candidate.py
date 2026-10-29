"""Offline Wii Sports US Rev1 environment candidate audit (existing private S002 windows).

Source-documented relative fields are NOT game-verified object identities,
ball coordinates, wind vector, terrain geometry, or shot scores.
No Dolphin, RPC, game controls, network, or publication occur in this module.
"""
from __future__ import annotations

from collections import Counter
import re
import struct
from typing import Any

MAX_ROWS = 100
WINDOW_SIZES = {"golf_config": 0x1C74, "golf_field": 0xA8}
PHASES = ("pre", "post", "settled")
# Source: kiwi515/ogws_info headers RPGolConfig.h, RPGolFieldManager.h.
# These are member offsets in source-supported objects, not RAM addresses.
CONFIG_MODE = 0x94
CONFIG_HOLE = 0x98
FIELD_COUNTS = {"pin_count": 0x3C, "start_count": 0x48}
FIELD_POINTERS = {
    "pin": 0x44, "start": 0x50, "cup": 0x54,
    "wind_object": 0x68, "course": 0x70, "map_data": 0x18,
}
FIELD_BOOL_FLAGS = {"wind_arrow_visible": 0x6C,
                    "green_slope_visible": 0x7C,
                    "minimap_visible": 0x88}


def _u32(b: bytes, offset: int) -> int:
    return struct.unpack_from(">I", b, offset)[0]


def _wii_ram(addr: int, size: int) -> bool:
    return (type(addr) is int and addr % 4 == 0 and size > 0 and
            (0x80000000 <= addr and addr + size <= 0x81800000 or
             0x90000000 <= addr and addr + size <= 0x94000000))


def _parse_window(row: dict, name: str) -> tuple[int, bytes]:
    windows = row.get("windows")
    if type(windows) is not dict or name not in windows:
        raise ValueError("Missing source-backed S002 environment window")
    entry = windows[name]
    if type(entry) is not dict or set(entry) != {"address", "bytes_hex"}:
        raise ValueError("Unsupported raw snapshot window shape")
    value = entry["address"]
    if type(value) is not str or re.fullmatch(r"0x[0-9a-fA-F]{8}", value) is None:
        raise ValueError("Invalid private address format")
    raw_text = entry["bytes_hex"]
    if type(raw_text) is not str or len(raw_text) != 2 * WINDOW_SIZES[name]:
        raise ValueError("Invalid private window length")
    try:
        raw = bytes.fromhex(raw_text)
    except ValueError as exc:
        raise ValueError("Invalid private hex content") from exc
    addr = int(value, 16)
    if not _wii_ram(addr, len(raw)):
        raise ValueError("Invalid private window RAM range")
    return addr, raw


def audit_environment_snapshots(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Conservative local summary of source-labelled CONFIG/FIELD objects.

    Strictly checks class/revision/mode and snapshot consistency. Never returns
    raw u32 pointer values or per-run paths. Multiple frames are not independent
    instances and snapshot regions are non-atomic.
    """
    if type(rows) is not list or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("Require bounded private S002 snapshots")
    bases: dict[str, int] = {}
    prior_end = -1
    prior_phase_rank = -1
    max_span = 0
    holes: list[int] = []
    counts: dict[str, list[int]] = {name: [] for name in FIELD_COUNTS}
    ptrs: dict[str, list[int]] = {name: [] for name in FIELD_POINTERS}
    flags: dict[str, list[bool]] = {name: [] for name in FIELD_BOOL_FLAGS}
    phase_counts: Counter[str] = Counter()
    for row in rows:
        if (type(row) is not dict or type(row.get("schema_version")) is not int
            or row["schema_version"] != 1
            or row.get("source") != "Felk-read-only-US-Rev1-unverified-golf-windows"
            or row.get("game_id") != "RSPE01"
            or type(row.get("disc_revision")) is not int or row["disc_revision"] != 1
            or type(row.get("game_mode_raw")) is not int or row["game_mode_raw"] != 4):
            raise ValueError("Wrong version, source provenance or game mode")
        phase = row.get("phase")
        if phase not in PHASES:
            raise ValueError("Unsupported shot phase")
        rank = PHASES.index(phase)
        if rank < prior_phase_rank:
            raise ValueError("Unexpected phase order")
        prior_phase_rank = rank
        start, end, span = (row.get("frame_start"), row.get("frame_end"),
                            row.get("non_atomic_frame_span"))
        if (type(start) is not int or type(end) is not int or type(span) is not int
            or start < 0 or start < prior_end or end < start or end - start != span
            or span > 240):
            raise ValueError("Unreliable or overlapping frame brackets")
        prior_end = end
        max_span = max(max_span, span)
        phase_counts[phase] += 1
        decoded: dict[str, bytes] = {}
        for name in WINDOW_SIZES:
            base, raw = _parse_window(row, name)
            if name in bases and bases[name] != base:
                raise ValueError("Source-backed instance changed within session")
            bases[name] = base
            decoded[name] = raw
        cfg, field = decoded["golf_config"], decoded["golf_field"]
        if _u32(cfg, CONFIG_MODE) != 4:
            raise ValueError("Memory game mode disagrees with wrapper")
        hole = _u32(cfg, CONFIG_HOLE)
        if hole > 31:
            raise ValueError("Implausible source-labelled hole index")
        holes.append(hole)
        for name, offset in FIELD_COUNTS.items():
            value = _u32(field, offset)
            if value > 256:
                raise ValueError("Implausible source-labelled map-object count")
            counts[name].append(value)
        for name, offset in FIELD_POINTERS.items():
            value = _u32(field, offset)
            if value != 0 and not _wii_ram(value, 4):
                raise ValueError("Invalid source-labelled object pointer")
            ptrs[name].append(value)
        for name, offset in FIELD_BOOL_FLAGS.items():
            value = field[offset]
            if value not in (0, 1):
                raise ValueError("Invalid source-labelled boolean field")
            flags[name].append(bool(value))
    return {
        "kind": "local-golf-environment-source-candidates",
        "schema_version": 1,
        "sample_count": len(rows),
        "phase_sample_counts": {p: phase_counts[p] for p in PHASES if phase_counts[p]},
        "max_non_atomic_frame_span": max_span,
        "timing_fine_enough_for_frame_events": False,
        "source_candidate_game_mode": 4,
        "source_candidate_current_hole_raw": holes[0] if len(set(holes)) == 1 else None,
        "hole_value_changed_in_capture": len(set(holes)) != 1,
        "map_object_counts": {k: {"distinct_values": len(set(v)),
                                    "first_observed": v[0]}
                              for k, v in sorted(counts.items())},
        "object_refs": {k: {"present_every_snapshot": all(v),
                            "changed_during_capture": len(set(v)) > 1}
                        for k, v in sorted(ptrs.items())},
        "visual_flags": {k: {"true_in_all_samples": all(v),
                             "changed_during_capture": len(set(v)) > 1}
                         for k, v in sorted(flags.items())},
        "scene_field_object_identity_verified": False,
        "pin_xyz_verified": False,
        "ball_xyz_verified": False,
        "wind_speed_direction_verified": False,
        "course_terrain_verified": False,
        "game_state_machine_verified": False,
        "warning": ("Source member-offset candidates from existing non-atomic private US Rev1 captures; "
                    "pointer presence does not decode positions, wind, physical ball or score."),
    }
