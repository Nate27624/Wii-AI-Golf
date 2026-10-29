"""Synthetic privacy-preserving phase jointness tests; no emulator or RAM files."""
from __future__ import annotations

import json
import struct
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.environment_phase_joint import (
    classify_one_environment_capture, summarize_phase_joint_cohort,
)


def put(b, off, x):
    struct.pack_into(">I", b, off, x)


def snapshot(phase, frame, pin, start, minimap=1, wind_arrow=1):
    cfg, field = bytearray(0x1C74), bytearray(0xA8)
    put(cfg, 0x94, 4)
    put(cfg, 0x98, 1)
    put(field, 0x3C, 6)
    put(field, 0x48, 31)
    for name, off, val in (
        ("map_data", 0x18, 0x80060000),
        ("pin", 0x44, pin),
        ("start", 0x50, start),
        ("cup", 0x54, 0x80060020),
        ("wind", 0x68, 0x80060040),
        ("course", 0x70, 0x80060060),
    ):
        put(field, off, val)
    field[0x6C] = wind_arrow
    field[0x7C] = 0
    field[0x88] = minimap
    return {
        "schema_version": 1,
        "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
        "game_id": "RSPE01", "disc_revision": 1, "game_mode_raw": 4,
        "phase": phase, "frame_start": frame,
        "frame_end": frame + 22, "non_atomic_frame_span": 22,
        "windows": {
            "golf_config": {"address": "0x80040000", "bytes_hex": cfg.hex()},
            "golf_field": {"address": "0x80044000", "bytes_hex": field.hex()},
        }
    }


def capture(transition="joint"):
    phases = ("pre", "pre", "pre", "post", "post",
              "settled", "settled", "settled")
    p1, s1 = 0x80051000, 0x80052000
    p2, s2 = 0x80053000, 0x80054000
    rows = []
    for i, phase in enumerate(phases):
        pin = p2 if i >= 3 and transition in ("joint", "pin_only") else p1
        start = s2 if i >= 3 and transition in ("joint", "start_only") else s1
        ui = 0 if i >= 3 and transition == "joint" else 1
        rows.append(snapshot(phase, 100 + 30*i, pin, start, minimap=ui))
    return rows


class JointEnvironmentPhaseTests(unittest.TestCase):
    def test_joint_changes_are_exact_adjacent_stage_pairs(self):
        report = classify_one_environment_capture(capture("joint"))
        self.assertTrue(report["pin_changed"])
        self.assertTrue(report["start_changed"])
        self.assertTrue(report["pin_start_changed_same_pair"])
        self.assertEqual(report["pin_start_joint_pair_count"], 1)
        self.assertEqual(report["pin_start_joint_edge_count"]["pre_to_post"], 1)
        self.assertEqual(report["ui_change_edge_count"]["pre_to_post"], 1)
        self.assertEqual(report["ui_changed_on_joint_pair_count"], 1)
        self.assertEqual(report["pin_change_edge_count"]["within_pre"], 0)
        self.assertEqual(report["boundary_comparison_count"]["pre_to_post"], 1)
        self.assertEqual(report["max_frame_span"], 22)

    def test_one_sided_change_is_not_a_joint_scene_claim(self):
        a = classify_one_environment_capture(capture("pin_only"))
        self.assertTrue(a["pin_changed"])
        self.assertFalse(a["start_changed"])
        self.assertFalse(a["pin_start_changed_same_pair"])
        b = classify_one_environment_capture(capture("start_only"))
        self.assertFalse(b["pin_changed"])
        self.assertTrue(b["start_changed"])
        self.assertFalse(b["pin_start_changed_same_pair"])

    def test_cross_capture_summary_counts_and_privacy(self):
        r = summarize_phase_joint_cohort([
            capture("joint"), capture("pin_only"), capture("start_only"),
            capture("none")
        ])
        self.assertEqual(r["capture_file_count"], 4)
        self.assertEqual(r["total_snapshot_count"], 32)
        self.assertEqual(r["pin_changed_file_count"], 2)
        self.assertEqual(r["start_changed_file_count"], 2)
        self.assertEqual(r["both_changed_file_count"], 1)
        self.assertEqual(r["pin_only_changed_file_count"], 1)
        self.assertEqual(r["start_only_changed_file_count"], 1)
        self.assertEqual(r["neither_changed_file_count"], 1)
        self.assertEqual(r["both_changed_on_same_adjacent_pair_file_count"], 1)
        self.assertEqual(r["pin_start_joint_edge_counts"]["pre_to_post"], 1)
        self.assertEqual(r["ui_changed_on_joint_pair_total"], 1)
        self.assertEqual(r["max_non_atomic_frame_span"], 22)
        self.assertFalse(r["independent_boots_verified"])
        self.assertFalse(r["pin_world_position_verified"])
        self.assertFalse(r["pointer_change_caused_by_action_verified"])
        value = json.dumps(r)
        self.assertNotIn("0x8005", value)
        self.assertNotIn("bytes_hex", value)
        self.assertNotIn("address", set(r))
        self.assertNotIn("file_path", set(r))

    def test_no_ui_change_does_not_invalidate_joint_pointer_change(self):
        rows = capture("joint")
        for row in rows:
            field = bytearray.fromhex(row["windows"]["golf_field"]["bytes_hex"])
            field[0x88] = 1
            row["windows"]["golf_field"]["bytes_hex"] = field.hex()
        r = classify_one_environment_capture(rows)
        self.assertEqual(r["pin_start_joint_pair_count"], 1)
        self.assertEqual(r["ui_changed_on_joint_pair_count"], 0)

    def test_missing_post_stage_is_an_explicit_blocker(self):
        rows = [x for x in capture("joint") if x["phase"] != "post"]
        with self.assertRaises(ValueError):
            classify_one_environment_capture(rows)

    def test_wrong_revision_or_pointer_shape_fails_before_comparison(self):
        rows = capture("joint")
        rows[0]["disc_revision"] = 0
        with self.assertRaises(ValueError):
            classify_one_environment_capture(rows)
        rows = capture("joint")
        raw = bytearray.fromhex(rows[0]["windows"]["golf_field"]["bytes_hex"])
        put(raw, 0x44, 0xDEADBEEF)
        rows[0]["windows"]["golf_field"]["bytes_hex"] = raw.hex()
        with self.assertRaises(ValueError):
            classify_one_environment_capture(rows)

    def test_bounds_and_chronology(self):
        with self.assertRaises(ValueError):
            summarize_phase_joint_cohort([capture("joint")])
        with self.assertRaises(ValueError):
            summarize_phase_joint_cohort([capture("none")] * 65)
        rows = capture("joint")
        rows[3]["frame_start"] = 110
        with self.assertRaises(ValueError):
            classify_one_environment_capture(rows)

    def test_stage_data_not_misreported_as_verified_game_phase(self):
        r = summarize_phase_joint_cohort([capture("joint"), capture("none")])
        self.assertFalse(r["game_phase_semantics_verified"])
        self.assertFalse(r["ball_world_position_verified"])
        self.assertFalse(r["independent_boots_verified"])


if __name__ == "__main__":
    unittest.main()
