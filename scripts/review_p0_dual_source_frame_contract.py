"""Pure offline P0 dual-source same-guest-frame acceptance contract.

NOT a Dolphin watcher, logger, capture reader, bridge patch, game-frame clock
validator, or physical-world-coordinate decoder. This only rejects unqualified
already-collected PRIVATE sample sequences before any semantic analysis.
No sample values, pointer identities, raw frame IDs, or shot IDs leave output.
"""
from __future__ import annotations

import json
import sys
from typing import Any

MIN_SAMPLES = 3
MAX_SAMPLES = 256
MAX_READ_US = 5000
MAX_GUEST_FRAME_GAP = 4
# Native RSPE01 MEM1/MEM2 guest address regions, not host pointers.
# Reject uncached aliases and fabricated pointers until the source owner
# establishes that exact address mapping. This is a range gate ONLY.
NATIVE_GUEST_RAM_RANGES = (
    (0x80000000, 0x81800000),  # 24 MiB MEM1
    (0x90000000, 0x94000000),  # 64 MiB MEM2
)
VECTORS = (
    "selected_ball_translation_words",
    "source_global_translation_words",
    "selected_ball_cache_cc_words",
    "pin_translation_words",
    "start_translation_words",
)
POINTERS = (
    "selected_ball_object_pointer",
    "source_global_ball_object_pointer",
    "pin_object_pointer",
    "start_object_pointer",
    "field_manager_pointer",
)
CONTEXT = (
    "boot_identity",
    "shot_identity",
    "selected_player_index",
    "hole_index",
    "selected_ball_object_pointer",
    "source_global_ball_object_pointer",
    "pin_object_pointer",
    "start_object_pointer",
    "field_manager_pointer",
    "config_bc_c0_c4_words",
    "pin_translation_words",
    "start_translation_words",
    "stage",
)


def _u32(x: object) -> bool:
    return type(x) is int and 0 <= x <= 0xFFFFFFFF


def _canonical_native_guest_pointer(x: object) -> bool:
    """Canonical 4-byte-aligned MEM1/MEM2 pointer, NOT a typed object proof."""
    return (_u32(x) and x % 4 == 0
            and any(start <= x <= end - 4
                    for start, end in NATIVE_GUEST_RAM_RANGES))


def _vector(v: object) -> tuple[int, int, int]:
    if not isinstance(v, (tuple, list)) or len(v) != 3 or not all(_u32(w) for w in v):
        raise ValueError("unqualified private vector")
    return tuple(v)


def _count_changed(a: tuple, b: tuple) -> int:
    return sum(x != y for x, y in zip(a, b))


def _checked_row(row: object) -> dict[str, Any]:
    if type(row) is not dict:
        raise ValueError("unqualified private row")
    expected = {
        "game_id", "disc_revision", "golf_scene_id", "golf_mode",
        "guest_frame_index", "guest_frame_clock_type",
        "same_callback_guest_frame_observation_attested",
        "source_selected_chain_verified", "rev1_ppc_source_gate_verified",
        "read_overhead_us", "boot_identity", "shot_identity",
        "selected_player_index", "hole_index", "stage",
        *POINTERS, *VECTORS, "config_bc_c0_c4_words",
    }
    if set(row) != expected:
        raise ValueError("unexpected private trace schema")
    if (row["game_id"] != "RSPE01" or row["disc_revision"] != 1
            or row["golf_scene_id"] != 5 or row["golf_mode"] != 4
            or row["guest_frame_clock_type"] != "machine_guest_physics_frame"
            or row["same_callback_guest_frame_observation_attested"] is not True
            or row["source_selected_chain_verified"] is not True
            or row["rev1_ppc_source_gate_verified"] is not True):
        raise ValueError("unqualified source/frame clock")
    if (not _u32(row["guest_frame_index"])
            or type(row["read_overhead_us"]) is not int
            or not 0 <= row["read_overhead_us"] <= MAX_READ_US
            or type(row["selected_player_index"]) is not int
            or not 0 <= row["selected_player_index"] <= 3
            or type(row["hole_index"]) is not int
            or not 0 <= row["hole_index"] <= 8
            or row["stage"] not in ("idle_control", "shot_observation")):
        raise ValueError("unqualified frame, source, or budget")
    for key in ("boot_identity", "shot_identity"):
        if type(row[key]) is not str or not 1 <= len(row[key]) <= 128:
            raise ValueError("missing frame provenance identity")
    for key in POINTERS:
        if not _canonical_native_guest_pointer(row[key]):
            raise ValueError("missing bounded canonical source-object identity")
    for key in (*VECTORS, "config_bc_c0_c4_words"):
        _vector(row[key])
    return row


