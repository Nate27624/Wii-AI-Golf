"""S002 synthetic controls: distinguish a periodic main word from aim-only child data."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from wii_ai_golf.audit.golfer_phase_specificity import analyze
import audit_golfer_phase_specificity as cli

RUN = "20261025T035500Z-a1b2c3d4"
SCENE = "0x80500000"
MAIN = "0x80502000"
CHILD_PTR = "0x80503000"


def raw_rows(*, include_child=True):
    result = []
    for i in range(9):
        stage = i // 3
        phase = "aim_only" if stage == 1 else "idle"
        main = bytearray(0x100)
        struct.pack_into(">I", main, 0x74, 100 + i)
        child = bytearray(0x80)
        # Child response ONLY during aim. Note that stage boundary changes
        # are excluded: only within-stage pairs are informative.
        struct.pack_into(">I", child, 0, i - 3 if stage == 1 else 0)
        result.append({
            "stage": stage, "phase": phase,
            "frame_start": i * 4, "frame_end": i * 4 + 2,
            "runtime_scene_address": SCENE,
            "runtime_golf_main_address": MAIN,
            "bytes_hex": main.hex(),
            "child_windows": {"+0x020": child.hex()} if include_child else {},
            "watched_child_addresses": {"+0x020": CHILD_PTR} if include_child else {},
        })
    return result


class GolferPhaseSpecificityTests(unittest.TestCase):
    def test_dynamic_counter_is_not_mistaken_for_aim_response(self):
        r = analyze(raw_rows(), run_id=RUN)
        self.assertEqual(r["sample_count"], 9)
        self.assertEqual(r["idle_samples"], 6)
        self.assertEqual(r["idle_opportunities"], 4)
        self.assertEqual(r["aim_opportunities"], 2)
        self.assertEqual(r["candidate_child_regions"], 1)
        self.assertEqual(r["changed_word_count"], 2)
        rows = {(x["region"], x["relative_offset"]): x
                for x in r["top_relative_words"]}
        self.assertEqual(rows[("main", "+0x074")]["control_class"], "background_dynamic")
        self.assertEqual(rows[("main", "+0x074")]["idle_changes"], 4)
        self.assertEqual(rows[("child_at_main+0x020", "+0x000")]["control_class"],
                         "aim_enriched_control_candidate")
        self.assertEqual(rows[("child_at_main+0x020", "+0x000")]["idle_changes"], 0)
        self.assertFalse(r["power_verified"])
        self.assertNotIn("8050", json.dumps(r))
        self.assertNotIn("bytes_hex", json.dumps(r))

    def test_negative_no_changed_words_remains_valid(self):
        rows = raw_rows(include_child=False)
        for row in rows:
            main = bytearray.fromhex(row["bytes_hex"])
            struct.pack_into(">I", main, 0x74, 1)
            row["bytes_hex"] = main.hex()
        r = analyze(rows, run_id=RUN)
        self.assertEqual(r["changed_word_count"], 0)
        self.assertEqual(r["top_relative_words"], [])

    def test_wrong_scene_or_pointer_relocation_rejected(self):
        for target, value in [
            ("runtime_scene_address", "0x80509000"),
            ("runtime_golf_main_address", "0x80509000"),
        ]:
            rows = raw_rows()
            rows[4][target] = value
            with self.subTest(field=target), self.assertRaisesRegex(ValueError, "relocated"):
                analyze(rows, run_id=RUN)
        rows = raw_rows()
        rows[4]["watched_child_addresses"]["+0x020"] = "0x80507000"
        with self.assertRaisesRegex(ValueError, "relocated"):
            analyze(rows, run_id=RUN)

    def test_reject_overlapping_frames_and_invalid_phase(self):
        rows = raw_rows()
        rows[4]["frame_start"] = rows[3]["frame_end"] - 1
        with self.assertRaisesRegex(ValueError, "frame"):
            analyze(rows, run_id=RUN)
        rows = raw_rows()
        rows[5]["phase"] = "shot_attempt"
        with self.assertRaisesRegex(ValueError, "stage"):
            analyze(rows, run_id=RUN)

    def test_reject_truncated_or_malformed_windows(self):
        rows = raw_rows()
        rows[3]["bytes_hex"] = "00"
        with self.assertRaisesRegex(ValueError, "window"):
            analyze(rows, run_id=RUN)
        rows = raw_rows()
        rows[5]["child_windows"] = {}
        with self.assertRaisesRegex(ValueError, "provenance"):
            analyze(rows, run_id=RUN)

    def test_no_git_attempt_for_invalid_raw_or_rejected_schema(self):
        # In current main the public kind is intentionally not allowlisted;
        # publication must fail closed and preserve sanitized output.
        with self.assertRaises(ValueError):
            analyze(raw_rows(), run_id="../secret")
        with patch.object(cli, "CAPTURES", Path("/tmp/do-not-use-s002-private")):
            with self.assertRaises(ValueError):
                cli.load_private(Path("/tmp/elsewhere/example.jsonl"))


if __name__ == "__main__":
    unittest.main()
