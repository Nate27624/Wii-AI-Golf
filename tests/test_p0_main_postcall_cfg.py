"""Synthetic-only source CFG negative controls. Never reads original B0/ROM."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_p0_main_postcall_cfg as m


def bl(pc, dest, *, linked=True):
    return (18 << 26) | ((dest - pc) & 0x03FFFFFC) | int(linked)


def bc(pc, dest):
    return (16 << 26) | (12 << 21) | (2 << 16) | (
        (dest - pc) & 0xFFFC)


def fixture(extra=None):
    # A purely synthetic source with published THREE BL offsets and
    # an ordinary last-instruction LR return. No actual ROM instructions.
    words = [0x60000000] * m.COUNT
    for offset, target in m.CALLS:
        words[offset // 4] = bl(m.ENTRY + offset, target)
    words[-1] = 0x4E800020
    for offset, word in (extra or {}).items():
        words[offset // 4] = word
    return tuple(words)


class TestMainPostcallCfg(unittest.TestCase):
    def test_exact_published_function_bounds_are_distinct_from_nextshot(self):
        self.assertEqual(m.END, 0x8028E2EC)
        self.assertEqual(m.COUNT, 101)
        self.assertEqual(m.CALLS[2], (0x168, 0x8029B57C))
        self.assertEqual(m.CALLS[0], (0x7C, 0x8029B554))

    def test_straightline_postcall_candidates_never_certify_physics(self):
        report = m.review_source_words(fixture())
        self.assertEqual(report["source_direct_sim_call_count"], 3)
        self.assertEqual(len(report["callsite_return_continuation_candidates"]), 3)
        self.assertEqual(report["source_LR_branch_possible_exit_offsets"], ["+0x0190"])
        self.assertFalse(report["source_possible_fallthrough_into_distinct_next_function"])
        for item in report["callsite_return_continuation_candidates"]:
            self.assertFalse(item["continuation_reachable_without_callsite"])
            self.assertFalse(item["continuation_can_recur_via_source_backedge"])
            self.assertFalse(item[
                "callee_return_and_writes_complete_at_continuation_verified"])
            self.assertFalse(item[
                "continuation_is_unique_post_ball_update_witness_verified"])
        self.assertFalse(report[
            "source_qualified_post_integrator_completion_site_verified"])

    def test_real_shaped_backward_bc_crosses_first_sim_call(self):
        report = m.review_source_words(fixture({
            0x88: bc(m.ENTRY + 0x88, m.ENTRY + 0x6C)
        }))
        first, second, third = report["callsite_return_continuation_candidates"]
        self.assertTrue(first["continuation_can_recur_via_source_backedge"])
        self.assertFalse(second["continuation_can_recur_via_source_backedge"])
        self.assertFalse(third["continuation_can_recur_via_source_backedge"])
        self.assertFalse(report[
            "source_qualified_scene_completion_site_verified"])

    def test_branch_around_call_makes_after_call_site_ambiguous(self):
        report = m.review_source_words(fixture({
            0x150: bc(m.ENTRY + 0x150, m.ENTRY + 0x16C)
        }))
        third = report["callsite_return_continuation_candidates"][2]
        self.assertTrue(third["continuation_reachable_without_callsite"])
        self.assertFalse(third[
            "continuation_is_unique_post_ball_update_witness_verified"])

    def test_nonlinked_backward_B_reenters_first_sim_call(self):
        report = m.review_source_words(fixture({
            0x88: bl(m.ENTRY + 0x88, m.ENTRY + 0x6C, linked=False)
        }))
        first = report["callsite_return_continuation_candidates"][0]
        self.assertTrue(first["continuation_can_recur_via_source_backedge"])

    def test_call_cannot_be_trusted_if_link_bit_removed(self):
        with self.assertRaisesRegex(ValueError, "three direct BL"):
            m.review_source_words(fixture({
                0x168: bl(m.ENTRY + 0x168, 0x8029B57C, linked=False)
            }))

    def test_target_drift_and_missing_word_refuse(self):
        with self.assertRaisesRegex(ValueError, "three direct BL"):
            m.review_source_words(fixture({
                0x90: bl(m.ENTRY + 0x90, 0x8029B554)
            }))
        with self.assertRaisesRegex(ValueError, "101"):
            m.review_source_words(fixture()[:-1])

    def test_unaligned_and_noninteger_words_refuse(self):
        for value in (True, "0x60000000", 0x100000000, -1, 1.0):
            words = list(fixture())
            words[0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.review_source_words(tuple(words))
        with self.assertRaises(ValueError):
            m.review_source_words(list(fixture()))

    def test_indirect_bctr_and_lr_returns_cannot_be_source_clock(self):
        report = m.review_source_words(fixture({
            0x104: 0x4E800420  # bctr, indirect unknown destination
        }))
        self.assertIn("+0x0104", report["source_CTR_indirect_exit_offsets"])
        self.assertFalse(report[
            "source_qualified_post_integrator_completion_site_verified"])

    def test_early_lr_return_and_conditional_control_are_exits(self):
        report = m.review_source_words(fixture({
            0x54: 0x4E800020,
            0x88: bc(m.ENTRY + 0x88, m.ENTRY + 0x6C),
        }))
        self.assertIn("+0x0054", report["source_LR_branch_possible_exit_offsets"])
        self.assertTrue(report["callsite_return_continuation_candidates"][0][
            "continuation_can_recur_via_source_backedge"])
        self.assertFalse(report[
            "runtime_guest_physics_step_or_backend_execution_verified"])

    def test_implicit_fallthrough_is_not_nextshot_completion(self):
        words = list(fixture())
        words[-1] = 0x60000000
        report = m.review_source_words(tuple(words))
        self.assertTrue(report[
            "source_possible_fallthrough_into_distinct_next_function"])
        self.assertEqual(report["source_LR_branch_possible_exit_offsets"], [])
        self.assertFalse(report[
            "source_qualified_scene_completion_site_verified"])

    def test_last_linked_call_would_return_into_distinct_next_function(self):
        words = list(fixture())
        words[-1] = bl(m.END - 4, 0x8029B554)
        report = m.review_source_words(tuple(words))
        self.assertTrue(report[
            "source_possible_fallthrough_into_distinct_next_function"])
        self.assertFalse(report[
            "source_qualified_post_integrator_completion_site_verified"])

    def test_last_conditional_bclr_has_possible_next_function_fallthrough(self):
        words = list(fixture())
        # BO=12 conditional bclr, not plain BO=20 unconditional BLR.
        words[-1] = (19 << 26) | (12 << 21) | (16 << 1)
        report = m.review_source_words(tuple(words))
        self.assertTrue(report[
            "source_possible_fallthrough_into_distinct_next_function"])
        self.assertEqual(report["source_LR_branch_possible_exit_offsets"],
                         ["+0x0190"])

    def test_unknown_external_branch_remains_exit(self):
        report = m.review_source_words(fixture({
            0x88: bl(m.ENTRY + 0x88, 0x8029A204, linked=False)
        }))
        self.assertIn("+0x0088", report["source_other_or_external_exit_offsets"])
        self.assertFalse(report[
            "source_qualified_post_integrator_completion_site_verified"])

    def test_no_raw_source_words_in_summary_and_no_training(self):
        report = m.review_source_words(fixture())
        serialized = json.dumps(report, sort_keys=True)
        for secret in ("0x60000000", "0x4E800020", "private_RAM",
                       "MEM1.bin", "runtime_xyz", "sha256"):
            self.assertNotIn(secret, serialized)
        self.assertFalse(report["typed_ball_integrator_or_actual_store_receiver_verified"])
        self.assertFalse(report["rendered_ball_and_training_approved"])


if __name__ == "__main__":
    unittest.main()
