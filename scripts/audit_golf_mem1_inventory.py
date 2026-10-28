"""Offline inventory of one private RSPE01 Rev1 MEM1 dump (optional MEM2).

A single native, headerless RAM dump can confirm source-supported singleton
chains and candidate reference presence; it CANNOT establish field semantics,
motion causation, ball physics or stable identity across sessions.
Read only; no Dolphin, network, file writes, or unreviewed publication.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT.parent / "Wii-AI-Golf-Data"
MEM1_BASE, MEM1_LEN = 0x80000000, 24 * 1024 * 1024
MEM2_BASE, MEM2_LEN = 0x90000000, 64 * 1024 * 1024
MEM1_SUPPORTED_FILE_SIZES = (MEM1_LEN, 32 * 1024 * 1024)
GAME_HEADER = b"RSPE01\x00\x01"
CONFIG_SLOT = 0x804BF8C4
MANAGER_SLOT = 0x804BF4D8
FIELD_SLOT = 0x804BF868
FIELD_REFS = {
    "map_data": 0x18, "pin": 0x44, "start": 0x50,
    "cup": 0x54, "wind_object": 0x68, "course": 0x70,
}


def _memory_location(addr: int, width: int):
    if type(addr) is not int or type(width) is not int or addr % 4 or width <= 0:
        return None
    if MEM1_BASE <= addr and addr + width <= MEM1_BASE + MEM1_LEN:
        return "MEM1", addr - MEM1_BASE
    if MEM2_BASE <= addr and addr + width <= MEM2_BASE + MEM2_LEN:
        return "MEM2", addr - MEM2_BASE
    return None


def _pointer_shape(addr: int, width: int = 4) -> bool:
    return _memory_location(addr, width) is not None


def _word(m1, m2, addr: int) -> int | None:
    loc = _memory_location(addr, 4)
    if loc is None:
        return None
    bank, offset = loc
    buf = m1 if bank == "MEM1" else m2
    if buf is None:
        return None
    return struct.unpack_from(">I", buf, offset)[0]


def _owned(m1, m2, addr: int, width: int = 4) -> bool:
    loc = _memory_location(addr, width)
    return loc is not None and (loc[0] == "MEM1" or m2 is not None)


def audit(m1, m2=None) -> dict:
    """Return only source-relative identities/booleans, never RAM values."""
    if len(m1) not in MEM1_SUPPORTED_FILE_SIZES:
        raise ValueError("unsupported MEM1 native dump size")
    if m2 is not None and len(m2) != MEM2_LEN:
        raise ValueError("unsupported MEM2 native dump size")
    if m1[:8] != GAME_HEADER:
        raise ValueError("not a verified RSPE01 USA Rev1 plain MEM1 dump")

    config = _word(m1, m2, CONFIG_SLOT)
    if not _pointer_shape(config, 0x9C) or not _owned(m1, m2, config, 0x9C):
        raise ValueError("golf config singleton not accessible in supplied banks")
    if _word(m1, m2, config + 0x94) != 4:
        raise ValueError("Hitting the Green mode is not verified")
    hole = _word(m1, m2, config + 0x98)
    if type(hole) is not int or not 0 <= hole <= 31:
        raise ValueError("source candidate current-hole word out of bounded range")

    manager = _word(m1, m2, MANAGER_SLOT)
    if not _pointer_shape(manager, 0x1C) or not _owned(m1, m2, manager, 0x1C):
        raise ValueError("scene manager singleton not accessible in supplied banks")
    if _word(m1, m2, manager + 0x18) != 5:
        raise ValueError("current scene manager ID is not Golf")
    scene = _word(m1, m2, manager + 0x0C)
    if not _pointer_shape(scene, 0xA0) or not _owned(m1, m2, scene, 0xA0):
        raise ValueError("Golf scene not accessible in supplied banks")
    if (_word(m1, m2, scene + 0x1C) != 5 or
            _word(m1, m2, scene + 0x20) != manager or
            _word(m1, m2, scene + 0x54) != 2):
        raise ValueError("Golf scene self ID/backlink/sport check failed")
    main = _word(m1, m2, scene + 0x9C)
    main_mapped = _pointer_shape(main)
    main_backed = bool(main_mapped and _owned(m1, m2, main))

    field = _word(m1, m2, FIELD_SLOT)
    field_mapped = _pointer_shape(field, 0xA8)
    field_backed = bool(field_mapped and _owned(m1, m2, field, 0xA8))
    references = {}
    counts = {}
    if field_backed:
        for label, offset in FIELD_REFS.items():
            p = _word(m1, m2, field + offset)
            references[label] = {
                "non_null": bool(p),
                "wii_ram_address_shape": bool(p and _pointer_shape(p)),
                "referenced_bank_supplied": bool(p and _pointer_shape(p) and _owned(m1, m2, p)),
                "source_member_offset_only": True,
                "semantic_object_identity_verified": False,
            }
        for label, offset in (("pin_object_count", 0x3C),
                              ("player_start_object_count", 0x48)):
            count = _word(m1, m2, field + offset)
            counts[label] = {"plausible_bounded_count": (
                type(count) is int and 0 <= count <= 256),
                "source_member_offset_only": True}
    return {
        "schema_version": 1,
        "kind": "local_single_mem1_source_root_inventory",
        "study_id": "S002-MEMORY-SOURCE-ROOT-01",
        "game_id": "RSPE01",
        "revision": 1,
        "hitting_the_green_mode_verified": True,
        "current_golf_scene_and_backlink_verified_in_snapshot": True,
        "current_hole_raw_source_candidate": hole,
        "candidate_main_pointer_wii_ram_shape": main_mapped,
        "candidate_main_pointer_bank_supplied": main_backed,
        "candidate_main_is_rpgolmain_verified": False,
        "field_manager_slot_wii_ram_shape": field_mapped,
        "field_manager_object_available_in_supplied_banks": field_backed,
        "field_member_refs": references,
        "field_object_counts": counts,
        "mem2_companion_supplied": m2 is not None,
        "independent_boot_stability_verified": False,
        "frame_timestamp_verified": False,
        "club_pose_verified": False,
        "ball_xyz_verified": False,
        "wind_vector_verified": False,
        "shot_power_verified": False,
        "score_verified": False,
        "raw_memory_kept_private": True,
        "allowed_to_publish_to_github": False,
        "warning": (
            "Single private memory checkpoint: only source-supported pointer "
            "chain and member-presence candidates. No type-safe dereference "
            "beyond fixed source-member words, no physical game field verified. "
            "Do not upload full RAM or promote candidate fields to training."
        ),
    }


def _check_private_file(p: Path, root: Path, sizes: tuple[int, ...]):
    if not p.is_file() or p.is_symlink():
        raise ValueError("private source dump missing or symlinked")
    real = p.resolve(strict=True)
    if not real.is_relative_to(root):
        raise ValueError("dump outside ignored private Wii-AI-Golf-Data")
    if p.suffix.lower() not in (".raw", ".bin"):
        raise ValueError("not a native raw memory file extension")
    if p.stat().st_size not in sizes:
        raise ValueError("unexpected native dump size")
    return real


SAFE_ERRORS = frozenset({
    "private source dump missing or symlinked",
    "dump outside ignored private Wii-AI-Golf-Data",
    "not a native raw memory file extension",
    "unexpected native dump size",
    "unsupported MEM1 native dump size",
    "unsupported MEM2 native dump size",
    "not a verified RSPE01 USA Rev1 plain MEM1 dump",
    "golf config singleton not accessible in supplied banks",
    "Hitting the Green mode is not verified",
    "source candidate current-hole word out of bounded range",
    "scene manager singleton not accessible in supplied banks",
    "current scene manager ID is not Golf",
    "Golf scene not accessible in supplied banks",
    "Golf scene self ID/backlink/sport check failed",
})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem1", type=Path, required=True)
    parser.add_argument("--mem2", type=Path)
    args = parser.parse_args(argv)
    try:
        root = PRIVATE_ROOT.resolve(strict=True)
        m1 = _check_private_file(args.mem1, root, MEM1_SUPPORTED_FILE_SIZES)
        m2 = _check_private_file(args.mem2, root, (MEM2_LEN,)) if args.mem2 else None
        with ExitStack() as stack:
            files = [stack.enter_context(m1.open("rb"))]
            if m2:
                files.append(stack.enter_context(m2.open("rb")))
            views = [stack.enter_context(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ))
                     for f in files]
            print(json.dumps(audit(views[0], views[1] if len(views) > 1 else None),
                             sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, BufferError) as exc:
        reason = str(exc)
        if reason not in SAFE_ERRORS:
            reason = "private source audit validation failed"
        print("Offline single MEM1 audit stopped: " + reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
