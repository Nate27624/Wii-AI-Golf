"""S001/S002/S003 offline gate for frame-linked RAM and human-observed swings.

Accepts sanitized dictionaries only. No Dolphin, raw RAM, I/O or publication.
The proposed linkage fields are NOT emitted by the current collectors.
No output constitutes a verified game power / ball carry measurement.
"""
from __future__ import annotations
from collections.abc import Mapping
import re
from typing import Any

SHA = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[A-Za-z0-9_-]{1,90}\Z")
SCENE = re.compile(r"[A-Za-z0-9_.-]{1,80}\Z")
REGIONS = frozenset(("golf_config", "golf_field", "sports_sequence",
                     "minimap_ball_effect", "minimap_player_effect",
                     "minimap_shot_line_effect"))
DANGEROUS_ROLES = frozenset(("game_mode", "current_hole", "sport", "sequence",
                             "training_game", "golf_final_hole", "golf_mode",
                             "hole_score_storage", "golf_score_storage"))
NEGATIVE_PHASES = ("idle", "aim_only", "a_hold")
POSITIVE_PHASES = ("club_motion", "shot_attempt")
ALLOWED_PHASES = frozenset((*NEGATIVE_PHASES, *POSITIVE_PHASES, "settled"))
MAX_ROWS = 300


def _sha(v: Any) -> bool:
    return type(v) is str and SHA.fullmatch(v) is not None


def _small_id(v: Any) -> bool:
    return type(v) is str and ID.fullmatch(v) is not None


def _frame(v: Any) -> bool:
    return type(v) is int and 0 <= v <= 2_000_000_000


def _link(memory: Mapping, swing: Mapping) -> list[str]:
    reasons: list[str] = []
    if memory.get("kind") != "golf-memory-phase-differential" or memory.get("schema_version") != 1:
        reasons.append("unsupported_memory_summary_schema")
    if swing.get("kind") != "v1" or swing.get("schema") != 1:
        reasons.append("unsupported_swing_summary_schema")
    mid, sid = memory.get("id"), swing.get("id")
    if not _small_id(mid) or not _small_id(sid):
        reasons.append("missing_or_invalid_public_record_id")
    m, s = memory.get("linkage"), swing.get("linkage")
    if not isinstance(m, Mapping) or not isinstance(s, Mapping):
        reasons.append("no_mutual_same_shot_linkage")
        return reasons
    if m.get("swing_id") != sid or s.get("memory_id") != mid:
        reasons.append("nonreciprocal_same_shot_ids")
    for key in ("session_id", "scene_fingerprint"):
        a, b = m.get(key), s.get(key)
        pattern = ID if key == "session_id" else SCENE
        if not (type(a) is str and pattern.fullmatch(a) and a == b):
            reasons.append("missing_or_mismatched_" + key)
    for key in ("bridge_sha256", "trace_sha256"):
        a, b = m.get(key), s.get(key)
        if not _sha(a) or a != b:
            reasons.append("missing_or_mismatched_" + key)
    controller = swing.get("controller")
    if not isinstance(controller, Mapping) or not _sha(controller.get("trace_sha256")):
        reasons.append("missing_swing_waveform_provenance")
    elif controller["trace_sha256"] != s.get("trace_sha256"):
        reasons.append("swing_waveform_linkage_conflict")
    if swing.get("bridge_sha256") != s.get("bridge_sha256"):
        reasons.append("swing_bridge_linkage_conflict")
    if memory.get("game_id") != "RSPE01" or memory.get("disc_revision") != 1:
        reasons.append("memory_game_revision_not_explicitly_validated")
    if memory.get("game_mode_raw") != 4:
        reasons.append("memory_hitting_green_mode_not_explicitly_validated")
    if not _frame(m.get("shot_start_frame")) or m.get("shot_start_frame") != s.get("shot_start_frame"):
        reasons.append("missing_or_mismatched_shot_start_frame")
    human = swing.get("human")
    if not isinstance(human, Mapping) or human.get("shot_start_frame_before_controller_trace") != s.get("shot_start_frame"):
        reasons.append("missing_original_swing_frame_anchor")
    if memory.get("scope") not in ("focused", "broad"):
        reasons.append("unknown_memory_window_scope")
    span = memory.get("max_non_atomic_frame_span")
    if not _frame(span) or span > 3:
        reasons.append("slow_or_unknown_non_atomic_ram_read")

    brackets = memory.get("phase_frame_brackets")
    if not isinstance(brackets, list) or not brackets or len(brackets) > 240:
        reasons.append("no_phase_specific_frame_brackets")
    else:
        start = s.get("shot_start_frame")
        length = controller.get("generated_trace_frames") if isinstance(controller, Mapping) else None
        if not _frame(start) or type(length) is not int or not 1 <= length <= 600:
            reasons.append("missing_swing_trace_frame_budget")
        else:
            good = set()
            for bracket in brackets:
                if not isinstance(bracket, Mapping):
                    reasons.append("invalid_phase_frame_bracket")
                    break
                phase, a, b = (bracket.get(k) for k in ("phase", "frame_start", "frame_end"))
                if phase not in ALLOWED_PHASES or not _frame(a) or not _frame(b) or b < a or b - a > 3:
                    reasons.append("invalid_phase_frame_bracket")
                    break
                if phase in POSITIVE_PHASES and a < start + length and b >= start:
                    good.add(phase)
            if not good:
                reasons.append("no_memory_samples_overlap_swing_window")
    return reasons


