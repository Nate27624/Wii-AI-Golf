"""Fabricated exact PPC savegpr prologue with fail-closed r3 effects."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_simulate_savegpr26_source as helper


def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def bl(pc,target):
    return (18<<26)|((target-pc)&0x03FFFFFC)|1


def good():
    e=helper.ENTRY
    m={
       e:d(37,1,1,-0x50),      # stwu r1,-0x50(r1)
       e+4:(31<<26)|(0<<21)|(339<<1),   # mfspr r0 (mflr class)
       e+8:d(36,0,1,0x54),   # stw r0,+0x54(r1)
       e+12:d(14,11,1,0x50), # addi r11,r1,0x50
       e+16:bl(e+16,helper.SAVE_HELPER),
       e+20:d(32,4,3,0x6B4),
    }
    for i,rs in enumerate(range(26,32)):
        m[helper.SAVE_HELPER+4*i]=d(36,rs,11,-24+4*i)
    m[helper.SAVE_HELPER+24]=0x4E800020
    return m


def run(m):
    return helper.inspect(lambda pc:m.get(pc,0x60000000))


class PPCPrologueTests(unittest.TestCase):
    def test_exact_savegpr_gpr26_to31_and_return_proves_bounded_preservation(self):
        r=run(good())
        self.assertEqual(r["status"],
                         "STATIC_PROLOGUE_PRESERVES_ENTRY_R3_UNDER_DIRECT_RETURN")
        self.assertTrue(r["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])
        self.assertTrue(r["six_save_gpr26_to31_stores_via_r11_no_r3_write"])
        self.assertTrue(r["source_helper_ends_with_plain_blr"])
        self.assertFalse(r["actual_r3_dynamic_object_type_verified"])
        self.assertFalse(r["member_6b4_semantic_role_verified"])
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["allowed_to_publish"])

    def test_r3_write_before_helper_abstains(self):
        m=good();m[helper.ENTRY+12]=d(14,3,3,8)
        r=run(m)
        self.assertFalse(r["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])
        self.assertFalse(r["four_entry_pre_call_instructions_have_only_supported_non_r3_writes"])

    def test_prologue_unsupported_x_form_abstains(self):
        m=good();m[helper.ENTRY+8]=(31<<26)|(3<<21)|(266<<1)
        self.assertFalse(run(m)["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])

    def test_r3_write_by_lwzu_ra_abstains(self):
        m=good();m[helper.ENTRY+8]=d(33,4,3,0x44)
        self.assertFalse(run(m)["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])

    def test_prehash_target_wrong_call_abstains(self):
        m=good();m[helper.CALL]=bl(helper.CALL,helper.SAVE_HELPER+4)
        self.assertFalse(run(m)["exact_linked_call_to_savegpr26"])
        self.assertFalse(run(m)["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])

    def test_nonlinked_branch_abstains(self):
        m=good();m[helper.CALL]&=~1
        self.assertFalse(run(m)["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])

    def test_helper_wrong_store_register_abstains(self):
        m=good();m[helper.SAVE_HELPER+8]=d(36,3,11,-16)
        r=run(m)
        self.assertFalse(r["six_save_gpr26_to31_stores_via_r11_no_r3_write"])
        self.assertFalse(r["entry_r3_preserved_to_6b4_load_under_bounded_prologue"])

    def test_helper_wrong_store_update_or_base_abstains(self):
        m=good();m[helper.SAVE_HELPER]=d(37,26,11,-24)
        self.assertFalse(run(m)["six_save_gpr26_to31_stores_via_r11_no_r3_write"])
        m=good();m[helper.SAVE_HELPER]=d(36,26,3,-24)
        self.assertFalse(run(m)["six_save_gpr26_to31_stores_via_r11_no_r3_write"])

    def test_helper_displacements_require_exact_progression(self):
        m=good();m[helper.SAVE_HELPER+4]=d(36,27,11,-25)
        self.assertFalse(run(m)["six_save_gpr26_to31_stores_via_r11_no_r3_write"])

    def test_helper_no_blr_abstains(self):
        m=good();m[helper.SAVE_HELPER+24]=0x60000000
        self.assertFalse(run(m)["source_helper_ends_with_plain_blr"])

    def test_load_other_offset_abstains(self):
        m=good();m[helper.LOAD]=d(32,4,3,0x88)
        self.assertFalse(run(m)["exact_lwz_r4_plus_0x6b4_r3_after_call"])

    def test_strict_word_validation_and_no_source_access(self):
        m=good()
        for bad in (None,True,-1,2**32,3.5):
            m[helper.SAVE_HELPER]=bad
            with self.assertRaises(ValueError):
                run(m)
        with self.assertRaises(ValueError):
            helper.inspect(None)

    def test_report_does_not_expose_any_raw_ppc_words_or_heap_pointers(self):
        payload=json.dumps(run(good()))
        for private in ("0x8029B43C","0x800B1D40","0x9000","PRIVATE"):
            self.assertNotIn(private,payload)


if __name__=="__main__":
    unittest.main()
