"""PRIVATE expanded Rev1 Golf source-object window differential, preserved B0..B3.

Reuses S002 #160/#163 authoritative private manifest, rev, scene, roster,
selected-ball and current-start source gates. Reads bounded known game-object
windows only; writes a fresh, local, detailed JSON under Wii-AI-Golf-Data.
Never launches Dolphin, sends controls, writes emulator memory or publishes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as four

WINDOW_BYTES = {
    "scene": 0xA0,   # source-gated +0x9c RPGolMain reference
    "main": 0x80,    # bounded hypothesis; includes observed +0x74 heartbeat
    "config": 0x9C,  # known +0x94 mode, +0x98 current hole
    "field": 0xA8,   # known pin/start object references
    "selected_start": 0x50,  # source-backed MapObjBase transform+selfptr
    "selected_pin": 0x50,    # same base-transform hypothesis
}
RECORD_BYTES = roster.ROSTER_STRIDE              # source four-slot 0xCC
BALL_BYTES = 0x1AC                            # source SimulateManager array
WIND_BYTES = 9 * 4                          # source bounded nine-hole tables
MAX_WINDOWS = 20
MAX_F32 = 100_000.0


def _gated_window(read_u32, start: int, size: int, expected_bank="MEM2") -> dict:
    """Finite fixed-length read. Never traverse pointers found inside a window."""
    if size % 4 or size > BALL_BYTES or roster._bank(start, size) != expected_bank:
        raise ValueError("Object window outside expected source bank/size")
    return {
        "guest_base_hex": f"0x{start:08X}",
        "word_u32_hex": [f"0x{read_u32(start + offset):08X}"
                         for offset in range(0, size, 4)],
    }


def _vector(read_u32, address: int) -> dict:
    if roster._bank(address, 12) != "MEM2":
        raise ValueError("Source vector is unmapped")
    words = [read_u32(address + k * 4) for k in range(3)]
    floats = [struct.unpack(">f", struct.pack(">I", w))[0] for w in words]
    if not all(math.isfinite(f) and abs(f) <= MAX_F32 for f in floats):
        raise ValueError("Candidate vector contains invalid/implausible values")
    return {"word_u32_hex": [f"0x{w:08X}" for w in words],
            "be_f32": floats, "units_verified": False, "world_xyz_verified": False}


def sample_one(read_u32, header: bytes) -> dict:
    """Extract only explicitly named bounded windows after full source-gated triage."""
    safe, private = selected.analyze_one(read_u32, header)
    if any(safe.get(k) is not True for k in (
        "selected_record_pointer_matches_code_defined_stride",
        "record_candidate_triplet_finite_bounded",
        "nested_ball_candidate_triplet_finite_bounded",
        "source_current_start_triplet_finite_bounded",
        "source_current_start_constructor_selfrefs_match",
        "selected_ball_translation_pointer_selfref_matches_base",
    )):
        raise ValueError("Source-selected ball/start candidate mismatch")
    pm = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    mgr = read_u32(roster.SCENE_MANAGER_STATIC)
    scene = read_u32(mgr + 0xC)
    main = read_u32(scene + 0x9C)
    config = read_u32(roster.GOLF_CONFIG_STATIC)
    field = read_u32(roster.GOLF_FIELD_STATIC)
    start = read_u32(field + 0x50)
    if roster._bank(start, 0x50) != "MEM2":
        raise ValueError("Current-start source pointer invalid")
    if read_u32(start + 0x4C) != start + 0x30:
        raise ValueError("Current-start translation pointer mismatch")
    windows = {}
    for label, addr in (
        ("scene", scene), ("main", main), ("config", config),
        ("field", field), ("selected_start", start),
    ):
        windows[label] = _gated_window(read_u32, addr, WINDOW_BYTES[label])
    # Source GetWind() reads these two nine-word MEM1 arrays. Runtime values
    # are unlabeled raw integer candidates; no wind units inferred.
    windows["wind_direction_table"] = _gated_window(
        read_u32, 0x804A8B54, WIND_BYTES, "MEM1")
    windows["wind_speed_table"] = _gated_window(
        read_u32, 0x804A8B78, WIND_BYTES, "MEM1")
    pin = read_u32(field + 0x44)
    pin_mapped = roster._bank(pin, 0x50) == "MEM2"
    if pin_mapped and read_u32(pin + 0x4C) == pin + 0x30:
        windows["selected_pin"] = _gated_window(
            read_u32, pin, WINDOW_BYTES["selected_pin"])
    vectors = {
        "selected_start": _vector(read_u32, start + 0x30),
        "selected_record_plus_054": None,
        "selected_record_plus_060": None,
        "selected_ball": None,
    }
    if "selected_pin" in windows:
        vectors["selected_pin"] = _vector(read_u32, pin + 0x30)

    balls_seen = set()
    for i in range(roster.ROSTER_SLOTS):
        record = pm + 4 + roster.ROSTER_STRIDE * i
        ball = read_u32(record + 0x88)
        if roster._bank(record, RECORD_BYTES) != "MEM2":
            raise ValueError("Record source-window bank mismatch")
        if roster._bank(ball, BALL_BYTES) != "MEM2":
            raise ValueError("Ball source-window bank mismatch")
        if ball in balls_seen or not roster._in_data(read_u32(ball), roster.BALL_DATA):
            raise ValueError("Ball source object or uniqueness mismatch")
        balls_seen.add(ball)
        windows[f"player_record_{i}"] = _gated_window(
            read_u32, record, RECORD_BYTES)
        windows[f"ball_object_{i}"] = _gated_window(
            read_u32, ball, BALL_BYTES)
        if i == private["selected_index"]:
            if read_u32(pm + 0x334) != record:
                raise ValueError("Selected source record changed")
            if read_u32(ball + 0x4C) != ball + 0x30:
                raise ValueError("Selected ball translation pointer mismatch")
            vectors["selected_record_plus_054"] = _vector(read_u32, record + 0x54)
            vectors["selected_record_plus_060"] = _vector(read_u32, record + 0x60)
            vectors["selected_ball"] = _vector(read_u32, ball + 0x30)
    if len(windows) > MAX_WINDOWS or any(v is None for v in vectors.values()):
        raise ValueError("Too many windows or required translation not found")
    return {
        "selected_slot_index": private["selected_index"],
        "raw_hole_index": private["hole"],
        "windows": windows,
        "source_linked_vec3_candidates": vectors,
        "ball_motion_verified": False,
    }


def combine(phases: list[dict], *, distinct_banks: bool) -> tuple[dict, dict]:
    """Safe console summary + FULL private object words/floats and change offsets."""
    if len(phases) != 4 or type(distinct_banks) is not bool:
        raise ValueError("Four valid snapshot phases and bank indicators required")
    keys = set(phases[0]["windows"])
    if any(set(x["windows"]) != keys for x in phases[1:]):
        raise ValueError("Source object windows differ between phases")
    if len({(x["selected_slot_index"], x["raw_hole_index"])
            for x in phases}) != 1:
        raise ValueError("Selected slot/hole changed")
    windows = {}
    console = {}
    for label in sorted(keys):
        data = [p["windows"][label] for p in phases]
        sizes = {len(x["word_u32_hex"]) for x in data}
        if len(sizes) != 1:
            raise ValueError("Object window dimensions differ")
        addresses = [x["guest_base_hex"] for x in data]
        stable = len(set(addresses)) == 1
        transitions = []
        for i in range(3):
            transitions.append([
                4 * j
                for j, (left, right) in enumerate(zip(
                    data[i]["word_u32_hex"], data[i + 1]["word_u32_hex"]))
                if left != right
            ] if stable else None)
        windows[label] = {
            "guest_bases_by_phase_hex": addresses,
            "guest_base_stable": stable,
            "size_bytes": len(data[0]["word_u32_hex"]) * 4,
            "all_words_by_phase_hex": [
                d["word_u32_hex"] for d in data
            ],
            "changed_byte_offsets_by_transition": [
                [f"+0x{off:03X}" for off in offsets]
                if offsets is not None else None
                for offsets in transitions
            ],
        }
        console[label] = {
            "object_address_stable": stable,
            "changed_u32_count_per_transition": [
                len(offsets) if offsets is not None else None
                for offsets in transitions
            ],
        }
    # A private report can be uploaded DIRECTLY by the operator for further
    # analysis; never auto-publish it or assert source vector is the true ball.
    private_report = {
        "kind": "PRIVATE-golf-source-object-windows-four-phase",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "phase_names": list(four.PHASE_LABELS),
        "all_bank_pairs_distinct": distinct_banks,
        "selected_slot_and_hole_stable": True,
        "windows": windows,
        "vec3_by_phase": [p["source_linked_vec3_candidates"] for p in phases],
        "candidate_xyz_units_verified": False,
        "ball_motion_verified": False,
        "model_training_allowed": False,
        "automatic_publication_allowed": False,
        "warning": (
            "PRIVATE raw gameplay numeric candidate words, addresses and vector "
            "reinterpretations. Not a game-physics decoder. Do not publish without "
            "operator review. Four GUI snapshots are NOT guest-frame synchronized."
        ),
    }
    safe_report = {
        "kind": "local-private-golf-source-object-window-change-counts",
        "schema_version": 1,
        "phase_names": list(four.PHASE_LABELS),
        "source_gate_passed_all_phases": True,
        "all_three_transitions_have_distinct_full_banks": distinct_banks,
        "window_change_counts": console,
        "candidate_position_world_xyz_verified": False,
        "ball_motion_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
        "private_details_written": True,
    }
    return safe_report, private_report


def run_local(folder: Path):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private B0-B3 session")
    root = selected.DATA_ROOT.resolve(strict=True)
    folder = folder.resolve(strict=True)
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Private snapshot folder must be under sibling Data root")
    manifest = four._validate_manifest(folder)
    samples = []
    hashes = []
    with ExitStack() as stack:
        for phase in four.PHASES:
            files = {
                k: four._approved_bank(
                    folder, f"{phase}-{k}.bin",
                    roster.MEM1_SIZE if k == "MEM1" else roster.MEM2_SIZE)
                for k in ("MEM1", "MEM2")
            }
            digests = {k: four._hash(v) for k, v in files.items()}
            if digests != {k: manifest[phase]["sha256"][k] for k in files}:
                raise ValueError("Private snapshot bank digest mismatch")
            hashes.append(digests)
            images = []
            for file in files.values():
                handle = stack.enter_context(file.open("rb"))
                images.append(stack.enter_context(mmap.mmap(
                    handle.fileno(), 0, access=mmap.ACCESS_READ
                )))
            reader = roster.TwoBankReader(*images)
            samples.append(sample_one(reader.u32, reader.header()))
    distinct = all(all(hashes[i][k] != hashes[i + 1][k]
                       for k in ("MEM1", "MEM2")) for i in range(3))
    return combine(samples, distinct_banks=distinct)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", required=True, type=Path)
    p.add_argument("--output-private", type=Path,
                   help="Exact NEW local report path within source Data root")
    args = p.parse_args(argv)
    try:
        folder = args.private_root
        out = args.output_private or (folder / "golf-object-windows-PRIVATE.json")
        data_root = selected.DATA_ROOT.resolve(strict=True)
        if (out.is_symlink() or not out.parent.resolve(strict=True).is_relative_to(data_root)
                or out.suffix.lower() != ".json" or not out.name.endswith("-PRIVATE.json")
                or out.exists()):
            raise ValueError("Output must be new private JSON inside ignored Data root")
        safe, detail = run_local(folder)
        with out.open("x", encoding="utf-8") as handle:
            json.dump(detail, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            struct.error):
        print("Expanded source-object memory study failed closed; inspect "
              "existing private B0-B3 files and output path.", file=sys.stderr)
        return 1
    print(json.dumps(safe, indent=2, sort_keys=True, allow_nan=False))
    print("Detailed game-memory report saved locally at:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
