"""Offline synthetic tests for private selected-ball swing report and fail-closed gates."""
import unittest
from scripts.record_selected_ball_swing_private import summarize


def sample(frame, ball=(0., 0., 0.), start=(0., 0., 0.),
           record=(0., 0., 0.), slot=0, hole=1, trace_index=None):
    return {
        "frame_tick_index": frame,
        "trace_sample_index_if_active": trace_index,
        "selected_slot_candidate": slot,
        "source_hole_index": hole,
        "ball_translation_f32_candidate": list(ball),
        "record_translation_f32_candidate": list(record),
        "current_start_f32_candidate": list(start),
        "read_overhead_us": 100,
    }


class ReportTests(unittest.TestCase):
    def test_idle_stable_then_ball_moves(self):
        reports = [
            sample(10), sample(14), sample(18, trace_index=0),
            sample(22, ball=(0.3, 0., 0.), trace_index=4),
            sample(26, ball=(1.2, 0., 0.)),
        ]
        safe = summarize(reports, human_ball_moved="yes")
        self.assertTrue(safe["start_vector_stable"])
        self.assertTrue(safe["candidate_ball_vector_changed_during_recording"])
        self.assertTrue(safe["candidate_motion_corroborated_by_human"])
        self.assertEqual(safe["samples_with_active_trace"], 2)
        self.assertFalse(safe["actual_active_ball_xyz_verified"])
        self.assertFalse(safe["training_allowed"])
        self.assertFalse(safe["allowed_to_publish"])
        self.assertNotIn("ball_translation_f32_candidate", safe)

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
