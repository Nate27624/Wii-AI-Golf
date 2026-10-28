"""Offline regression tests for safe game-memory variable documentation."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("memory_registry_validator", ROOT / "scripts/validate_memory_registry.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
REGISTRY = ROOT / "research/memory-variables/registry.json"


class MemoryRegistryTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.variable = self.payload["variables"][0]

    def test_committed_registry_has_no_validation_errors(self):
        self.assertEqual(validator.validate_registry(self.payload), [])

    def test_no_unaudited_variable_is_training_approved(self):
        self.assertTrue(self.payload["variables"])
        self.assertTrue(all(not v["training"]["approved"] for v in self.payload["variables"]))
        self.assertTrue(all(not v["training"]["eligible_as_input"] and
                            not v["training"]["eligible_as_label"]
                            for v in self.payload["variables"]))

    def test_source_ball_and_cache_entries_present_without_training_promotion(self):
        ids = {v["id"] for v in self.payload["variables"]}
        for key in ("golf.ball_object.current_translation_candidate",
                    "golf.ball_object.initialized_cache_cc",
                    "golf.ball_object.conditional_cache_f0",
                    "golf.ball_object.conditional_cache_fc",
                    "golf.player.selected_record.aim_rotation",
                    "golf.ball.world_xyz",
                    "golf.ball.velocity_xyz"):
            self.assertIn(key, ids)
            v = next(x for x in self.payload["variables"] if x["id"] == key)
            self.assertFalse(v["training"]["approved"])
            self.assertFalse(v["training"]["eligible_as_input"])
            self.assertFalse(v["training"]["eligible_as_label"])

    def test_ball_translation_requires_pointer_dereference(self):
        v = next(x for x in self.payload["variables"]
                 if x["id"] == "golf.ball_object.current_translation_candidate")
        self.assertIn("be_u32", v["memory_locator"]["expression"])
        self.assertIn("read_ptr",
                      [step["op"] for step in v["memory_locator"]["steps"]])

    def test_angle_candidate_is_scalar_not_vector(self):
        v = next(x for x in self.payload["variables"]
                 if x["id"] == "golf.player.selected_record.aim_rotation")
        self.assertEqual(v["datatype"], "float32_be")

    def test_evidence_crosswalk_points_to_existing_ledger(self):
        self.assertTrue(self.payload["variables"])
        self.assertTrue(all("evidence_ledger_field_ids" in v
                            and isinstance(v["evidence_ledger_field_ids"], list)
                            for v in self.payload["variables"]))
        self.assertIn("pull/154", self.payload["related_evidence_ledger"]["url"])

    def test_real_airborne_evidence_preserves_changed_pin_confound(self):
        observations = [e for e in self.payload["operator_evidence_history"]
                        if e.get("kind") == "human_observed_airborne_fullbank_vs_idle_b0"]
        self.assertEqual(len(observations), 1)
        evidence = observations[0]
        changes = evidence["changed_u32_components_of_three"]
        self.assertEqual(changes["golf.ball_object.current_translation_candidate"], 3)
        self.assertEqual(changes["golf.ball_object.conditional_cache_f0"], 3)
        self.assertEqual(changes["golf.tee_start.map_translation_xyz"], 0)
        self.assertEqual(changes["golf.pin.map_translation_xyz"], 3)
        self.assertFalse(evidence["training_allowed"])
        self.assertTrue(evidence["limitations"])

    def test_disputed_outcome_label_is_not_overwritten_by_airborne_evidence(self):
        history = self.payload["operator_evidence_history"]
        disputed = next(e for e in history
                        if e.get("kind") == "disputed_green_outcome_label")
        self.assertEqual(disputed["adjudication"]["recorded_green_yes_status"],
                         "disputed_by_operator")
        self.assertFalse(disputed["training_allowed"])
        self.assertFalse(self.payload["last_operator_evidence"]["training_allowed"])
        self.assertTrue(all(not v["training"]["approved"]
                            for v in self.payload["variables"]))

    def test_duplicate_id_is_rejected(self):
        self.payload["variables"].append(copy.deepcopy(self.variable))
        self.assertTrue(any("duplicate id" in s for s in validator.validate_registry(self.payload)))

    def test_missing_evidence_is_rejected(self):
        del self.variable["evidence"]
        self.assertTrue(any("evidence" in s for s in validator.validate_registry(self.payload)))

    def test_unknown_status_rejected(self):
        self.variable["status"] = "validated_by_vibes"
        self.assertTrue(any("invalid status" in s for s in validator.validate_registry(self.payload)))

    def test_dynamic_mem2_root_rejected(self):
        self.variable["memory_locator"]["root_static_address"] = "0x91BE3834"
        self.assertTrue(any("static singleton" in s for s in validator.validate_registry(self.payload)))

    def test_unresolved_field_must_not_invent_locator(self):
        pending = next(v for v in self.payload["variables"] if v["id"] == "golf.ball.world_xyz")
        pending["memory_locator"]["expression"] = "be_f32x3(0x91BE3834)"
        self.assertTrue(any("unresolved locator" in s for s in validator.validate_registry(self.payload)))

    def test_premature_training_approval_rejected(self):
        self.variable["training"]["approved"] = True
        self.variable["training"]["eligible_as_input"] = True
        errors = validator.validate_registry(self.payload)
        self.assertTrue(any("runtime_verified" in s for s in errors))
        self.assertTrue(any("reviewer" in s for s in errors))
        self.assertTrue(any("validation evidence" in s for s in errors))

    def test_unapproved_eligibility_rejected(self):
        self.variable["training"]["eligible_as_label"] = True
        self.assertTrue(any("unapproved" in s for s in validator.validate_registry(self.payload)))

    def test_two_training_roles_rejected(self):
        self.variable["training"]["eligible_as_input"] = True
        self.variable["training"]["eligible_as_label"] = True
        self.assertTrue(any("both" in s for s in validator.validate_registry(self.payload)))

    def test_wrong_revision_and_endian_rejected(self):
        self.variable["game"]["disc_revision"] = 0
        self.variable["game"]["endianness"] = "little"
        self.assertTrue(any("revision or endian" in s for s in validator.validate_registry(self.payload)))

    def test_empty_controls_rejected(self):
        self.variable["required_controls"] = []
        self.assertTrue(any("required_controls" in s for s in validator.validate_registry(self.payload)))


if __name__ == "__main__":
    unittest.main()
