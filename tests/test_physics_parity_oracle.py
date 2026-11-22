"""S003 M2 synthetic fixtures only: no native shot, guest clock or training."""
from dataclasses import replace
from pathlib import Path
import math
import sys
import unittest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wii_ai_golf.physics.airborne import (AirborneTrace, FlightParameters,
                                           SourceSpinCandidate,
                                           UnverifiedNormalizerBranch,
                                           sample_trajectory)
from wii_ai_golf.physics.parity_oracle import (EvidenceLabels, ReferenceSample,
                                              TraceIdentity, compare_airborne)


def ident(precision="binary64"):
    return TraceIdentity(
        source_revision="SYNTHETIC_ZERO_WIND", source_cohort_tag="synthetic_cohort",
        boot_id="boot_fixture", scene_id="scene_fixture", shot_id="shot_fixture",
        selected_ball_tag="selected_synthetic_ball", ball_epoch="epoch_fixture",
        model_sha="a" * 40, physics_parameter_provenance="assumed_accel_damping",
        coordinate_basis="synthetic_xyz", units="synthetic_units",
        numeric_precision=precision)


def labels(**changes):
    return replace(EvidenceLabels(
        trace_kind="synthetic", clock_domain="synthetic_numerical_steps",
        guest_step_status="SYNTHETIC_CONTRACT_PASS",
        basis_status="SYNTHETIC_BASIS"), **changes)


def trace(precision="binary64", *, steps=6):
    return sample_trajectory((1., 2., 3.), (0.5, 0., -0.25),
                             FlightParameters((0., -0.25, 0.), 1., precision),
                             steps=steps)


def reference(m):
    return [ReferenceSample(n, p, v) for n, p, v in m.samples]


def run(m=None, refs=None, origin=None, model_id=None, reference_id=None, **kw):
    m = trace() if m is None else m
    refs = reference(m) if refs is None else refs
    m_id = ident(m.precision) if model_id is None else model_id
    r_id = m_id if reference_id is None else reference_id
    return compare_airborne(m, refs, model_identity=m_id,
                            reference_identity=r_id,
                            evidence=labels() if origin is None else origin, **kw)


