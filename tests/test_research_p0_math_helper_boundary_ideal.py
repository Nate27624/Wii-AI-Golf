"""Synthetic-only threshold and source-provenance checks, no native data."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import math
import unittest

FILE=Path(__file__).resolve().parents[1] / "scripts" / "research_p0_math_helper_boundary_ideal.py"
spec=importlib.util.spec_from_file_location("research_p0_math_helper_boundary_ideal",FILE)
assert spec is not None and spec.loader is not None
study=importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)

class BoundaryIdealStudyTests(unittest.TestCase):
    def test_f32_predecessor_and_cutoff(self):
        below=study.previous_positive_f32(study.TAU)
        self.assertLess(below,study.TAU)
        self.assertEqual(study.f32(below),below)
        self.assertEqual(study.signed_power_ideal(study.PARAM_EASE,below),0.0)
        self.assertGreater(study.signed_power_ideal(study.PARAM_EASE,study.TAU),0.0)

    def test_negative_sign_and_guard(self):
        at=study.signed_power_ideal(study.PARAM_SINE,study.TAU)
        self.assertAlmostEqual(study.signed_power_ideal(study.PARAM_SINE,-study.TAU),-at)
        self.assertEqual(study.signed_power_ideal(-1.0,0.5),0.0)
        self.assertEqual(study.signed_power_ideal(0.0,0.5),0.0)

    def test_reject_specials(self):
        for invalid in (float("nan"),float("inf"),-float("inf")):
            with self.assertRaises(ValueError):
                study.signed_power_ideal(study.PARAM_EASE,invalid)
            with self.assertRaises(ValueError):
                study.signed_power_ideal(invalid,0.5)

    def test_both_source_parameters_and_no_native_claim(self):
        result=study.report()
        self.assertEqual(result["source_f32_threshold"],study.TAU)
        self.assertGreater(result["normal_finite_parameter_0p85"]["ideal_weight_gain_ratio"],4.0)
        self.assertGreater(result["normal_finite_parameter_0p55"]["ideal_calc_0x1B0_jump_over_q"],0.01)
        self.assertFalse(result["native_nw4r_table_parity_verified"])
        self.assertFalse(result["guest_executed_shot_verified"])
        self.assertFalse(result["accepted_ball_launch_verified"])
        self.assertFalse(result["training_approved"])
        self.assertTrue(math.isfinite(result["normal_finite_parameter_0p55"]["ideal_exponent"]))

if __name__ == "__main__":
    unittest.main()