def summarize_private_samples(samples: list[dict]) -> dict:
    """Return categorical relations only. Does not authenticate attestations."""
    if type(samples) is not list or not MIN_SAMPLES <= len(samples) <= MAX_SAMPLES:
        raise ValueError("unqualified sample count")
    rows = [_checked_row(r) for r in samples]
    first = rows[0]
    for row in rows[1:]:
        if any(row[key] != first[key] for key in CONTEXT):
            raise ValueError("source object, pin/start or config changed")
    frames = [r["guest_frame_index"] for r in rows]
    if any(not 1 <= b - a <= MAX_GUEST_FRAME_GAP
           for a, b in zip(frames, frames[1:])):
        raise ValueError("guest frame sequence not bounded/monotonic")
    for key in POINTERS:
        if first[key] == 0:
            raise ValueError("invalid source pointer")
    alias = [
        r["source_global_ball_object_pointer"] ==
        r["selected_ball_object_pointer"] for r in rows
    ]
    if any(a != alias[0] for a in alias):
        raise ValueError("source object identity alias changed")
    # The original seven source-gated captures independently establish
    # that source-global and player-selected refer to DIFFERENT ball
    # objects. Consistently aliasing them is not a valid dual-object trace.
    # This gate is only a relationship check, not renderer identification.
    if alias[0]:
        raise ValueError("source-global and selected ball must be distinct")
    sel = [_vector(r[VECTORS[0]]) for r in rows]
    glob = [_vector(r[VECTORS[1]]) for r in rows]
    cc = [_vector(r[VECTORS[2]]) for r in rows]
    # These are bitwise source-object words, NOT proven physical positions.
    # A shot-labeled cohort with no source-object or cache change carries
    # no movement evidence; do not silently accept it as a shot observation.
    candidate_change_observed = any(
        a != b for series in (sel, glob, cc)
        for a, b in zip(series, series[1:])
    )
    if first["stage"] == "idle_control":
        if (any(x != sel[0] for x in sel[1:])
                or any(x != glob[0] for x in glob[1:])
                or any(x != cc[0] for x in cc[1:])):
            raise ValueError("source objects not stationary in idle control")
    elif not candidate_change_observed:
        raise ValueError("shot observation has no changing source ball candidates")
    return {
        "kind": "P0-DUAL-SOURCE-FRAME-TRACE-CONTRACT-REVIEW-ONLY",
        "accepted_for_offline_relationship_review": True,
        "sample_count": len(rows),
        "declared_stage": first["stage"],
        "candidate_vector_change_observed": candidate_change_observed,
        "candidate_change_proves_rendered_ball_motion": False,
        "max_observed_read_overhead_under_5ms": True,
        "selected_global_object_pointers_distinct": not alias[0],
        "source_global_equals_selected_current_components_per_sample":
            [3 - _count_changed(a, b)
             for a, b in zip(sel, glob)],
        "source_global_equals_selected_cc_components_per_sample":
            [3 - _count_changed(a, b) for a, b in zip(glob, cc)],
        "selected_ball_changed_components_per_transition":
            [_count_changed(a, b) for a, b in zip(sel, sel[1:])],
        "global_object_changed_components_per_transition":
            [_count_changed(a, b) for a, b in zip(glob, glob[1:])],
        "cache_cc_changed_components_per_transition":
            [_count_changed(a, b) for a, b in zip(cc, cc[1:])],
        "frame_indices_externally_attested_not_independently_verified": True,
        "actual_guest_physics_time_verified_by_analyzer": False,
        "rendered_ball_object_identity_verified": False,
        "actual_ball_world_xyz_verified": False,
        "velocity_verified": False,
        "impact_verified": False,
        "power_verified": False,
        "score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def main() -> int:
    # Deliberately no --input/--live mode: downstream owner must explicitly
    # wire reviewed private samples in-process after source and timing approval.
    print(json.dumps({
        "kind": "P0-DUAL-SOURCE-FRAME-TRACE-CONTRACT-DRY-RUN",
        "private_samples_read": 0,
        "emulator_contacted": False,
        "source_global_and_selected_objects_must_be_separately_observed": True,
        "source_owner_live_capture_approved": False,
        "training_approved": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
