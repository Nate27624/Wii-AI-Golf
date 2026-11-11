"""Source-anchored Wii Sports Rev1 golf environment transforms (PRIVATE/OFFLINE).

RPGolFieldManager documented singleton (0x804BF868), map object pointers
+0x2C/+0x44/+0x50/+0x54/+0x70, RPGolMapObjBase transform at +0x0C/+0x30/
+0x3C. Emits only derived geometry and booleans. Neither source nor values
identify golf ball, club head, swing power or world units in meters/yards.

NOTE: upstream RPGolMapObjBase.h annotates pointer offsets +0x40/+0x44
overlapping the declared 3-float scale at +0x3C; those pointer annotations
are internally inconsistent. NEVER trust or dereference those locations.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct

from wii_ai_golf.audit.golf_cross_bank_state import (
    _Banks, MEM1_SIZE, MEM2_SIZE, STATIC_CONFIG, STATIC_FIELD,
    audit_pair,
)

# All offsets below are field names declared in kiwi515/ogws_info:
# RP/RPSports/RPGolScene/RPGolFieldManager.h
# RP/RPSports/RPGolScene/RPGolMapObjBase.h
_TRANS = 0x30
_SCALE = 0x3C
_ROT = 0x0C
_OBJECT_OFFSETS = {
    "current_start": 0x50, "current_pin": 0x44, "cup": 0x54,
    "course": 0x70, "tee_marker": 0x2C,
}
MAX_ABS_TRANS = 100000.0
EPSILON_ORTHONORMAL = 0.08


def _f32(data, offset):
    return struct.unpack_from(">f", data, offset)[0]


def _vec(data, off):
    return tuple(_f32(data, off + 4 * j) for j in range(3))


def _rot(data):
    return tuple(_vec(data, _ROT + 12*j) for j in range(3))


def _norm(row):
    return math.sqrt(sum(v*v for v in row))


def _orthonormal(rows):
    if any(abs(_norm(row)-1.0) > EPSILON_ORTHONORMAL for row in rows):
        return False
    return all(abs(sum(x*y for x, y in zip(rows[i], rows[j]))) < EPSILON_ORTHONORMAL
               for i in range(3) for j in range(i+1, 3))


def _object_transform(banks, ptr):
    if banks.region(ptr, 0x48) != "MEM2":
        raise ValueError("Expected source-named current map object in MEM2")
    data = banks.read(ptr, 0x48)
    trans, scale, rows = _vec(data, _TRANS), _vec(data, _SCALE), _rot(data)
    if not all(math.isfinite(v) and abs(v) < MAX_ABS_TRANS for v in trans):
        raise ValueError("Nonfinite/out-of-range source translation")
    if not all(math.isfinite(v) and 0.001 <= v <= 100.0 for v in scale):
        raise ValueError("Invalid declared source scale")
    if not _orthonormal(rows):
        raise ValueError("Invalid declared source rotation")
    return trans, scale, rows


def audit_environment_geometry(mem1, mem2, *, strict_size=True):
    """Validate source-backed instance chain, return derived metrics only."""
    ancestor = audit_pair(mem1, mem2, strict_size=strict_size)
    banks = _Banks(mem1, mem2)
    field = banks.u32(STATIC_FIELD)
    conf = banks.u32(STATIC_CONFIG)
    if ancestor["conditions"]["game_mode"] != 4:
        raise ValueError("Not Hitting the Green game mode")
    transforms = {}
    for name, offset in _OBJECT_OFFSETS.items():
        transforms[name] = _object_transform(
            banks, banks.u32(field + offset))
    start = transforms["current_start"][0]
    pin = transforms["current_pin"][0]
    cup = transforms["cup"][0]
    horizontal = math.hypot(start[0]-pin[0], start[2]-pin[2])
    pin_cup_horizontal = math.hypot(pin[0]-cup[0], pin[2]-cup[2])
    if horizontal > MAX_ABS_TRANS:
        raise ValueError("Implausible start/pin separation")
    # RPGolConfig::mPlayerScores is declared as u32 [4][9] at +0x004,
    # but all zeros alone do not prove a real shot count.
    scores = [banks.u32(conf + 4 + i*4) for i in range(36)]
    return {
        "schema_version": 1,
        "kind": "local-private-golf-environment-geometry-candidate",
        "source": "kiwi515/ogws_info RPGolFieldManager.h + RPGolMapObjBase.h + RPGolConfig.h",
        "disc_revision": 1, "game_mode": 4,
        "active_scene_and_backlink_verified_in_pair": True,
        "source_declared_current_transform_count": len(transforms),
        "transform_identity_checks": {
            name: {
                "source_translation_finite": True,
                "source_rotation_orthonormal": True,
                "source_scale_positive": True,
            } for name in transforms
        },
        "current_start_to_pin_horizontal_game_units": round(horizontal, 3),
        "current_start_to_pin_vertical_game_units": round(pin[1]-start[1], 3),
        "pin_cup_horizontal_game_units": round(pin_cup_horizontal, 3),
        "pin_cup_horizontal_coincident_within_0_01_units": pin_cup_horizontal <= .01,
        "pin_cup_vertical_absolute_game_units": round(abs(pin[1]-cup[1]), 3),
        "score_array_source_slots_checked": len(scores),
        "score_slots_zero": sum(x == 0 for x in scores),
        "no_scoreboard_state_change_tested": True,
        "golf_ball_xyz_verified": False,
        "golfer_body_pose_verified": False,
        "club_head_pose_verified": False,
        "swing_power_verified": False,
        "output_yards_or_meters_calibrated": False,
        "same_game_frame_proven": False,
        "same_boot_proven": False,
        "prediction_or_training_authorized": False,
        "runtime_addresses_exported": False,
        "raw_memory_words_exported": False,
        "allowed_to_publish": False,
        "header_offset_overlap_warning":
            "RPGolMapObjBase.h annotations at +0x40/+0x44 overlap declared scale; "
            "no such pointer was dereferenced.",
        "warning": (
            "This is a single pair of non-atomic GUI exports. "
            "Source-based map-object translation is not a measured ball/club "
            "trajectory; game coordinate units are not calibrated to feet."),
    }


def audit_environment_geometry_files(mem1_path, mem2_path, output):
    from mmap import mmap, ACCESS_READ
    from contextlib import ExitStack
    p1, p2, out = map(Path, (mem1_path, mem2_path, output))
    if (not p1.is_file() or not p2.is_file() or p1.is_symlink()
            or p2.is_symlink() or p1.resolve() == p2.resolve()
            or p1.stat().st_size != MEM1_SIZE
            or p2.stat().st_size != MEM2_SIZE or out.exists() or out.is_symlink()
            or out.suffix.lower() != ".json"):
        raise ValueError("Missing, nonnative, duplicate or unsafe private snapshot/output")
    # Leave all raw data operator-local, no arbitrary output path in payload.
    with ExitStack() as stack:
        files = [stack.enter_context(open(p, "rb")) for p in (p1, p2)]
        images = [stack.enter_context(mmap(f.fileno(), 0, access=ACCESS_READ))
                  for f in files]
        result = audit_environment_geometry(*images)
    with out.open("x", encoding="utf-8") as fp:
        json.dump(result, fp, sort_keys=True, indent=2, allow_nan=False)
        fp.write("\n")
    return result
