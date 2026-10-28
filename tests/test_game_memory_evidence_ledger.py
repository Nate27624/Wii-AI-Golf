"""Offline S000 evidence ledger quality and anti-overclaim regression."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.game_memory_ledger import (
    read_memory_ledger, validate_memory_ledger,
)

SOURCE = ROOT / "research" / "memory" / "field-evidence-ledger.json"


class GameMemoryEvidenceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(SOURCE.read_text(encoding="utf-8"))

    def mutate(self, field_id, **changes):
        doc = copy.deepcopy(self.doc)
        item = next(row for row in doc["fields"] if row["field_id"] == field_id)
        item.update(changes)
        return doc

    def test_current_ledger_is_valid_without_training_claims(self):
        fields = validate_memory_ledger(self.doc)
        self.assertEqual(len(fields), 24)
        self.assertFalse(any(x["training_eligible"] for x in fields))
        self.assertEqual(len([x for x in fields if x["negative_control"]]), 4)
        self.assertEqual(len([x for x in fields if x["identity_level"] == "unlocated"]), 10)
        self.assertEqual(len([x for x in fields if x["object_role"] == "golf_field_manager"]), 6)
        self.assertEqual(len(read_memory_ledger(SOURCE)), 24)

    def test_environment_reference_is_not_a_physical_quantity(self):
        entries = validate_memory_ledger(self.doc)
        by_id = {entry["field_id"]: entry for entry in entries}
        for name in ("environment.current_pin_ref", "environment.current_start_ref",
                     "environment.cup_ref", "environment.wind_object_ref",
                     "environment.course_object_ref", "environment.map_data_ref"):
            entry = by_id[name]
            self.assertEqual(entry["identity_level"], "runtime_candidate")
            self.assertIsNotNone(entry["relative_offset"])
            self.assertFalse(entry["gameplay_value_verified"])
            self.assertFalse(entry["writer_instruction_verified"])
            self.assertFalse(entry["training_eligible"])
        # A confirmed reference cannot substitute for real ball XYZ or wind.
        self.assertEqual(by_id["gameplay.ball_position"]["identity_level"], "unlocated")
        self.assertEqual(by_id["gameplay.wind"]["identity_level"], "unlocated")
        with self.assertRaisesRegex(ValueError, "Training promotion"):
            validate_memory_ledger(self.mutate(
                "environment.current_pin_ref", training_eligible=True))

    def test_a_time_correlated_field_cannot_be_promoted_directly(self):
        with self.assertRaisesRegex(ValueError, "Training promotion"):
            validate_memory_ledger(self.mutate(
                "scene.golfer_main_candidate", training_eligible=True))
        with self.assertRaisesRegex(ValueError, "negative control"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074",
                source_typed_member_verified=True,
                writer_instruction_verified=True,
                independent_boot_replication_verified=True,
                same_shot_frame_join_verified=True,
                gameplay_value_verified=True,
                behavior_level="action_correlated",
                training_eligible=True))

    def test_unlocated_field_cannot_acquire_guessed_offset(self):
        with self.assertRaisesRegex(ValueError, "Unlocated"):
            validate_memory_ledger(self.mutate(
                "gameplay.swing_power", relative_offset="+0x080"))
        with self.assertRaisesRegex(ValueError, "Unlocated"):
            validate_memory_ledger(self.mutate(
                "gameplay.ball_velocity", gameplay_value_verified=True))

    def test_reject_private_address_and_unknown_schema_fields(self):
        with self.assertRaisesRegex(ValueError, "pointer/address"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074", notes="Private pointer at 0x80123456"))
        bad = self.mutate("golfer.main_0x074", raw_memory_hex="AABBCCDD")
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            validate_memory_ledger(bad)

    def test_reject_unaligned_offset_and_false_evidence_types(self):
        with self.assertRaisesRegex(ValueError, "aligned"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074", relative_offset="+0x075"))
        with self.assertRaisesRegex(ValueError, "booleans"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074", independent_boot_replication_verified=1))

    def test_no_evidence_no_behavior_or_runtime_claim(self):
        with self.assertRaisesRegex(ValueError, "evidence reference"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074", evidence_refs=[]))
        with self.assertRaisesRegex(ValueError, "known public"):
            validate_memory_ledger(self.mutate(
                "golfer.main_0x074",
                evidence_refs=["file:///C:/Users/private/RAW-PRIVATE.jsonl"]))

    def test_reject_duplicate_id_and_unknown_game_revision(self):
        doc = copy.deepcopy(self.doc)
        doc["fields"].append(copy.deepcopy(doc["fields"][0]))
        with self.assertRaisesRegex(ValueError, "repeated"):
            validate_memory_ledger(doc)
        doc = copy.deepcopy(self.doc)
        doc["target_revision"] = 2
        with self.assertRaisesRegex(ValueError, "revision"):
            validate_memory_ledger(doc)

    def test_missing_or_symlink_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            blank = Path(folder) / "missing.json"
            with self.assertRaisesRegex(ValueError, "Missing"):
                read_memory_ledger(blank)
            linked = Path(folder) / "linked.json"
            try:
                linked.symlink_to(SOURCE)
            except (OSError, NotImplementedError):
                return
            with self.assertRaisesRegex(ValueError, "linked"):
                read_memory_ledger(linked)


if __name__ == "__main__":
    unittest.main()
