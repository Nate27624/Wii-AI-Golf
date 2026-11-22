"""Independent synthetic truth tests, not production-CCD snapshot tests."""
from decimal import Decimal, localcontext
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_p0_ccd_precision_oracle_v2 as oracle


class FirstEntryDecimalTruth(unittest.TestCase):
    def test_edge_h_ladder_center_and_surface_are_first_entry(self):
        with localcontext() as ctx:
            ctx.prec = oracle.PRECISION
            y = Decimal("0.1875").sqrt()
            for h in (2, 100, 10000, 100000, 1000000, 10**8, 10**10, 10**14, 10**16):
                r = oracle.analytic_vertical("edge", str(h), str(-h))
                self.assertEqual(r["status"], "HIT", h)
                self.assertEqual(r["feature"], "edge")
                center = tuple(map(Decimal, r["first_center_xyz_decimal"]))
                self.assertEqual(center[0], Decimal(1))
                self.assertEqual(center[2], Decimal("-0.25"))
                self.assertLess(abs(center[1] - y), Decimal("1e-90"))
                self.assertEqual(tuple(map(Decimal, r["surface_xyz_decimal"])),
                                 (Decimal(1), Decimal(0), Decimal(0)))
                self.assertLess(abs(Decimal(r["t_decimal"]) -
                                    (Decimal(h)-y)/(2*Decimal(h))), Decimal("1e-90"))
                self.assertLess(abs(Decimal(r["squared_radius_residual_decimal"])),
                                Decimal("1e-90"))
                self.assertFalse(r["native_kcol_parity_verified"])
                self.assertFalse(r["training_approved"])

    def test_vertex_h_ladder_center_and_point_surface_are_first_entry(self):
        with localcontext() as ctx:
            ctx.prec = oracle.PRECISION
            y = Decimal("0.23").sqrt()
            for h in (2, 10000, 100000, 1000000, 10**8, 10**10, 10**16):
                r = oracle.analytic_vertical("vertex", str(h), str(-h))
                self.assertEqual(r["status"], "HIT", h)
                self.assertEqual(r["feature"], "vertex")
                center = tuple(map(Decimal, r["first_center_xyz_decimal"]))
                self.assertEqual((center[0], center[2]),
                                 (Decimal("-0.1"), Decimal("-0.1")))
                self.assertLess(abs(center[1]-y), Decimal("1e-90"))
                self.assertEqual(tuple(map(Decimal, r["surface_xyz_decimal"])),
                                 (Decimal(0), Decimal(0), Decimal(0)))
                self.assertLess(abs(Decimal(r["squared_radius_residual_decimal"])),
                                Decimal("1e-90"))

    def test_float64_normalized_time_can_collapse_while_first_center_does_not(self):
        fine = oracle.analytic_vertical("edge", "100000000", "-100000000")
        boundary = oracle.analytic_vertical("edge", "10000000000000000", "-10000000000000000")
        self.assertEqual(fine["time_resolution"], "BINARY64_TIME_DISTINCT")
        self.assertEqual(boundary["time_resolution"], "ABSTAIN_BINARY64_TIME_COLLAPSE")
        self.assertEqual(boundary["t_float64"], 0.5)
        self.assertAlmostEqual(float(Decimal(boundary["first_center_xyz_decimal"][1])),
                               math.sqrt(3)/4, places=14)
        self.assertEqual(boundary["float64_reconstructed_local_y"], 0.0)
        self.assertGreater(abs(boundary["float64_local_y_error"]), 0.4)
        self.assertEqual(float(Decimal(boundary["t_decimal"])) , 0.5)
        # The distinct representable number immediately below 0.5 is only 2**-54 away.
        self.assertEqual(0.5 - math.nextafter(0.5, 0), 2**-54)

    def test_exact_tangent_and_strictly_inside_at_short_span(self):
        tangent = oracle.analytic_vertical("tangent", "0.01", "-0.01")
        self.assertEqual(tangent["status"], "HIT")
        self.assertEqual(Decimal(tangent["t_decimal"]), Decimal("0.5"))
        self.assertEqual(tuple(map(Decimal, tangent["first_center_xyz_decimal"])),
                         (Decimal(1), Decimal(0), Decimal("-0.5")))
        self.assertEqual(tangent["surface_xyz_decimal"], ["1", "0", "0"])
        self.assertEqual(tuple(map(Decimal, tangent["outward_normal_decimal"])),
                         (Decimal(0), Decimal(0), Decimal(-1)))
        inside = oracle.analytic_vertical("near_inside", "0.01", "-0.01")
        self.assertEqual(inside["status"], "HIT")
        self.assertGreater(Decimal(inside["first_center_xyz_decimal"][1]), 0)
        self.assertGreater(Decimal(inside["t_decimal"]), 0)
        self.assertLess(Decimal(inside["t_decimal"]), Decimal("0.5"))
        self.assertLess(abs(Decimal(inside["squared_radius_residual_decimal"])), Decimal("1e-90"))

    def test_one_f32_ulp_outside_stays_miss_at_every_subdivision(self):
        self.assertEqual(float(oracle.ONE_F32_ULP_OUTSIDE),
                         oracle.f32(-0.5 - 5e-8))
        self.assertLess(oracle.ONE_F32_ULP_OUTSIDE, Decimal("-0.5"))
        for h in ("0.001", "0.01", "0.1", "1", "100000"):
            r = oracle.analytic_vertical("one_f32_ulp_outside", h, str(-Decimal(h)))
            self.assertEqual(r["status"], "MISS")
            self.assertLess(Decimal(r["radial_gap2"]), 0)
        for n in (1, 2, 4, 5, 8, 10, 20, 40, 100, 200):
            m = oracle.split_path("one_f32_ulp_outside", "0.1", n, quantize_f32=True)
            self.assertEqual(m["expected"], "MISS", n)
            self.assertIsNone(m["first"])

    def test_split_true_entry_has_identical_world_position_and_global_time(self):
        single = oracle.analytic_vertical("edge", "2", "-2")
        for n in (1, 2, 3, 4, 10, 50):
            split = oracle.split_path("edge", "2", n)
            self.assertEqual(split["expected"], "HIT")
            self.assertEqual(split["first"]["center_xyz_decimal"],
                             single["first_center_xyz_decimal"])
            with localcontext() as ctx:
                ctx.prec = oracle.PRECISION
                self.assertLess(abs(Decimal(split["first"]["t_global_decimal"])-
                                    Decimal(single["t_decimal"])), Decimal("1e-90"))

    def test_reversed_direction_enters_from_opposite_side(self):
        fwd = oracle.analytic_vertical("edge", "100000", "-100000")
        rev = oracle.analytic_vertical("edge", "-100000", "100000")
        self.assertEqual(fwd["status"], rev["status"])
        self.assertEqual(fwd["t_decimal"], rev["t_decimal"])
        self.assertEqual(fwd["surface_xyz_decimal"], rev["surface_xyz_decimal"])
        with localcontext() as ctx:
            ctx.prec = oracle.PRECISION
            self.assertEqual(Decimal(fwd["first_center_xyz_decimal"][1]),
                             -Decimal(rev["first_center_xyz_decimal"][1]))
        self.assertLess(Decimal(rev["first_center_xyz_decimal"][1]), 0)

    def test_translation_preserves_first_entry_t_and_relative_geometry(self):
        a = oracle.analytic_vertical("vertex", "100000", "-100000")
        shift = (10000, 250, -30000)
        b = oracle.analytic_vertical("vertex", "100000", "-100000", shift)
        self.assertEqual(a["t_decimal"], b["t_decimal"])
        self.assertEqual(a["outward_normal_decimal"], b["outward_normal_decimal"])
        for av, bv, off in zip(a["first_center_xyz_decimal"],
                               b["first_center_xyz_decimal"], shift):
            self.assertEqual(Decimal(bv)-Decimal(av), Decimal(off))
        for av, bv, off in zip(a["surface_xyz_decimal"],
                               b["surface_xyz_decimal"], shift):
            self.assertEqual(Decimal(bv)-Decimal(av), Decimal(off))

    def test_zero_length_and_initial_overlap_abstention(self):
        self.assertEqual(oracle.analytic_vertical("edge", "1", "1")["status"],
                         "MISS_ZERO_LENGTH")
        self.assertEqual(oracle.analytic_vertical("edge", "0", "0")["status"],
                         "ABSTAIN_INITIAL_OVERLAP")
        self.assertEqual(oracle.analytic_vertical("edge", "0", "1")["status"],
                         "ABSTAIN_INITIAL_OVERLAP")
        self.assertEqual(oracle.analytic_vertical("edge", "2", "1")["status"], "MISS")
        self.assertEqual(oracle.analytic_vertical("one_f32_ulp_outside", "0", "0")["status"],
                         "MISS")

    def test_invalid_input_fails_closed(self):
        for f in ("invalid", "face"):
            with self.assertRaises(ValueError):
                oracle.analytic_vertical(f, "2", "-2")
        with self.assertRaises(TypeError):
            oracle.analytic_vertical("edge", 2.0, -2.0)
        with self.assertRaises(ValueError):
            oracle.analytic_vertical("edge", "NaN", "1")
        with self.assertRaises(ValueError):
            oracle.analytic_vertical("edge", "2", "-2", (1, 2))
        with self.assertRaises(ValueError):
            oracle.split_path("edge", 2, 0)
        with self.assertRaises(ValueError):
            oracle.split_path("edge", 2, 201)


