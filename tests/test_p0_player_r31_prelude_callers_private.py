"""Only synthetic PPC words, no Dolphin/native data in CI."""
from __future__ import annotations
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_player_r31_prelude_callers_private as m


def b(pc,target,linked=True):
    return (18<<26)|((target-pc)&0x03fffffc)|int(linked)


class EntryCallTests(unittest.TestCase):
    def test_preceding_plain_blr_yields_hypothetical_entry(self):
        words=[0x60000000]*(m.BACK//4+1)
        words[5]=0x4e800020
        words[12]=0x4e800020
        data=b"".join(struct.pack(">I",w) for w in words)
        c=m.candidate_after_blr(data,m.COPY-m.BACK)
        self.assertEqual(c,(m.COPY-m.BACK+13*4,m.COPY-m.BACK+6*4))

    def test_no_plain_blr_returns_no_hypothesis(self):
        data=b"\x60\x00\x00\x00"*(m.BACK//4+1)
        self.assertEqual(m.candidate_after_blr(data,m.COPY-m.BACK),())

    def test_branch_decode_forward_and_backward(self):
        pc=0x802A0000
        self.assertEqual(m.bl_target(pc,b(pc,pc+0x40)),pc+0x40)
        self.assertEqual(m.bl_target(pc,b(pc,pc-0x40)),pc-0x40)

    def test_nonlink_and_non_branch_do_not_count(self):
        self.assertIsNone(m.bl_target(0x802A0000,b(0x802A0000,0x802A0080,False)))
        self.assertIsNone(m.bl_target(0x802A0000,0x60000000))

    def test_scan_returns_public_relative_bl_only(self):
        lo=0x802A0000
        target=lo+0x20
        words=[0x60000000]*16
        words[3]=b(lo+12,target)
        words[4]=b(lo+16,target)
        data=b"".join(struct.pack(">I",w) for w in words)
        units=((lo,lo+len(data),"Pack/RPSports/RPGolScene/Fake.cpp"),)
        count,rows=m.scan(units,lambda x,y:data,(target,))
        self.assertEqual(count,1)
        self.assertEqual(rows[0]["direct_Golf_BL_count"],2)
        self.assertEqual(rows[0]["bounded_source_calls"][0]["relative_BL_site"],"+0x0000C")
        self.assertFalse(rows[0]["incoming_r3_selected_player_record_verified"])
        self.assertFalse(rows[0]["entry_function_boundary_proven"])

    def test_non_golf_unit_not_in_caller_count(self):
        lo=0x802A0000
        data=struct.pack(">I",b(lo,lo+0x20))
        count,rows=m.scan(((lo,lo+4,"Pack/Other/Thing.cpp"),),
                          lambda x,y:data,(lo+0x20,))
        self.assertEqual(count,0)
        self.assertEqual(rows[0]["direct_Golf_BL_count"],0)

    def test_wrong_candidate_or_truncated_source_fails(self):
        with self.assertRaises(ValueError):
            m.scan(((0x802A0000,0x802A0008,"Pack/RPSports/RPGolScene/X.cpp"),),
                   lambda x,y:b"\x00"*4,(0x802A0010,))
        with self.assertRaises(ValueError):
            m.candidate_after_blr(b"\x00"*4,m.COPY-m.BACK)

    def test_raw_memory_not_in_synthetic_output(self):
        lo=0x802A0000
        count,rows=m.scan(((lo,lo+4,"Pack/RPSports/RPGolScene/X.cpp"),),
                          lambda x,y:b"\x60\x00\x00\x00",(lo+0x40,))
        output=json.dumps(rows)
        self.assertNotIn("0x802A0000",output)
        self.assertNotIn("0x60000000",output)
        self.assertNotIn("private",output)

    def test_private_archive_failure_is_redacted(self):
        stderr=io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status=m.main(["--data-root","/missing","--private-session","SECRET_PATH"])
        self.assertEqual(status,2)
        self.assertNotIn("SECRET_PATH",stderr.getvalue())


if __name__=="__main__":
    unittest.main()
