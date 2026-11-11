"""Classify source-reviewed pin/start pointer transitions in existing S002 captures.

This is an OFFLINE, local-only co-occurrence study. Adjacent snapshots can be
separated by many emulated frames, and source member names do not prove actual
player/ball or pin movement. No raw words/pointers are returned.
"""
from __future__ import annotations

from collections import Counter
import struct
from typing import Any

from .environment_state_candidate import audit_environment_snapshots

MAX_CAPTURES = 64
BOUNDARIES = ("within_pre", "pre_to_post", "within_post",
              "post_to_settled", "within_settled")
REFERENCE_OFFSETS = {"pin": 0x44, "start": 0x50}
UI_OFFSETS = {"minimap": 0x88, "wind_arrow": 0x6C}


def _u32(raw: bytes, offset: int) -> int:
    return struct.unpack_from(">I", raw, offset)[0]


def _boundary(before: str, after: str) -> str:
    if before == after:
        return "within_" + before
    if before == "pre" and after == "post":
        return "pre_to_post"
    if before == "post" and after == "settled":
        return "post_to_settled"
    raise ValueError("Unexpected or skipped phase boundary")


def classify_one_environment_capture(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Private per-capture boolean/count details, NEVER a publication record.

    Only call with genuine S002 single-capture rows. First runs the strict
    schema/version/phase/frame/object source gate. No raw field values leave.
    """
    gated = audit_environment_snapshots(rows)
    prior: tuple[str, dict[str, int]] | None = None
    changed = {k: False for k in REFERENCE_OFFSETS}
    any_same_pair = False
    same_pair_count = 0
    ui_on_joint_pair = 0
    ui_on_nonjoint_pair = 0
    boundary_count = Counter()
    pin_count = Counter()
    start_count = Counter()
    joint_count = Counter()
    ui_count = Counter()
    for row in rows:
        raw = bytes.fromhex(row["windows"]["golf_field"]["bytes_hex"])
        current = {k: _u32(raw, offset) for k, offset in REFERENCE_OFFSETS.items()}
        current.update({k: raw[offset] for k, offset in UI_OFFSETS.items()})
        if prior is not None:
            phase, older = prior
            edge = _boundary(phase, row["phase"])
            boundary_count[edge] += 1
            pin = current["pin"] != older["pin"]
            start = current["start"] != older["start"]
            ui = any(current[k] != older[k] for k in UI_OFFSETS)
            changed["pin"] |= pin
            changed["start"] |= start
            if pin:
                pin_count[edge] += 1
            if start:
                start_count[edge] += 1
            if ui:
                ui_count[edge] += 1
            if pin and start:
                joint_count[edge] += 1
                same_pair_count += 1
                any_same_pair = True
                ui_on_joint_pair += int(ui)
            elif pin or start:
                ui_on_nonjoint_pair += int(ui)
        prior = (row["phase"], current)
    if any(changed[k] != gated["object_refs"][k]["changed_during_capture"]
           for k in REFERENCE_OFFSETS):
        raise ValueError("Pointer-change accounting mismatch")
    return {
        "pin_changed": changed["pin"],
        "start_changed": changed["start"],
        "pin_start_changed_same_pair": any_same_pair,
        "pin_start_joint_pair_count": same_pair_count,
        "ui_changed_on_joint_pair_count": ui_on_joint_pair,
        "ui_changed_on_one_sided_pair_count": ui_on_nonjoint_pair,
        "boundary_comparison_count": {b: boundary_count[b] for b in BOUNDARIES},
        "pin_change_edge_count": {b: pin_count[b] for b in BOUNDARIES},
        "start_change_edge_count": {b: start_count[b] for b in BOUNDARIES},
        "pin_start_joint_edge_count": {b: joint_count[b] for b in BOUNDARIES},
        "ui_change_edge_count": {b: ui_count[b] for b in BOUNDARIES},
        "sample_count": len(rows),
        "max_frame_span": gated["max_non_atomic_frame_span"],
    }


def summarize_phase_joint_cohort(captures: list[list[dict]]) -> dict:
    """Aggregate file-level and stage-edge counts; never report file identities."""
    if type(captures) is not list or not 2 <= len(captures) <= MAX_CAPTURES:
        raise ValueError("Require 2..64 bounded capture files")
    results = [classify_one_environment_capture(rows) for rows in captures]
    pin_files = sum(v["pin_changed"] for v in results)
    start_files = sum(v["start_changed"] for v in results)
    both_files = sum(v["pin_changed"] and v["start_changed"] for v in results)
    same_files = sum(v["pin_start_changed_same_pair"] for v in results)
    pairs = Counter()
    pin_edges = Counter()
    start_edges = Counter()
    joint_edges = Counter()
    ui_edges = Counter()
    for v in results:
        for stage in BOUNDARIES:
            pairs[stage] += v["boundary_comparison_count"][stage]
            pin_edges[stage] += v["pin_change_edge_count"][stage]
            start_edges[stage] += v["start_change_edge_count"][stage]
            joint_edges[stage] += v["pin_start_joint_edge_count"][stage]
            ui_edges[stage] += v["ui_change_edge_count"][stage]
    if any(joint_edges[k] > min(pin_edges[k], start_edges[k])
           for k in BOUNDARIES):
        raise ValueError("Inconsistent phase counts")
    return {
        "schema_version": 1, "kind": "local-golf-environment-phase-joint-cohort",
        "capture_file_count": len(results),
        "total_snapshot_count": sum(v["sample_count"] for v in results),
        "max_non_atomic_frame_span": max(v["max_frame_span"] for v in results),
        "pin_changed_file_count": pin_files,
        "start_changed_file_count": start_files,
        "both_changed_file_count": both_files,
        "pin_only_changed_file_count": pin_files - both_files,
        "start_only_changed_file_count": start_files - both_files,
        "neither_changed_file_count": len(results) - pin_files - start_files + both_files,
        "both_changed_on_same_adjacent_pair_file_count": same_files,
        "pin_start_same_pair_total": sum(v["pin_start_joint_pair_count"] for v in results),
        "ui_changed_on_joint_pair_total": sum(v["ui_changed_on_joint_pair_count"] for v in results),
        "ui_changed_on_one_sided_pair_total": sum(v["ui_changed_on_one_sided_pair_count"] for v in results),
        "phase_adjacent_pair_counts": {k: pairs[k] for k in BOUNDARIES},
        "pin_change_edge_counts": {k: pin_edges[k] for k in BOUNDARIES},
        "start_change_edge_counts": {k: start_edges[k] for k in BOUNDARIES},
        "pin_start_joint_edge_counts": {k: joint_edges[k] for k in BOUNDARIES},
        "ui_change_edge_counts": {k: ui_edges[k] for k in BOUNDARIES},
        "independent_boots_verified": False,
        "game_phase_semantics_verified": False,
        "pin_world_position_verified": False,
        "ball_world_position_verified": False,
        "pointer_change_caused_by_action_verified": False,
        "warning": ("Adjacent RAM reads are non-atomic (up to recorded maximum); "
                    "coincident pointer changes are not proof of causal action, "
                    "player/ball movement, physical pin relocation, or screen transition."),
    }