class ObservationalContract(unittest.TestCase):
    def test_report_is_quarantined_and_bounded(self):
        r = oracle.report(compare=False)
        self.assertEqual(r["classification"], "SYNTHETIC_ANALYTICAL_DECIMAL_CCD_ORACLE")
        self.assertFalse(r["native_kcol_parity_verified"])
        self.assertFalse(r["selected_ball_launch_verified"])
        self.assertFalse(r["training_approved"])
        self.assertTrue(r["source_query_radius_not_physical_ball_size"])
        self.assertEqual(len(r["cases"]), 24)
        self.assertEqual(len(r["splits"]), 6)

    def test_observes_current_or_future_solver_without_requiring_defect_to_persist(self):
        # This calls the actual existing module but never rewrites it.
        allowed = {"AGREES", "FALSE_NEGATIVE", "PHANTOM_HIT", "FIRST_ENTRY_CENTER_ERROR",
                   "FEATURE_MISMATCH", "DISAGREES"}
        if not (Path(__file__).resolve().parents[1] / "src" / "wii_ai_golf" / "physics" / "first_contact.py").exists():
            self.skipTest("production source not in isolated local test workspace")
        for f, p, q in (("edge", 100000, -100000), ("vertex", 100000, -100000),
                        ("one_f32_ulp_outside", "0.01", "-0.01"),
                        ("edge", "0", "0")):
            obs = oracle.observe_existing_solver(f, str(p), str(q))
            self.assertIn(obs["comparison"], allowed)
            self.assertIn(obs["observed"], ("HIT", "MISS", "ABSTAIN"))
        segmented = oracle.split_path("one_f32_ulp_outside", "0.1", 10,
                                      quantize_f32=True, compare=True)
        self.assertEqual(segmented["expected"], "MISS")
        self.assertEqual(len(segmented["observed_comparisons"]), 10)
        self.assertTrue(set(segmented["observed_comparisons"]) <= allowed)


if __name__ == "__main__":
    unittest.main()