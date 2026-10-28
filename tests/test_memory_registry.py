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
