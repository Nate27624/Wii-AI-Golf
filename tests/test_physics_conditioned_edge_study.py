"""Regression controls for independent conditioned-edge numerical research."""
import importlib.util
from pathlib import Path
import sys
import unittest


def study():
    path = Path(__file__).resolve().parents[1] / "scripts" / "research_p0_ccd_conditioned_edge_root.py"
    spec = importlib.util.spec_from_file_location("ccd_conditioned_edge_study", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("study module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ConditionedEdgeResearchTests(unittest.TestCase):
    def test_conditioned_reference_agrees_with_analytic_edge_hit(self):
        result = study().report()
        self.assertEqual(result["classification"], "SYNTHETIC_NUMERICAL_REFERENCE")
        self.assertFalse(result["native_kcol_parity_verified"])
        self.assertFalse(result["training_approved"])
        self.assertEqual(len(result["cases"]), 6)
        for row in result["cases"]:
            self.assertTrue(row["conditioned_hit"], row["span"])
            self.assertLess(row["time_error"], 1e-9, row)
            self.assertLess(row["radial_error"], 1e-6, row)
        self.assertEqual(result["outside_radius_misses"], [True, True])
        self.assertTrue(result["translation_hit"])

    def test_invalid_or_nonintersecting_edge_conditions(self):
        s = study()
        with self.assertRaises(ValueError):
            s.conditioned_edge_hit((0, 0, 0), (0, 0, 0),
                                   (0, 0, 0), (0, 0, 0), .5)
        with self.assertRaises(ValueError):
            s.conditioned_edge_hit((0, 0, 0), (0, 1, 0),
                                   (0, 0, 0), (2, 0, 0), -1.)
        self.assertIsNone(s.conditioned_edge_hit(
            (1, 2, 2), (1, -2, 2), (0, 0, 0), (2, 0, 0), .5))
        # Closest line crossing lies outside finite edge interior:
        self.assertIsNone(s.conditioned_edge_hit(
            (-4, 2, 0), (-4, -2, 0), (0, 0, 0), (2, 0, 0), .5))


if __name__ == "__main__":
    unittest.main()
