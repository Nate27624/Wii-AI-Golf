"""Synthetic-only tests: cross-hit recurrence cannot become ball XYZ."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

FILE = Path(__file__).resolve().parents[1] / "scripts/contrast_p0_hit_signatures_private.py"
spec = importlib.util.spec_from_file_location("private_hit_contrast", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def candidate(offset="+0x078", pointer=False, window="minimap_ball_effect"):
    return {
        "source_relative_locations": [{
            "window": window, "relative_word_offset": offset,
            "triage_family": "visual_effect_confound"}],
        "before_or_after_pointer_shaped": pointer, "training_eligible": False
    }


def run(label, entries):
    return {"human_green_label": label, "audit": {
        "kind": mod.AUDIT_KIND, "human_contact_yes": True,
        "model_training_allowed": False, "verified_ball_xyz": False,
        "stored_persistent_candidate_count": len(entries), "candidates": entries}}


class CrossHitStratificationTests(unittest.TestCase):
    def test_strict_human_label_not_false_equals_no(self):
        self.assertEqual(mod.human_green_label({"human_observation": {
            "finished_on_green_human": "unknown"}}), "unknown")
        self.assertEqual(mod.human_green_label({"human_observation": {
            "finished_on_green_human": "yes"}}), "yes")
        self.assertEqual(mod.human_green_label({"human_observation": {
            "finished_on_green_human": "no"}}), "no")
        self.assertEqual(mod.human_green_label({}), "unknown")

    def test_single_yes_is_insufficient(self):
        x = mod.stratify([run("yes", [candidate()]),
                          run("no", [candidate()]),
                          run("no", [candidate("+0x07C", True)])])
        self.assertEqual(x["human_labeled_green_yes"], 1)
        self.assertEqual(x["human_labeled_green_no"], 2)
        self.assertTrue(x["single_green_positive_insufficient_for_specificity"])
        self.assertFalse(x["model_training_allowed"])
        self.assertEqual(x["signature_recurrence"][0]["present_in_total"], 2)

    def test_unknown_not_coded_as_offgreen(self):
        x = mod.stratify([run("unknown", [candidate()]),
                          run("no", [candidate()])])
        self.assertEqual(x["human_green_unknown"], 1)
        self.assertEqual(x["human_labeled_green_no"], 1)
        self.assertEqual(x["signature_recurrence"][0]["present_in_green_unknown"], 1)

    def test_aliases_deduplicated_per_run(self):
        first = candidate()
        first["source_relative_locations"].append({
            "window": "minimap_player_effect", "relative_word_offset": "+0x198",
            "triage_family": "visual_effect_confound"})
        reverse = copy.deepcopy(first)
        reverse["source_relative_locations"].reverse()
        x = mod.stratify([run("yes", [first, reverse]), run("no", [first])])
        self.assertEqual(x["signature_recurrence"][0]["present_in_total"], 2)
        self.assertEqual(x["signature_recurrence"][0]["present_in_green_yes"], 1)
        self.assertEqual(x["distinct_alias_signatures"], 1)

    def test_pointer_shape_not_approved(self):
        x = mod.stratify([run("no", [candidate(pointer=True)])])
        self.assertEqual(x["signature_recurrence"][0]["pointer_shaped_run_count"], 1)
        self.assertFalse(x["signature_recurrence"][0]["training_eligible"])

    def test_rejects_changed_candidate_count(self):
        q = run("yes", [candidate()])
        q["audit"]["stored_persistent_candidate_count"] = 2
        with self.assertRaises(ValueError):
            mod.stratify([q])

    def test_rejects_unsafe_audit(self):
        q = run("yes", [candidate()])
        q["audit"]["verified_ball_xyz"] = True
        with self.assertRaises(ValueError):
            mod.stratify([q])

    def test_rejects_untrusted_relative_offsets(self):
        q = run("no", [candidate("+0x90000000")])
        with self.assertRaises(ValueError):
            mod.stratify([q])

    def test_rejects_invalid_outcomes(self):
        with self.assertRaises(ValueError):
            mod.stratify([run("implicitly_no", [candidate()])])

    def test_scan_uses_existing_validator_for_every_pair(self):
        with tempfile.TemporaryDirectory() as root:
            cap = Path(root) / "Wii-AI-Golf-Data" / "captures"
            cap.mkdir(parents=True)
            for idx, label in enumerate(("yes", "no", "unknown")):
                stem = f"outcome-20261028T01270{idx}Z-synthetic"
                (cap / (stem+"-candidates.json")).write_text(json.dumps({
                    "human_observation": {"contact_human": "yes",
                                          "finished_on_green_human":label}
                }))
                (cap / (stem+"-RAW-PRIVATE.jsonl")).write_text(
                    json.dumps({"phase": "synthetic", "raw_test":idx}) + "\n")
            calls = []
            def fake_validate(summary, rows):
                calls.append((summary["human_observation"], rows))
                return run("yes", [candidate()])["audit"]
            auditor = SimpleNamespace(PRIVATE_ROOT=cap, audit=fake_validate)
            x = mod.scan_local(cap, auditor)
            self.assertEqual(len(calls), 3)
            self.assertEqual(x["validated_human_contact_captures"], 3)
            self.assertEqual(x["human_green_unknown"], 1)
            self.assertEqual(x["human_labeled_green_no"], 1)
            self.assertNotIn("outcome-20261028", json.dumps(x))

    def test_mismatched_private_folder_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            cap = Path(root)/"not-private"
            cap.mkdir()
            auditor = SimpleNamespace(PRIVATE_ROOT=cap, audit=lambda a,b: None)
            with self.assertRaises(ValueError):
                mod.scan_local(cap, auditor)

if __name__ == "__main__":
    unittest.main()
