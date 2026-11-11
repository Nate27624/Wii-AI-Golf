"""Read-only S002 phase-memory to S003 swing-power evidence bridge.

Only sanitized public aggregate data is accepted. Do not infer power, physical
carry, club identity, or same-run correspondence from timestamps or RAM changes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import math
import re

MEMORY_KIND = "golf-memory-phase-differential"
MEMORY_STUDY = "S002-GOLF-MEMORY-PHASES"
_ID = re.compile(r"[A-Za-z0-9_.-]{1,90}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OFFSET = re.compile(r"\+0x([0-9A-Fa-f]{1,5})\Z")
_ALLOWED_PHASES = {"idle", "aim_only", "a_hold", "club_motion", "shot_attempt",
                   "settled", "pre", "post"}
_ALLOWED_OBSERVATIONS = {"unchanged", "camera_moved", "club_moved", "ball_hit",
                         "no_contact", "unknown"}
_BOUNDS = {"golf_config": 0x1C74, "golf_field": 0xA8,
           "sports_sequence": 0xD0, "minimap_ball_effect": 0x200,
           "minimap_player_effect": 0x200, "minimap_shot_line_effect": 0x200}
_RENDER = {"minimap_ball_effect", "minimap_player_effect",
           "minimap_shot_line_effect"}


def _number(value: object) -> float | None:
    if type(value) not in (float, int):
        return None
    try:
        x = float(value)
    except (ValueError, OverflowError):
        return None
    return x if math.isfinite(x) else None


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID.fullmatch(value))


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _validate_memory(report: Mapping) -> tuple[list[tuple], str | None]:
    """Check the existing S002 summary and return only safe relative facts."""
    if (report.get("kind") != MEMORY_KIND or report.get("study_id") != MEMORY_STUDY
            or type(report.get("schema_version")) is not int
            or report.get("schema_version") != 1 or not _valid_id(report.get("id"))):
        return [], "invalid_memory_record_identity"
    if (report.get("scope") not in ("focused", "broad")
            or not _integer(report.get("sample_count"), 2, 240)
            or not _integer(report.get("changed_word_count"), 0, 10000)):
        return [], "invalid_capture_size_or_scope"
    span = _number(report.get("max_non_atomic_frame_span"))
    if span is None or not 0 <= span <= 100000:
        return [], "invalid_non_atomic_span"
    phases = report.get("phase_sample_counts")
    if (not isinstance(phases, Mapping) or len(phases) > len(_ALLOWED_PHASES)
            or not phases or any(p not in _ALLOWED_PHASES or
                              not _integer(n, 1, 240) for p, n in phases.items())
            or sum(phases.values()) != report["sample_count"]):
        return [], "invalid_phase_counts"
    if report.get("confirmed_power_address") is not False:
        return [], "untrusted_power_address_claim"
    rows = report.get("top_changed_relative_words")
    if (not isinstance(rows, list) or len(rows) > 300
            or len(rows) > report["changed_word_count"]):
        return [], "invalid_candidate_list"
    seen: set[tuple[str, int]] = set()
    safe = []
    for row in rows:
        if not isinstance(row, Mapping):
            return [], "invalid_candidate"
        region, relative = row.get("region"), row.get("relative_offset")
        match = _OFFSET.fullmatch(relative) if isinstance(relative, str) else None
        if not isinstance(region, str) or region not in _BOUNDS or match is None:
            return [], "invalid_region_or_offset"
        offset = int(match.group(1), 16)
        if offset % 4 or offset >= _BOUNDS[region] or (region, offset) in seen:
            return [], "unaligned_out_of_bounds_or_duplicate_offset"
        seen.add((region, offset))
        counts = tuple(row.get(k) for k in ("within_phase_changes",
                        "at_phase_boundary_changes", "pointer_like_changes",
                        "float_like_changes"))
        if not all(_integer(k, 0, 239) for k in counts):
            return [], "invalid_change_counts"
        within, boundary, pointer, floatlike = counts
        if (within + boundary > report["sample_count"] - 1
                or pointer > within + boundary or floatlike > within + boundary):
            return [], "inconsistent_change_counts"
        safe.append((region, offset, within, boundary, pointer, floatlike))
    obs = report.get("human_observations", [])
    if (not isinstance(obs, list) or len(obs) > 12
            or any(not isinstance(x, Mapping)
                   or x.get("phase") not in _ALLOWED_PHASES
                   or x.get("observation") not in _ALLOWED_OBSERVATIONS
                   or not _integer(x.get("stage"), 0, 5) for x in obs)):
        return [], "invalid_stage_observations"
    return safe, None


def _link_reason(memory: Mapping, swings: Mapping[str, Mapping]) -> str | None:
    """Require an explicit same-run and same-frame contract; never time-join.

    These are PROPOSED future S002 fields, absent from current S002 PR #116.
    """
    swing_id = memory.get("linked_swing_observation_id")
    if not _valid_id(swing_id):
        return "missing_explicit_same_run_link"
    shot = swings.get(swing_id)
    if shot is None:
        return "linked_swing_not_found_or_ambiguous"
    if (shot.get("schema") != 1 or shot.get("kind") != "v1"
            or type(shot.get("process_exit_code")) is not int
            or shot.get("process_exit_code") != 0):
        return "swing_record_not_validated"
    controller, human = shot.get("controller"), shot.get("human")
    if not isinstance(controller, Mapping) or not isinstance(human, Mapping):
        return "swing_controller_or_human_missing"
    if (not _valid_sha(memory.get("bridge_sha256"))
            or memory["bridge_sha256"] != shot.get("bridge_sha256")
            or not _valid_sha(memory.get("trace_sha256"))
            or memory["trace_sha256"] != controller.get("trace_sha256")):
        return "bridge_or_trace_mismatch"
    scene = memory.get("scenario_id")
    if not _valid_id(scene) or scene != shot.get("scenario_id"):
        return "missing_or_different_verified_scene_id"
    if (not _integer(memory.get("a_lead_observed_frame_delta"), 0, 600)
            or memory["a_lead_observed_frame_delta"] !=
            controller.get("a_lead_observed_frame_delta")):
        return "a_lead_mismatch"
    if human.get("initial_club_pose_human") not in ("back", "center", "forward"):
        return "unknown_initial_club_pose"
    if human.get("contact_human") not in ("yes", "no", "unknown"):
        return "missing_contact_provenance"
    start = memory.get("shot_start_frame_before_controller_trace")
    first, last = memory.get("capture_frame_min"), memory.get("capture_frame_max")
    if (not _integer(start, 0, 10000000000)
            or type(human.get("shot_start_frame_before_controller_trace")) is not int
            or start != human["shot_start_frame_before_controller_trace"]
            or not _integer(first, 0, 10000000000)
            or not _integer(last, 0, 10000000000)
            or not first <= start <= last
            or memory.get("phase_sample_counts", {}).get("shot_attempt", 0) < 1):
        return "no_proven_shot_frame_coverage"
    # Even a valid metadata join does NOT decode memory values or game power.
    return None


def review_memory_power_evidence(memory_summaries: Iterable[Mapping],
                                 swing_observations: Iterable[Mapping],
                                 *, max_records: int = 240,
                                 max_frame_span_for_timing: int = 5) -> dict:
    """Summarize candidate region recurrence, link gaps and next probe.

    Only existing S002 sanitized aggregate words are admitted; the absence of
    per-offset phase-specific changes and a decoded golfer address means the
    resulting shortlist is always exploratory, never a power predictor.
    """
    if (not _integer(max_records, 1, 1000)
            or not _integer(max_frame_span_for_timing, 0, 1000)):
        raise ValueError("invalid report limits")
    memory, shots = list(memory_summaries), list(swing_observations)
    if len(memory) > max_records or len(shots) > max_records:
        raise ValueError("too many records")
    shot_id_counts = Counter(x.get("id") for x in shots if isinstance(x, Mapping)
                             and _valid_id(x.get("id")))
    swing_lookup = {x["id"]: x for x in shots if isinstance(x, Mapping)
                    and _valid_id(x.get("id")) and shot_id_counts[x["id"]] == 1}
    memory_id_counts = Counter(x.get("id") for x in memory if isinstance(x, Mapping)
                               and _valid_id(x.get("id")))
    invalid, failed_link = Counter(), Counter()
    phase_timing_uncertain = phase_labeled = accepted = linked = 0
    candidates = defaultdict(lambda: {"runs": 0, "within": 0, "boundary": 0,
                                       "pointer_like": 0, "float_like": 0})
    for record in memory:
        if not isinstance(record, Mapping):
            invalid["not_an_object"] += 1
            continue
        ident = record.get("id")
        if _valid_id(ident) and memory_id_counts[ident] > 1:
            invalid["duplicate_memory_id"] += 1
            continue
        rows, reason = _validate_memory(record)
        if reason is not None:
            invalid[reason] += 1
            continue
        accepted += 1
        if record["max_non_atomic_frame_span"] > max_frame_span_for_timing:
            phase_timing_uncertain += 1
        obs = record.get("human_observations", [])
        if any(x["phase"] in ("club_motion", "shot_attempt") for x in obs):
            phase_labeled += 1
        if (link_reason := _link_reason(record, swing_lookup)) is not None:
            failed_link[link_reason] += 1
        else:
            linked += 1
        for region, offset, within, boundary, pointer, floatlike in rows:
            item = candidates[(region, offset)]
            item["runs"] += 1
            item["within"] += within
            item["boundary"] += boundary
            item["pointer_like"] += pointer
            item["float_like"] += floatlike
    ranking = []
    for (region, offset), stats in candidates.items():
        group = ("minimap_rendering_negative_control" if region in _RENDER else
                 "source_documented_non_golfer_window")
        ranking.append({"region": region, "relative_offset": f"+0x{offset:X}",
                        "candidate_class": group,
                        "independent_capture_runs": stats["runs"],
                        "within_phase_changes": stats["within"],
                        "phase_boundary_changes": stats["boundary"],
                        "pointer_like_changes": stats["pointer_like"],
                        "float_like_changes": stats["float_like"],
                        "verified_power_signal": False})
    ranking.sort(key=lambda x: (-x["independent_capture_runs"],
                                -x["within_phase_changes"], x["region"],
                                int(x["relative_offset"][3:], 16)))
    if accepted == 0:
        next_step = ("S002 offline: produce source-gated phase summaries from existing "
                     "private captures; no new live swings.")
    elif linked == 0:
        next_step = ("S002/S003: design explicit same-run observation-ID, scene, bridge, "
                     "trace and A-lead provenance; current summaries cannot join to "
                     "shot power by timestamp.")
    else:
        next_step = ("S002: publish per-offset changes separated by idle/aim-only/A-hold/"
                     "club-motion, verify golfer-owner pointer chain "
                     "(RPGolScene +0x9C -> RPGolMain) before targeting power.")
    return {
        "schema_version": 1, "kind": "memory-power-evidence-review",
        "memory_summaries_received": len(memory),
        "valid_memory_summaries": accepted, "linked_same_run_pairs": linked,
        "unlinked_or_refused_pairs": accepted - linked,
        "memory_rejection_reasons": dict(sorted(invalid.items())),
        "link_refusal_reasons": dict(sorted(failed_link.items())),
        "non_atomic_timing_unreliable_runs": phase_timing_uncertain,
        "club_or_shot_stage_labeled_runs": phase_labeled,
        "candidate_relative_words": ranking[:60],
        "candidate_list_is_exploratory": True,
        "per_offset_negative_control_discrimination_available": False,
        "verified_golfer_state_field": False,
        "verified_swing_power_field": False, "training_ready": False,
        "predicted_swing_power": None, "next_research_action": next_step,
        "warning": ("No verified memory-to-power mapping. Only within-run relative "
                    "word-change counts, not numeric game power, impact frame or "
                    "physical carry. Off-green 100ft is a penalty, not ball travel.")
    }
