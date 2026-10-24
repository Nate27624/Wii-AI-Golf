"""Offline outcome evidence recovery and unit suffix regression tests."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.audit.outcome_recovery import (
    parse_displayed_distance, recover_outcome_summary,
)


def shot_row(phase: str, value: int) -> dict:
    return {
        "schema_version": 1, "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
        "phase": phase, "frame_start": 50, "frame_end": 60,
        "game_id": "RSPE01", "disc_revision": 1,
        "windows": {"golf_config": {
            "address": "0x91000000",
            "bytes_hex": struct.pack(">I", value).hex(),
        }},
    }


def fixture_raw(path: Path) -> None:
    rows = [shot_row("pre", 1), shot_row("pre", 1),
            shot_row("post", 4), shot_row("post", 5),
            shot_row("settled", 8), shot_row("settled", 8)]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class RecoveryTests(unittest.TestCase):
    def test_accept_distance_with_suffix_and_space(self):
        self.assertEqual(parse_displayed_distance("100.0ft"), (100.0, "ft"))
        self.assertEqual(parse_displayed_distance("2.1 ft"), (2.1, "ft"))
        self.assertEqual(parse_displayed_distance("3 yards"), (3.0, "yd"))
        self.assertEqual(parse_displayed_distance("1 meter"), (1.0, "m"))
        self.assertEqual(parse_displayed_distance("100.0"), (100.0, None))
        self.assertEqual(parse_displayed_distance("   "), (None, None))

    def test_bad_or_nonfinite_distance_never_normalized_silently(self):
        for entry in ("NaN", "-1ft", "100.0fthuh", "inf", "1e600", "$100"):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                parse_displayed_distance(entry)

    def test_salvage_original_raw_with_manual_label(self):
        with TemporaryDirectory() as d:
            raw = Path(d) / "outcome-XYZ-RAW-PRIVATE.jsonl"
            fixture_raw(raw)
            result = recover_outcome_summary(
                raw, contact="yes", green="no", distance_text="100.0ft")
            self.assertEqual(result["candidate_ranking"]["all_phase_stable_change_count"], 1)
            self.assertEqual(result["human_observation"]["displayed_distance_human"], 100)
            self.assertEqual(result["human_observation"]["displayed_unit_human"], "ft")
            self.assertEqual(result["human_observation"]["finished_on_green_human"], "no")
            self.assertIsNone(result["swing_dispatch"]["applied_frames"])
            self.assertFalse(result["candidate_ranking"]["game_score_verified"])
            self.assertFalse(result["recovery"]["live_dispatch_metadata_recovered"])
            self.assertEqual(len(raw.read_text().splitlines()), 6)

    def test_recovery_does_not_guess_swing_or_screen_state(self):
        with TemporaryDirectory() as d:
            raw = Path(d) / "outcome-X-RAW-PRIVATE.jsonl"
            fixture_raw(raw)
            result = recover_outcome_summary(
                raw, contact="yes", green="no", distance_text="100ft")
            self.assertIsNone(result["known_good_swing_request"]["trace_sha256"])
            self.assertFalse(result["recovery"]["screen_state_at_capture_verified"])

    def test_conflicting_labels_rejected(self):
        with TemporaryDirectory() as d:
            raw = Path(d) / "outcome-X-RAW-PRIVATE.jsonl"
            fixture_raw(raw)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                recover_outcome_summary(raw, contact="yes", green="no",
                                        distance_text="100ft", unit="m")
            with self.assertRaisesRegex(ValueError, "Contact/green"):
                recover_outcome_summary(raw, contact="hit", green="no",
                                        distance_text="100ft")

    def test_bad_partial_jsonl_is_not_saved_as_successful_evidence(self):
        with TemporaryDirectory() as d:
            raw = Path(d) / "outcome-X-RAW-PRIVATE.jsonl"
            raw.write_text(json.dumps(shot_row("pre", 1)) + "\n")
            with self.assertRaises(ValueError):
                recover_outcome_summary(raw, contact="yes", green="no",
                                        distance_text="100.0ft")

    def test_recovery_cli_isolated_and_no_overwrite(self):
        with TemporaryDirectory() as d:
            raw = Path(d) / "outcome-test-RAW-PRIVATE.jsonl"
            out = Path(d) / "outcome-test-candidates.json"
            fixture_raw(raw)
            cmd = [sys.executable, "-I", str(ROOT / "scripts" / "recover_outcome_capture.py"),
                   "--raw", str(raw), "--contact", "yes", "--green", "no",
                   "--distance", "100.0ft"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(out.read_text())["human_observation"]["displayed_unit_human"], "ft")
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Refusing to overwrite", second.stderr)
            self.assertEqual(len(raw.read_text().splitlines()), 6)


if __name__ == "__main__":
    unittest.main()
