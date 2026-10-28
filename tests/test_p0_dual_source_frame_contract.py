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
        self.assertEqual(r["source_global_equals_selected_cc_components_per_sample"],[3,3,3,3])
        self.assertFalse(r["actual_ball_world_xyz_verified"])

    def test_reject_persistently_aliased_global_and_selected_ball(self):
        rows = self.cohort()
        for row in rows:
            row["source_global_ball_object_pointer"] = (
                row["selected_ball_object_pointer"])
        # The former validator accepted a stable SAME-object relationship
        # while reporting accepted_for_offline_relationship_review=true.
        with self.assertRaisesRegex(ValueError, "must be distinct"):
            mod.summarize_private_samples(rows)

    def test_reject_even_single_aliased_frame(self):
        rows = self.cohort()
        rows[2]["source_global_ball_object_pointer"] = (
            rows[2]["selected_ball_object_pointer"])
        with self.assertRaises(ValueError):
            mod.summarize_private_samples(rows)

    def test_distinct_but_stable_ids_still_accepted(self):
        rows = self.cohort()
        result = mod.summarize_private_samples(rows)
        self.assertTrue(result["selected_global_object_pointers_distinct"])
        self.assertTrue(result["accepted_for_offline_relationship_review"])
        self.assertFalse(result["rendered_ball_object_identity_verified"])

    def test_reject_shot_label_with_all_candidate_vectors_stationary(self):
        rows = self.cohort()
        for row in rows:
            row["selected_ball_translation_words"] = (1, 2, 3)
            row["source_global_translation_words"] = (7, 8, 9)
            row["selected_ball_cache_cc_words"] = (7, 8, 9)
        with self.assertRaisesRegex(ValueError, "no changing source ball"):
            mod.summarize_private_samples(rows)

    def test_shot_label_global_only_change_is_accepted_as_candidate(self):
        rows = self.cohort()
        for i, row in enumerate(rows):
            row["selected_ball_translation_words"] = (1, 2, 3)
            row["selected_ball_cache_cc_words"] = (7, 8, 9)
            row["source_global_translation_words"] = (7 + i, 8, 9)
        report = mod.summarize_private_samples(rows)
        self.assertTrue(report["candidate_vector_change_observed"])
        self.assertFalse(report["candidate_change_proves_rendered_ball_motion"])
        self.assertFalse(report["rendered_ball_object_identity_verified"])

    def test_idle_report_is_never_misreported_as_motion(self):
        rows = [sample(i, stage="idle_control") for i in range(4)]
        for row in rows:
            row["selected_ball_translation_words"] = (1, 2, 3)
            row["source_global_translation_words"] = (7, 8, 9)
            row["selected_ball_cache_cc_words"] = (7, 8, 9)
        report = mod.summarize_private_samples(rows)
        self.assertFalse(report["candidate_vector_change_observed"])
        self.assertFalse(report["candidate_change_proves_rendered_ball_motion"])

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

    def test_reject_off_bank_and_unaligned_pointer_claims(self):
        # Nonzero u32 alone is not a native MEM1/MEM2 object pointer.
        for raw in (0x90001001, 0x80000001, 0x12345678, 0x94000000,
                    0x81800000, 0xC0001000, 0xFFFFFFFF, 0x90000002):
            with self.subTest(raw=raw):
                rows = self.cohort()
                for row in rows:
                    row["selected_ball_object_pointer"] = raw
                with self.assertRaisesRegex(ValueError, "canonical"):
                    mod.summarize_private_samples(rows)

    def test_each_source_pointer_uses_same_canonical_ram_gate(self):
        # All five fields must independently have aligned/native addresses.
        for key in mod.POINTERS:
            for bad in (0x90001001, 0x12345678):
                with self.subTest(key=key, bad=bad):
                    rows = self.cohort()
                    for row in rows:
                        row[key] = bad
                    with self.assertRaisesRegex(ValueError, "canonical"):
                        mod.summarize_private_samples(rows)

    def test_native_mem1_mem2_last_word_boundaries(self):
        self.assertTrue(mod._canonical_native_guest_pointer(0x80000000))
        self.assertTrue(mod._canonical_native_guest_pointer(0x817FFFFC))
        self.assertTrue(mod._canonical_native_guest_pointer(0x90000000))
        self.assertTrue(mod._canonical_native_guest_pointer(0x93FFFFFC))
        for not_native in (0x7FFFFFFC, 0x81800000, 0x8FFFFFFC,
                           0x94000000, True, 0, 0x100000000):
            with self.subTest(value=not_native):
                self.assertFalse(mod._canonical_native_guest_pointer(not_native))

    def test_good_distinct_native_ram_pointers_still_accepted(self):
        rows = self.cohort()
        for row in rows:
            row["selected_ball_object_pointer"] = 0x93FFFEF8
            row["source_global_ball_object_pointer"] = 0x90000000
        result = mod.summarize_private_samples(rows)
        self.assertTrue(result["selected_global_object_pointers_distinct"])
        self.assertFalse(result["rendered_ball_object_identity_verified"])
        self.assertFalse(result["training_approved"])

    def test_reject_selected_ball_pointer_with_no_room_for_4c_member(self):
        # Both values are aligned and inside native banks with one word
        # available, but PPC's ball-object +0x4C load would cross the end.
        for bad in (0x817FFFFC, 0x817FFFB4, 0x93FFFFFC, 0x93FFFFB4):
            with self.subTest(bank_end_pointer=bad):
                rows = self.cohort()
                for row in rows:
                    row["selected_ball_object_pointer"] = bad
                with self.assertRaisesRegex(ValueError, "bounded canonical"):
                    mod.summarize_private_samples(rows)

    def test_reject_global_ball_pointer_with_no_room_for_4c_member(self):
        for bad in (0x817FFFFC, 0x817FFFB4, 0x93FFFFFC, 0x93FFFFB4):
            with self.subTest(bank_end_pointer=bad):
                rows = self.cohort()
                for row in rows:
                    row["source_global_ball_object_pointer"] = bad
                with self.assertRaisesRegex(ValueError, "bounded canonical"):
                    mod.summarize_private_samples(rows)

    def test_selected_and_global_balls_can_reach_last_full_4c_field(self):
        rows = self.cohort()
        for row in rows:
            row["selected_ball_object_pointer"] = 0x93FFFEF8
            row["source_global_ball_object_pointer"] = 0x93FFFFB0
        result = mod.summarize_private_samples(rows)
        self.assertTrue(result["accepted_for_offline_relationship_review"])
        self.assertTrue(result["selected_global_object_pointers_distinct"])
        self.assertFalse(result["actual_guest_physics_time_verified_by_analyzer"])

    def test_other_object_types_retain_one_word_only_not_guessed_spans(self):
        # Original Rev1 readers actually require the three objects in MEM2
        # with +0x50, +0x50, +0xA8 footprints, respectively.
        rows = self.cohort()
        for row in rows:
            row["pin_object_pointer"] = 0x93FFFFB0
            row["start_object_pointer"] = 0x90004000
            row["field_manager_pointer"] = 0x93FFFF58
        self.assertTrue(mod.summarize_private_samples(rows)[
            "accepted_for_offline_relationship_review"])

    def test_4c_span_helper_fails_closed_on_bad_minimums(self):
        for minimum in (0, 1, 3, 5, -4, True, 2.0):
            with self.subTest(minimum=minimum):
                self.assertFalse(mod._canonical_native_guest_pointer(
                    0x90001000, min_bytes=minimum))
        self.assertTrue(mod._canonical_native_guest_pointer(
            0x93FFFFB0, min_bytes=0x50))
        self.assertFalse(mod._canonical_native_guest_pointer(
            0x93FFFFB4, min_bytes=0x50))

    def test_mem2_only_full_source_footprints_are_required(self):
        self.assertEqual(mod.SOURCE_OBJECT_MEM2_MIN_SPANS, {
            "selected_ball_object_pointer": 0x108,
            "source_global_ball_object_pointer": 0x50,
            "pin_object_pointer": 0x50,
            "start_object_pointer": 0x50,
            "field_manager_pointer": 0xA8,
        })
        self.assertTrue(mod._qualified_mem2_object_span(
            0x93FFFEF8, min_bytes=0x108))
        self.assertFalse(mod._qualified_mem2_object_span(
            0x93FFFEFC, min_bytes=0x108))
        self.assertTrue(mod._qualified_mem2_object_span(
            0x93FFFFB0, min_bytes=0x50))
        self.assertTrue(mod._qualified_mem2_object_span(
            0x93FFFF58, min_bytes=0xA8))

    def test_all_five_object_fields_refuse_mem1_even_with_available_span(self):
        # The source-global static r13 slot may be MEM1, but its pointee
        # is MEM2. Original readers restrict every source object to MEM2.
        for key in mod.POINTERS:
            with self.subTest(key=key):
                rows = self.cohort()
                for row in rows:
                    row[key] = 0x80001000
                with self.assertRaisesRegex(ValueError, "bounded canonical"):
                    mod.summarize_private_samples(rows)

    def test_each_mem2_object_rejects_its_last_partial_span(self):
        for key, span in mod.SOURCE_OBJECT_MEM2_MIN_SPANS.items():
            with self.subTest(key=key, span=span):
                rows = self.cohort()
                for row in rows:
                    row[key] = 0x94000000 - span + 4
                with self.assertRaisesRegex(ValueError, "bounded canonical"):
                    mod.summarize_private_samples(rows)

    def test_each_mem2_object_accepts_exact_full_span_boundary(self):
        for key, span in mod.SOURCE_OBJECT_MEM2_MIN_SPANS.items():
            with self.subTest(key=key, span=span):
                rows = self.cohort()
                for row in rows:
                    row[key] = 0x94000000 - span
                self.assertTrue(mod.summarize_private_samples(rows)[
                    "accepted_for_offline_relationship_review"])

    def test_selected_cc_fc_source_span_rejects_50_only_false_positive(self):
        # A selected ball with +0x50 room still cannot hold +0xFC
        # three-word region that the original source reader qualified.
        for near_end in (0x93FFFFB0, 0x93FFFF80, 0x93FFFF00):
            with self.subTest(selected=near_end):
                rows = self.cohort()
                for row in rows:
                    row["selected_ball_object_pointer"] = near_end
                with self.assertRaisesRegex(ValueError, "bounded canonical"):
                    mod.summarize_private_samples(rows)

    def test_mem2_span_helper_refuses_noninteger_or_unaligned_minimum(self):
        for bad in (True, False, -4, 0, 1, 2.0, 5, 0x101):
            with self.subTest(bad=bad):
                self.assertFalse(mod._qualified_mem2_object_span(
                    0x90001000, min_bytes=bad))
        for bad in (0x94000000, 0x817FFFF0, 0x90000002, 0x7FFFFFFC,
                    0xFFFFFFFF, True, "0x90000000"):
            with self.subTest(bad=bad):
                self.assertFalse(mod._qualified_mem2_object_span(
                    bad, min_bytes=0x50))

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
