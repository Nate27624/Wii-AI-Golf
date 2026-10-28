"""Fabricated-only tests for RPGolMain+0x74. Never load real RAM."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_main_counter74_private as a


def capture(counter, ball=(0, 0, 0), *, owner=3, selector=10):
    return {
        "main_counter": counter,
        "owner": (1, 2, owner, 4, 5, 6, 7, 8, 9, 10),
        "selection": (0, 1, 8, selector, 12),
        "pin": (101, 102, 103),
        "tee": (201, 202, 203),
        "ball": ball,
    }


def fixture():
    s = {n: capture(100 + n) for n in range(1, 8)}
    s[1] = capture(10, (1, 1, 1))
    s[2] = capture(40, (3, 3, 3))
    s[5] = capture(80, (5, 5, 5))
    s[6] = capture(90, (6, 6, 6))
    s[7] = capture(130, (7, 7, 7))
    return s


class CounterTests(unittest.TestCase):
    def test_normal_increasing_counter_is_not_time_verified(self):
        result = a.summarize(fixture())
        self.assertTrue(result["wedge_main_plus_0x74_strictly_numerically_increasing"])
        self.assertEqual(result["wedge_increment_comparison_if_strictly_increasing"],
                         "earlier_numerical_increment_smaller")
        self.assertFalse(result["counter_is_guest_frame_number_verified"])
        self.assertFalse(result["counter_is_swing_power_verified"])
        self.assertFalse(result["training_approved"])

    def test_only_human_same_shot_edges_compared(self):
        rows = a.summarize(fixture())["comparisons"]
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["human_phase_edge_unverified_frame_link"] for r in rows], [
            "driver_airborne_to_settled", "wedge_near_apex_to_descent",
            "wedge_descent_to_flag_ui", "wedge_near_apex_to_flag_ui"])
        self.assertEqual([r["ball_changed_components_of_three"] for r in rows],
                         [3, 3, 3, 3])

    def test_counter_unchanged_not_fabricated_motion_time(self):
        samples = fixture()
        samples[6]["main_counter"] = samples[5]["main_counter"]
        result = a.summarize(samples)
        self.assertEqual(result["comparisons"][1]["main_plus_0x74_numerical_order"],
                         "unchanged")
        self.assertFalse(result["wedge_main_plus_0x74_strictly_numerically_increasing"])

    def test_backwards_may_be_wrap_or_reset(self):
        samples = fixture()
        samples[6]["main_counter"] = 12
        result = a.summarize(samples)
        self.assertEqual(result["comparisons"][1]["main_plus_0x74_numerical_order"],
                         "numerically_decreased_or_wrapped_unknown")
        self.assertFalse(result["counter_is_monotonic_game_tick_verified"])

    def test_equal_early_late_increments(self):
        samples = fixture()
        samples[7]["main_counter"] = 100
        self.assertEqual(a.summarize(samples)["wedge_increment_comparison_if_strictly_increasing"],
                         "increments_equal")

    def test_earlier_increment_larger(self):
        samples = fixture()
        samples[6]["main_counter"] = 120
        self.assertEqual(a.summarize(samples)["wedge_increment_comparison_if_strictly_increasing"],
                         "earlier_numerical_increment_larger")

    def test_selection_mismatch_fails_closed(self):
        samples = fixture()
        samples[6]["selection"] = (0, 1, 8, 20, 12)
        with self.assertRaises(ValueError):
            a.summarize(samples)

    def test_object_identity_mismatch_fails_closed(self):
        samples = fixture()
        samples[7]["owner"] = (1, 2, 99, 4, 5, 6, 7, 8, 9, 10)
        with self.assertRaises(ValueError):
            a.summarize(samples)

    def test_pin_or_tee_change_fails_closed(self):
        for key in ("pin", "tee"):
            samples = fixture()
            samples[6][key] = (111, 112, 113)
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.summarize(samples)

    def test_invalid_u32_width_or_type_fails_closed(self):
        for value in (-1, 1 << 32, 4.0, None, True):
            samples = fixture()
            samples[6]["main_counter"] = value
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                a.summarize(samples)

    def test_malformed_missing_phase_fails_closed(self):
        s = fixture()
        del s[4]
        with self.assertRaises(ValueError):
            a.summarize(s)

    def test_output_contains_no_counter_words_or_private_objects(self):
        result = a.summarize(fixture())
        out = json.dumps(result, sort_keys=True)
        for text in ('"owner"', '"selection"', '"pin":', '"ball":', 
                     '"main_counter":', '"main_ptr"', "sha256_private",
                     "raw_ram", "private_path", "source_pointer"):
            self.assertNotIn(text, out)
        self.assertFalse(result["allowed_to_publish"])
        self.assertFalse(result["same_emulator_boot_across_captures_machine_verified"])

    def test_archive_sha_gate_is_before_any_native_read(self):
        with patch.object(a.seven, "_check_archive", side_effect=ValueError("bad SHA")):
            with self.assertRaises(ValueError):
                a.analyze(Path("missing-private"))

    def test_isolated_python_help_imports_checkout_siblings(self):
        script = ROOT / "scripts" / "audit_p0_seven_main_counter74_private.py"
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run([sys.executable, "-I", str(script), "--help"],
                                  cwd=temp, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--archive", proc.stdout)
        self.assertNotIn("ModuleNotFoundError", proc.stderr)


if __name__ == "__main__":
    unittest.main()
