"""Source-derived NW4R sine near-zero approximation; no native game data."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "research_p0_sinfidx_deadzone_public.py"
spec = importlib.util.spec_from_file_location("research_p0_sinfidx_deadzone_public", SCRIPT)
assert spec is not None and spec.loader is not None
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)

class SinFIdxDeadzoneTests(unittest.TestCase):
    def test_zero_knots_and_source_scale(self):
        self.assertEqual(study.f32(study.SOURCE_INDEX_GAIN * study.SOURCE_ANGLE_LIMIT), 448.0)
        for n in range(-3, 4):
            self.assertEqual(study.public_lut_sine_near_zero(study.f32(n * __import__("math").pi)), 0.0)

    def test_all_seven_zero_neighborhoods_are_small(self):
        rows = study.report()["zeros_within_conditional_domain"]
        self.assertEqual([r["multiple_of_pi"] for r in rows], list(range(-3, 4)))
        for row in rows:
            self.assertGreater(row["deadzone_width_rad_approx"], 0.0019)
            self.assertLess(row["deadzone_width_rad_approx"], 0.0021)
            self.assertLess(row["inside_left_rad_f32"], row["center_rad_f32"])
            self.assertGreater(row["inside_right_rad_f32"], row["center_rad_f32"])

    def test_last_inside_f32_then_first_outside(self):
        for n in (0,1,2,3):
            left = study.angle_boundary(n, "left")
            right = study.angle_boundary(n, "right")
            self.assertLess(abs(study.public_lut_sine_near_zero(left["inside"])),study.SOURCE_TAU)
            self.assertGreaterEqual(abs(study.public_lut_sine_near_zero(left["outside"])),study.SOURCE_TAU)
            self.assertLess(abs(study.public_lut_sine_near_zero(right["inside"])),study.SOURCE_TAU)
            self.assertGreaterEqual(abs(study.public_lut_sine_near_zero(right["outside"])),study.SOURCE_TAU)

    def test_outside_scope_and_invalid_inputs_abstain(self):
        for x in (float("nan"),float("inf"),-float("inf"),20.0):
            with self.assertRaises(ValueError):
                study.public_lut_sine_near_zero(x)
        with self.assertRaises(ValueError):
            study.public_lut_sine_near_zero(0.1)
        with self.assertRaises(ValueError):
            study.angle_boundary(4,"right")

    def test_explicit_no_native_or_ball_parity(self):
        x=study.report()
        self.assertFalse(x["native_f32_lut_parity_verified"])
        self.assertFalse(x["selected_ball_consumer_verified"])
        self.assertFalse(x["guest_shot_executed"])
        self.assertFalse(x["training_approved"])
        self.assertTrue(x["fastcast_truncation_assumed"])

if __name__ == "__main__":
    unittest.main()