def _candidate(row: Mapping) -> dict | None:
    region, offset = row.get("region"), row.get("relative_offset")
    if region not in REGIONS or type(offset) is not str or re.fullmatch(r"\+0x[0-9A-F]{1,4}", offset) is None:
        return None
    stats = row.get("phase_change_counts")
    if not isinstance(stats, Mapping) or set(stats) - ALLOWED_PHASES:
        return None
    safe = {}
    for phase in ALLOWED_PHASES:
        v = stats.get(phase, 0)
        if type(v) is not int or not 0 <= v <= 240:
            return None
        safe[phase] = v
    motion = sum(safe[x] for x in POSITIVE_PHASES)
    negative = sum(safe[x] for x in NEGATIVE_PHASES)
    if not motion:
        return None
    role = row.get("documented_role")
    visual = region.startswith("minimap_") or role == "minimap_rendering_unknown"
    structural = role in DANGEROUS_ROLES or (type(role) is str and role.endswith("_pointer"))
    return {"region": region, "relative_offset": offset,
            "motion_phase_changes": motion, "negative_control_changes": negative,
            "settled_changes": safe["settled"],
            "priority": "visual_or_structural_control" if visual or structural else (
                "test_with_repeated_controls" if negative == 0 else "negative_control_sensitive"),
            "evidence_type": "exploratory_offset_change_not_identified_power"}


def assess_memory_swing_link(memory: Mapping, swing: Mapping) -> dict:
    """Gate one same-shot cross-agent pair; do not expose raw values."""
    if not isinstance(memory, Mapping) or not isinstance(swing, Mapping):
        raise TypeError("expected already-sanitized memory and swing mappings")
    reasons = _link(memory, swing)
    human = swing.get("human")
    if not isinstance(human, Mapping) or human.get("contact_human") not in ("yes", "no", "unknown"):
        reasons.append("human_contact_label_missing")
    if not isinstance(human, Mapping) or human.get("initial_club_pose_human") not in ("back", "center", "forward", "unknown"):
        reasons.append("initial_club_pose_missing")
    if swing.get("process_exit_code") != 0:
        reasons.append("incomplete_swing_run")
    candidates = memory.get("top_changed_relative_words")
    if not isinstance(candidates, list) or len(candidates) > MAX_ROWS:
        reasons.append("missing_or_oversized_sanitized_offset_list")
        candidates = []
    if memory.get("candidate_list_truncated") is True:
        reasons.append("candidate_list_truncated")
    with_phase_counts = any(isinstance(row, Mapping) and
                            isinstance(row.get("phase_change_counts"), Mapping)
                            for row in candidates)
    if not with_phase_counts:
        reasons.append("no_per_offset_phase_change_counts")
    linked = not any(r for r in reasons if r not in (
        "no_per_offset_phase_change_counts", "candidate_list_truncated"))
    ranked = []
    if linked and with_phase_counts:
        ranked = [v for item in candidates if isinstance(item, Mapping)
                  if (v := _candidate(item)) is not None]
        ranked.sort(key=lambda x: (
            x["priority"] != "test_with_repeated_controls",
            -x["motion_phase_changes"], x["negative_control_changes"],
            x["region"], int(x["relative_offset"][3:], 16)))
    return {
        "schema_version": 1,
        "evidence_class": "human_labeled_non_atomic_ram_candidate_triage_only",
        "mutually_linked_trial": linked,
        "phase_specific_candidate_count": len(ranked),
        "candidate_priorities": ranked[:40],
        "blockers": sorted(set(reasons)),
        "power_address_verified": False,
        "game_accepted_a_state_verified": False,
        "physical_ball_carry_verified": False,
        "game_power_calibrated": False,
        "next_step": (
            "S001/S002 owners: record same-run IDs and bounded emulator-frame "
            "anchors, then add phase-specific relative-offset counts and "
            "independent idle/aim/A-hold/failed-hit controls. Do not infer "
            "physical power from off-green penalty scores or RPC ACKs."),
    }
