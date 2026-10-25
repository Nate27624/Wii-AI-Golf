"""Read-only experiment-identifiability diagnostic for published HUMAN V1 labels.

Input is an iterable of already-sanitized dicts; no file or network IO, no
emulator commands, and no claims that a screen score is physical ball travel.
This supplements (never replaces) the S000 overall evidence reviewer.
"""
from __future__ import annotations
from collections import Counter
import math
import re
from typing import Any, Iterable, Mapping

SHA = re.compile(r"[0-9a-f]{64}\Z")
POSES = {"back", "center", "forward", "unknown"}
ANSWERS = {"yes", "no", "unknown"}

def _number(value: Any, lo: float, hi: float) -> float | None:
    if type(value) not in (int, float):
        return None
    v = float(value)
    return v if math.isfinite(v) and lo <= v <= hi else None

def audit_power_identifiability(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Never infer a baseline default from an absent parameter field.

    Group by explicit bridge, scene (when published), timing, waveform and
    human starting pose. Off-green 100-ft display values are penalties, never
    training targets for a physical carry-distance regression. Only explicit,
    fixed, safe fields can appear in this report.
    """
    counts = Counter()
    seen = set()
    arms = {}
    contexts = {}
    power_estimates = set()
    missing_scene = missing_scale = missing_power = False
    for record in records:
        counts["records_seen"] += 1
        if not isinstance(record, Mapping) or record.get("kind") != "v1":
            counts["non_v1_ignored"] += 1
            continue
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier or len(identifier) > 100:
            counts["invalid_v1"] += 1
            continue
        if identifier in seen:
            counts["duplicate_ids"] += 1
            continue
        seen.add(identifier)
        if (record.get("schema") != 1 or
            record.get("capture_status") != "sanitized_human_annotation_only" or
            type(record.get("process_exit_code")) is not int or
            record["process_exit_code"] != 0):
            counts["noncomparable_v1"] += 1
            continue
        human = record.get("human")
        controller = record.get("controller")
        bridge = record.get("bridge_sha256")
        if (not isinstance(human, Mapping) or not isinstance(controller, Mapping)
            or not isinstance(bridge, str) or not SHA.fullmatch(bridge)):
            counts["invalid_v1"] += 1
            continue
        trace = controller.get("trace_sha256")
        lead = controller.get("a_lead_observed_frame_delta")
        frames = controller.get("generated_trace_frames")
        pose = human.get("initial_club_pose_human")
        contact = human.get("contact_human")
        green = human.get("finished_on_green_human")
        if (not isinstance(trace, str) or not SHA.fullmatch(trace)
            or type(lead) is not int or not 0 <= lead <= 600
            or type(frames) is not int or not 1 <= frames <= 600
            or pose not in POSES or contact not in ANSWERS or green not in ANSWERS):
            counts["invalid_v1"] += 1
            continue
        scene = record.get("scenario_id")
        scene = scene if isinstance(scene, str) and re.fullmatch(
            r"[A-Za-z0-9_.-]{1,80}", scene) else None
        if scene is None:
            missing_scene = True
        scales = tuple(_number(controller.get(key), 0.01, 4) for key in
                       ("speed_scale", "backswing_scale", "motion_scale"))
        if None in scales:
            missing_scale = True
        key = (bridge, scene, lead, frames, pose, *scales, trace)
        if key not in arms:
            arms[key] = {
                "bridge_sha256": bridge, "scenario_id": scene,
                "observed_a_lead_frames": lead,
                "generated_trace_frames": frames,
                "initial_club_pose_human": pose, "speed_scale": scales[0],
                "backswing_scale": scales[1], "motion_scale": scales[2],
                "trace_sha256": trace, "trials": 0,
                "human_contact": {"yes": 0, "no": 0, "unknown": 0},
                "human_on_green_yes": 0, "human_off_green_no": 0,
                "off_green_displayed_100ft_count": 0,
                "other_human_displayed_score_count": 0,
                "human_power_estimate_count": 0,
                "human_power_estimates_percent": [],
                "missing_power_estimate_count": 0}
        arm = arms[key]
        arm["trials"] += 1
        arm["human_contact"][contact] += 1
        if green == "yes":
            arm["human_on_green_yes"] += 1
        if green == "no":
            arm["human_off_green_no"] += 1
        distance = _number(human.get("displayed_distance_human"), 0, 1000000)
        unit = human.get("displayed_unit_human")
        if distance is not None and unit in ("ft", "yd", "m"):
            if green == "no" and distance == 100 and unit == "ft":
                arm["off_green_displayed_100ft_count"] += 1
            else:
                arm["other_human_displayed_score_count"] += 1
        power = _number(human.get("displayed_power_percent_human"), 0, 100)
        if power is None:
            missing_power = True
            arm["missing_power_estimate_count"] += 1
        else:
            arm["human_power_estimate_count"] += 1
            arm["human_power_estimates_percent"].append(power)
            power_estimates.add(power)
        contexts.setdefault((bridge, scene, lead, frames, pose), set()).add((scales, trace))
        counts["eligible_human_trials"] += 1

    rows = sorted(arms.values(), key=lambda x: (x["bridge_sha256"],
        x["scenario_id"] or "", x["observed_a_lead_frames"],
        x["initial_club_pose_human"],
        tuple(-1 if x[k] is None else x[k] for k in
              ("speed_scale", "backswing_scale", "motion_scale")), x["trace_sha256"]))
    comparisons = sum(1 for (_, scene, *_), v in contexts.items()
                      if scene is not None and len(v) > 1)
    reasons = []
    if not rows:
        reasons.append("no_comparable_human_labeled_v1_trials")
    if missing_scene or (rows and comparisons == 0):
        reasons.append("no_verified_same_scene_cross_arm_comparison")
    if missing_scale:
        reasons.append("some_motion_parameters_not_published")
    if missing_power:
        reasons.append("some_power_gauge_estimates_missing")
    if len(power_estimates) < 2:
        reasons.append("no_distinct_human_power_gauge_estimates")
    if any(a["off_green_displayed_100ft_count"] for a in rows):
        reasons.append("off_green_100ft_is_penalty_not_flight_distance")
    reasons.append("no_verified_physical_power_or_carry_distance")
    return {
        "schema_version": 1, "evidence_class": "sanitized_human_report_only",
        "counts": {k: counts[k] for k in (
            "records_seen", "non_v1_ignored", "duplicate_ids", "invalid_v1",
            "noncomparable_v1", "eligible_human_trials")},
        "arms": rows,
        "observed_distinct_human_power_estimates": sorted(power_estimates),
        "same_scene_cross_arm_comparison_count": comparisons,
        "gates": {
            "power_model_identifiable": False,
            "continuous_ball_carry_measurements_available": False,
            "game_power_measurements_verified": False,
            "same_scene_cross_arm_comparison_available": comparisons > 0},
        "stop_reasons": reasons,
        "next_step": (
            "Do not regress displayed 100-ft misses on motion parameters. "
            "Record matched control repeats; have S002 verify scene identity, "
            "power source and continuous physical ball/score measurement first.")
    }
