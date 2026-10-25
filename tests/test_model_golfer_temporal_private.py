"""Synthetic offline tests. No Dolphin, RPC, game file or GitHub publication."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.modeling.golfer_temporal_private import (
    analyze_files, analyze_private_trajectory)


def synthetic():
    rows = []
    for n in range(6):
        main = bytearray(0x100)
        child = bytearray(0x80)
        struct.pack_into(">I", main, 0x74, 100 + n*10)
        struct.pack_into(">I", child, 0x50, 900 + n*10)
        # Additional private values should never survive in the summary.
        stage = (0 if n < 2 else 1 if n < 4 else 2)
        rows.append({
            "bytes_hex": main.hex(),
            "child_windows": {"+0x008": child.hex()},
            "frame_start": n*10,
            "frame_end": n*10+2,
            "phase": "aim_only" if stage == 1 else "idle",
            "stage": stage,
            "runtime_scene_address": "0x800BAD00",
            "watched_child_addresses": {"+0x008": "0x800BAD04"},
        })
    fields = [{"region": reg, "offset": off, "within_stage_changes": 3,
               "between_stage_changes": 2, "plausible_float_changes": 0}
              for reg, off in (("main", "+0x074"),
                               ("child_at_main+0x008", "+0x050"))]
    report = {
        "schema_version": 2, "kind": "local-golfer-memory-audit",
        "id": "golfer-synthetic-RAW-PRIVATE",
        "candidate_only": True,
        "source_claim": ("RPSysSceneMgr .sbss 0x804BF4D8..0x804BF4DF; "
                         "EGG::SceneManager +0xC/+0x18; EGG::Scene +0x1C/+0x20; "
                         "RPSportsBaseScene +0x54; RPGolScene +0x9C"),
        "source_static_slot_count": 2,
        "global_pointer_candidates": 1,
        "game_id": "RSPE01", "revision": 1, "game_mode": 4,
        "actual_scene_id_verified": True,
        "manager_backlink_verified": True,
        "creator_scene_id_not_used_for_identity": True,
        "matched_scene_chains": 1,
        "samples": 6, "max_non_atomic_frame_span": 2,
        "phase_sample_counts": {"idle": 4, "aim_only": 2},
        "first_level_child_parent_offsets": ["+0x008"],
        "first_level_child_watch_count": 1,
        "first_level_child_watch_truncated": True,
        "first_level_child_batch_start": 0,
        "power_verified": False,
        "club_rotation_verified": False,
        "changed_candidate_words": 2,
        "top_relative_changes": fields,
    }
    return rows, report


class PrivateTemporalTests(unittest.TestCase):
    def test_monotonic_clock_and_equal_delta_pattern_group(self):
        rows, report = synthetic()
        out = analyze_private_trajectory(rows, report)
        self.assertEqual(out["samples"], 6)
        self.assertEqual(out["analyzed_changed_words"], 2)
        self.assertEqual(out["distinct_delta_patterns"], 1)
        self.assertTrue(out["batch_incomplete"])
        for row in out["offset_patterns"]:
            self.assertTrue(row["changes_all_transitions"])
            self.assertTrue(row["constant_integer_step"])
            self.assertTrue(row["one_direction_monotonic"])
            self.assertTrue(row["integer_step_proportional_to_frame_gap"])
            self.assertEqual(row["delta_pattern_group"], 1)
        self.assertFalse(out["power_verified"])

    def test_private_information_never_reemitted(self):
        rows, report = synthetic()
        out = analyze_private_trajectory(rows, report)
        dumped = json.dumps(out)
        for forbidden in ("800BAD00", "800BAD04", "bytes_hex", "100", "900",
                          "runtime_scene_address", "frame_start",
                          "watched_child_addresses", "RAW-PRIVATE"):
            self.assertNotIn(forbidden, dumped)

    def test_malformed_frame_count_rejected(self):
        rows, report = synthetic()
        rows[2]["frame_start"] = rows[1]["frame_start"]
        with self.assertRaises(ValueError):
            analyze_private_trajectory(rows, report)

    def test_source_and_mode_gate_fail_closed(self):
        rows, report = synthetic()
        report["game_mode"] = 2
        with self.assertRaises(ValueError):
            analyze_private_trajectory(rows, report)

    def test_summary_counts_verified_against_private_bytes(self):
        rows, report = synthetic()
        report["top_relative_changes"][0]["within_stage_changes"] = 2
        with self.assertRaises(ValueError):
            analyze_private_trajectory(rows, report)

    def test_unrecorded_child_region_rejected(self):
        rows, report = synthetic()
        report["top_relative_changes"][1]["region"] = "child_at_main+0x020"
        with self.assertRaises(ValueError):
            analyze_private_trajectory(rows, report)

    def test_private_window_must_be_exact_and_bounded(self):
        rows, report = synthetic()
        rows[0]["bytes_hex"] = "00"
        with self.assertRaises(ValueError):
            analyze_private_trajectory(rows, report)

    def test_frame_ratio_different_for_fixed_step_with_irregular_frames(self):
        rows, report = synthetic()
        for i, row in enumerate(rows):
            row["frame_start"] = i * (i + 1) * 10
            row["frame_end"] = row["frame_start"] + 2
        out = analyze_private_trajectory(rows, report)
        self.assertTrue(out["offset_patterns"][0]["constant_integer_step"])
        self.assertFalse(out["offset_patterns"][0]["integer_step_proportional_to_frame_gap"])

    def test_file_cli_sidecar_never_overwrites(self):
        rows, report = synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "golfer-synthetic-RAW-PRIVATE.jsonl"
            meta = base / "golfer-synthetic-summary.json"
            output = base / "golfer-synthetic-temporal-summary.json"
            raw.write_text("".join(json.dumps(row)+"\n" for row in rows))
            meta.write_text(json.dumps(report))
            review = analyze_files(raw, meta, output)
            self.assertEqual(json.loads(output.read_text()), review)
            with self.assertRaises(ValueError):
                analyze_files(raw, meta, output)

    def test_mismatched_report_id_rejected_before_analysis(self):
        rows, report = synthetic()
        report["id"] = "not-this-capture"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "golfer-synthetic-RAW-PRIVATE.jsonl"
            meta = base / "golfer-synthetic-summary.json"
            raw.write_text("".join(json.dumps(row)+"\n" for row in rows))
            meta.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                analyze_files(raw, meta, base / "safe.json")


if __name__ == "__main__":
    unittest.main()