class SyntheticParityTests(unittest.TestCase):
    def check(self, answer, status):
        self.assertEqual(answer["status"], status)
        self.assertIs(answer["native_game_parity_verified"], False)
        self.assertIs(answer["training_approved"], False)
        self.assertIs(answer["selected_ball_world_xyz_verified"], False)
        self.assertIs(answer["guest_physics_clock_independently_verified"], False)
        self.assertIsNone(answer["verified_native_guest_step_count"])
        self.assertEqual(answer["time_base"], "unverified_numerical_steps")

    def test_independent_closed_form_zero_wind_trace(self):
        m = trace()
        # Independent no-damping, constant-a mathematical reference:
        # v_n=v0+n*a; p_n=p0+n*v0+n*(n+1)/2*a.
        expected = []
        for n in range(7):
            expected.append(ReferenceSample(
                n, (1 + 0.5*n, 2 - (n*(n+1)/2)*0.25, 3 - 0.25*n),
                (0.5, -0.25*n, -0.25)))
        ans = run(m, expected)
        self.check(ans, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(ans["compared_steps"], 7)
        self.assertIsNone(ans["first_divergent_step"])
        self.assertEqual(ans["velocity_comparison"], "COMPLETE")
        self.assertTrue(all(row["position_l2"] == 0 and row["velocity_l2"] == 0
                            for row in ans["residuals"]))

    def test_exact_one_axis_step_three_earliest_not_endpoint(self):
        m = trace()
        refs = reference(m)
        refs[3] = replace(refs[3], position_xyz=(refs[3].position_xyz[0] + 0.125,
                                                   *refs[3].position_xyz[1:]))
        ans = run(m, refs)
        self.check(ans, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(ans["first_divergent_step"], 3)
        self.assertEqual(ans["residuals"][3]["position_delta_xyz"], (-0.125, 0., 0.))
        self.assertEqual(ans["residuals"][3]["position_l2"], 0.125)
        self.assertEqual(ans["residuals"][-1]["position_l2"], 0.)

    def test_endpoint_aliased_launch_and_force_diverge_earlier(self):
        # Canonical M1 zero-spin order: u=v+a; p+=u; v=d*u.
        # A single terminal endpoint cannot identify both v0 and a.
        steps = 100
        damping = 0.999000013
        acceleration_delta = 0.001
        a_steps = (1.0 - damping**steps) / (1.0 - damping)
        b_steps = (steps - damping * a_steps) / (1.0 - damping)
        other_v0 = 0.1 - (b_steps / a_steps) * acceleration_delta
        primary = sample_trajectory(
            (0., 5., 0.), (0., 0.1, 0.),
            FlightParameters((0., -0.004, 0.), damping, "binary64"), steps=steps)
        alternative = sample_trajectory(
            (0., 5., 0.), (0., other_v0, 0.),
            FlightParameters((0., -0.003, 0.), damping, "binary64"), steps=steps)
        # Position-only references isolate the earliest *position* divergence;
        # optional genuine velocity samples correctly identify step-zero v0.
        without_velocity = [replace(row, velocity_xyz=None)
                            for row in reference(alternative)]
        answer = run(primary, without_velocity, position_atol=1e-10)
        self.check(answer, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(answer["velocity_comparison"], "UNKNOWN")
        self.assertEqual(answer["first_divergent_step"], 1)
        self.assertLess(answer["residuals"][-1]["position_l2"], 1e-10)
        self.assertGreater(answer["residuals"][50]["position_l2"], 1.2)
        self.assertEqual(answer["compared_steps"], 101)
        with_velocity = run(primary, reference(alternative))
        self.check(with_velocity, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(with_velocity["first_divergent_step"], 0)
        self.assertEqual(with_velocity["velocity_comparison"], "COMPLETE")

    def test_reference_count_is_bounded_before_provenance_traversal(self):
        class NeverRead:
            def __getattribute__(self, name):
                raise AssertionError("oversized input was traversed")

        # A single invalid member should not be visited if the length already
        # makes the reference sequence ineligible for comparison.
        for too_many in ([NeverRead()] * 10002, (NeverRead(),) * 10002):
            with self.subTest(kind=type(too_many).__name__):
                with self.assertRaisesRegex(ValueError, "bounded nonempty"):
                    run(refs=too_many)
        with self.assertRaisesRegex(ValueError, "bounded nonempty"):
            run(refs=[])

    def test_reference_exact_max_count_is_accepted(self):
        # 10,000 M1 steps plus the preintegration sample zero is the maximum.
        m = sample_trajectory((0., 0., 0.), (0., 0., 0.),
                              FlightParameters((0., 0., 0.), 1., "binary64"),
                              steps=10000)
        refs = tuple(reference(m))
        self.assertEqual(len(refs), 10001)
        answer = run(m, refs)
        self.check(answer, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(answer["compared_steps"], 10001)
        self.assertEqual(answer["reference_count"], 10001)
        self.assertIsNone(answer["first_divergent_step"])

    def test_wrong_force_update_order_reports_step_one(self):
        m = trace()
        refs = reference(m)
        # Wrong p+=v (instead of p+=v+a) changes the first step.
        refs[1] = replace(refs[1], position_xyz=(1.5, 2., 2.75))
        self.assertEqual(run(m, refs)["first_divergent_step"], 1)

    def test_discrete_drift_keeps_exact_earliest_step(self):
        m = trace()
        refs = reference(m)
        for step in range(3, len(refs)):
            x, y, z = refs[step].position_xyz
            refs[step] = replace(refs[step], position_xyz=(x, y + (step-2)*0.01, z))
        ans = run(m, refs)
        self.assertEqual(ans["first_divergent_step"], 3)
        self.assertAlmostEqual(ans["residuals"][-1]["position_l2"], 0.04)

    def test_tolerance_is_only_caller_synthetic_threshold(self):
        m = trace()
        refs = reference(m)
        refs[3] = replace(refs[3], position_xyz=(refs[3].position_xyz[0] + 0.125,
                                                   *refs[3].position_xyz[1:]))
        self.assertIsNone(run(m, refs, position_atol=0.125)["first_divergent_step"])
        self.assertEqual(run(m, refs, position_atol=0.124)["first_divergent_step"], 3)

    def test_missing_middle_step_abstains_no_zip_or_interpolation(self):
        m = trace()
        refs = reference(m)
        refs.pop(3)
        ans = run(m, refs)
        self.check(ans, "ABSTAIN_GAPPED_OR_UNALIGNED_STEPS")
        self.assertEqual(ans["skipped_steps"], [3])
        self.assertEqual(ans["compared_steps"], 0)

    def test_missing_last_step_abstains(self):
        m = trace()
        ans = run(m, reference(m)[:-1])
        self.check(ans, "ABSTAIN_GAPPED_OR_UNALIGNED_STEPS")
        self.assertEqual(ans["skipped_steps"], [6])

    def test_duplicate_nonmonotonic_and_reordered_steps_abstain(self):
        m = trace()
        for change in (lambda rows: rows.insert(3, rows[2]),
                       lambda rows: rows.reverse(),
                       lambda rows: rows.__setitem__(2, replace(rows[2], numerical_step=7))):
            with self.subTest(change=change):
                refs = reference(m)
                change(refs)
                self.check(run(m, refs), "ABSTAIN_DUPLICATE_OR_NONMONOTONIC_STEP")

    def test_missing_zero_even_if_both_sides_aligned_would_abstain(self):
        m = trace()
        refs = reference(m)[1:]
        self.assertEqual(run(m, refs)["skipped_steps"], [0])

    def test_shot_boot_scene_receiver_epoch_revision_cohort_basis_units_mismatch(self):
        m = trace()
        for key in ("boot_id", "shot_id", "scene_id", "selected_ball_tag",
                    "ball_epoch", "source_revision", "source_cohort_tag",
                    "coordinate_basis", "units", "physics_parameter_provenance"):
            with self.subTest(key=key):
                other = replace(ident(), **{key: "other_symbolic"})
                self.check(run(m, reference_id=other), "ABSTAIN_IDENTITY_OR_BASIS_MISMATCH")

    def test_wrong_model_sha_abstains_without_residuals(self):
        ans = run(reference_id=replace(ident(), model_sha="b" * 40))
        self.check(ans, "ABSTAIN_MODEL_SHA_MISMATCH")
        self.assertEqual(ans["residuals"], [])

    def test_unknown_velocity_is_not_finite_differenced(self):
        m = trace()
        refs = [replace(row, velocity_xyz=None) for row in reference(m)]
        ans = run(m, refs)
        self.check(ans, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(ans["velocity_comparison"], "UNKNOWN")
        self.assertIsNone(ans["residuals"][3]["velocity_l2"])
        self.assertIsNone(ans["first_divergent_step"])

    def test_partial_direct_velocity_observation(self):
        m = trace()
        refs = reference(m)
        refs[2] = replace(refs[2], velocity_xyz=None)
        ans = run(m, refs)
        self.assertEqual(ans["velocity_comparison"], "PARTIAL")
        self.assertEqual(ans["residuals"][2]["velocity_delta_xyz"], None)

    def test_host_vi_and_unknown_clock_cannot_be_guest_clock(self):
        for domain in ("host_callback", "vi_frame", "unknown"):
            with self.subTest(domain=domain):
                self.check(run(origin=labels(clock_domain=domain)),
                           "ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")

    def test_claimed_guest_frame_index_is_not_synthetic_numerical_step(self):
        refs = reference(trace())
        refs[1] = replace(refs[1], guest_physics_frame=1)
        self.check(run(refs=refs), "ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")

    def test_unverified_guest_clock_s002_abstention(self):
        self.check(run(origin=labels(guest_step_status="ABSTAIN_MISSING_EXECUTED_PC")),
                   "ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")

    def test_conditional_s002_basis_is_not_native_verification(self):
        ans = run(origin=labels(basis_status="CONDITIONALLY_CONSISTENT"))
        self.check(ans, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertFalse(ans["selected_ball_world_xyz_verified"])
        self.check(run(origin=labels(basis_status="ABSTAIN")),
                   "ABSTAIN_UNVERIFIED_COORDINATE_BASIS")

    def test_stale_nonatomic_or_unqualified_synthetic_packet(self):
        refs = reference(trace())
        refs[3] = replace(refs[3], atomic=False)
        self.check(run(refs=refs), "ABSTAIN_NONATOMIC_SAMPLE")
        refs = reference(trace())
        refs[3] = replace(refs[3], source_quality="stale_packet")
        self.check(run(refs=refs), "ABSTAIN_UNVERIFIED_SOURCE_OR_GUEST_PC")

    def test_sanitized_candidate_never_gets_numeric_residuals(self):
        for status in ("CANDIDATE_REQUIRES_EXTERNAL_PROOF", "ABSTAIN_MISSING_EXECUTED_PC"):
            evidence = labels(trace_kind="sanitized_candidate",
                              clock_domain="claimed_guest_physics_steps",
                              guest_step_status=status)
            ans = run(origin=evidence)
            self.check(ans, "ABSTAIN_UNVERIFIED_SOURCE_OR_GUEST_PC")
            self.assertEqual(ans["residuals"], [])

    def test_native_candidate_source_receiver_v0_basis_normalizer_precision_gates(self):
        base = labels(trace_kind="sanitized_candidate",
                      clock_domain="claimed_guest_physics_steps",
                      guest_step_status="SYNTHETIC_CONTRACT_PASS",
                      basis_status="CONDITIONALLY_CONSISTENT",
                      source_revision_qualified=True, source_archive_qualified=True,
                      selected_receiver_qualified=True, selected_ball_xyz_qualified=True,
                      selected_launch_v0_qualified=True, normalizer_branch_qualified=True,
                      ppc_f32_qualified=True)
        cases = (("source_archive_qualified", "ABSTAIN_UNVERIFIED_SOURCE_OR_GUEST_PC"),
                 ("selected_receiver_qualified", "ABSTAIN_UNVERIFIED_SELECTED_BALL_RECEIVER"),
                 ("selected_launch_v0_qualified", "ABSTAIN_UNVERIFIED_LAUNCH_V0"),
                 ("selected_ball_xyz_qualified", "ABSTAIN_UNVERIFIED_COORDINATE_BASIS"),
                 ("normalizer_branch_qualified", "ABSTAIN_UNVERIFIED_NORMALIZER_BRANCH"),
                 ("ppc_f32_qualified", "ABSTAIN_UNVERIFIED_PPC_PRECISION"))
        for field, status in cases:
            with self.subTest(field=field):
                self.check(run(origin=replace(base, **{field: False})), status)
        # Even all supplied yes flags do NOT confer independent native truth.
        self.check(run(origin=base), "ABSTAIN_NATIVE_PARITY_REQUIRES_INDEPENDENT_PROOF")

    def test_host_f32_word_diagnostics_only_for_declared_matched_synthetic_ops(self):
        m = trace("host_f32")
        refs = reference(m)
        ans = run(m, refs)
        self.assertFalse(ans["host_f32_ulp_diagnostics"])
        self.assertIsNone(ans["residuals"][1]["host_f32_position_ulp_xyz"])
        detailed = run(m, refs, origin=labels(host_f32_operations_matched=True))
        self.assertTrue(detailed["host_f32_ulp_diagnostics"])
        self.assertIsNone(detailed["residuals"][0]["host_f32_position_ulp_xyz"])
        self.assertEqual(detailed["residuals"][1]["host_f32_position_ulp_xyz"], (0, 0, 0))
        self.assertFalse(detailed["native_game_parity_verified"])

    def test_float32_boundary_detects_position_ulp_but_not_native_ppc(self):
        m = trace("host_f32")
        refs = reference(m)
        x, y, z = refs[1].position_xyz
        refs[1] = replace(refs[1], position_xyz=(math.nextafter(x, math.inf), y, z))
        ans = run(m, refs, origin=labels(host_f32_operations_matched=True))
        self.assertEqual(ans["first_divergent_step"], 1)
        # The immediate host-binary64 neighbor is not necessarily one f32 ULP.
        self.assertIsNotNone(ans["residuals"][1]["host_f32_position_ulp_xyz"])
        self.assertFalse(ans["native_game_parity_verified"])

    def test_binary64_never_has_float32_word_diagnostics(self):
        ans = run(origin=labels(host_f32_operations_matched=True))
        self.assertFalse(ans["host_f32_ulp_diagnostics"])
        self.assertIsNone(ans["residuals"][1]["host_f32_position_ulp_xyz"])

    def test_held_vs_recomputed_spin_cache_diverges_only_after_initial_step(self):
        base = dict(speed_like=2., lift=5., lateral=3.,
                    normalizer_guard_assumption=0., lift_decay=1., lateral_decay=1.)
        held = SourceSpinCandidate(**base, speed_policy="held_input")
        fresh = SourceSpinCandidate(**base, speed_policy="recompute_from_velocity")
        def flight(spin):
            return sample_trajectory((0., 2., 0.), (1., 1., 0.),
                                     FlightParameters((0., -0.01, 0.), 0.95,
                                                      "binary64", spin), steps=4)
        m = flight(held)
        refs = reference(flight(fresh))
        ans = run(m, refs)
        self.check(ans, "ELIGIBLE_SYNTHETIC_COMPARISON")
        self.assertEqual(ans["residuals"][1]["position_l2"], 0.)
        self.assertEqual(ans["first_divergent_step"], 2)

    def test_required_vertical_normalizer_guard_abstains_upstream(self):
        spin = SourceSpinCandidate(1., 1., 1., 0.)
        with self.assertRaises(UnverifiedNormalizerBranch):
            sample_trajectory((0., 2., 0.), (0., 1., 0.),
                              FlightParameters((0., -0.01, 0.), 1., "binary64", spin),
                              steps=3)

    def test_prohibited_promoted_model_trace_abstains(self):
        m = trace()
        self.check(run(m=replace(m, native_game_parity_verified=True)),
                   "ABSTAIN_MODEL_PROVENANCE")
        self.check(run(m=replace(m, training_approved=True)),
                   "ABSTAIN_MODEL_PROVENANCE")
        self.check(run(m=replace(m, time_base="guest_frame")),
                   "ABSTAIN_MODEL_PROVENANCE")

    def test_precision_mismatch_abstains(self):
        m = trace("host_f32")
        self.check(run(m, model_id=ident("binary64")),
                   "ABSTAIN_NUMERIC_SEMANTICS_MISMATCH")

    def test_invalid_samples_tolerance_and_ids_fail_closed(self):
        m = trace()
        cases = [replace(reference(m)[1], position_xyz=(float("nan"), 0., 0.)),
                 replace(reference(m)[1], position_xyz=(True, 0., 0.)),
                 replace(reference(m)[1], position_xyz=(1e15, 0., 0.))]
        for sample in cases:
            refs = reference(m)
            refs[1] = sample
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                run(m, refs)
        for tolerance in (-1., float("nan"), True, 1e7):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                run(position_atol=tolerance)
        for value in ("0x804BF900", "private/path", "", "🔒"):
            with self.subTest(identity=value), self.assertRaises(ValueError):
                run(reference_id=replace(ident(), selected_ball_tag=value))
        with self.assertRaises(ValueError):
            run(origin=labels(source_archive_qualified=1))

    def test_input_immutable_and_no_private_identifier_echo(self):
        m = trace()
        refs = reference(m)
        before = tuple(refs)
        ans = run(m, refs)
        self.assertEqual(tuple(refs), before)
        self.assertNotIn("shot_fixture", str(ans))
        self.assertNotIn("synthetic_cohort", str(ans))
        self.assertNotIn("a" * 40, str(ans))


if __name__ == "__main__":
    unittest.main()
