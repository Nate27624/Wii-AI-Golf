"""Offline synthetic physics study regression; never opens private game data."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def study(filename):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PhysicsResearchLocalOpsTests(unittest.TestCase):
    def test_source_basis_orthogonality(self):
        module = study("research_p0_spin_basis_differential.py")
        r = module.report()
        self.assertEqual(r["status"], "SYNTHETIC_COMPARISON")
        self.assertFalse(r["native_selected_ball_parity_verified"])
        self.assertEqual(len(r["cases"]), 5)
        for item in r["cases"]:
            self.assertAlmostEqual(item["source_lift_dot_v"], 0., places=8)
            self.assertAlmostEqual(item["source_lateral_dot_v"], 0., places=8)
            self.assertAlmostEqual(item["source_lift_dot_lateral"], 0., places=8)
            self.assertEqual(item["provisional_default_spin_delta_v"], 0.)
        self.assertGreater(
            r["cases"][0]["provisional_explicit_spin_delta_v"], 0.)

    def test_geometry_transformation_comparison(self):
        module = study("research_p0_contact_invariance.py")
        r = module.report()
        self.assertEqual(r["status"], "SYNTHETIC_COMPARISON")
        self.assertFalse(r["native_collision_parity_verified"])
        self.assertTrue(r["query_radius_not_ball_radius"])
        self.assertEqual(len(r["cases"]), 8)
        for item in r["cases"]:
            self.assertEqual(item["status"], "COMPARABLE_HIT")
            for field in ("time_difference", "center_xyz_difference",
                          "surface_xyz_difference"):
                self.assertTrue(math.isfinite(item[field]))
                self.assertGreaterEqual(item[field], 0.)
        for item in r["cases"]:
            if item["variant"] in ("winding_reversed", "double_scale"):
                self.assertLess(item["center_xyz_difference"], 1e-7)
                self.assertLess(item["surface_xyz_difference"], 1e-7)


if __name__ == "__main__":
    unittest.main()
