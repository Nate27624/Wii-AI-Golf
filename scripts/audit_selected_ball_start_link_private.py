"""Local-only, source-gated selected ball/start triple LINK hypothesis.

REUSES S002 #160 roster source/scene/code verification. Not a ball-physics
decoder and not a temporal sampler. Exact input banks remain ignored/private.
No Dolphin, IPC, controller inputs, RAM writes, paths or raw words in stdout.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import math
import mmap
from pathlib import Path
import struct
import sys

import audit_golf_two_bank_roster_private as roster

DATA_ROOT = (Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data")
MAX_ABS_CANDIDATE_FLOAT = 100_000.0
FLOAT_COMPONENTS = 3


def _triplet(read_u32, address):
    if roster._bank(address, 12) != "MEM2":
        raise ValueError("Source-directed vector is not mapped MEM2")
    return tuple(read_u32(address + i * 4) for i in range(FLOAT_COMPONENTS))


def _finite_bounded(words):
    return all(math.isfinite(value) and abs(value) <= MAX_ABS_CANDIDATE_FLOAT
               for value in (struct.unpack(">f", struct.pack(">I", w))[0]
                             for w in words))


def analyze_one(read_u32, header):
    """Private in-process candidates plus a safe public-facing summary.

    The tuple of actual 32-bit words is NEVER printed or serialized. An
    identical float-looking triplet does NOT prove moving ball/world XYZ.
    """
    baseline = roster.triage(read_u32, header)
    code = baseline["bounded_source_register_flow_evidence"]
    for key in ("manager_selected_record_pointer_offset_source_supported",
                "ball_child_plus_0x4c_three_float_writer_source_supported",
                "record_plus_0x88_ball_code_path_source_supported"):
        # Selector support is in code flow, not necessarily all candidate words.
        if not code[key]:
            raise ValueError("Required Rev1 PPC source chain not established")
    index = baseline["source_gated_selected_record_index_hypothesis"]
    if (type(index) is not int or index not in range(roster.ROSTER_SLOTS)
            or not baseline["all_candidate_slots_pairwise_distinct"]):
        raise ValueError("No uniquely source-gated selected roster slot")
    manager = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = manager + 4 + index * roster.ROSTER_STRIDE
    if read_u32(manager + 0x334) != rec:
        raise ValueError("Selected record pointer mismatch")
    ball = read_u32(rec + 0x88)
    if (roster._bank(ball, 0x50) != "MEM2"
            or not roster._in_data(read_u32(ball), roster.BALL_DATA)):
        raise ValueError("Selected ball-related object code-region gate failed")
    ball_translation_ptr = read_u32(ball + 0x4C)
    record_words = _triplet(read_u32, rec + 0x54)
    ball_words = _triplet(read_u32, ball_translation_ptr)

    field = read_u32(roster.GOLF_FIELD_STATIC)
    if roster._bank(field, 0xA8) != "MEM2":
        raise ValueError("Golf field source manager missing")
    current_start = read_u32(field + 0x50)
    if roster._bank(current_start, 0x50) != "MEM2":
        raise ValueError("Source-labelled current start object is not mapped MEM2")
    start_translation_ptr = read_u32(current_start + 0x4C)
    start_words = _triplet(read_u32, start_translation_ptr)
    # The two known Base ctor self-reference invariants are identity hints.
    start_selfrefs = (
        read_u32(current_start + 0x48) == current_start + 0x0C
        and start_translation_ptr == current_start + 0x30
    )
    # Rev1 0x802A03B4 loads child+0x4C and floats are written through it;
    # Base ctor commonly initializes it to obj+0x30, but subclass identity
    # is not independently proven by this one snapshot.
    ball_selfref = ball_translation_ptr == ball + 0x30
    config = read_u32(roster.GOLF_CONFIG_STATIC)
    hole_raw = read_u32(config + 0x98)
    if type(hole_raw) is not int or hole_raw not in range(9):
        raise ValueError("Unexpected training-hole candidate index")
    safe = {
        "selected_record_relative_index_candidate": index,
        "selected_record_pointer_matches_code_defined_stride": True,
        "selected_ball_object_firstword_in_ball_unit_data": True,
        "selected_ball_translation_pointer_is_mem2": True,
        "selected_ball_translation_pointer_selfref_matches_base": ball_selfref,
        "source_current_start_translation_pointer_is_mem2": True,
        "source_current_start_constructor_selfrefs_match": start_selfrefs,
        "record_candidate_triplet_finite_bounded": _finite_bounded(record_words),
        "nested_ball_candidate_triplet_finite_bounded": _finite_bounded(ball_words),
        "source_current_start_triplet_finite_bounded": _finite_bounded(start_words),
        "selected_record_vs_nested_ball_component_equal_count":
            sum(a == b for a, b in zip(record_words, ball_words)),
        "selected_record_vs_current_start_component_equal_count":
            sum(a == b for a, b in zip(record_words, start_words)),
        "selected_nested_ball_vs_current_start_component_equal_count":
            sum(a == b for a, b in zip(ball_words, start_words)),
        "all_three_candidate_triplets_bitwise_equal":
            record_words == ball_words == start_words,
        "source_gated_raw_hole_index_candidate": hole_raw,
        "selected_active_human_player_verified": False,
        "source_candidate_is_dynamic_ball_world_xyz_verified": False,
    }
    private = {"record": record_words, "ball": ball_words, "start": start_words,
               "selected_index": index, "hole": hole_raw}
    return safe, private


def summarize_two_pairs(reports, *, same_mem1=None, same_mem2=None):
    """Reports contain only safe fields and transient private word tuples.

    Never re-label differences between unrelated GUI exports as movement.
    """
    if len(reports) not in (1, 2):
        raise ValueError("Only one or two paused paired-bank observations")
    public = {
        "kind": "local-golf-selected-ball-start-link-candidates",
        "schema_version": 1,
        "input_pair_count": len(reports),
        "game_id": "RSPE01", "disc_revision": 1, "mode": 4,
        "observations": [safe for safe, _ in reports],
        "different_boots_or_phases_proven": False,
        "same_emulated_frame_mem1_mem2_proven": False,
        "visual_ball_motion_verified": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "wind_vector_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
        "warning": ("Source/constructor-backed candidate position word equalities "
                    "do not prove active human, physics ball, world coordinates, "
                    "ball movement, independent boots or phase timing."),
    }
    if len(reports) == 2:
        a, b = (private for _, private in reports)
        if type(same_mem1) is not bool or type(same_mem2) is not bool:
            raise ValueError("Two-pair duplicate-image comparisons required")
        public["between_pairs"] = {
            "mem1_files_bitwise_identical": same_mem1,
            "mem2_files_bitwise_identical": same_mem2,
            "both_banks_bitwise_identical": same_mem1 and same_mem2,
            "raw_hole_index_candidates_equal": a["hole"] == b["hole"],
            "selected_record_index_candidates_equal":
                a["selected_index"] == b["selected_index"],
            "record_triplet_words_equal": a["record"] == b["record"],
            "ball_related_triplet_words_equal": a["ball"] == b["ball"],
            "current_start_triplet_words_equal": a["start"] == b["start"],
            "triplet_difference_is_ball_motion_verified": False,
        }
    return public


def _approved_bank(path, root, size):
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in (".raw", ".bin", ".mem"):
        raise ValueError("Unsupported private bank path")
    exact = path.resolve(strict=True)
    if not exact.is_relative_to(root) or exact.stat().st_size != size:
        raise ValueError("Private memory bank size/location mismatch")
    return exact


def run_local(dirs):
    """Read exact existing pairs; never writes files or talks to Dolphin."""
    root = DATA_ROOT.resolve(strict=True)
    if not root.is_dir() or len(dirs) not in (1, 2):
        raise ValueError("Canonical private data root / observation count required")
    with ExitStack() as stack:
        memories = []
        paths = []
        for folder in dirs:
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError("Invalid private pair directory")
            d = folder.resolve(strict=True)
            if not d.is_relative_to(root):
                raise ValueError("Pair must remain under ignored sibling data root")
            p1 = _approved_bank(d / "mem1.raw", root, roster.MEM1_SIZE)
            p2 = _approved_bank(d / "mem2.raw", root, roster.MEM2_SIZE)
            f1 = stack.enter_context(p1.open("rb"))
            f2 = stack.enter_context(p2.open("rb"))
            m1 = stack.enter_context(mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ))
            m2 = stack.enter_context(mmap.mmap(f2.fileno(), 0, access=mmap.ACCESS_READ))
            memories.append((m1, m2))
            paths.append((p1, p2))
        if len(paths) == 2 and paths[0] == paths[1]:
            raise ValueError("Duplicate private pair directories")
        reports = []
        for m1, m2 in memories:
            rd = roster.TwoBankReader(m1, m2)
            reports.append(analyze_one(rd.u32, rd.header()))
        equal1 = equal2 = None
        if len(memories) == 2:
            # SHA is used only for equal/different and never emitted.
            equal1 = hashlib.sha256(memories[0][0]).digest() == hashlib.sha256(memories[1][0]).digest()
            equal2 = hashlib.sha256(memories[0][1]).digest() == hashlib.sha256(memories[1][1]).digest()
        return summarize_two_pairs(reports, same_mem1=equal1, same_mem2=equal2)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first-dir", required=True, type=Path,
                   help="Existing directory containing mem1.raw and mem2.raw")
    p.add_argument("--second-dir", type=Path,
                   help="Optional second existing preserved memory pair")
    args = p.parse_args(argv)
    dirs = [args.first_dir] + ([args.second_dir] if args.second_dir else [])
    try:
        result = run_local(dirs)
    except (OSError, ValueError, TypeError, struct.error, OverflowError):
        print("Selected ball/start offline source gate failed; do not "
              "infer motion or publish private files.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
