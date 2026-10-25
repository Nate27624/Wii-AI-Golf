"""Lab must surface human-labeled results without reading RAW-PRIVATE memory."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab.reports import sanitized_reports


class SanitizedReportTests(unittest.TestCase):
    def test_only_sanitized_candidates_visible_and_no_score_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Wii-AI-Golf"
            root.mkdir()
            data = root.parent / "Wii-AI-Golf-Data" / "captures"
            data.mkdir(parents=True)
            raw = data / "outcome-example-RAW-PRIVATE.jsonl"
            raw.write_text("CONFIDENTIAL MEMORY DATA", encoding="utf-8")
            report = data / "outcome-example-candidates.json"
            report.write_text(json.dumps({
                "human_observation": {
                    "contact_human": "no", "finished_on_green_human": "no",
                    "displayed_distance_human": None, "displayed_unit_human": "unknown",
                },
                "known_good_swing_request": {
                    "trace_sha256": "a" * 64, "a_button_only_prime_requests": 0,
                },
                "candidate_ranking": {"fake_score": 9999},
            }), encoding="utf-8")
            items = sanitized_reports(root=root)
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertTrue(item["path"].endswith("-candidates.json"))
            self.assertFalse(item["verified_game_score"])
            self.assertEqual(item["contact_human"], "no")
            self.assertEqual(item["a_prime_requests"], 0)
            self.assertNotIn("CONFIDENTIAL", str(item))
            self.assertNotIn("fake_score", str(item))
            self.assertNotIn("game_score", item)

    def test_bad_reports_are_skipped_without_interpreting_raw(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Wii-AI-Golf"
            root.mkdir()
            data = root.parent / "Wii-AI-Golf-Data" / "captures"
            data.mkdir(parents=True)
            (data / "outcome-broken-candidates.json").write_text("{bad JSON", encoding="utf-8")
            (data / "outcome-broken-RAW-PRIVATE.jsonl").write_text('{"secret":"x"}')
            self.assertEqual(sanitized_reports(root=root), [])


if __name__ == "__main__":
    unittest.main()
