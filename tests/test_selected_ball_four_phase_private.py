"""License-safe synthetic selected-ball no-shot B0-B3 contrast tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_selected_ball_four_phase_private as phase
import audit_golf_two_bank_roster_private as roster
from test_selected_ball_start_link_private import fixture, inspect


def four_phases():
    return [inspect(fixture()[0]) for _ in range(4)]


def diff_banks():
    return [{"MEM1": True, "MEM2": True} for _ in range(3)]


class FourPhaseSelectedBallTests(unittest.TestCase):
    def test_four_no_shot_phases_stable_with_real_aim_and_distinct_banks(self):
        summary = phase.summarize_four_selected(
            four_phases(), diff_banks(), aim_visibly_moved=True,
            operator_same_session=True)
        self.assertTrue(summary[
            "no_shot_controls_consistent_with_stationary_ball_candidate"])
        self.assertTrue(summary["selected_ball_vector_stable_during_no_shot"])
        self.assertTrue(summary["source_start_vector_stable_during_no_shot"])
        self.assertTrue(summary["all_three_transitions_have_distinct_whole_banks"])
        self.assertEqual(len(summary["transitions"]), 3)
        self.assertFalse(summary["ball_world_xyz_verified"])
        self.assertFalse(summary["approved_for_model_training"])

    def test_aim_time_ball_candidate_change_not_promoted_to_stable(self):
        pairs = four_phases()
        words, refs = fixture()
        ball = words[refs["pm"] + roster.BALL_CANDIDATE_MEMBER]
        vec = words[ball + 0x4C]
        words[vec] = 0x40C00000
        pairs[2] = inspect(words)
        summary = phase.summarize_four_selected(
            pairs, diff_banks(), aim_visibly_moved=True,
            operator_same_session=True)
        self.assertEqual(summary["transitions"][1][
            "selected_ball_vector_changed_components"], 1)
        self.assertFalse(summary["selected_ball_vector_stable_during_no_shot"])
        self.assertFalse(summary[
            "no_shot_controls_consistent_with_stationary_ball_candidate"])
        self.assertFalse(summary["ball_motion_verified"])

    def test_source_start_drift_is_rejected_as_good_control(self):
        pairs = four_phases()
        words, refs = fixture()
        field = words[roster.GOLF_FIELD_STATIC]
        start = words[field + 0x50]
        words[start + 0x30] = 0x40000000
        pairs[1] = inspect(words)
        summary = phase.summarize_four_selected(
            pairs, diff_banks(), aim_visibly_moved=True,
            operator_same_session=True)
        self.assertFalse(summary["source_start_vector_stable_during_no_shot"])
        self.assertFalse(summary[
            "no_shot_controls_consistent_with_stationary_ball_candidate"])

    def test_selected_actor_identity_change_fails_closed(self):
        pairs = four_phases()
        safe, private = pairs[3]
        tampered = copy.deepcopy(private)
        tampered["selected_index"] = 1
        pairs[3] = safe, tampered
        with self.assertRaises(ValueError):
            phase.summarize_four_selected(pairs, diff_banks())

    def test_hole_change_fails_closed(self):
        pairs = four_phases()
        safe, private = pairs[2]
        tampered = copy.deepcopy(private)
        tampered["hole"] = 2
        pairs[2] = safe, tampered
        with self.assertRaises(ValueError):
            phase.summarize_four_selected(pairs, diff_banks())

    def test_invalid_boolean_bank_change_fails_closed(self):
        changed = diff_banks()
        changed[1]["MEM1"] = "true"
        with self.assertRaises(ValueError):
            phase.summarize_four_selected(four_phases(), changed)

    def test_identical_bank_pair_does_not_pass_independent_capture_gate(self):
        changed = diff_banks()
        changed[1]["MEM2"] = False
        summary = phase.summarize_four_selected(
            four_phases(), changed, aim_visibly_moved=True,
            operator_same_session=True)
        self.assertFalse(summary["all_three_transitions_have_distinct_whole_banks"])
        self.assertFalse(summary[
            "no_shot_controls_consistent_with_stationary_ball_candidate"])

    def test_aim_or_session_unconfirmed_prevents_positive_label(self):
        for aim, session in ((True, False), (False, True)):
            summary = phase.summarize_four_selected(
                four_phases(), diff_banks(), aim_visibly_moved=aim,
                operator_same_session=session)
            self.assertFalse(summary[
                "no_shot_controls_consistent_with_stationary_ball_candidate"])

    def test_stdout_does_not_leak_actual_words_or_runtime_addresses(self):
        summary = phase.summarize_four_selected(
            four_phases(), diff_banks(), aim_visibly_moved=True,
            operator_same_session=True)
        content = json.dumps(summary, sort_keys=True)
        for key in ('"ball":', '"record":', '"start":',
                    "bytes_hex", "runtime_pointer", "0x91040000",
                    "0x91010000", "0x3F800000", "mem2.raw", "file_path"):
            self.assertNotIn(key, content)
        self.assertFalse(summary["allowed_to_publish"])

    def test_requires_four_phase_pairs_and_three_transitions(self):
        with self.assertRaises(ValueError):
            phase.summarize_four_selected(four_phases()[:3], diff_banks())
        with self.assertRaises(ValueError):
            phase.summarize_four_selected(four_phases(), diff_banks()[:2])


if __name__ == "__main__":
    unittest.main()
