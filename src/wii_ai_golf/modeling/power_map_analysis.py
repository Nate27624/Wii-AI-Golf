"""S003 read-only analysis of the preregistered, human-labeled V1 power map.

No emulator, filesystem, network, CLI, or score-extraction side effects.
The caller supplies the canonical schedule; this module never owns a second one.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import math
import re

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CAPTURE_SOURCES = frozenset({"sanitized_human_annotation_only",
                              "human_fallback_after_missing_collector_summary"})


def _number(value: object) -> float | None:
    if type(value) not in (int, float):  # bool is NOT a measurement
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def _same_number(value: object, expected: float) -> bool:
    observed = _number(value)
    return observed is not None and math.isclose(observed, expected, abs_tol=1e-9, rel_tol=0)


def _wilson_95(yes: int, total: int) -> dict | None:
    """Descriptive 95% Wilson score interval for explicitly known binary labels."""
    if not total:
        return None
    z = 1.959963984540054
    p = yes / total
    denom = 1.0 + z * z / total
    middle = (p + z * z / (2.0 * total)) / denom
    radius = z * math.sqrt((p * (1 - p) + z * z / (4.0 * total)) / total) / denom
    return {"rate": round(p, 4), "lower": round(max(0.0, middle - radius), 4),
            "upper": round(min(1.0, middle + radius), 4), "n": total}


def analyze_power_map(
    records: Iterable[Mapping],
    schedule: Sequence[tuple[float, float]],
    *,
    study_id: str,
    expected_bridge_sha256: str,
    required_pose: str = "back",
    required_a_lead_frames: int = 45,
    required_trace_frames: int = 89,
) -> dict:
    """Return a JSON-safe evidence summary without treating penalties as distances.

    The schedule is the single, already-registered trial-index -> (speed,
    backswing) mapping supplied by the canonical study owner. Duplicate trial
    indices invalidate ALL records at that index rather than silently choosing
    a convenient repeat. Missing/failed/unknown observations are never misses.

    This measures only human labels; it cannot verify a game score, infer
    physical carry, or justify a learned response surface.
    """
    if (not isinstance(study_id, str) or not study_id
            or not isinstance(expected_bridge_sha256, str)
            or not _SHA256.fullmatch(expected_bridge_sha256)
            or required_pose not in {"back", "center", "forward"}
            or type(required_a_lead_frames) is not int or required_a_lead_frames < 0
            or type(required_trace_frames) is not int or required_trace_frames < 1):
        raise ValueError("invalid preregistered study requirements")
    if not schedule:
        raise ValueError("schedule must not be empty")
    plan = []
    for pair in schedule:
        if len(pair) != 2:
            raise ValueError("schedule entries must be (speed, backswing)")
        speed, back = (_number(x) for x in pair)
        if speed is None or back is None or speed <= 0 or back <= 0:
            raise ValueError("non-finite or non-positive schedule setting")
        plan.append((speed, back))

    matches: dict[int, list[Mapping]] = {}
    unindexed = 0
    other_studies = 0
    for record in records:
        if not isinstance(record, Mapping):
            unindexed += 1
            continue
        if record.get("study_id") != study_id:
            other_studies += 1
            continue
        idx = record.get("trial_index")
        if type(idx) is not int or not 1 <= idx <= len(plan):
            unindexed += 1
            continue
        matches.setdefault(idx, []).append(record)

    duplicates = sorted(i for i, rows in matches.items() if len(rows) > 1)
    missing = [i for i in range(1, len(plan) + 1) if i not in matches]
    rejected: list[dict] = []
    summaries: dict[tuple[float, float], dict] = {}
    for pair, planned in Counter(plan).items():
        summaries[pair] = {"speed_scale": pair[0], "backswing_scale": pair[1],
                           "planned": planned, "eligible": 0,
                           "contact_yes": 0, "contact_no": 0, "contact_unknown": 0,
                           "green_yes": 0, "green_no": 0, "green_unknown": 0,
                           "off_green_penalty_labels": 0,
                           "human_on_green_displayed_ft": [],
                           "human_power_estimates_percent": []}

    for idx in sorted(matches):
        pair = plan[idx - 1]
        row = summaries[pair]
        if idx in duplicates:
            rejected.append({"trial_index": idx, "reason": "duplicate_trial_index"})
            continue
        record = matches[idx][0]
        controller = record.get("controller")
        human = record.get("human")
        reason = None
        if (record.get("schema") != 1 or record.get("kind") != "v1"
                or record.get("trial_count") != len(plan)):
            reason = "study_schema_or_count_mismatch"
        elif (record.get("bridge_sha256") != expected_bridge_sha256
              or record.get("capture_status") not in _CAPTURE_SOURCES):
            reason = "unmatched_bridge_or_capture_provenance"
        elif (not _same_number(record.get("requested_a_lead_frames"), required_a_lead_frames)
              or not _same_number(record.get("requested_motion_scale"), 1.0)
              or not _same_number(record.get("requested_speed_scale"), pair[0])
              or not _same_number(record.get("requested_backswing_scale"), pair[1])):
            reason = "requested_trace_deviates_from_plan"
        elif not isinstance(controller, Mapping) or not isinstance(human, Mapping):
            reason = "missing_human_or_controller_evidence"
        elif (not _same_number(controller.get("a_lead_observed_frame_delta"),
                               required_a_lead_frames)
              or not _same_number(controller.get("generated_trace_frames"),
                                  required_trace_frames)
              or not isinstance(controller.get("trace_sha256"), str)
              or not _SHA256.fullmatch(controller["trace_sha256"])):
            reason = "missing_or_unmatched_observed_trace"
        elif any(k in controller and not _same_number(controller[k], val)
                 for k, val in (("speed_scale", pair[0]), ("backswing_scale", pair[1]),
                                ("motion_scale", 1.0))):
            reason = "controller_requested_setting_conflict"
        elif human.get("initial_club_pose_human") != required_pose:
            reason = "initial_pose_not_comparable"
        elif record.get("process_exit_code") != 0:
            reason = "process_failed_outcome_unknown"
        if reason:
            rejected.append({"trial_index": idx, "reason": reason})
            continue

        row["eligible"] += 1
        contact = human.get("contact_human")
        contact = contact if contact in ("yes", "no") else "unknown"
        row["contact_" + contact] += 1
        green = human.get("finished_on_green_human")
        green = green if green in ("yes", "no") else "unknown"
        row["green_" + green] += 1
        score = _number(human.get("displayed_distance_human"))
        unit = human.get("displayed_unit_human")
        if green == "no" and score == 100.0 and unit == "ft":
            row["off_green_penalty_labels"] += 1
        # On-green game display is target proximity, NOT physical carry;
        # never include 100ft off-green scores in continuous measurement.
        if green == "yes" and score is not None and score >= 0 and unit == "ft":
            row["human_on_green_displayed_ft"].append(score)
        power = _number(human.get("displayed_power_percent_human"))
        if power is not None and 0 <= power <= 100:
            row["human_power_estimates_percent"].append(power)

    conditions = []
    for pair, row in summaries.items():
        contact_known = row["contact_yes"] + row["contact_no"]
        green_known = row["green_yes"] + row["green_no"]
        row["contact_wilson_95"] = _wilson_95(row["contact_yes"], contact_known)
        row["green_wilson_95"] = _wilson_95(row["green_yes"], green_known)
        # Suppress the raw numeric samples: the output remains a compact,
        # allowlisted summary with no unverified pseudo-distance dataset.
        row["human_on_green_displayed_ft_count"] = len(row.pop("human_on_green_displayed_ft"))
        powers = row.pop("human_power_estimates_percent")
        row["human_power_estimates_count"] = len(powers)
        row["human_power_mean_percent"] = (round(sum(powers) / len(powers), 3)
                                           if powers else None)
        conditions.append(row)

    # Intentionally conservative: 2/condition provides exploratory rates only,
    # and these records never independently verify game score/carry.
    contact_eligible = sum(x["eligible"] for x in conditions)
    return {"study_id": study_id, "planned_attempts": len(plan),
            "observed_study_records": sum(len(x) for x in matches.values()) + unindexed,
            "ignored_other_study_records": other_studies,
            "missing_indices": missing, "duplicate_indices": duplicates,
            "unindexed_study_records": unindexed,
            "excluded_trials": rejected, "eligible_attempts": contact_eligible,
            "conditions": conditions,
            "exploratory_contact_comparison_ready": all(
                x["contact_yes"] + x["contact_no"] >= 3 for x in conditions),
            "verified_game_score_count": 0,
            "physical_carry_measurement_count": 0,
            "power_response_identified": False,
            "interpretation": "Human-labeled contact/green rates only; off-green 100ft is a penalty, not carry; on-green display is not carry; no validated score or power model."}
