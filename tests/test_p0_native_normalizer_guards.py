"""Isolated synthetic PPC normalizer guard opcode, provenance and abstention tests."""
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_p0_native_normalizer_guards_private as m


def fcmp(crf=0, fra=1, frb=2, ordered=False):
    return (63 << 26) | (crf << 23) | (fra << 16) | (frb << 11) | ((32 if ordered else 0) << 1)


def bc(bo=12, bi=2, bd=8, aa=False, lk=False):
    return (16 << 26) | (bo << 21) | (bi << 16) | (bd & 0xfffc) | (int(aa) << 1) | int(lk)


def bl(pc, target):
    return (18 << 26) | ((target-pc) & 0x03fffffc) | 1


def fixtures():
    result = {w: bytearray(w[1]-w[0]) for w in m.GUARD_WINDOWS.values()}
    def write(pc, word):
        lo, hi = next(w for w in result if w[0] <= pc < w[1])
        struct.pack_into(">I", result[lo,hi], pc-lo, word)
    return result, write


class GuardStudyTests(unittest.TestCase):
    def test_fcmpu_and_fcmpo_decode_registers(self):
        r = m.decode_compare(0x80295f3c, fcmp(3,4,7))
        self.assertEqual((r["op"],r["crf"],r["fra"],r["frb"]),
                         ("fcmpu",3,4,7))
        self.assertEqual(m.decode_compare(0x80295f40,fcmp(0,1,2,True))["op"],"fcmpo")

    def test_noncompare_xo_is_rejected(self):
        self.assertIsNone(m.decode_compare(0x80295f3c,(63<<26)|(1<<1)))
        self.assertIsNone(m.decode_compare(0x80295f3c,0))

    def test_relative_conditional_branch_sign(self):
        p=0x80295f60
        b=m.decode_bc(p,bc(bd=-8))
        self.assertEqual(b["target"],"0x80295F58")
        self.assertEqual((b["bo"],b["bi"],b["aa"],b["lk"]), (12,2,False,False))

    def test_absolute_conditional_branch_not_relocated(self):
        self.assertEqual(m.decode_bc(0x80295f60,bc(bd=0x100,aa=True))["target"],
                         "0x00000100")

    def test_compare_and_branch_candidates_remain_unverified(self):
        w,write=fixtures()
        write(0x80295F3C,fcmp())
        write(0x80295F40,bc(bd=8))
        write(0x80295F44,bl(0x80295F44,0x800E8558))
        r=m.lexical_guard_report(w)
        x=r["windows"]["lift_candidate"]
        self.assertEqual(x["total_counts"],[1,1,1])
        self.assertEqual(x["direct_helper_calls"],[["0x80295F44","0x800E8558"]])
        self.assertFalse(r["native_epsilon_or_exact_zero_proven"])
        self.assertFalse(r["same_selected_ball_receiver_verified"])
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["allowed_to_publish"])

    def test_standalone_fcmp_without_branch_is_not_guard_proof(self):
        w,write=fixtures()
        write(0x8029605C,fcmp())
        r=m.lexical_guard_report(w)
        self.assertEqual(r["windows"]["lateral_candidate"]["total_counts"],[1,0,0])
        self.assertFalse(r["zero_branch_operand_proven"])

    def test_guard_window_truncation_abstains(self):
        w,_=fixtures()
        w[m.GUARD_WINDOWS["lift_candidate"]]=b""
        with self.assertRaises(m.source.Abstain):
            m.lexical_guard_report(w)

    def test_guard_output_count_cap(self):
        w,_=fixtures()
        lo,hi=m.GUARD_WINDOWS["lateral_candidate"]
        for i in range(0,hi-lo,4):
            struct.pack_into(">I",w[lo,hi],i,bc())
        with self.assertRaises(m.source.Abstain):
            m.lexical_guard_report(w)

    def test_no_fake_selected_receiver_even_empty_source(self):
        w,_=fixtures()
        r=m.lexical_guard_report(w)
        self.assertEqual(r["nondegenerate_normalized_force_eligible"],"UNKNOWN")
        self.assertEqual(r["lift_vs_side_update_order"],"UNKNOWN")
        self.assertFalse(r["native_game_parity_verified"])

    def test_source_qualification_pre_post_gate(self):
        w,_=fixtures()
        banks=tuple((p, m.source.MEM1_SIZE,Path("dummy"),"same") for p in range(1,8))
        banks+=tuple((p,m.source.MEM2_SIZE,Path("dummy"),"same") for p in range(1,8))
        with patch.object(m.source,"_source_owners",return_value=True), \
             patch.object(m.source,"_find_candidates",return_value=((Path("fake"),"test"),)), \
             patch.object(m.source,"_validate_banks",side_effect=(banks,banks)) as verify, \
             patch.object(m.source,"_read_windows",return_value=w), \
             patch.object(m.source,"_source_gates",return_value={}):
            r=m.audit(Path("checkout"))
        self.assertEqual(verify.call_count,2)
        self.assertTrue(r["original_14_bank_sha_pre_post_verified"])
        self.assertTrue(r["phase_1_5_7_source_equal"])

    def test_phase_drift_abstains(self):
        w,_=fixtures()
        w2={k:bytes(v) for k,v in w.items()}
        w3={k:bytearray(v) for k,v in w.items()}
        w3[m.GUARD_WINDOWS["lift_candidate"]][0]=1
        banks=tuple((p,m.source.MEM1_SIZE,Path("dummy"),"same") for p in range(1,8))
        banks+=tuple((p,m.source.MEM2_SIZE,Path("dummy"),"same") for p in range(1,8))
        with patch.object(m.source,"_source_owners",return_value=True), \
             patch.object(m.source,"_find_candidates",return_value=((Path("fake"),"test"),)), \
             patch.object(m.source,"_validate_banks",return_value=banks), \
             patch.object(m.source,"_read_windows",side_effect=(w,w2,w3)), \
             patch.object(m.source,"_source_gates",return_value={}):
            with self.assertRaises(m.source.Abstain):
                m.audit(Path("checkout"))


if __name__ == "__main__":
    unittest.main()
