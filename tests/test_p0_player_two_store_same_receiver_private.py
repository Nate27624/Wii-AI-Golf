"""PPC fabricated source fragments only: no native RAM or Dolphin in CI."""
from __future__ import annotations
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_player_two_store_same_receiver_private as m


def d(op,rt=0,ra=0,disp=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&65535)


def mr(rs,ra):
    return (31<<26)|(rs<<21)|(ra<<16)|(rs<<11)|(444<<1)


def b(index,to,link=False,conditional=False):
    pc=m.BEGIN+index*4
    dest=m.BEGIN+to*4
    primary=16 if conditional else 18
    mask=0xFFFC if conditional else 0x03FFFFFC
    return (primary<<26)|((dest-pc)&mask)|int(link)


def sample(changes=None):
    words=[0x60000000]*m.COUNT
    words[0]=d(52,0,30,0x30)
    words[5]=mr(30,3)
    words[-1]=b(m.COUNT-1,(m.TARGET-m.BEGIN)//4,True)
    for i,w in (changes or {}).items():
        words[i]=w
    return b"".join(struct.pack(">I",w) for w in words)


class SameSourceReceiver(unittest.TestCase):
    def test_common_base_on_straightline_source(self):
        row=m.analyze(sample())
        self.assertTrue(row["caller_path_forwards_original_r30_to_callee_possible"])
        self.assertFalse(row["caller_path_has_unresolved_r3_or_r30_possible"])
        self.assertFalse(row["same_object_runtime_write_proven"])
        self.assertFalse(row["training_approved"])

    def test_r30_write_breaks_source_identity(self):
        row=m.analyze(sample({3:d(14,30,4,12)}))
        self.assertFalse(row["caller_path_forwards_original_r30_to_callee_possible"])
        self.assertTrue(row["caller_path_r30_changed_before_call_possible"])

    def test_branch_bypass_r30_clobber(self):
        row=m.analyze(sample({1:b(1,5,conditional=True),3:d(14,30,4,12)}))
        self.assertTrue(row["caller_path_forwards_original_r30_to_callee_possible"])
        self.assertTrue(row["caller_path_r30_changed_before_call_possible"])

    def test_r3_write_after_copy_breaks_forward(self):
        row=m.analyze(sample({6:d(14,3,0,1)}))
        self.assertFalse(row["caller_path_forwards_original_r30_to_callee_possible"])

    def test_r3_read_only_store_after_copy_preserves_forward(self):
        row=m.analyze(sample({6:d(36,3,1,0x44)}))
        self.assertTrue(row["caller_path_forwards_original_r30_to_callee_possible"])

    def test_intervening_call_requires_unknown_register_effect(self):
        row=m.analyze(sample({2:b(2,17,link=True)}))
        self.assertFalse(row["caller_path_forwards_original_r30_to_callee_possible"])
        self.assertTrue(row["caller_path_has_unresolved_r3_or_r30_possible"])
        self.assertIn("unverified_intervening_call_effect",row["caller_incomplete_reasons"])

    def test_update_form_r30_clobber(self):
        row=m.analyze(sample({3:d(49,3,30,12)}))
        self.assertFalse(row["caller_path_forwards_original_r30_to_callee_possible"])

    def test_source_only_mr_r3_r30_does_not_clobber_r30(self):
        self.assertEqual(m._write_r30(mr(30,3)),"none")
        self.assertTrue(m._mr_r3_r30(mr(30,3)))
        self.assertFalse(m._mr_r3_r30(mr(3,30)))

    def test_wrong_exact_store_copy_or_bl_abstains(self):
        cases=[sample({0:d(52,0,31,0x30)}),
               sample({5:mr(31,3)}),
               sample({m.COUNT-1:b(m.COUNT-1,8,link=False)}),
               sample()[:-4]]
        for blob in cases:
            with self.assertRaises(ValueError):
                m.analyze(blob)

    def test_no_raw_native_data_leaks(self):
        encoded=json.dumps(m.analyze(sample()))
        for s in ("0x60000000","0x802A","ball-study","private_session"):
            self.assertNotIn(s,encoded)
        self.assertIn('"true_function_boundary_or_typed_receiver_verified": false',encoded)

    def test_invalid_original_b0_redacted(self):
        err=io.StringIO()
        with contextlib.redirect_stderr(err):
            rc=m.main(["--data-root","/missing","--private-session","SECRET"])
        self.assertEqual(rc,2)
        self.assertNotIn("SECRET",err.getvalue())


if __name__=="__main__":
    unittest.main()
