"""Fabricated-only future native Golf site-event trace pairing regressions."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_p0_golf_poststore_event_trace as m


def event(n, kind, *, scene=1, call=None, callee=None):
    return {"ordinal": n, "scene_token": scene, "event": kind,
            "call_token": call, "callee": callee}


def group(*labels, scene=1):
    out = [event(1, "scene_enter", scene=scene)]
    for kind, call, callee in labels:
        out.append(event(len(out) + 1, kind, scene=scene, call=call,
                         callee=callee))
    out.append(event(len(out) + 1, "scene_exit", scene=scene))
    return out


class TestP0PoststorePairing(unittest.TestCase):
    def test_valid_B57C_store_then_return_is_candidate_only(self):
        rows = group(("sim_enter", 101, "B57C"),
                     ("b57c_store_candidate", 101, "B57C"),
                     ("sim_return", 101, "B57C"))
        result = m.inspect_events(rows)
        self.assertEqual(result[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 1)
        self.assertEqual(result["scene_exit_event_count_unverified"], 1)
        self.assertFalse(result[
            "source_qualified_post_ball_integrator_completed_verified"])
        self.assertFalse(result["guest_physics_step_clock_verified"])

    def test_original_B0_r26_stack_candidate_is_not_ball_update(self):
        # #270 real B0 says nearest recognized r26 assignment uses r1;
        # control transfer prevents a proven dynamic stack-local address.
        rows = group(("sim_enter", 101, "B57C"),
                     ("b57c_store_candidate", 101, "B57C"),
                     ("sim_return", 101, "B57C"))
        report = m.inspect_events(rows)
        self.assertEqual(report[
            "B57C_static_r26_nearest_recognized_def_class"],
            "addi_or_addis_from_r1_with_control_barrier")
        self.assertEqual(report["B57C_store_source_role_class"],
            "stack_derived_scratch_or_output_candidate_not_typed_ball")
        self.assertEqual(report[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 1)
        self.assertEqual(report["eligible_ball_update_completion_observations"], 0)
        self.assertIs(report["B57C_store_is_eligible_ball_update_completion_anchor"],
                      False)
        self.assertIs(report["B57C_stfs_actual_runtime_receiver_verified"], False)

    def test_two_paired_B57C_store_returns_still_yield_zero_ball_steps(self):
        rows = group(
            ("sim_enter", 11, "B57C"),
            ("b57c_store_candidate", 11, "B57C"),
            ("sim_return", 11, "B57C"),
            ("sim_enter", 12, "B57C"),
            ("b57c_store_candidate", 12, "B57C"),
            ("sim_return", 12, "B57C"),
        )
        report = m.inspect_events(rows)
        self.assertEqual(report[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 2)
        self.assertEqual(report["eligible_ball_update_completion_observations"], 0)
        self.assertFalse(report["guest_physics_step_clock_verified"])
        self.assertFalse(report["source_qualified_post_ball_integrator_completed_verified"])
        self.assertFalse(report["training_approved"])

    def test_forged_post_integrator_completion_event_is_explicitly_disallowed(self):
        rows = group(("sim_enter", 101, "B57C"),
                     ("b57c_store_candidate", 101, "B57C"),
                     ("sim_return", 101, "B57C"))
        rows[2]["event"] = "ball_physics_update_completed"
        with self.assertRaisesRegex(ValueError, "unqualified"):
            m.inspect_events(rows)

    def test_repeated_B554_inside_one_scene_is_not_two_scene_steps(self):
        rows = group(("sim_enter", 1, "B554"),
                     ("sim_return", 1, "B554"),
                     ("sim_enter", 2, "B554"),
                     ("sim_return", 2, "B554"),
                     ("sim_enter", 3, "B43C"),
                     ("sim_return", 3, "B43C"))
        result = m.inspect_events(rows)
        self.assertEqual(result["source_call_entry_counts_unverified"]["B554"], 2)
        self.assertEqual(result["scene_event_groups_with_multiple_B554_entries"], 1)
        self.assertEqual(result["scene_exit_event_count_unverified"], 1)
        self.assertEqual(result[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 0)
        self.assertTrue(result["per_scene_event_count_is_not_guest_physics_step"])

    def test_return_without_store_is_not_poststore(self):
        result = m.inspect_events(group(("sim_enter", 7, "B57C"),
                                        ("sim_return", 7, "B57C")))
        self.assertEqual(result[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 0)

    def test_duplicate_store_not_multiple_integrator_steps(self):
        rows = group(("sim_enter", 7, "B57C"),
                     ("b57c_store_candidate", 7, "B57C"),
                     ("b57c_store_candidate", 7, "B57C"),
                     ("sim_return", 7, "B57C"))
        with self.assertRaisesRegex(ValueError, "syntactic store"):
            m.inspect_events(rows)

    def test_early_return_or_truncated_scene_rejected(self):
        cases = [
            [event(1, "scene_enter")],
            group(("sim_enter", 7, "B57C"))[:-1],
            [event(1, "scene_enter"), event(2, "sim_enter",
                                            call=7, callee="B57C"),
             event(3, "scene_exit")],
        ]
        for rows in cases:
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                m.inspect_events(rows)

    def test_unmatched_return_or_wrong_call_identity_rejected(self):
        cases = [
            group(("sim_return", 9, "B554")),
            group(("sim_enter", 4, "B43C"), ("sim_return", 5, "B43C")),
            group(("sim_enter", 4, "B43C"), ("sim_return", 4, "B554")),
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                m.inspect_events(rows)

    def test_nested_different_callees_require_lifo_same_call(self):
        rows = group(("sim_enter", 1, "B43C"),
                     ("sim_enter", 2, "B57C"),
                     ("b57c_store_candidate", 2, "B57C"),
                     ("sim_return", 2, "B57C"),
                     ("sim_return", 1, "B43C"))
        result = m.inspect_events(rows)
        self.assertEqual(result[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 1)
        rows[3]["call_token"] = 1
        with self.assertRaises(ValueError):
            m.inspect_events(rows)

    def test_store_cannot_be_assigned_to_B554_or_B43C(self):
        for callee in ("B554", "B43C"):
            rows = group(("sim_enter", 1, callee),
                         ("b57c_store_candidate", 1, callee),
                         ("sim_return", 1, callee))
            with self.subTest(callee=callee), self.assertRaises(ValueError):
                m.inspect_events(rows)

    def test_source_call_token_cannot_be_reused_even_between_scenes(self):
        rows = group(("sim_enter", 1, "B554"),
                     ("sim_return", 1, "B554"))
        second = group(("sim_enter", 1, "B57C"),
                       ("sim_return", 1, "B57C"), scene=2)
        for row in second:
            row["ordinal"] += len(rows)
        with self.assertRaisesRegex(ValueError, "reused"):
            m.inspect_events(rows + second)

    def test_two_scenes_with_distinct_calls_are_separately_counted(self):
        rows = group(("sim_enter", 1, "B554"),
                     ("sim_return", 1, "B554"))
        second = group(("sim_enter", 2, "B57C"),
                       ("b57c_store_candidate", 2, "B57C"),
                       ("sim_return", 2, "B57C"), scene=2)
        for row in second:
            row["ordinal"] += len(rows)
        result = m.inspect_events(rows + second)
        self.assertEqual(result["scene_exit_event_count_unverified"], 2)
        self.assertEqual(result[
            "B57C_callee_returns_after_same_call_syntactic_store_candidates"], 1)

    def test_ordinals_are_bounded_and_strictly_contiguous(self):
        rows = group(("sim_enter", 1, "B43C"),
                     ("sim_return", 1, "B43C"))
        for value in (True, 1.0, -1, 0, 0x80000000, 45):
            candidate = [dict(x) for x in rows]
            candidate[1]["ordinal"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.inspect_events(candidate)

    def test_scene_and_call_tokens_are_positive_nonbool_ints(self):
        rows = group(("sim_enter", 1, "B554"),
                     ("sim_return", 1, "B554"))
        for value in (0, -1, True, "1", 1.0, 0x80000000):
            bad = [dict(x) for x in rows]
            bad[1]["call_token"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.inspect_events(bad)
        rows[0]["scene_token"] = 0
        with self.assertRaises(ValueError):
            m.inspect_events(rows)

    def test_extra_untrusted_evidence_fields_rejected(self):
        rows = group()
        rows[1]["trusted_guest_frame_id"] = True
        with self.assertRaisesRegex(ValueError, "schema"):
            m.inspect_events(rows)

    def test_unknown_source_site_rejected(self):
        rows = group(("sim_enter", 2, "B554"),
                     ("sim_return", 2, "B554"))
        rows[1]["event"] = "frameadvance"
        with self.assertRaises(ValueError):
            m.inspect_events(rows)

    def test_no_timing_render_training_or_raw_values_published(self):
        report = m.inspect_events(group())
        serialized = json.dumps(report, sort_keys=True)
        for s in ("raw_word", "player_pointer", "MEM2.raw",
                  "world_xyz", "dolphin.exe", "sha256"):
            self.assertNotIn(s, serialized)
        for key in ("externally_supplied_event_semantics_source_verified",
                    "B57C_stfs_receiver_is_selected_or_global_ball_verified",
                    "B57C_stfs_actual_runtime_receiver_verified",
                    "B57C_store_is_eligible_ball_update_completion_anchor",
                    "source_qualified_post_ball_integrator_completed_verified",
                    "actual_felk_execution_provenance_and_backend_verified",
                    "guest_physics_step_clock_verified",
                    "same_callback_rendered_ball_visual_join_verified",
                    "training_approved", "allowed_to_publish"):
            self.assertFalse(report[key])


if __name__ == "__main__":
    unittest.main()
