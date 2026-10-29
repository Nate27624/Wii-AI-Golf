"""Offline synthetic tests for private selected-ball swing report and fail-closed gates."""
import unittest
from scripts.record_selected_ball_swing_private import summarize, validate_frozen_trace
from scripts.probe_swing import build_probe
from dataclasses import replace


def sample(frame, ball=(0., 0., 0.), start=(0., 0., 0.),
           record=(0., 0., 0.), slot=0, hole=1, trace_index=None,
           stage="idle_control", owner=True, overhead=100, trace_id=7):
    return {
        "frame_tick_index": frame,
        "trace_sample_index_if_active": trace_index,
        "trace_id_if_active": trace_id if trace_index is not None else None,
        "input_stage": stage,
        "source_owner_consistent": owner,
        "selected_slot_candidate": slot,
        "source_hole_index": hole,
        "ball_translation_f32_candidate": list(ball),
        "record_translation_f32_candidate": list(record),
        "current_start_f32_candidate": list(start),
        "read_overhead_us": overhead,
    }


class ReportTests(unittest.TestCase):
    def test_idle_stable_then_ball_moves(self):
        reports = [
            sample(10), sample(14),
            sample(16, stage="a_prime"),
            sample(18, trace_index=0, stage="trace"),
            sample(22, ball=(0.3, 0., 0.), trace_index=4, stage="trace"),
            sample(26, ball=(1.2, 0., 0.), stage="posttrace"),
        ]
        safe = summarize(reports, human_ball_moved="yes", watch_state="complete")
        self.assertTrue(safe["start_vector_stable"])
        self.assertTrue(safe["candidate_ball_vector_changed_during_recording"])
        self.assertTrue(safe["candidate_motion_corroborated_by_human"])
        self.assertEqual(safe["samples_with_active_trace"], 2)
        self.assertFalse(safe["actual_active_ball_xyz_verified"])
        self.assertFalse(safe["training_allowed"])
        self.assertFalse(safe["allowed_to_publish"])
        self.assertNotIn("ball_translation_f32_candidate", safe)

    def test_same_length_modified_waveform_fails_closed(self):
        baseline = build_probe("forward", follow_through_frames=30, a_setup_frames=12)
        self.assertEqual(len(validate_frozen_trace(baseline)), 64)
        changed = list(baseline)
        changed[15] = replace(changed[15], speed_m_s=changed[15].speed_m_s + 0.01)
        with self.assertRaises(ValueError):
            validate_frozen_trace(changed)

    def test_forged_owner_or_slow_read_or_partial_drain_blocks_corroboration(self):
        reports = [sample(10), sample(14), sample(16, stage="a_prime"),
                   sample(18, trace_index=0, stage="trace"),
                   sample(22, ball=(1., 0., 0.), trace_index=4, stage="trace"),
                   sample(26, ball=(1., 0., 0.), stage="posttrace")]
        self.assertTrue(summarize(reports, human_ball_moved="yes", watch_state="complete")[
            "candidate_motion_corroborated_by_human"])
        self.assertFalse(summarize(reports, human_ball_moved="yes", watch_state="recording")[
            "candidate_motion_corroborated_by_human"])
        reports[3]["source_owner_consistent"] = False
        self.assertFalse(summarize(reports, human_ball_moved="yes", watch_state="complete")[
            "candidate_motion_corroborated_by_human"])
        reports[3]["source_owner_consistent"] = True
        reports[3]["read_overhead_us"] = 9000
        self.assertFalse(summarize(reports, human_ball_moved="yes", watch_state="complete")[
            "candidate_motion_corroborated_by_human"])

    def test_trace_only_no_baseline_is_safe_and_abstains(self):
        reports = [sample(18, trace_index=0, stage="trace"),
                   sample(22, ball=(1., 0., 0.), trace_index=4, stage="trace")]
        safe = summarize(reports, human_ball_moved="yes", watch_state="complete")
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])
        self.assertFalse(safe["pretrace_candidate_ball_stationary"])

    def test_idle_drift_or_changed_start_blocks_corroboration(self):
        r = [sample(1), sample(5, ball=(1., 0., 0.), start=(1., 0., 0.))]
        safe = summarize(r, human_ball_moved="yes")
        self.assertFalse(safe["start_vector_stable"])
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])

    def test_pretrace_ball_drift_blocks_false_contact(self):
        reports = [sample(10), sample(14, ball=(0.1, 0., 0.)),
                   sample(18, ball=(0.2, 0., 0.), trace_index=0),
                   sample(22, ball=(1., 0., 0.), trace_index=4)]
        safe = summarize(reports, human_ball_moved="yes")
        self.assertFalse(safe["pretrace_candidate_ball_stationary"])
        self.assertTrue(safe["candidate_ball_changed_after_trace_start"])
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])

    def test_no_trace_blocks_corroboration_even_if_ball_changes(self):
        reports = [sample(10), sample(14, ball=(1., 0., 0.))]
        safe = summarize(reports, human_ball_moved="yes")
        self.assertFalse(safe["candidate_ball_changed_after_trace_start"])
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])

    def test_human_unknown_blocks_corroboration(self):
        r = [sample(1), sample(5, ball=(1., 0., 0.))]
        safe = summarize(r, human_ball_moved="unknown")
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])

    def test_slot_change_blocks_corroboration(self):
        r = [sample(1), sample(5, ball=(1., 0., 0.), slot=1)]
        safe = summarize(r, human_ball_moved="yes")
        self.assertFalse(safe["candidate_motion_corroborated_by_human"])

    def test_rejects_bad_frame_order_and_size(self):
        with self.assertRaises(ValueError):
            summarize([sample(5), sample(5)], human_ball_moved="no")
        with self.assertRaises(ValueError):
            summarize([sample(5), sample(4)], human_ball_moved="no")
        with self.assertRaises(ValueError):
            summarize([], human_ball_moved="unknown")
        with self.assertRaises(ValueError):
            summarize([sample(i) for i in range(81)], human_ball_moved="no")


if __name__ == "__main__":
    unittest.main()
