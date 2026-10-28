"""Synthetic unit tests for private swing selected-record ranking. No game data."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_selected_player_swing_words_private.py"
spec = importlib.util.spec_from_file_location("swing_ranker_private", SCRIPT)
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)


def make_report(*, drift=False, no_motion=False, wrong_trace=False):
    samples = []
    # Modest synthetic set; 0x24 is our fabricated swing-specific word.
    rows = [
        ("idle_control", None, 0),
        ("idle_control", None, 0),
        ("a_prime", None, 0),
        ("trace", 4, 0),
        ("trace", 12, 5),
        ("trace", 27, 6),
        ("trace", 47, 7),
        ("trace", 77, 7),
        ("posttrace", None, 0),
    ]
    for i, (stage, idx, v) in enumerate(rows):
        values = [0] * analyzer.WORD_COUNT
        values[0x24 // 4] = (0 if no_motion else v)
        # Fabricate a field that changes under idle, so it is not promoted.
        values[0x90 // 4] = i if drift else 0
        samples.append({
            "frame_tick_index": 2 * i,
            "input_stage": stage,
            "trace_sample_index_if_active": idx,
            "trace_id_if_active": (None if idx is None else (22 if not wrong_trace or i < 5 else 23)),
            "selected_slot_candidate": 0,
            "source_hole_index": 1,
            "source_owner_consistent": True,
            "read_overhead_us": 20,
            "selected_player_record_words_PRIVATE": values,
        })
    return {
        "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
        "watch_status": {"state": "complete"},
        "safe_summary": {
            "watch_complete": True,
            "source_owner_consistency_checks_passed": True,
            "read_performance_checks_passed": True,
            "source_selected_slot_stable": True,
            "source_hole_stable": True,
            "start_vector_stable": True,
        },
        "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": samples,
    }


class SelectedPlayerSwingPrivateTests(unittest.TestCase):
    def test_flags_source_record_motion_specific_without_typing_power(self):
        result = analyzer.analyze(make_report())
        row = next(x for x in result["source_relative_candidate_offsets"]
                   if x["source_relative_offset"] == "+0x024")
        self.assertTrue(row["motion_specific_candidate_not_verified"])
        self.assertEqual(result["motion_specific_candidate_count_not_verified"], 1)
        self.assertFalse(result["swing_power_verified"])
        self.assertFalse(result["approved_for_training"])
        self.assertFalse(result["allowed_to_publish"])

    def test_idle_drift_excluded_from_motion_specific(self):
        result = analyzer.analyze(make_report(drift=True))
        confounds = [x for x in result["source_relative_candidate_offsets"]
                     if x["source_relative_offset"] == "+0x090"]
        self.assertTrue(
            not confounds or not confounds[0]["motion_specific_candidate_not_verified"]
        )

    def test_no_motion_has_no_swing_specific(self):
        result = analyzer.analyze(make_report(no_motion=True))
        self.assertEqual(result["motion_specific_candidate_count_not_verified"], 0)

    def test_wrong_trace_rejected(self):
        with self.assertRaises(ValueError):
            analyzer.analyze(make_report(wrong_trace=True))

    def test_incomplete_watch_rejected(self):
        report = make_report()
        report["watch_status"]["state"] = "recording"
        with self.assertRaises(ValueError):
            analyzer.analyze(report)

    def test_missing_record_refused(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][2].pop("selected_player_record_words_PRIVATE")
        with self.assertRaises(ValueError):
            analyzer.analyze(report)

    def test_wrong_record_size_refused(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][2]["selected_player_record_words_PRIVATE"].pop()
        with self.assertRaises(ValueError):
            analyzer.analyze(report)

    def test_bad_word_or_pointer_type_refused(self):
        for bad in (-1, 0x100000000, 1.0, None, True):
            report = make_report()
            report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][1]["selected_player_record_words_PRIVATE"][3] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyzer.analyze(report)

    def test_trace_phase_outside_range_rejected(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["trace_sample_index_if_active"] = 90
        with self.assertRaises(ValueError):
            analyzer.analyze(report)

    def test_wrong_source_identity_rejected(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][4]["source_owner_consistent"] = False
        with self.assertRaises(ValueError):
            analyzer.analyze(report)

    def test_missing_forward_phase_is_explicitly_incomplete(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][5]["trace_sample_index_if_active"] = 13
        result = analyzer.analyze(report)
        self.assertIn("forward_swing", result["missing_motion_phases"])
        self.assertEqual(result["motion_specific_candidate_count_not_verified"], 0)

    def test_result_never_contains_raw_u32(self):
        report = make_report()
        report["PRIVATE_UNVERIFIED_NUMERIC_VECTORS"][4]["selected_player_record_words_PRIVATE"][0x24//4] = 0xDEADBEEF
        result = str(analyzer.analyze(report))
        self.assertNotIn("3735928559", result)
        self.assertNotIn("DEADBEEF", result)


if __name__ == "__main__":
    unittest.main()
