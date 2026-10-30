#!/usr/bin/env python3
"""Offline, sanitized weak/strong visible-gauge P0 candidate falsification.

No Dolphin, controller input, raw-memory scans, capture, physics proof or training.
Input is a manually reviewed *derived* per-window hypothesis-value summary.
All human meter labels, source gates and shot labels remain claims, not proof.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

FIELDS = (
    "player_record_030", "player_record_034_byte0",
    "player_record_034_byte1", "player_record_090",
    "player_record_094", "player_record_098", "aim_03c",
    "selected_ball_030", "selected_ball_cache_cc",
    "selected_ball_cache_f0", "selected_ball_cache_fc",
)
# Explicit alternative hypotheses: do not promote easing, discrete flags,
# aim/pose trigonometry, or ball trajectory as swing-strength measurements.
ALTERNATIVES = {
    "player_record_030": "source_player_easing_or_animation",
    "player_record_034_byte0": "byte_state_flag_not_graded_power",
    "player_record_034_byte1": "byte_state_flag_not_graded_power",
    "player_record_094": "aim_or_pose_coupling",
    "player_record_098": "aim_or_pose_coupling",
}
GEOMETRY = {"aim_03c", "selected_ball_030", "selected_ball_cache_cc",
            "selected_ball_cache_f0", "selected_ball_cache_fc"}
TRIALS = ("L1", "H1", "H2", "L2")  # intentionally counterbalanced
CONTROLS = ("IDLE", "A_ONLY", "MOTION_NO_A")
WINDOWS = ("PRE", "GAUGE", "RECOVER")
TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


def _exact(x, keys, description):
    if type(x) is not dict or set(x) != set(keys):
        raise ValueError("bad " + description)


def _number(v):
    if type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e9:
        raise ValueError("unsafe or nonfinite derived candidate value")
    return float(v)


def _values(v):
    if type(v) is not dict or set(v) - set(FIELDS):
        raise ValueError("unknown or raw candidate field")
    return {k: _number(n) for k, n in v.items()}


def validate(data):
    _exact(data, ("schema_version", "kind", "origin", "revision", "trials", "controls"),
           "evidence envelope")
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["kind"] != "p0_power_visible_meter_contrast"
            or data["origin"] not in ("synthetic", "operator_reviewed")
            or data["revision"] != "RSPE01 Rev1"):
        raise ValueError("wrong provenance or version")
    trials = data["trials"]
    if type(trials) is not list or len(trials) != 4:
        raise ValueError("requires four independent low/high trials")
    shots = set()
    scenes = set()
    for index, t in enumerate(trials):
        _exact(t, ("trial", "shot_id", "scene_id", "hole_id", "actor_id",
                   "generation", "source_gated", "owner_stable",
                   "operator_precontact", "display_percent", "windows"), "trial")
        if (t["trial"] != TRIALS[index]
                or any(not isinstance(t[key], str) or not TOKEN.fullmatch(t[key])
                       for key in ("shot_id", "scene_id", "hole_id", "actor_id", "generation"))):
            raise ValueError("unqualified trial or token")
        if t["shot_id"] in shots:
            raise ValueError("cross-shot identity reused")
        shots.add(t["shot_id"])
        scenes.add((t["scene_id"], t["hole_id"], t["actor_id"]))
        if any(t[key] is not True for key in ("source_gated", "owner_stable",
                                              "operator_precontact")):
            raise ValueError("unverified source/owner or UI precontact")
        p = _number(t["display_percent"])
        if not 0 <= p <= 100:
            raise ValueError("invalid human visual gauge label")
        _exact(t["windows"], WINDOWS, "trial windows")
        for name in WINDOWS:
            w = t["windows"][name]
            _exact(w, ("span_ms", "values"), "window")
            span = _number(w["span_ms"])
            if not 0 < span <= 5000:
                raise ValueError("slow or invalid non-atomic window")
            _values(w["values"])
    if len(scenes) != 1:
        raise ValueError("scene/hole/actor changed across trials")
    for i in (0, 2):
        low, high = (trials[i], trials[i+1]) if i == 0 else (trials[i+1], trials[i])
        if _number(high["display_percent"]) - _number(low["display_percent"]) < 15:
            raise ValueError("visible meter contrast too small")
    controls = data["controls"]
    _exact(controls, CONTROLS, "negative controls")
    for name in CONTROLS:
        c = controls[name]
        _exact(c, ("source_gated", "operator_no_contact", "delta"), "control")
        if c["source_gated"] is not True or c["operator_no_contact"] is not True:
            raise ValueError("negative control not qualified")
        _values(c["delta"])
    return data


def _trial_delta(t, field):
    w = t["windows"]
    if any(field not in w[k]["values"] for k in WINDOWS):
        return None
    pre = _number(w["PRE"]["values"][field])
    peak = _number(w["GAUGE"]["values"][field])
    after = _number(w["RECOVER"]["values"][field])
    return peak-pre, after-pre


def judge_field(data, field):
    if field in GEOMETRY:
        return "GEOMETRY_OR_AIM_CONTROL", False, "Not a source-typed power variable."
    deltas = [_trial_delta(t, field) for t in data["trials"]]
    if any(d is None for d in deltas):
        return "NOT_MEASURED", False, "Collect source-gated PRE/GAUGE/RECOVER for each trial."
    if any(field not in data["controls"][c]["delta"] for c in CONTROLS):
        return "MISSING_NEGATIVE_CONTROL", False, "Include all three no-contact control deltas."
    low = [deltas[0][0], deltas[3][0]]
    high = [deltas[1][0], deltas[2][0]]
    # Magnitudes can encode inverse power; retain sign consistency explicitly.
    signs = [1 if v > 0 else -1 if v < 0 else 0 for v in low+high]
    if len(set(signs)) != 1 or 0 in signs or min(map(abs, low)) <= 1e-7:
        return "NO_REPEATED_SIGNED_RESPONSE", False, "Repeat blind low/high visual contrasts."
    if not all(abs(h) >= 1.25 * abs(l) for h, l in zip(high, low)):
        return "NOT_GRADED_IN_BOTH_PAIRS", False, "Vary amplitude independent of timing/aim."
    baseline = min(map(abs, low))
    if any(abs(deltas[i][1]) >= 0.25 * baseline for i in range(4)):
        return "PERSISTENT_AFTER_RECOVERY", False, "Separate animation/latch from power."
    if any(abs(_number(data["controls"][name]["delta"][field])) >= 0.25 * baseline
           for name in CONTROLS):
        return "NO_CONTACT_CONFOUND", False, "Exclude idle/A-only/motion-only response."
    if field in ALTERNATIVES:
        return "GRADED_BUT_ALTERNATIVE_EXPLANATION", True, ALTERNATIVES[field]
    return "REPEATABLE_GAUGE_ASSOCIATION_ONLY", True, "Prove source owner, independent units and actual game acceptance."


def review(data):
    validate(data)
    rows = []
    for field in FIELDS:
        status, graded, next_step = judge_field(data, field)
        rows.append({"candidate": field, "status": status,
                     "graded_in_two_counterbalanced_pairs": graded,
                     "next_discriminator": next_step,
                     "runtime_verified": False, "training_eligible": False})
    return {
        "kind": "sanitized_p0_power_hypothesis_review",
        "schema_version": 1, "origin": data["origin"],
        "source_gates_operator_claims_only": True,
        "human_visible_meter_not_calibrated_power": True,
        "host_window_not_guest_physics_step": True,
        "game_A_acceptance_verified": False,
        "contact_and_native_result_verified": False,
        "power_measured": False, "training_approved": False, "rows": rows,
    }


def plan():
    return {
        "kind": "p0_power_contrast_preregistered_plan", "revision": "RSPE01 Rev1",
        "trials_in_order": list(TRIALS),
        "windows_each": list(WINDOWS),
        "negative_controls": list(CONTROLS),
        "instructions": (
            "S001 operator-authorized capture only: idle/A-only/motion-without-A; "
            "four independent same-scene same-hole low/high visual meter trials "
            "L1,H1,H2,L2, sampled before and during visible meter, then recovered. "
            "Document independent visible percent and uncertain contact. Stop on "
            "unexpected scene/owner/shot change. Do not issue game input from this analyzer."
        ),
        "candidate_fields": list(FIELDS),
        "known_alternatives": ALTERNATIVES,
        "never_use_100ft_penalty_as_measured_distance": True,
        "training_approved": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence", type=Path,
                   help="private sanitized derived summary, not raw banks or JSONL")
    p.add_argument("--plan", action="store_true")
    a = p.parse_args(argv)
    if a.plan and a.evidence is None:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if a.evidence is None or a.plan:
        p.error("use --plan or --evidence PATH")
    try:
        data = json.loads(a.evidence.read_text(encoding="utf-8"))
        result = review(data)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        print('{"status":"ABSTAIN_UNQUALIFIED_POWER_EVIDENCE","training_approved":false}')
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
