"""Offline, read-only Wii Sports RSPE01 Rev1 MEM1+MEM2 source-root audit.

Accepts two existing raw Dolphin MRAM/ExRAM files. Does not touch Dolphin,
issue inputs, upload data, or claim the snapshots are frame-atomic.
Outputs only source-constrained, privacy-safe summary facts.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
import os
from pathlib import Path
import struct
import sys

MEM1_BASE, MEM1_SIZE = 0x80000000, 24 * 1024 * 1024
MEM2_BASE, MEM2_SIZE = 0x90000000, 64 * 1024 * 1024
SCENE_GLOBAL = 0x804BF4D8
CONFIG_PTR = 0x804BF8C4
FIELD_PTR = 0x804BF868
MAIN_LEN = 0x100


def _bank(addr: int, size: int = 4) -> str | None:
    if type(addr) is not int or addr % 4 or size <= 0:
        return None
    if MEM1_BASE <= addr and addr + size <= MEM1_BASE + MEM1_SIZE:
        return "MEM1"
    if MEM2_BASE <= addr and addr + size <= MEM2_BASE + MEM2_SIZE:
        return "MEM2"
    return None


class SourceRAM:
    def __init__(self, mem1, mem2):
        if len(mem1) != MEM1_SIZE or len(mem2) != MEM2_SIZE:
            raise ValueError("Expected exactly 24MiB MEM1 and 64MiB MEM2 plain raw files")
        if bytes(mem1[:6]) != b"RSPE01" or mem1[7] != 1:
            raise ValueError("Expected Wii Sports RSPE01 revision 1 MEM1 header")
        self.banks = {"MEM1": mem1, "MEM2": mem2}

    def u32(self, addr: int) -> int | None:
        bank = _bank(addr)
        if bank is None:
            return None
        base = MEM1_BASE if bank == "MEM1" else MEM2_BASE
        return struct.unpack_from(">I", self.banks[bank], addr - base)[0]

    def mapped(self, addr: int | None, length: int = 4) -> bool:
        return _bank(addr, length) is not None

    def u8(self, addr: int) -> int | None:
        bank = _bank(addr, 1)
        if bank is None:
            return None
        base = MEM1_BASE if bank == "MEM1" else MEM2_BASE
        return self.banks[bank][addr - base]

    def f32(self, addr: int) -> float | None:
        bank = _bank(addr, 4)
        if bank is None:
            return None
        base = MEM1_BASE if bank == "MEM1" else MEM2_BASE
        return struct.unpack_from(">f", self.banks[bank], addr - base)[0]


def _plausible_vec3(r: SourceRAM, addr: int | None) -> dict:
    """Shape validation only. NEVER return raw f32 values or claim coordinates."""
    if not r.mapped(addr, 12):
        return {"mapped": False, "three_finite_components": False,
                "nonzero": False}
    values = [r.f32(addr + i * 4) for i in range(3)]
    finite = all(v is not None and math.isfinite(v) for v in values)
    return {"mapped": True, "three_finite_components": finite,
            "nonzero": bool(finite and any(v != 0.0 for v in values))}


def audit(mem1, mem2, *, timestamp_gap_seconds: float | None = None) -> dict:
    r = SourceRAM(mem1, mem2)
    config = r.u32(CONFIG_PTR)
    field = r.u32(FIELD_PTR)
    config_ok = r.mapped(config, 0xA0)
    field_ok = r.mapped(field, 0x90)
    mode = r.u32(config + 0x94) if config_ok else None
    hole = r.u32(config + 0x98) if config_ok else None
    slots = [r.u32(SCENE_GLOBAL + 4 * i) for i in range(2)]
    unique_managers = set(x for x in slots if r.mapped(x, 0x20))
    checks = {"candidate_static_manager_cells": len(unique_managers),
              "manager_scene_id_5": 0, "scene_sport_2": 0,
              "own_scene_id_and_backlink": 0, "golf_main_mapped": 0}
    matches = []
    for manager in sorted(unique_managers):
        if r.u32(manager + 0x18) != 5:
            continue
        checks["manager_scene_id_5"] += 1
        scene = r.u32(manager + 0x0C)
        if not r.mapped(scene, 0xA0):
            continue
        if r.u32(scene + 0x54) != 2:
            continue
        checks["scene_sport_2"] += 1
        if r.u32(scene + 0x1C) != 5 or r.u32(scene + 0x20) != manager:
            continue
        checks["own_scene_id_and_backlink"] += 1
        main = r.u32(scene + 0x9C)
        if not r.mapped(main, MAIN_LEN):
            continue
        checks["golf_main_mapped"] += 1
        matches.append({"manager_bank": _bank(manager), "scene_bank": _bank(scene),
                        "main_bank": _bank(main)})
    field_ptrs = {
        "map_data": 0x18, "current_pin": 0x44, "current_start": 0x50,
        "cup": 0x54, "wind_object": 0x68, "course": 0x70,
    }
    fields = {name: {"pointer_bank": _bank(r.u32(field + offset), 4) if field_ok else None,
                     "pointer_mapped": bool(field_ok and r.mapped(r.u32(field + offset), 4))}
              for name, offset in field_ptrs.items()}
    pin_count = r.u32(field + 0x3C) if field_ok else None
    start_count = r.u32(field + 0x48) if field_ok else None
    def bounded(x):
        return x if x is not None and x <= 10000 else None

    # Exact source-defined RPGolFieldManager members. These are RAM-level
    # field shapes, NOT validated in-game visual semantics or physics.
    ui_offsets = {"wind_arrow": 0x6C, "green_slope_preview": 0x7C,
                  "minimap": 0x88}
    ui_states = {}
    for name, offset in ui_offsets.items():
        raw = r.u8(field + offset) if field_ok else None
        ui_states[name] = bool(raw) if raw in (0, 1) else None
    opacity = r.f32(field + 0x80) if field_ok else None
    opacity_unit_interval = bool(
        opacity is not None and math.isfinite(opacity) and 0 <= opacity <= 1
    )
    sun_shape = _plausible_vec3(r, field + 0x5C if field_ok else None)

    # mCourseObj is declared RPGolMapObjBase* in source; base mTrans+0x30
    # is eligible only as a source-layout *candidate*, never terrain/ball XYZ.
    course_ptr = r.u32(field + 0x70) if field_ok else None
    course_trans = _plausible_vec3(
        r, course_ptr + 0x30 if r.mapped(course_ptr, 0x3C) else None
    )
    gap = round(timestamp_gap_seconds, 2) if timestamp_gap_seconds is not None else None
    return {
        "kind": "local-source-gated-mem1-mem2-pair-audit", "schema_version": 1,
        "game_id": "RSPE01", "revision": 1,
        "snapshot_bank_sizes_verified": True,
        "same_emulator_frame_verified": False,
        "dump_modified_time_gap_seconds": gap,
        "cross_bank_time_mismatch_warning": gap is None or gap > 5,
        "source_config_pointer_bank": _bank(config),
        "source_config_instance_mapped": config_ok,
        "source_field_pointer_bank": _bank(field),
        "source_field_instance_mapped": field_ok,
        "candidate_training_mode_4": mode == 4,
        "source_config_mode_raw_if_bounded": mode if mode is not None and mode <= 20 else None,
        "source_current_hole_raw_if_bounded": hole if hole is not None and hole <= 100 else None,
        "scene_chain_checks": checks,
        "unique_source_gated_scene_chain": len(matches) == 1,
        "scene_chain_candidate_banks": matches[:1] if len(matches) == 1 else [],
        "source_field_candidate_counts": {
            "pin_count_raw_if_bounded": bounded(pin_count),
            "start_count_raw_if_bounded": bounded(start_count)},
        "source_field_pointer_candidates": fields,
        "source_labeled_ui_flag_candidates": ui_states,
        "source_labeled_green_slope_opacity_in_unit_interval": opacity_unit_interval,
        "source_labeled_sun_vec3_shape": sun_shape,
        "source_course_base_mtrans_vec3_shape": course_trans,
        "field_member_shape_claim_only": True,
        "source_field_member_layout_reference":
            "ogws_info/RPGolFieldManager.h and RPGolMapObjBase.h, RSPE01 Rev1",
        "ball_xyz_verified": False, "club_pose_verified": False,
        "swing_power_verified": False, "shot_contact_verified": False,
        "wind_speed_direction_verified": False, "terrain_verified": False,
        "source_type_identity_verified": False,
        "next_action": ("Review cross-bank timestamp and object owner provenance; "
                        "if snapshots differ in time, compare only independent static facts, "
                        "not joint per-frame states. Source-backed pointers are not ball or power data."),
        "warning": "No private pointers, raw memory bytes or paths disclosed; not an atomic capture."
    }


def _read_only_input(path: Path, expected_size: int, stack: ExitStack):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected_size:
        raise ValueError("Wrong/missing/symlinked raw file")
    file = stack.enter_context(path.open("rb"))
    return stack.enter_context(mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    default_dump = Path(os.environ.get("APPDATA", ".")) / "Dolphin Emulator" / "Dump"
    ap.add_argument("--mem1", type=Path, default=default_dump / "mem1.raw")
    ap.add_argument("--mem2", type=Path, default=default_dump / "mem2.raw")
    args = ap.parse_args(argv)
    try:
        if args.mem1.resolve() == args.mem2.resolve():
            raise ValueError("Cannot reuse the same input for both memory banks")
        times = [args.mem1.stat().st_mtime, args.mem2.stat().st_mtime]
        with ExitStack() as stack:
            mem1 = _read_only_input(args.mem1, MEM1_SIZE, stack)
            mem2 = _read_only_input(args.mem2, MEM2_SIZE, stack)
            result = audit(mem1, mem2, timestamp_gap_seconds=abs(times[0]-times[1]))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, OverflowError) as exc:
        print(f"Offline pair audit stopped: {type(exc).__name__} (inspect private files locally)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
