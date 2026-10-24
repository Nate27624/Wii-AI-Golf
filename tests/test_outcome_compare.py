"""Offline cross-shot comparison regression tests (no Dolphin or user data)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.outcome_compare import compare_outcome_runs


def make_report(*, green="yes", distance=2.1, frames=122, contents=None):
    contents = contents or [("0x91BF176C", 3, 5), ("0x91BF1770", 10, 1)]
    return {
        "schema_version": 1,
        "human_observation": {
            "contact_human": "yes",
            "finished_on_green_human": green,
            "displayed_distance_human": distance,
            "displayed_unit_human": "ft",
        },
        "known_good_swing_request": {"generated_trace_frames": frames},
        "swing_dispatch": {"applied_frames": frames, "state": "complete"},
        "candidate_ranking": {"candidates_truncated": False, "candidates": [
            {"address": address, "before": {"u32": before},
             "settled": {"u32": after}, "windows": ["golf_config"],
             "matches_displayed_numeric_label_as": []}
            for address, before, after in contents
        ]},
    }


class OutcomeComparisonTests(unittest.TestCase):
    def test_different_labels_same_ram_does_not_verify_score(self):
        out = compare_outcome_runs([
            make_report(), make_report(green="no", distance=100.0, frames=89),
        ])
        self.assertTrue(out["human_labels_differ"])
        self.assertEqual(out["shared_candidate_addresses"], 2)
        self.assertEqual(out["identical_before_u32_among_shared"], 2)
        self.assertEqual(out["identical_settled_u32_among_shared"], 2)
        self.assertEqual(out["identical_before_and_settled_transitions_among_shared"], 2)
        self.assertFalse(out["waveforms_proven_identical"])
        self.assertFalse(out["game_score_verified"])
        self.assertEqual(out["different_settled_candidates"], [])

    def test_different_settled_bits_not_assumed_score(self):
        result = compare_outcome_runs([
            make_report(contents=[("0x91BF176C", 3, 5)]),
            make_report(green="no", distance=100,
                        contents=[("0x91BF176C", 3, 8)]),
        ])
        self.assertEqual(result["different_settled_u32_among_shared"], 1)
        self.assertEqual(result["different_settled_candidates"][0]["settled_u32_by_run"], [5, 8])
        self.assertEqual(result["different_settled_candidates"][0]["hypothesis_status"],
                         "NOT_VERIFIED_OUTCOME_FIELD")

    def test_repeated_patterns_collapsed_independently_of_addresses(self):
        result = compare_outcome_runs([
            make_report(contents=[("0x91BF4800", 1, 5),
                                  ("0x91BF4890", 1, 5),
                                  ("0x91BF4810", 1, 9)]),
            make_report(contents=[("0x91BF4800", 1, 7),
                                  ("0x91BF4890", 1, 7),
                                  ("0x91BF4810", 1, 9)]),
        ])
        self.assertEqual(result["unique_before_settled_bit_signatures_among_shared"], 2)
        self.assertEqual(result["repeated_value_pattern_groups"],
                         [["0x91BF4800", "0x91BF4890"]])

    def test_unequal_address_sets_do_not_invent_absent_value(self):
        result = compare_outcome_runs([
            make_report(contents=[("0x91BF4800", 1, 5)]),
            make_report(contents=[("0x91BF4810", 1, 5)]),
        ])
        self.assertEqual(result["shared_candidate_addresses"], 0)
        self.assertEqual(result["candidate_union_addresses"], 2)

    def test_differing_baseline_is_reported(self):
        result = compare_outcome_runs([
            make_report(contents=[("0x91BF4800", 1, 5)]),
            make_report(contents=[("0x91BF4800", 2, 5)]),
        ])
        self.assertEqual(result["identical_before_u32_among_shared"], 0)
        self.assertEqual(result["identical_settled_u32_among_shared"], 1)

    def test_same_trace_hash_is_more_informative_than_same_frame_count(self):
        docs = [make_report(frames=89), make_report(frames=89)]
        out = compare_outcome_runs(docs)
        self.assertFalse(out["waveforms_proven_identical"])
        for d in docs:
            d["known_good_swing_request"]["trace_sha256"] = "a" * 64
        self.assertTrue(compare_outcome_runs(docs)["waveforms_proven_identical"])
        docs[1]["known_good_swing_request"]["trace_sha256"] = "b" * 64
        self.assertFalse(compare_outcome_runs(docs)["waveforms_proven_identical"])

    def test_reject_duplicate_invalid_addresses_or_bad_telemetry(self):
        same = make_report()
        same["candidate_ranking"]["candidates"].append(same["candidate_ranking"]["candidates"][0].copy())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_outcome_runs([same, make_report()])
        broken = make_report()
        broken["candidate_ranking"]["candidates"][0]["before"]["u32"] = -1
        with self.assertRaisesRegex(ValueError, "32-bit"):
            compare_outcome_runs([broken, make_report()])
        with self.assertRaises(ValueError):
            compare_outcome_runs([make_report()])
        with self.assertRaises(ValueError):
            compare_outcome_runs([make_report(), make_report(), *[make_report()] * 24])

    def test_offline_cli_exclusive_create_and_isolated_python(self):
        with TemporaryDirectory() as d:
            folder = Path(d)
            f1, f2, out = (folder / n for n in ("shot1.json", "shot2.json", "audit.json"))
            f1.write_text(json.dumps(make_report()))
            f2.write_text(json.dumps(make_report(green="no", distance=100.0, frames=89)))
            args = [sys.executable, "-I", str(ROOT / "scripts" / "compare_outcome_runs.py"),
                    "--input", str(f1), str(f2), "--out", str(out)]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(out.read_text())["shared_candidate_addresses"], 2)
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("File exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
