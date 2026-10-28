"""Synthetic-only tests for private JSON capture-provenance inventory."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inventory_private_golf_json_motion.py"
spec = importlib.util.spec_from_file_location("json_motion_inventory", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class JsonMotionInventoryTests(unittest.TestCase):
    def test_detects_varying_ball_vectors_without_claiming_physics(self):
        records = [
            {"shot_id": "fake", "frame": 100, "phase": "flight",
             "ball": {"position": [1.0, 2.0, 3.0], "velocity": [0.0,-1.0,0.0]}},
            {"shot_id": "fake", "frame": 101, "phase": "flight",
             "ball": {"position": [1.0, 1.7, 3.0], "velocity": [0.0,-2.0,0.0]}}
        ]
        summary = mod.summarize_records(records)
        self.assertTrue(summary["candidate_changing_ball_vector_paths"])
        self.assertIn("flight", summary["declared_phase_terms"])
        self.assertTrue(summary["velocity_related_paths"])
        self.assertFalse(summary["ball_world_xyz_verified"])
        self.assertFalse(summary["motion_or_vertical_velocity_verified"])
        self.assertNotIn("1.7", json.dumps(summary))

    def test_different_records_without_motion_keys_do_not_claim_motion(self):
        summary = mod.summarize_records([
            {"ball": {"position": [1.0, 2.0, 3.0]}},
            {"ball": {"position": [1.0, 2.0, 3.0]}}
        ])
        self.assertFalse(summary["candidate_changing_ball_vector_paths"])
        self.assertFalse(summary["possible_motion_annotation"])

    def test_single_record_not_independent_motion(self):
        summary = mod.summarize_records([
            {"ball": {"position": [1.0, 2.0, 3.0]}}
        ])
        self.assertFalse(summary["candidate_changing_ball_vector_paths"])

    def test_velocity_key_is_not_verified_velocity(self):
        summary = mod.summarize_records([
            {"ball_velocity_candidate": 42, "phase": "settled"}
        ])
        self.assertTrue(summary["velocity_related_paths"])
        self.assertFalse(summary["motion_or_vertical_velocity_verified"])
        self.assertIn("settled", summary["declared_phase_terms"])

    def test_nested_json_and_jsonl_parsed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"one.json").write_text(json.dumps(
                {"observations": [{"phase": "pre", "ball": {"xyz": [1,2,3]}},
                                  {"phase": "post", "ball": {"xyz": [1,4,3]}}]}))
            (root/"two.jsonl").write_text(
                json.dumps({"frame": 1, "ball": {"position": [1,2,3]}})+"\n"+
                json.dumps({"frame": 2, "ball": {"position": [1,3,3]}})+"\n")
            report = mod.audit_directory(root)
            self.assertEqual(report["files_scanned"], 2)
            self.assertTrue(all(not x["ball_world_xyz_verified"]
                                for x in report["candidate_files"]))
            self.assertTrue(all(x["candidate_changing_ball_vector_paths"]
                                for x in report["candidate_files"]))
            self.assertFalse(report["training_approved"])

    def test_directory_ignores_non_json_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"private.bin").write_bytes(b'RSPE')
            (root/"valid.json").write_text('{"foo":1}')
            self.assertEqual(mod.audit_directory(root)["files_scanned"], 1)

    def test_size_budget_avoids_large_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"large.json").write_text('{"data":"' + "a"*4096 + '"}')
            self.assertEqual(mod.audit_directory(root, max_file_bytes=100)["files_scanned"],0)
            self.assertEqual(mod.audit_directory(root, max_file_bytes=100)
                             ["files_skipped_by_reason"]["oversize"],1)

    def test_report_does_not_include_numeric_vector_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"f.jsonl").write_text(
                json.dumps({"ball": {"position":[98765.1, 12345.2, 111.3]}})+"\n"+
                json.dumps({"ball": {"position":[22222.1, 33333.2, 44444.3]}}))
            result = mod.audit_directory(root)
            body = json.dumps(result)
            self.assertNotIn("98765.1",body)
            self.assertNotIn("22222.1",body)
            self.assertEqual(result["candidate_files"][0]["file_id"],
                             mod.rel_identifier("f.jsonl"))

    def test_capture_paths_are_local_only_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"a.json").write_text("{}")
            row = mod.audit_directory(root)["candidate_files"][0]
            self.assertIn("relative_path_PRIVATE", row)
            self.assertFalse(row["shot_to_RAM_pair_verified"])

if __name__ == "__main__":
    unittest.main()
