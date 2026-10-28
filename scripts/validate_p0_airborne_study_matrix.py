#!/usr/bin/env python3
"""S000 P0: reconcile THREE SANITIZED S002 source-gated airborne studies.

This is an evidence consistency gate, NOT another memory reader, ball XYZ
extractor, or guest-frame synchronizer. It requires local outputs generated
by S002 #223 (base), #224 (pin), and #225 (cache) on the same B0/flight
paths. Never prints raw vectors, private locations, runtime pointers or hashes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


CACHE_TAGS = ("ball_cache_0x0cc", "ball_cache_0x0f0", "ball_cache_0x0fc")
PIN_TO_CACHE = dict(zip(("cache_cc", "cache_f0", "cache_fc"), CACHE_TAGS))
PHASE_TAGS = (("B0_stationary_original", "B0_cache_vs_ball_words_equal"),
              ("airborne_operator", "flight_cache_vs_ball_words_equal"))


class EvidenceRejected(ValueError):
    pass


def require(flag: bool):
    if not flag:
        raise EvidenceRejected("inconsistent S002 sanitized evidence")


def three(value):
    require(type(value) is int and 0 <= value <= 3)
    return value


def boolean(value):
    require(type(value) is bool)
    return value


def negative_gate(report, keys):
    for key in keys:
        require(report.get(key) is False)


def reconcile(base: dict, pin: dict, cache: dict) -> dict:
    """Strictly enforce source equivalence; never bless actual world XYZ."""
    require(all(type(d) is dict for d in (base, pin, cache)))
    require(base.get("kind") == "PRIVATE-SANITIZED-B0-VS-HUMAN-IN_FLIGHT-SOURCE-COMPARE")
    require(pin.get("kind") == "S002-B0-AIRBORNE-PIN-CONTROL-CONFOUND")
    require(cache.get("kind") == "PRIVATE-SANITIZED-INFLIGHT-BALL-CACHE-COHERENCE")
    require(all(d.get("schema_version") == 1 for d in (base, pin, cache)))
    require(base.get("game_id") == pin.get("game_id") == "RSPE01")
    require(base.get("disc_revision") == pin.get("disc_revision") == 1)
    require(base.get("golf_mode") == pin.get("mode") == 4)
    require(base.get("source_gated_both_snapshots") is True)
    require(base.get("selected_slot_and_hole_match") is True)
    require(pin.get("source_gated_both_snapshots") is True)
    require(pin.get("source_selected_slot_and_hole_stable") is True)
    require(pin.get("pin_constructor_invariants_pass_both") is True)
    require(cache.get("source_selected_slot_and_hole_match") is True)
    require(base.get("human_airborne_observed") is True)
    require(base.get("human_labeled_phases") ==
            ["B0_stationary_original", "airborne_operator"])
    negative_gate(base, ("actual_ball_world_xyz_verified", "ball_velocity_verified",
                         "impact_frame_verified", "power_ram_variable_verified",
                         "approved_for_training", "allowed_to_publish",
                         "mem1_mem2_exports_same_guest_frame_verified", "same_boot_verified"))
    negative_gate(pin, ("actual_ball_world_xyz_verified", "ball_velocity_verified",
                        "power_ram_verified", "training_approved", "allowed_to_publish",
                        "same_guest_frame_verified", "independent_same_boot_proven"))
    negative_gate(cache, ("actual_ball_world_xyz_verified",
                          "actual_velocity_or_power_verified",
                          "approved_for_training", "allowed_to_publish",
                          "same_boot_proven", "mem1_mem2_exports_same_guest_frame_verified",
                          "five_cross_phase_3_component_changes_independent_evidence"))

    src = base.get("candidate_triplet_component_checks")
    require(type(src) is dict)
    def changed(name):
        require(type(src.get(name)) is dict)
        return three(src[name].get("changed_components_between_stationary_and_airborne"))
    ball_changed = changed("ball_nested_plus_0x4c")
    start_changed = changed("source_current_start")
    require(changed("ball_object_0x030") == ball_changed)
    require(three(pin.get("ball_position_candidate_change_component_count")) == ball_changed)
    require(boolean(base.get("candidate_ball_triplet_changed_while_start_stable"))
            == (ball_changed > 0 and start_changed == 0))
    pin_change = three(pin.get("pin_changed_bitwise_components_out_of_three"))
    pin_confounded = boolean(pin.get("pin_control_confounded"))
    pin_passed = boolean(pin.get("pin_control_passed"))
    require(pin_confounded == (pin_change > 0 or not pin_passed))
    require(pin_passed == (pin_change == 0 and not pin_confounded))
    require(type(pin.get("ball_current_vs_cache_word_equality")) is dict)
    phases = cache.get("phases")
    require(type(phases) is dict and set(phases) == {p for p, _ in PHASE_TAGS})

    cache_summary = {}
    for pin_name, base_name in PIN_TO_CACHE.items():
        require(changed(base_name) ==
                three(pin["ball_current_vs_cache_word_equality"][pin_name]
                      .get("B0_to_flight_cache_changed_words")))
        matches = []
        for phase, pin_property in PHASE_TAGS:
            phase_details = phases[phase]
            require(type(phase_details) is dict)
            require(phase_details.get("source_selected_ball_alias_selfref_validated") is True)
            require(phase_details.get("actual_ball_world_xyz_verified") is False)
            require(phase_details.get("cache_role_or_semantics_verified") is False)
            pairwise = phase_details.get("pairwise_equal_component_counts")
            require(type(pairwise) is dict)
            require(three(pairwise.get(
                "ball_nested_plus_0x4c__vs__ball_object_0x030")) == 3)
            matching = three(pairwise.get(
                "ball_nested_plus_0x4c__vs__" + base_name))
            require(matching == three(
                pin["ball_current_vs_cache_word_equality"][pin_name].get(pin_property)))
            matches.append(matching)
        cache_summary[base_name] = {
            "changed_components_B0_to_airborne": changed(base_name),
            "equal_to_current_ball_components_B0": matches[0],
            "equal_to_current_ball_components_airborne": matches[1],
        }

    for i, phase in enumerate(("B0_stationary_original", "airborne_operator")):
        derived_all = all(cache_summary[name][
            "equal_to_current_ball_components_" + ("B0" if i == 0 else "airborne")] == 3
            for name in CACHE_TAGS)
        key = ("all_three_caches_equal_current_ball_within_B0" if i == 0 else
               "all_three_caches_equal_current_ball_within_airborne")
        require(boolean(cache.get(key)) == derived_all)

    require(boolean(base.get("position_confounded_by_different_start")) ==
            (start_changed > 0))
    require(type(base.get("whole_bank_differences")) is dict)
    require(all(type(base["whole_bank_differences"].get(k)) is bool
                for k in ("MEM1", "MEM2")))

    return {
        "kind": "S000-PRIVATE-SANITIZED-P0-FLIGHT-THREE-STUDY-EVIDENCE-GATE",
        "schema_version": 1,
        "three_independent_reader_outputs_consistent": True,
        "validated_readers": ["S002_223_base", "S002_224_pin", "S002_225_cache"],
        "ball_translation_changed_components": ball_changed,
        "tee_changed_components": start_changed,
        "pin_changed_components": pin_change,
        "target_control_confounded": pin_confounded,
        "cache_current_ball_word_match": cache_summary,
        "cache_all_equal_B0": cache["all_three_caches_equal_current_ball_within_B0"],
        "cache_all_equal_airborne": cache["all_three_caches_equal_current_ball_within_airborne"],
        "all_archives_shot_synchrony_independently_verified": False,
        "physical_world_xyz_verified": False,
        "vertical_velocity_verified": False,
        "model_training_allowed": False,
        "allowed_to_publish": False,
        "interpretation": (
            "Consistent source-owned bytes only. Identical cache values imply redundancy, "
            "not independent physics evidence. Changed pin/boot/frame confounds remain."
        ),
    }


def load_safe(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size < 128 * 1024)
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    require(type(value) is dict)
    return value


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, type=Path)
    p.add_argument("--pin", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = reconcile(*(load_safe(p) for p in (args.base, args.pin, args.cache)))
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            json.JSONDecodeError):
        print("P0_EVIDENCE_MATRIX=ABSTAIN_MISMATCH_OR_UNTRUSTED_REPORT",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
