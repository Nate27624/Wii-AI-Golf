"""S003 M1: purely synthetic, no Dolphin/source archive or native parity tests."""
import math
from pathlib import Path
import sys
import unittest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wii_ai_golf.physics import airborne as ab
from wii_ai_golf.physics import first_contact as fc


def settings(*, acceleration=(0.0, 0.0, 0.0), damping=1.0,
             precision="binary64", spin=None):
    return ab.FlightParameters(acceleration, damping, precision, spin)


def synthetic_ground():
    return fc.Triangle((-10.0, 0.0, -10.0),
                       (0.0, 0.0, 10.0),
                       (10.0, 0.0, -10.0), face_id=17)


class AirborneIntegratorTests(unittest.TestCase):
    def test_sample_zero_is_exact_caller_input(self):
        p = (0.123456789, 2.0, 0.0)
        v = (0.1, 0.15, 0.0)
        trace = ab.sample_trajectory(p, v, settings(precision="host_f32"),
                                     steps=2)
        self.assertEqual(trace.samples[0], (0, p, v))
        self.assertEqual([x[0] for x in trace.samples], [0, 1, 2])
        self.assertNotEqual(trace.samples[1][1][0], p[0] + v[0])
        self.assertFalse(trace.native_game_parity_verified)
        self.assertFalse(trace.training_approved)

    def test_zero_force_linear_and_no_damping(self):
        trace = ab.sample_trajectory((1.0, 2.0, 3.0), (0.5, -1.0, 0.25),
                                     settings(), steps=3)
        self.assertEqual(trace.samples, (
            (0, (1.0, 2.0, 3.0), (0.5, -1.0, 0.25)),
            (1, (1.5, 1.0, 3.25), (0.5, -1.0, 0.25)),
            (2, (2.0, 0.0, 3.5), (0.5, -1.0, 0.25)),
            (3, (2.5, -1.0, 3.75), (0.5, -1.0, 0.25)),
        ))

    def test_acceleration_before_position_and_damping_after(self):
        p = settings(acceleration=(0.0, -0.2, 0.0), damping=0.5)
        trace = ab.sample_trajectory((0., 2., 0.), (1., 0., 0.), p, steps=2)
        self.assertEqual(trace.samples[1],
                         (1, (1., 1.8, 0.), (0.5, -0.1, 0.)))
        self.assertEqual(trace.samples[2][0], 2)
        for actual, expected in zip(trace.samples[2][1], (1.5, 1.5, 0.)):
            self.assertAlmostEqual(actual, expected, places=12)
        for actual, expected in zip(trace.samples[2][2], (0.25, -0.15, 0.)):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_constant_gravity_closed_form_control(self):
        # Exact no-damping candidate p_n=p0+n*v0 + n(n+1)/2*a.
        trace = ab.sample_trajectory((0., 2., 0.), (0.1, 0.0, 0.),
                                     settings(acceleration=(0., -0.002, 0.)),
                                     steps=100)
        for n, position, velocity in trace.samples:
            self.assertAlmostEqual(position[0], n * 0.1, places=9)
            self.assertAlmostEqual(position[1], 2 - n * (n+1) / 2 * 0.002,
                                   places=9)
            self.assertAlmostEqual(velocity[1], -n*0.002, places=9)

    def test_refinement_consistency_on_assumed_constant_acceleration(self):
        # Algebraic check: explicit caller step units, not a native timestep.
        full = ab.sample_trajectory((0., 2., 0.), (0., 0., 0.),
                                    settings(acceleration=(0., -0.04, 0.)),
                                    steps=1)
        half = ab.sample_trajectory((0., 2., 0.), (0., 0., 0.),
                                    settings(acceleration=(0., -0.01, 0.)),
                                    steps=2)
        # Semi-implicit Euler's position depends on chosen step subdivision.
        self.assertNotEqual(full.samples[-1][1][1], half.samples[-1][1][1])
        self.assertEqual(full.time_base, "unverified_numerical_steps")

    def test_reproducible_host_f32_and_binary64_are_distinct(self):
        v0 = (0.1, 0.15, 0.0)
        args = ((0., 2., 0.), v0)
        p64 = settings(acceleration=(0., -0.002, 0.),
                       damping=0.999000013, precision="binary64")
        p32 = settings(acceleration=(0., -0.002, 0.),
                       damping=0.999000013, precision="host_f32")
        t32a = ab.sample_trajectory(*args, p32, steps=250)
        t32b = ab.sample_trajectory(*args, p32, steps=250)
        t64 = ab.sample_trajectory(*args, p64, steps=250)
        self.assertEqual(t32a, t32b)
        self.assertNotEqual(t32a.samples[-1][1], t64.samples[-1][1])
        self.assertIn("host_float32_not_ppc_fma", t32a.assumptions)
        self.assertIn("binary64_exploratory_not_native_float32", t64.assumptions)

    def test_source_direction_sign_and_normalization(self):
        lift, side = ab.source_direction_candidate((1., 1., 0.),
                                                   guard_assumption=0.,
                                                   precision="binary64")
        self.assertAlmostEqual(lift[0], -1 / math.sqrt(2))
        self.assertAlmostEqual(lift[1], 1 / math.sqrt(2))
        self.assertEqual(lift[2], 0.)
        self.assertEqual(side, (0., 0., -1.))

    def test_exact_vertical_or_near_guard_abstains(self):
        for v, guard in [((0., 1., 0.), 0.),
                         ((1e-9, 1., 0.), 1e-7)]:
            with self.assertRaises(ab.UnverifiedNormalizerBranch):
                ab.source_direction_candidate(v, guard)

    def test_spin_force_direction_is_not_legacy_world_axis(self):
        spin = ab.SourceSpinCandidate(speed_like=2., lift=2., lateral=3.,
                                      normalizer_guard_assumption=0.,
                                      lift_decay=1., lateral_decay=1.)
        trace = ab.sample_trajectory((0., 2., 0.), (1., 1., 0.),
                                     settings(spin=spin), steps=1)
        u = trace.samples[1][1]
        self.assertAlmostEqual(u[0], 1 - 0.0048 / math.sqrt(2), places=9)
        self.assertAlmostEqual(u[1], 2 + 1 + 0.0048 / math.sqrt(2), places=9)
        self.assertAlmostEqual(u[2], -0.006, places=9)
        self.assertIn("normalizer_guard_assumed_not_source_verified",
                      trace.assumptions)

    def test_speed_cache_hypotheses_are_not_silently_conflated(self):
        base = dict(speed_like=2., lift=5., lateral=3.,
                    normalizer_guard_assumption=0.,
                    lift_decay=1., lateral_decay=1.)
        held = ab.SourceSpinCandidate(**base, speed_policy="held_input")
        fresh = ab.SourceSpinCandidate(**base,
                                       speed_policy="recompute_from_velocity")
        params = lambda s: settings(acceleration=(0., -0.01, 0.),
                                    damping=0.95, spin=s)
        a = ab.sample_trajectory((0., 2., 0.), (1., 1., 0.),
                                 params(held), steps=4)
        b = ab.sample_trajectory((0., 2., 0.), (1., 1., 0.),
                                 params(fresh), steps=4)
        self.assertEqual(a.samples[1], b.samples[1])
        self.assertNotEqual(a.samples[-1], b.samples[-1])

    def test_inactive_lift_does_not_block_valid_lateral_candidate(self):
        # With vy=0, |L|=vx**2 while |S|=|vx|. For vx=1e-5,
        # an assumed guard of 1e-8 rejects L but not S. A lateral-only
        # force must not unnecessarily normalize the inactive lift basis.
        v = (1e-5, 0., 0.)
        with self.assertRaises(ab.UnverifiedNormalizerBranch):
            ab.source_direction_candidate(v, 1e-8, "binary64")

        lift_dir, side_dir = ab.source_direction_candidate(
            v, 1e-8, "binary64",
            require_lift=False, require_side=True)
        self.assertEqual(lift_dir, (0., 0., 0.))
        self.assertEqual(side_dir, (0., 0., -1.))

        side_only = ab.SourceSpinCandidate(
            speed_like=1., lift=0., lateral=1.,
            normalizer_guard_assumption=1e-8)
        trace = ab.sample_trajectory(
            (0., 2., 0.), v, settings(spin=side_only), steps=1)
        self.assertAlmostEqual(trace.samples[1][1][2], -0.001, places=12)

        # A required, genuinely unqualified lift remains fail-closed.
        lift_only = ab.SourceSpinCandidate(
            speed_like=1., lift=1., lateral=0.,
            normalizer_guard_assumption=1e-8)
        with self.assertRaises(ab.UnverifiedNormalizerBranch):
            ab.sample_trajectory((0., 2., 0.), v,
                                 settings(spin=lift_only), steps=1)

    def test_selected_normalization_flags_are_strict_booleans(self):
        with self.assertRaises(ValueError):
            ab.source_direction_candidate(
                (1., 1., 0.), 0., "binary64", require_lift=1)
        with self.assertRaises(ValueError):
            ab.source_direction_candidate(
                (1., 1., 0.), 0., "binary64", require_side=None)

    def test_unknown_zero_vector_branch_abstains_in_flight(self):
        spin = ab.SourceSpinCandidate(speed_like=1., lift=1., lateral=1.,
                                      normalizer_guard_assumption=1e-7)
        with self.assertRaises(ab.UnverifiedNormalizerBranch):
            ab.sample_trajectory((0., 2., 0.), (0., 1., 0.),
                                 settings(spin=spin), steps=3)

    def test_missing_and_bad_parameters_fail_closed(self):
        invalid = [
            lambda: ab.FlightParameters((0., float("nan"), 0.), 1.),
            lambda: ab.FlightParameters((0., 0., 0.), float("inf")),
            lambda: ab.FlightParameters((0., 0., 0.), -1.),
            lambda: ab.FlightParameters((0., 0., 0.), 1., "native_ppc"),
            lambda: ab.FlightParameters((0., 0., 0.), 1., spin="untyped"),
            lambda: ab.SourceSpinCandidate(1., 1., 1., -0.1),
            lambda: ab.SourceSpinCandidate(float("nan"), 1., 1., 0.),
            lambda: ab.SourceSpinCandidate(1., 1., 1., 0.,
                                            speed_policy="native_proven"),
        ]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                case()
        for count in (0, -1, 10001, 2.5, True):
            with self.subTest(steps=count), self.assertRaises(ValueError):
                ab.sample_trajectory((0, 2, 0), (0, 0, 0), settings(),
                                     steps=count)
        with self.assertRaises(ValueError):
            ab.sample_trajectory((0, 2, float("inf")), (0, 0, 0),
                                 settings(), steps=1)
        with self.assertRaises(ValueError):
            ab.sample_trajectory((0, 2), (0, 0, 0), settings(), steps=1)

    def test_overflow_fails_closed(self):
        with self.assertRaises(ValueError):
            ab.sample_trajectory((1e38, 0., 0.), (1e38, 0., 0.),
                                 settings(precision="host_f32"), steps=10)

    def test_external_first_contact_integration(self):
        trace = ab.sample_trajectory((0., 2., 0.), (0., -1., 0.),
                                     settings(), steps=3)
        unknown_tree = ab.predict_provisional_contact(trace,
                                                       [synthetic_ground()])
        self.assertEqual(unknown_tree["status"],
                         "ABSTAIN_TREE_CLEARANCE_UNKNOWN")
        hit = ab.predict_provisional_contact(
            trace, [synthetic_ground()], assume_tree_free=True)
        self.assertEqual(hit["status"], "PROVISIONAL_FIRST_CONTACT")
        self.assertAlmostEqual(hit["contact_t"], 2.)
        self.assertEqual(hit["ball_center_xyz"], (0., 0., 0.))
        self.assertEqual(hit["surface_contact_xyz"], (0., 0., 0.))
        self.assertEqual(hit["trajectory_provenance"],
                         "S003_M1_OFFLINE_ZERO_WIND_CANDIDATE")
        self.assertFalse(hit["native_game_parity_verified"])
        self.assertFalse(hit["training_approved"])

    def test_no_contact_horizon_and_caller_time_unchanged(self):
        trace = ab.sample_trajectory((0., 2., 0.), (0., 1., 0.),
                                     settings(), steps=3)
        result = ab.predict_provisional_contact(
            trace, [synthetic_ground()], assume_tree_free=True)
        self.assertEqual(result["status"], "NO_CONTACT_IN_HORIZON")
        self.assertEqual(result["time_base"], "unverified_numerical_steps")

    def test_source_query_radius_is_never_silent_physical_ball_radius(self):
        trace = ab.sample_trajectory((0., 2., 0.), (0., -1., 0.),
                                     settings(), steps=3)
        hit = ab.predict_provisional_contact(
            trace, [synthetic_ground()], assume_tree_free=True,
            contact_mode="swept_kcol_query_0p5")
        self.assertEqual(hit["query_radius"], 0.5)
        self.assertEqual(hit["contact_mode"], "swept_kcol_query_0p5")
        self.assertFalse(hit["native_game_parity_verified"])


if __name__ == "__main__":
    unittest.main()
