"""Synthetic no-ROM/no-emulator tests for source-supported environment candidates."""
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.environment_state_candidate import audit_environment_snapshots


def put(b, off, value):
    struct.pack_into(">I", b, off, value)


def sample(frame=100, phase="pre", hole=0, pin=0x80050000):
    cfg = bytearray(0x1C74)
    field = bytearray(0xA8)
    put(cfg, 0x94, 4)
    put(cfg, 0x98, hole)
    put(field, 0x3C, 4)
    put(field, 0x48, 3)
    put(field, 0x44, pin)
    put(field, 0x50, 0x80051000)
    put(field, 0x54, 0x80052000)
    put(field, 0x68, 0x80053000)
    put(field, 0x70, 0x80054000)
    put(field, 0x18, 0x80055000)
    field[0x6C] = 1
    field[0x7C] = 0
    field[0x88] = 1
    return {"schema_version": 1,
            "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
            "game_id": "RSPE01", "disc_revision": 1,
            "game_mode_raw": 4, "phase": phase,
            "frame_start": frame, "frame_end": frame + 6,
            "non_atomic_frame_span": 6,
            "windows": {
                "golf_config": {"address": "0x80040000", "bytes_hex": cfg.hex()},
                "golf_field": {"address": "0x80044000", "bytes_hex": field.hex()},
                "minimap_ball_effect": {"address": "0x80057000", "bytes_hex": "00"*0x200},
            }}


class EnvironmentCandidateTests(unittest.TestCase):
    def test_source_known_candidates_no_physics_claim(self):
        result = audit_environment_snapshots([sample(), sample(120, "post"), sample(140, "settled")])
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["source_candidate_current_hole_raw"], 0)
        self.assertEqual(result["source_candidate_game_mode"], 4)
        self.assertTrue(result["object_refs"]["pin"]["present_every_snapshot"])
        self.assertFalse(result["object_refs"]["pin"]["changed_during_capture"])
        self.assertTrue(result["visual_flags"]["wind_arrow_visible"]["true_in_all_samples"])
        for key in ("ball_xyz_verified", "pin_xyz_verified", "wind_speed_direction_verified",
                    "course_terrain_verified", "game_state_machine_verified"):
            self.assertFalse(result[key])
        output = json.dumps(result)
        for forbidden in ("0x80050000", "0x80040000", "80053000", "bytes_hex", "local_path"):
            self.assertNotIn(forbidden, output)

    def test_pin_pointer_change_does_not_identify_xyz(self):
        data = [sample(), sample(120, "post", pin=0x80059000)]
        r = audit_environment_snapshots(data)
        self.assertTrue(r["object_refs"]["pin"]["changed_during_capture"])
        self.assertFalse(r["pin_xyz_verified"])

    def test_hole_changes_are_annotated_without_inference(self):
        r = audit_environment_snapshots([sample(), sample(120, "post", hole=1)])
        self.assertIsNone(r["source_candidate_current_hole_raw"])
        self.assertTrue(r["hole_value_changed_in_capture"])

    def test_reject_wrong_disc_and_mode(self):
        for key, value in [("game_id", "RSPP01"), ("disc_revision", 0),
                           ("disc_revision", True), ("game_mode_raw", 3)]:
            row = sample()
            row[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit_environment_snapshots([row])

    def test_reject_mismatched_source_bytes(self):
        row = sample()
        raw = bytearray.fromhex(row["windows"]["golf_config"]["bytes_hex"])
        put(raw, 0x94, 9)
        row["windows"]["golf_config"]["bytes_hex"] = raw.hex()
        with self.assertRaises(ValueError):
            audit_environment_snapshots([row])

    def test_reject_invalid_pointer(self):
        with self.assertRaisesRegex(ValueError, "pointer"):
            audit_environment_snapshots([sample(pin=0xDEADBEEF)])

    def test_reject_moved_instance_and_reverse_frames(self):
        rows = [sample(), sample(120, "post")]
        rows[1]["windows"]["golf_config"]["address"] = "0x80060000"
        with self.assertRaises(ValueError):
            audit_environment_snapshots(rows)
        with self.assertRaises(ValueError):
            audit_environment_snapshots([sample(), sample(105, "post")])

    def test_reject_partial_or_bad_byte_windows(self):
        for subcase in ("missing", "truncated", "invalidhex", "wrongbase"):
            row = sample()
            win = row["windows"]["golf_field"]
            if subcase == "missing":
                del row["windows"]["golf_field"]
            elif subcase == "truncated":
                win["bytes_hex"] = win["bytes_hex"][:-4]
            elif subcase == "invalidhex":
                win["bytes_hex"] = "Z" * len(win["bytes_hex"])
            else:
                win["address"] = "0x00000000"
            with self.subTest(subcase=subcase), self.assertRaises(ValueError):
                audit_environment_snapshots([row])

    def test_reject_nonboolean_flag_and_implausible_hole_count(self):
        for offset, value in ((0x6C, 3), (0x7C, 255), (0x88, 2)):
            row = sample()
            field = bytearray.fromhex(row["windows"]["golf_field"]["bytes_hex"])
            field[offset] = value
            row["windows"]["golf_field"]["bytes_hex"] = field.hex()
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                audit_environment_snapshots([row])
        with self.assertRaises(ValueError):
            audit_environment_snapshots([sample(hole=100)])

    def test_reject_unbounded_rows(self):
        with self.assertRaises(ValueError):
            audit_environment_snapshots([])
        with self.assertRaises(ValueError):
            audit_environment_snapshots([sample()] * 101)

    def test_do_not_assume_phase_independent(self):
        with self.assertRaises(ValueError):
            audit_environment_snapshots([sample(), sample(120, "settled"), sample(140, "pre")])
        result = audit_environment_snapshots([sample(), sample(120)])
        self.assertEqual(result["phase_sample_counts"], {"pre": 2})
        self.assertFalse(result["timing_fine_enough_for_frame_events"])


if __name__ == "__main__":
    unittest.main()
