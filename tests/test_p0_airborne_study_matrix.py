"""No-Dolphin synthetic three-study evidence agreement gates."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / "scripts/validate_p0_airborne_study_matrix.py"
spec = importlib.util.spec_from_file_location("p0_study_matrix", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(*, pin_diff=3, cache_diffs=(3, 3, 3), matches_b0=(3,3,3),
            matches_flight=(0,1,2), ball_diff=3):
    names = mod.CACHE_TAGS
    checks = {name: {"changed_components_between_stationary_and_airborne": count}
              for name, count in zip(names, cache_diffs)}
    checks.update({
        "ball_nested_plus_0x4c": {"changed_components_between_stationary_and_airborne": ball_diff},
        "ball_object_0x030": {"changed_components_between_stationary_and_airborne": ball_diff},
        "source_current_start": {"changed_components_between_stationary_and_airborne": 0}
    })
    base = {
        "kind": "PRIVATE-SANITIZED-B0-VS-HUMAN-IN_FLIGHT-SOURCE-COMPARE",
        "schema_version": 1, "game_id": "RSPE01", "disc_revision": 1,
        "golf_mode": 4, "source_gated_both_snapshots": True,
        "selected_slot_and_hole_match": True, "human_airborne_observed": True,
        "human_labeled_phases": ["B0_stationary_original", "airborne_operator"],
        "candidate_triplet_component_checks": checks,
        "candidate_ball_triplet_changed_while_start_stable": ball_diff > 0,
        "position_confounded_by_different_start": False,
        "whole_bank_differences": {"MEM1":True,"MEM2":True},
        "actual_ball_world_xyz_verified": False, "ball_velocity_verified": False,
        "impact_frame_verified": False, "power_ram_variable_verified":False,
        "approved_for_training":False, "allowed_to_publish":False,
        "mem1_mem2_exports_same_guest_frame_verified":False, "same_boot_verified":False,
    }
    p_cache = {}
    for i, label in enumerate(("cache_cc","cache_f0","cache_fc")):
        p_cache[label] = {
            "B0_to_flight_cache_changed_words": cache_diffs[i],
            "B0_cache_vs_ball_words_equal": matches_b0[i],
            "flight_cache_vs_ball_words_equal": matches_flight[i],
        }
    pin = {
        "kind":"S002-B0-AIRBORNE-PIN-CONTROL-CONFOUND",
        "schema_version":1, "game_id":"RSPE01", "disc_revision":1, "mode":4,
        "source_gated_both_snapshots":True,
        "source_selected_slot_and_hole_stable":True,
        "pin_constructor_invariants_pass_both":True,
        "ball_position_candidate_change_component_count":ball_diff,
        "pin_changed_bitwise_components_out_of_three":pin_diff,
        "pin_control_confounded":pin_diff>0, "pin_control_passed":pin_diff==0,
        "ball_current_vs_cache_word_equality":p_cache,
        "actual_ball_world_xyz_verified":False, "ball_velocity_verified":False,
        "power_ram_verified":False, "training_approved":False,
        "allowed_to_publish":False, "same_guest_frame_verified":False,
        "independent_same_boot_proven":False,
    }
    phases = {}
    for phase, matches in zip(("B0_stationary_original","airborne_operator"),
                              (matches_b0,matches_flight)):
        pairs = {"ball_nested_plus_0x4c__vs__ball_object_0x030":3}
        for key, count in zip(names,matches):
            pairs["ball_nested_plus_0x4c__vs__"+key]=count
        phases[phase] = {
            "source_selected_ball_alias_selfref_validated":True,
            "actual_ball_world_xyz_verified":False,
            "cache_role_or_semantics_verified":False,
            "pairwise_equal_component_counts":pairs
        }
    cache = {
        "kind":"PRIVATE-SANITIZED-INFLIGHT-BALL-CACHE-COHERENCE",
        "schema_version":1, "source_selected_slot_and_hole_match":True,
        "phases":phases,
        "all_three_caches_equal_current_ball_within_B0":all(x==3 for x in matches_b0),
        "all_three_caches_equal_current_ball_within_airborne":all(x==3 for x in matches_flight),
        "five_cross_phase_3_component_changes_independent_evidence":False,
        "same_boot_proven":False,"mem1_mem2_exports_same_guest_frame_verified":False,
        "actual_ball_world_xyz_verified":False,"actual_velocity_or_power_verified":False,
        "approved_for_training":False,"allowed_to_publish":False,
    }
    return base, pin, cache


class MatrixTests(unittest.TestCase):
    def test_realistic_3_3_ball_and_pin_does_not_promote_xyz(self):
        result = mod.reconcile(*fixture())
        self.assertTrue(result["three_independent_reader_outputs_consistent"])
        self.assertEqual(result["pin_changed_components"],3)
        self.assertTrue(result["target_control_confounded"])
        self.assertEqual(result["cache_current_ball_word_match"]["ball_cache_0x0cc"]
                         ["equal_to_current_ball_components_airborne"],0)
        for label in ("physical_world_xyz_verified","vertical_velocity_verified",
                      "model_training_allowed","allowed_to_publish",
                      "all_archives_shot_synchrony_independently_verified"):
            self.assertFalse(result[label])

    def test_all_caches_duplicate_current_not_four_independent_positions(self):
        out = mod.reconcile(*fixture(matches_flight=(3,3,3)))
        self.assertTrue(out["cache_all_equal_airborne"])
        self.assertFalse(out["model_training_allowed"])

    def test_stable_pin_is_distinct_control(self):
        out = mod.reconcile(*fixture(pin_diff=0))
        self.assertFalse(out["target_control_confounded"])

    def test_base_vs_pin_ball_count_conflict_abstains(self):
        b,p,c=fixture()
        p["ball_position_candidate_change_component_count"]=1
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_cache_cross_phase_count_conflict_abstains(self):
        b,p,c=fixture()
        p["ball_current_vs_cache_word_equality"]["cache_cc"]["B0_to_flight_cache_changed_words"]=2
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_cache_within_phase_equality_conflict_abstains(self):
        b,p,c=fixture()
        c["phases"]["airborne_operator"]["pairwise_equal_component_counts"][
            "ball_nested_plus_0x4c__vs__ball_cache_0x0cc"]=3
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_cache_all_equal_claim_must_match_counts(self):
        b,p,c=fixture()
        c["all_three_caches_equal_current_ball_within_airborne"]=True
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_pin_confound_cannot_be_suppressed(self):
        b,p,c=fixture()
        p["pin_control_confounded"]=False
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_unverified_frame_and_training_required(self):
        for idx,key in ((0,"same_boot_verified"),(1,"training_approved"),
                        (2,"actual_ball_world_xyz_verified")):
            inputs=list(fixture())
            inputs[idx][key]=True
            with self.subTest(idx=idx,key=key), self.assertRaises(mod.EvidenceRejected):
                mod.reconcile(*inputs)

    def test_missing_pin_constructor_fails(self):
        b,p,c=fixture()
        p["pin_constructor_invariants_pass_both"]=False
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_out_of_bounds_counts_rejected(self):
        b,p,c=fixture()
        b["candidate_triplet_component_checks"]["ball_cache_0x0cc"][
            "changed_components_between_stationary_and_airborne"]=4
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)

    def test_file_mode_no_raw_pointer_or_filename_leak(self):
        with tempfile.TemporaryDirectory() as root:
            paths=[]
            for idx, src in enumerate(fixture()):
                path=Path(root)/f"secret-0x91BE3834-{idx}.json"
                path.write_text(json.dumps(src),encoding="utf-8")
                paths.append(path)
            from contextlib import redirect_stdout
            from io import StringIO
            buff=StringIO()
            with redirect_stdout(buff):
                result=mod.main(["--base",str(paths[0]),"--pin",str(paths[1]),
                                 "--cache",str(paths[2])])
            self.assertEqual(result,0)
            rendered=buff.getvalue()
            self.assertNotIn("0x91BE3834",rendered)
            self.assertNotIn(root,rendered)
            self.assertNotIn("secret",rendered)
            self.assertNotIn("training_allowed\": true",rendered)


    def test_wrapper_requires_private_paths_only_outside_tests_only(self):
        wrapper = (Path(__file__).resolve().parents[1]
                   / "scripts/Invoke-P0FlightEvidenceMatrix.ps1")
        text = wrapper.read_text(encoding="utf-8")
        self.assertNotIn("D:" + chr(92) + "Projects", text)
        self.assertIn("[string]$Baseline,", text)
        self.assertIn("[string]$Flight,", text)
        self.assertIn("if (-not $TestsOnly) {", text)
        self.assertIn("$Baseline = Require-PrivateDirectory $Baseline", text)
        self.assertIn("Explicit private Baseline and Flight directories", text)

    def test_duplicate_phase_or_missing_phase_fails(self):
        b,p,c=fixture()
        c["phases"].pop("B0_stationary_original")
        with self.assertRaises(mod.EvidenceRejected): mod.reconcile(b,p,c)


if __name__ == "__main__":
    unittest.main()
