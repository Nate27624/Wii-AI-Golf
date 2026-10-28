"""Offline synthetic tests only, no actual private RAM or Dolphin."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_inflight_vs_b0_private as audit


def sample(*, ball=(1,2,3), start=(1,2,3), record=(1,2,3),
           idx=0, hole=1):
    triplets={name: (1,2,3) for name, _, _ in audit.MEMBERS}
    triplets["ball_nested_plus_0x4c"]=ball
    triplets["source_current_start"]=start
    triplets["record_0x054"]=record
    return {
        "selected_index": idx, "hole": hole, "triplets": triplets,
        "whole_record": tuple(range(51)),
        "ball_constructor_translation_selfref": True,
        "start_constructor_selfrefs": True,
    }


class FlightCompareTests(unittest.TestCase):
    def test_ball_changes_with_stable_start_does_not_claim_xyz(self):
        result=audit.compare(sample(), sample(ball=(1,5,7)),
                             mem1_diff=True, mem2_diff=True)
        self.assertEqual(result["candidate_triplet_component_checks"]["ball_nested_plus_0x4c"]["changed_components_between_stationary_and_airborne"],2)
        self.assertTrue(result["candidate_ball_triplet_changed_while_start_stable"])
        self.assertFalse(result["actual_ball_world_xyz_verified"])
        self.assertFalse(result["mem1_mem2_exports_same_guest_frame_verified"])
        self.assertFalse(result["approved_for_training"])
        self.assertFalse(result["allowed_to_publish"])
        self.assertNotIn("pointer",json.dumps(result).lower().split("note")[0])

    def test_start_changes_disqualifies_stable_start_hypothesis(self):
        result=audit.compare(sample(),sample(ball=(1,5,7),start=(1,9,3)),
                             mem1_diff=True,mem2_diff=True)
        self.assertFalse(result["candidate_ball_triplet_changed_while_start_stable"])
        self.assertTrue(result["position_confounded_by_different_start"])

    def test_no_change_does_not_claim_ball_motion(self):
        result=audit.compare(sample(),sample(),mem1_diff=False,mem2_diff=False)
        self.assertEqual(result["candidate_triplet_component_checks"]["ball_nested_plus_0x4c"]["changed_components_between_stationary_and_airborne"],0)
        self.assertFalse(result["candidate_ball_triplet_changed_while_start_stable"])

    def test_different_slot_and_hole_refused(self):
        for kwargs in ({"idx":1},{"hole":3}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError,"owner or hole"):
                    audit.compare(sample(),sample(**kwargs),mem1_diff=True,mem2_diff=True)

    def test_51_word_offsets_only_no_words(self):
        a=sample()
        b=sample()
        b["whole_record"]=tuple(123456789 if j in (0, 26, 50) else x
                                 for j,x in enumerate(a["whole_record"]))
        report=audit.compare(a,b,mem1_diff=True,mem2_diff=True)
        self.assertEqual(report["selected_player_record_changed_relative_offsets"],
                         ["+0x000","+0x068","+0x0C8"])
        self.assertNotIn("123456789",json.dumps(report))

    def test_manifest_duplicate_or_false_synchronization_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            data={
                "kind":"private-human-observed-in-flight-dolphin-dump",
                "banks_same_physics_frame_verified":False,
                "ball_xyz_verified":False,
                "training_approved":False,
                "files":[
                    {"file":n,"bytes":v,"copy_verified":True,
                     "original_modified_utc":"2026-10-28T05:00:00Z",
                     "sha256":"0"*64}
                    for n,v in audit.SIZES.items()
                ]
            }
            file=p/audit.PRIVATE_MANIFEST
            data["files"][1]["file"]="mem1.raw"
            file.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"duplicate"):
                audit._flight_manifest(p)
            data["files"][1]["file"]="mem2.raw"
            data["banks_same_physics_frame_verified"]=True
            file.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"unknown or falsely"):
                audit._flight_manifest(p)

    def test_input_outside_private_root_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"data"
            root.mkdir()
            with self.assertRaisesRegex(ValueError,"nested"):
                audit._under_data(root,root)

    def test_sample_requires_source_chain_before_candidate_read(self):
        class RD:
            def u32(self,a):
                raise AssertionError("unvalidated source pointer deref")
            def header(self):
                return b""
        with patch.object(audit.selected,"analyze_one",side_effect=ValueError("bad Rev1 scene")):
            with self.assertRaisesRegex(ValueError,"bad Rev1"):
                audit._sample(RD())

    def test_invalid_record_word_count_refused(self):
        a=sample()
        b=sample()
        b["whole_record"]=(0,)*50
        with self.assertRaisesRegex(ValueError,"expected 51"):
            audit.compare(a,b,mem1_diff=True,mem2_diff=True)


if __name__=="__main__":
    unittest.main()
