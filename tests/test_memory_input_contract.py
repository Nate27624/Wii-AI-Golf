"""Synthetic-only provenance join tests. No Dolphin/ROM/private RAM."""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wii_ai_golf.memory_input_contract import (
    ActorReceipt, InputReceipt, OutcomeReceipt, Rejection,
    join_memory_input_observation,
)


class MemoryInputJoinTests(unittest.TestCase):
    def setUp(self):
        self.input = InputReceipt("synthetic-run", "shot-1", 77, True, True, True, True,
                                  scene_id="synthetic-scene", hole_id="synthetic-hole")
        self.actor = ActorReceipt(
            "synthetic-run", "shot-1", 77,
            0x1234, "lifetime-A", 0x1234, "lifetime-A",
            0x1234, "lifetime-A", "START", "idle",
            scene_id="synthetic-scene", hole_id="synthetic-hole"
        )
        self.result = OutcomeReceipt(
            "synthetic-run", "shot-1", 77,
            0x1234, "lifetime-A", "synthetic", "synthetic_distance", False,
            scene_id="synthetic-scene", hole_id="synthetic-hole"
        )

    def decide(self, input=None, actor=None, result=None):
        return join_memory_input_observation(
            input if input is not None else self.input,
            actor if actor is not None else self.actor,
            result if result is not None else self.result,
        )

    def test_consistent_toy_fixture_is_not_real_training_proof(self):
        d = self.decide()
        self.assertTrue(d.synthetic_consistent)
        self.assertFalse(d.real_training_eligible)
        self.assertEqual(d.validity_mask, ("synthetic_internal_join",))
        self.assertEqual(d.rejected, (Rejection.NO_PHYSICAL_PROOF,))

    def test_swapped_run_and_shot_abstain(self):
        for result in (replace(self.result, run_id="other"),
                       replace(self.result, shot_id="other")):
            with self.subTest(result=result):
                d = self.decide(result=result)
                self.assertFalse(d.synthetic_consistent)
                self.assertEqual(d.validity_mask, ())
                self.assertFalse(d.real_training_eligible)

    def test_guest_frame_mismatch_and_stale_frame_abstain(self):
        d = self.decide(result=replace(self.result, guest_frame=80))
        self.assertIn(Rejection.FRAME_MISMATCH, d.rejected)
        self.assertIn(Rejection.STALE_FRAME, d.rejected)
        self.assertFalse(d.synthetic_consistent)
        self.assertFalse(join_memory_input_observation(
            self.input, self.actor, replace(self.result, guest_frame=78),
            max_frame_lag=2).synthetic_consistent)

    def test_selected_global_rendered_actor_mismatch(self):
        for actor in (
            replace(self.actor, selected_address=0x2222),
            replace(self.actor, global_address=0x2222),
            replace(self.actor, rendered_address=0x2222),
        ):
            with self.subTest(actor=actor):
                self.assertIn(Rejection.ACTOR_MISMATCH, self.decide(actor=actor).rejected)

    def test_same_pointer_new_lifetime_not_actor_continuity(self):
        changed = replace(self.actor, rendered_generation="reused-address-new-object")
        self.assertIn(Rejection.OBJECT_REPLACED, self.decide(actor=changed).rejected)
        changed_result = replace(self.result, actor_generation="next-shot")
        self.assertIn(Rejection.OBJECT_REPLACED,
                      self.decide(result=changed_result).rejected)

    def test_callback_only_and_a_only_not_accepted_contact(self):
        for input in (
            replace(self.input, game_side_a_accepted=False),
            replace(self.input, contact_witness=False),
            replace(self.input, requested_a=False),
            replace(self.input, callback_seen=False),
        ):
            with self.subTest(input=input):
                self.assertIn(Rejection.CONTACT_UNVERIFIED,
                              self.decide(input=input).rejected)

    def test_d1_airborne_start_contradiction(self):
        d = self.decide(actor=replace(self.actor, human_label="airborne"))
        self.assertIn(Rejection.D1_CONTRADICTION, d.rejected)

    def test_offgreen_censored_100ft_never_becomes_carry(self):
        for result in (
            replace(self.result, censored=True),
            replace(self.result, distance_label="offgreen_100ft_penalty"),
            replace(self.result, measurement="offgreen_100ft_penalty"),
        ):
            with self.subTest(result=result):
                d = self.decide(result=result)
                self.assertIn(Rejection.CENSORED_OUTCOME, d.rejected)
                self.assertFalse(d.synthetic_consistent)
                self.assertFalse(d.real_training_eligible)

    def test_unverified_human_result_abstains(self):
        d = self.decide(result=replace(self.result, source="human"))
        self.assertIn(Rejection.OUTCOME_UNVERIFIED, d.rejected)

    def test_no_forged_positive_from_missing_identifiers(self):
        for actor in (replace(self.actor, selected_address=0),
                      replace(self.actor, selected_generation=""),
                      replace(self.actor, guest_frame=-1)):
            self.assertFalse(self.decide(actor=actor).synthetic_consistent)

    def test_negative_lag_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_frame_lag"):
            join_memory_input_observation(
                self.input, self.actor, self.result, max_frame_lag=-1)


    def test_swapped_scene_or_hole_abstains_before_any_real_training(self):
        for change, expected in (
            ({"scene_id": "other-scene"}, Rejection.SCENE_MISMATCH),
            ({"hole_id": "other-hole"}, Rejection.HOLE_MISMATCH),
            ({"scene_id": ""}, Rejection.SCENE_MISMATCH),
            ({"hole_id": ""}, Rejection.HOLE_MISMATCH),
        ):
            with self.subTest(change=change):
                result = replace(self.result, **change)
                decision = self.decide(result=result)
                self.assertIn(expected, decision.rejected)
                self.assertFalse(decision.synthetic_consistent)
                self.assertFalse(decision.real_training_eligible)
                self.assertEqual(decision.validity_mask, ())

    def test_scene_hole_mismatch_from_input_and_actor_also_abstains(self):
        for evidence in (
            ("input", replace(self.input, scene_id="different")),
            ("input", replace(self.input, hole_id="different")),
            ("actor", replace(self.actor, scene_id="different")),
            ("actor", replace(self.actor, hole_id="different")),
        ):
            kind, modified = evidence
            with self.subTest(kind=kind, value=modified):
                decision = self.decide(**{kind: modified})
                self.assertFalse(decision.synthetic_consistent)
                self.assertFalse(decision.real_training_eligible)

    def test_missing_scene_hole_from_legacy_receipts_fail_closed(self):
        bare_input = replace(self.input, scene_id="", hole_id="")
        bare_actor = replace(self.actor, scene_id="", hole_id="")
        bare_outcome = replace(self.result, scene_id="", hole_id="")
        decision = self.decide(bare_input, bare_actor, bare_outcome)
        self.assertIn(Rejection.SCENE_MISMATCH, decision.rejected)
        self.assertIn(Rejection.HOLE_MISMATCH, decision.rejected)
        self.assertFalse(decision.synthetic_consistent)



if __name__ == "__main__":
    unittest.main()
