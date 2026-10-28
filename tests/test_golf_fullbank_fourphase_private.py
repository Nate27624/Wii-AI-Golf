"""Entirely fabricated four-stage full-bank/typed overlay test. No game bytes."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_golf_fullbank_fourphase_private as x


def states():
    m=[bytearray(x.PAGE) for _ in range(4)]
    # Aim-specific persistent w0=w1 !=w2=w3 at source-block index 3.
    for i in (2,3):
        struct.pack_into(">I",m[i],3*x.BLOCK,0x3F800000)
    # Aim-specific reverted w0=w1=w3 !=w2 at same block.
    struct.pack_into(">I",m[2],3*x.BLOCK+4,0x40000000)
    # Timer/control change on all three boundaries in other block.
    for i in (0,1,2,3):
        struct.pack_into(">I",m[i],5*x.BLOCK,i+1)
    return m


class FullBankFourPhaseStudyTests(unittest.TestCase):
    def test_classifies_persistent_and_reverted_aim_signatures(self):
        with patch.dict(x.SIZES,{"MEM1":x.PAGE}):
            r=x._scan_bank(states(),"MEM1",top_blocks=4)
        self.assertEqual(r["all_aligned_words_examined"],1024)
        self.assertEqual(r["pages_different_by_transition"],[1,1,1])
        self.assertEqual(r["pages_different_in_any_transition"],1)
        self.assertEqual(r["word_change_counts"]["aim_persistent"],1)
        self.assertEqual(r["word_change_counts"]["aim_reverted"],1)
        self.assertEqual(r["word_change_counts"]["aim_with_quiet_prior_idle"],2)
        self.assertEqual(r["top_changed_256byte_blocks"][0][
            "bank_relative_block_index"],3)

    def test_block_rank_and_truncation(self):
        with patch.dict(x.SIZES,{"MEM1":x.PAGE}):
            r=x._scan_bank(states(),"MEM1",top_blocks=1)
        self.assertEqual(len(r["top_changed_256byte_blocks"]),1)
        self.assertEqual(r["omitted_changed_blocks"],1)
        self.assertEqual(r["changed_256byte_blocks_total"],2)

    def test_noshot_all_equal_is_empty_even_with_4_images(self):
        imgs=[bytearray(x.PAGE) for _ in range(4)]
        with patch.dict(x.SIZES,{"MEM1":x.PAGE}):
            r=x._scan_bank(imgs,"MEM1",top_blocks=10)
        self.assertEqual(r["pages_different_in_any_transition"],0)
        self.assertEqual(r["changed_256byte_blocks_total"],0)
        self.assertEqual(r["word_change_counts"],{})

    def test_invalid_input_size_and_sample_count_rejected(self):
        with patch.dict(x.SIZES,{"MEM1":x.PAGE}):
            for seq in (states()[:3],[bytearray(13)]*4):
                with self.assertRaises(ValueError):
                    x._scan_bank(seq,"MEM1",top_blocks=2)

    def test_source_region_relative_offset_and_pointer_reallocation_flag(self):
        pages=[(bytearray(0x4000),bytearray(0x4000)) for _ in range(4)]
        for stage,pair in enumerate(pages):
            # One mocked source-labelled object. Dynamic heap relocation is
            # re-resolved at every phase, not automatically confused for change.
            base=0x100 if stage<2 else 0x200
            struct.pack_into(">I",pair[1],base+0x04,
                             8 if stage>=2 else 0)
        with (patch.object(x.roster,"TwoBankReader",side_effect=lambda *p:object()),
              patch.object(x,"_resolve_objects",side_effect=[
                  (0,1,{"selected_player_record":(x.MEM2_BASE+(0x100 if i<2 else 0x200),0x20)})
                  for i in range(4)
              ])):
            r=x._region_analysis(pages,max_object_offsets=4)
        obj=r["source_resolved_regions"]["selected_player_record"]
        self.assertFalse(obj["source_object_address_constant_all_phases"])
        self.assertEqual(obj["counts"]["aim_persist_words"],1)
        self.assertEqual(obj["changed_word_details"][0][
            "source_object_relative_word_offset"],"+0x004")
        self.assertNotIn("0x90000100",json.dumps(r))

    def test_selected_slot_or_hole_change_fails_closed(self):
        pages=[(bytearray(0x2000),bytearray(0x2000)) for _ in range(4)]
        for vals in ((0,1,0,0),(1,1,2,1)):
            with (patch.object(x.roster,"TwoBankReader",side_effect=lambda *p:object()),
                  patch.object(x,"_resolve_objects",side_effect=[
                      (int(vals[i]),1,{"p":(x.MEM2_BASE+0x100,4)})
                      for i in range(4)
                  ])):
                with self.assertRaises(ValueError):
                    x._region_analysis(pages,max_object_offsets=3)

    def test_non_native_output_restrictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with self.assertRaises(ValueError):
                x.run_local(folder,folder/"results.json")

    def test_all_gate_flags_never_claim_semantics(self):
        with (patch.object(x,"_scan_bank",return_value={"word_change_counts":{}}),
              patch.object(x,"_region_analysis",return_value={
                  "source_resolved_regions":{},"selected_record_index":0
              })):
            r=x.analyze_four_pairs([(b"",b"")]*4)
        for field in ("physical_ball_xyz_verified","club_pose_verified",
                      "swing_power_verified","ball_motion_observed",
                      "approved_for_training","allowed_to_publish",
                      "independently_verified_guest_frames"):
            self.assertFalse(r[field])
        self.assertEqual(r["all_native_bytes_scanned_in_each_phase"],
                         88*1024*1024)

    def test_no_unbounded_cli_report_opts(self):
        for k in (0,x.MAX_TOP+1):
            with self.assertRaises(ValueError):
                x.analyze_four_pairs([(b"",b"")]*4,top_blocks=k)
        with self.assertRaises(ValueError):
            x.analyze_four_pairs([(b"",b"")]*4,max_object_offsets=0)

if __name__=="__main__":
    unittest.main()
