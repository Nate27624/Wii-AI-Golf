"""Entirely fabricated dual-object offline timing/source safety tests."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_p0_dual_source_frame_contract.py"
spec = importlib.util.spec_from_file_location("dual_frame_review", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample(i: int, *, stage="shot_observation"):
    return {
        "game_id": "RSPE01", "disc_revision": 1,
        "golf_scene_id": 5, "golf_mode": 4,
        "guest_frame_index": 100 + i * 2,
        "guest_frame_clock_type": "machine_guest_physics_frame",
        "same_callback_guest_frame_observation_attested": True,
        "source_selected_chain_verified": True,
        "rev1_ppc_source_gate_verified": True,
        "read_overhead_us": 700,
        "boot_identity": "private-boot-001",
        "shot_identity": "private-shot-001",
        "selected_player_index": 0,
        "hole_index": 1,
        "stage": stage,
        "selected_ball_object_pointer": 0x90001000,
        "source_global_ball_object_pointer": 0x90002000,
        "pin_object_pointer": 0x90003000,
        "start_object_pointer": 0x90004000,
        "field_manager_pointer": 0x90005000,
        "selected_ball_translation_words": (1 + i, 20 + i, 30 + i),
        "source_global_translation_words": (7, 8, 9),
        "selected_ball_cache_cc_words": (7, 8, 9),
        "pin_translation_words": (2, 3, 4),
        "start_translation_words": (1, 1, 1),
        "config_bc_c0_c4_words": (10, 20, 30),
    }


class DualObjectTests(unittest.TestCase):
    def cohort(self):
        return [sample(i) for i in range(4)]

    def test_distinct_global_and_selected(self):
        r=mod.summarize_private_samples(self.cohort())
        self.assertTrue(r["selected_global_object_pointers_distinct"])
        self.assertEqual(r["global_object_changed_components_per_transition"],[0,0,0])
        self.assertEqual(r["selected_ball_changed_components_per_transition"],[3,3,3])
        self.assertEqual(r["source_global_equals_selected_cc_components_per_sample"],[3,3,3])
        self.assertFalse(r["actual_ball_world_xyz_verified"])

    def test_no_real_frame_claim_from_attestation(self):
        r=mod.summarize_private_samples(self.cohort())
        self.assertFalse(r["actual_guest_physics_time_verified_by_analyzer"])
        self.assertTrue(r["frame_indices_externally_attested_not_independently_verified"])

    def test_reject_bridge_ticks_claimed_as_frames(self):
        rows=self.cohort();rows[2]["guest_frame_clock_type"]="bridge_coroutine_tick"
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_unattested_same_hook(self):
        rows=self.cohort();rows[2]["same_callback_guest_frame_observation_attested"]=False
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_wrong_revision_or_scene(self):
        for key,value in (("disc_revision",0),("golf_scene_id",4),("golf_mode",2),("game_id","BAD")):
            with self.subTest(key=key):
                rows=self.cohort();rows[0][key]=value
                with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_pointer_relocation_selected(self):
        rows=self.cohort();rows[3]["selected_ball_object_pointer"]+=4
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_pointer_relocation_global(self):
        rows=self.cohort();rows[3]["source_global_ball_object_pointer"]+=4
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_changed_pin_contents_same_pointer(self):
        rows=self.cohort();rows[3]["pin_translation_words"]=(0,0,0)
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_changed_start_contents(self):
        rows=self.cohort();rows[3]["start_translation_words"]=(0,1,1)
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_changed_config(self):
        rows=self.cohort();rows[2]["config_bc_c0_c4_words"]=(10,21,30)
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_wrong_boot(self):
        rows=self.cohort();rows[1]["boot_identity"]="another"
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_wrong_shot(self):
        rows=self.cohort();rows[1]["shot_identity"]="another"
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_frame_rollback(self):
        rows=self.cohort();rows[2]["guest_frame_index"]=rows[1]["guest_frame_index"]
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_frame_gap_beyond_bound(self):
        rows=self.cohort();rows[2]["guest_frame_index"]=rows[1]["guest_frame_index"]+5
        rows[3]["guest_frame_index"]=rows[2]["guest_frame_index"]+2
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_over_budget(self):
        rows=self.cohort();rows[2]["read_overhead_us"]=5001
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_mixed_stage(self):
        rows=self.cohort();rows[3]["stage"]="idle_control"
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_idle_requires_absolute_stationarity(self):
        rows=[sample(i,stage="idle_control") for i in range(4)]
        for row in rows:
            row["selected_ball_translation_words"]=(1,2,3)
        self.assertEqual(mod.summarize_private_samples(rows)["declared_stage"],"idle_control")
        rows[3]["selected_ball_translation_words"]=(2,2,3)
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_unknown_extra_raw_field(self):
        rows=self.cohort();rows[0]["unreviewed_raw_data"]=[0x90001000]
        with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_reject_malformed_words(self):
        for v in ((0,1,-1),(0,1,2.0),(0,1,0x100000000),(0,1)):
            with self.subTest(v=v):
                rows=self.cohort();rows[2]["selected_ball_translation_words"]=v
                with self.assertRaises(ValueError): mod.summarize_private_samples(rows)

    def test_result_does_not_contain_raw_pointer_or_shot_id(self):
        r=mod.summarize_private_samples(self.cohort())
        self.assertNotIn("private-shot-001",str(r))
        self.assertNotIn("2415923200",str(r))
        self.assertNotIn("0x9000",str(r))
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["allowed_to_publish"])

    def test_dry_run_no_live_mode(self):
        p=subprocess.run([sys.executable,str(SCRIPT)],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('"emulator_contacted": false',p.stdout.lower())
        self.assertIn('"private_samples_read": 0',p.stdout.lower())


if __name__ == "__main__":
    unittest.main()
