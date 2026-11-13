"""Offline numerical research tests: source-normalizer and non-face CCD."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def script(filename):
    path = Path(__file__).resolve().parents[1] / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    if spec is None or spec.loader is None:
        raise ValueError("SCRIPT_NOT_FOUND")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


class NumericalPhysicsBoundaryStudiesTests(unittest.TestCase):
    def test_nonface_contact_matches_analytic_geometry(self):
        r = script("research_p0_ccd_edge_vertex_analytic.py").evaluate()
        self.assertEqual(r["classification"], "SYNTHETIC_NOT_NATIVE")
        self.assertFalse(r["native_kcol_parity"])
        names = {row["case"]: row for row in r["cases"]}
        self.assertEqual(len(names), 7)
        for label in ("edge", "vertex", "fast_edge", "grazing_inside"):
            row = names[label]
            self.assertTrue(row["hit"], label)
            self.assertEqual(row["feature"], row["expected_feature"])
            for field in ("t_err", "surface_y_err", "center_y_err"):
                self.assertLess(row[field], 1e-6, (label, field))
        self.assertFalse(names["grazing_outside"]["hit"])
        self.assertTrue(names["fast_point"]["hit"])
        self.assertLess(names["fast_point"]["t_err"], 1e-8)
        self.assertTrue(names["time_split"]["hit"])
        self.assertLess(names["time_split"]["t_err"], 1e-7)

    def test_near_vertical_source_basis_does_not_fake_native_guard(self):
        r = script("research_p0_near_vertical_spin.py").run()
        self.assertFalse(r["native_normalization_guard_known"])
        self.assertTrue(r["source_vectors_normalized_when_eligible"])
        self.assertFalse(r["training_approved"])
        self.assertEqual(len(r["cases"]), 8)
        v0 = r["cases"][0]
        self.assertEqual(v0["raw_s"], 0)
        self.assertEqual(v0["raw_l"], 0)
        self.assertEqual(v0["up"], "REJECTED")
        self.assertGreater(v0["other"], 0)
        v_last = r["cases"][-1]
        self.assertGreater(v_last["raw_s"], 0)
        self.assertGreater(v_last["raw_l"], 0)
        self.assertGreater(v_last["up"], 0)


if __name__ == "__main__":
    unittest.main()
