"""Fabricated native-free constructor register-clobber/branch-bypass tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_ball_ctor_return_register_risks as m

def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)

def dform(op,rt,ra,imm=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)

def bc(pc,dest):
    return (16<<26)|((dest-pc)&0xfffc)

def branch(pc,dest):
    return (18<<26)|((dest-pc)&0x03fffffc)

def fixture():
    w={pc:0x60000000 for pc in range(m.ENTRY,m.END,4)}
    w[m.ENTRY+4]=mr(31,3)
    w[m.FINAL_COPY]=mr(3,31)
    w[m.RETURN]=0x4e800020
    return w

class RegGuard(unittest.TestCase):
    def test_clean_syntactic_path_keeps_all_claim_flags_false(self):
        o=m.audit(fixture().__getitem__)
        self.assertTrue(o["source_no_detected_r31_or_r3_clobber_or_direct_bypass"])
        self.assertEqual(o["recognized_r31_write_count"],0)
        self.assertEqual(o["recognized_r3_suffix_write_count"],0)
        self.assertTrue(o["entry_saved_receiver_is_r31"])
        self.assertFalse(o["whole_function_receiver_to_return_must_def_verified"])
        self.assertFalse(o["training_approved"])

    def test_lwz_r31_clobber_classified(self):
        w=fixture();w[m.ENTRY+0x40]=dform(32,31,1,4)
        o=m.audit(w.__getitem__)
        self.assertEqual(o["recognized_r31_write_count"],1)
        self.assertEqual(o["recognized_r31_writes_after_save_before_copy"][0]["write_risk_class"],"direct_integer_destination")

    def test_lmw_r27_clobbers_r31(self):
        w=fixture();w[m.ENTRY+0x40]=dform(46,27,1,4)
        o=m.audit(w.__getitem__)
        self.assertEqual(o["recognized_r31_write_count"],1)
        self.assertEqual(o["recognized_r31_writes_after_save_before_copy"][0]["write_risk_class"],"lmw_includes_register")

    def test_stmw_r27_does_not_write_r31(self):
        w=fixture();w[m.ENTRY+0x40]=dform(47,27,1,4)
        self.assertEqual(m.audit(w.__getitem__)["recognized_r31_write_count"],0)

    def test_ori_destination_r31_not_source(self):
        w=fixture();w[m.ENTRY+0x40]=dform(24,3,31,0)
        self.assertEqual(m.audit(w.__getitem__)["recognized_r31_write_count"],1)

    def test_stwu_base_r31_is_write(self):
        w=fixture();w[m.ENTRY+0x40]=dform(37,4,31,8)
        self.assertEqual(m.audit(w.__getitem__)["recognized_r31_write_count"],1)

    def test_nonupdating_stw_source_r31_not_write(self):
        w=fixture();w[m.ENTRY+0x40]=dform(36,31,1,8)
        self.assertEqual(m.audit(w.__getitem__)["recognized_r31_write_count"],0)

    def test_ambiguous_X_form_r31_risk(self):
        w=fixture();w[m.ENTRY+0x40]=(31<<26)|(31<<21)|(1<<16)|(2<<11)|(266<<1)
        o=m.audit(w.__getitem__)
        self.assertEqual(o["recognized_r31_write_count"],1)

    def test_tail_r3_clobber_from_lwz_refused_to_claim_safe(self):
        w=fixture();w[m.FINAL_COPY+4]=dform(32,3,1,12)
        o=m.audit(w.__getitem__)
        self.assertEqual(o["recognized_r3_suffix_write_count"],1)
        self.assertFalse(o["source_no_detected_r31_or_r3_clobber_or_direct_bypass"])

    def test_direct_bypass_branch_detected(self):
        w=fixture();w[m.ENTRY+0x40]=bc(m.ENTRY+0x40,m.RETURN)
        o=m.audit(w.__getitem__)
        self.assertTrue(o["direct_branch_bypasses_copy"])
        self.assertFalse(o["source_no_detected_r31_or_r3_clobber_or_direct_bypass"])

    def test_nonbypass_local_branch_not_overclaimed(self):
        w=fixture();w[m.ENTRY+0x40]=branch(m.ENTRY+0x40,m.ENTRY+0x80)
        self.assertFalse(m.audit(w.__getitem__)["direct_branch_bypasses_copy"])

    def test_external_branch_preserves_unknown_without_runtime_proof(self):
        w=fixture();w[m.ENTRY+0x40]=branch(m.ENTRY+0x40,m.END+0x10)
        o=m.audit(w.__getitem__)
        self.assertTrue(o["external_branch_sites"])
        self.assertFalse(o["whole_function_receiver_to_return_must_def_verified"])

    def test_indirect_branch_classified(self):
        w=fixture();w[m.ENTRY+0x40]=0x4e800420
        self.assertTrue(m.audit(w.__getitem__)["indirect_branch_sites"])

    def test_missing_entry_r3_save_abstains(self):
        w=fixture();w[m.ENTRY+4]=0x60000000
        with self.assertRaises(ValueError):m.audit(w.__getitem__)

    def test_duplicate_entry_save_abstains(self):
        w=fixture();w[m.ENTRY+8]=mr(31,3)
        with self.assertRaises(ValueError):m.audit(w.__getitem__)

    def test_missing_return_copy_abstains(self):
        w=fixture();w[m.FINAL_COPY]=mr(3,30)
        with self.assertRaises(ValueError):m.audit(w.__getitem__)

    def test_missing_blr_abstains(self):
        w=fixture();w[m.RETURN]=0x4e800420
        with self.assertRaises(ValueError):m.audit(w.__getitem__)

    def test_invalid_word_abstains(self):
        w=fixture();w[m.ENTRY+12]=-1
        with self.assertRaises(ValueError):m.audit(w.__getitem__)

    def test_privacy_and_false_physics_flags(self):
        out=m.audit(fixture().__getitem__)
        serialized=json.dumps(out)
        for token in ("raw_u32","0x9000","private_file_path","bank_sha256"):
            self.assertNotIn(token,serialized)
        self.assertFalse(out["actual_global_pointer_runtime_identity_verified"])
        self.assertFalse(out["physical_world_xyz_velocity_contact_power_score_verified"])
        self.assertFalse(out["allowed_to_publish"])

if __name__=="__main__":
    unittest.main()
