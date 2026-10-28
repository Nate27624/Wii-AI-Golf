"""Fabricated-only seven-phase writer-input role tests."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
sys.path.insert(0, SCRIPT_DIR)
import audit_p0_seven_writer_inputs_private as target


def make_sample(phase):
    moving = {5: (0x3f800000, 0x40000000, 0x40400000),
              6: (0x40800000, 0x40a00000, 0x40c00000),
              7: (0x40e00000, 0x41000000, 0x41100000)}
    live = moving.get(phase, (0x3f800000,)*3)
    record = (0x3f800000,)*3
    endpoint = moving[7]
    return {
        "selected_index": 0, "hole": 1,
        "refs": {"scene_field": 0x90000010, "ball": 0x90000100,
                 "pin": 0x90000200, "start": 0x90000300},
        "triplets": {
            "record_0x060": record, "record_0x054": record,
            "ball_nested_plus_0x4c": live, "ball_object_0x030": live,
            "ball_cache_0x0cc": endpoint if phase in (5,6,7) else record,
            "ball_cache_0x0f0": endpoint if phase in (5,6,7) else record,
            "ball_cache_0x0fc": endpoint if phase in (5,6,7) else record,
            "source_current_start": record,
            "source_selected_pin": (0x42200000, 0x42000000, 0x42000000),
        },
        "ball_alias_validated": True,
        "pin_selfref_validated": True,
        "start_selfref_validated": True,
    }


class SevenWriterInputs(unittest.TestCase):
    def samples(self):
        return {i: make_sample(i) for i in range(1, 8)}

    def test_wedge_current_changes_while_static_player_input_and_cache(self):
        report = target.summarize(self.samples())
        self.assertEqual(report["sample_count_source_gated"], 7)
        self.assertEqual(report["wedge_current_ball_distinct_triplet_count"], 3)
        self.assertTrue(report["wedge_record_0x060_bitwise_constant"])
        self.assertTrue(report["wedge_cache_CC_bitwise_constant"])
        self.assertTrue(report["wedge_static_cache_CC_equal_final_W7_live"])
        self.assertTrue(report["wedge_static_cache_CC_differs_from_live_W5"])
        self.assertTrue(report["wedge_static_cache_CC_differs_from_live_W6"])
        self.assertTrue(report["wedge_constant_record_input_not_sufficient_as_sole_snapshot_state_source"])
        rows=report["per_snapshot_equal_components"]
        self.assertEqual(rows[4]["source_live_equals_cache_CC_components"], 0)
        self.assertEqual(rows[5]["source_live_equals_cache_CC_components"], 0)
        self.assertEqual(rows[6]["source_live_equals_cache_CC_components"], 3)
        self.assertEqual(rows[4]["source_live_equals_player_record_0x060_components"], 0)
        self.assertEqual(rows[6]["source_live_equals_player_record_0x060_components"], 0)
        self.assertFalse(report["cache_CC_is_predicted_landing_endpoint_verified"])
        self.assertFalse(report["global_ball_pointer_runtime_identity_verified"])
        self.assertFalse(report["approved_for_training"])
        self.assertFalse(report["allowed_to_publish"])

    def test_missing_phase_refused(self):
        samples=self.samples()
        del samples[4]
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_slot_hole_identity_refused(self):
        samples=self.samples()
        samples[6]["hole"]=2
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_runtime_ball_pointer_change_refused(self):
        samples=self.samples()
        samples[6]["refs"]["ball"]+=4
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_missing_source_alias_refused(self):
        samples=self.samples()
        samples[5]["ball_alias_validated"]=False
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_current_nested_alias_disagreement_refused(self):
        samples=self.samples()
        samples[5]["triplets"]["ball_object_0x030"]=(1,2,3)
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_source_vector_invalid_u32_refused(self):
        samples=self.samples()
        samples[5]["triplets"]["ball_cache_0x0cc"]=(1,2,-2)
        with self.assertRaises(ValueError): target.summarize(samples)

    def test_cache_changed_no_endpoint_precompute_flag(self):
        samples=self.samples()
        samples[6]["triplets"]["ball_cache_0x0cc"]=(9,10,11)
        report=target.summarize(samples)
        self.assertFalse(report["wedge_cache_CC_bitwise_constant"])
        self.assertFalse(report["wedge_static_cache_CC_equal_final_W7_live"])

    def test_privacy_and_false_physics_flags(self):
        report=target.summarize(self.samples())
        output=json.dumps(report)
        for needle in ("0x90000010","0x3f800000","D:\\\\Projects",
                       "sha256","raw_memory_words"):
            self.assertNotIn(needle,output)
        self.assertNotIn('"path"',output)
        self.assertFalse(report["actual_ball_world_xyz_axes_units_verified"])
        self.assertFalse(report["player_record_writer_executed_between_snapshots_verified"])

    def test_isolated_python_cli_from_unrelated_cwd(self):
        p=Path(target.__file__)
        run=subprocess.run([sys.executable,"-I",str(p),"--help"],
                           cwd=p.parents[2],capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn("--dump-directory",run.stdout)


if __name__=="__main__":
    unittest.main()
