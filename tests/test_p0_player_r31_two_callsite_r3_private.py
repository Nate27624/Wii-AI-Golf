"""Synthetic PPC r3 source classes only; no native game banks."""
from __future__ import annotations
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_player_r31_two_callsite_r3_private as m


def d(op,rt=0,ra=0,disp=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&0xffff)


def x(xo,rs=0,ra=0,rb=0):
    return (31<<26)|(rs<<21)|(ra<<16)|(rb<<11)|(xo<<1)


def call_src(target=0x1BD4, at=0x2024):
    source_pc=m.UNIT_START+at
    target_pc=m.UNIT_START+target
    return (18<<26)|((target_pc-source_pc)&0x03fffffc)|1


def synthetic(changes=None, at=0x2024):
    words=[0x60000000]*(m.WINDOW//4+1)
    for off,word in (changes or {}).items():
        words[off]=word
    words[-1]=call_src(at=at)
    return b"".join(struct.pack(">I",w) for w in words)


class TwoCallsiteR3(unittest.TestCase):
    def test_mr_r3_r31_is_recognized(self):
        result=m.inspect_call(synthetic({39:x(444,31,3,31)}),
                              m.UNIT_START+0x2024-m.WINDOW,
                              m.UNIT_START+0x2024)
        self.assertEqual(result["nearest_post_barrier_r3_hint"]["class"],
                         "mr_register_copy")
        self.assertEqual(result["nearest_post_barrier_r3_hint"]["source"],"r31")
        self.assertFalse(result["incoming_r3_is_selected_player_record_verified"])

    def test_addi_from_r30_vs_zero_base_literal(self):
        self.assertEqual(m.r3_event(d(14,3,30,8))["source"],"r30")
        self.assertEqual(m.r3_event(d(14,3,0,8))["source"],"literal_zero_base")

    def test_load_from_r31_records_source_not_values(self):
        self.assertEqual(m.r3_event(d(32,3,31,0x10))["source"],"r31")
        self.assertEqual(m.r3_event(d(32,3,31,0x10))["class"],"gpr_memory_load")

    def test_andi_result_is_ra_not_rs(self):
        self.assertEqual(m.r3_event(d(28,31,3,0xF))["source"],"r31")
        self.assertIsNone(m.r3_event(d(28,3,31,0xF)))

    def test_mr_r30_r3_not_destination_r3(self):
        self.assertIsNone(m.r3_event(x(444,3,30,3)))

    def test_control_barrier_prevents_claimed_nearest(self):
        words={6:x(444,31,3,31),8:18<<26}
        result=m.inspect_call(synthetic(words),m.UNIT_START+0x2024-m.WINDOW,
                              m.UNIT_START+0x2024)
        self.assertIsNone(result["nearest_post_barrier_r3_hint"])
        self.assertEqual(result["r3_definition_or_uncertain_touch_count"],1)

    def test_two_real_site_numbers_accepted(self):
        for site in m.BL_RELS:
            value=m.inspect_call(synthetic(at=site),m.UNIT_START+site-m.WINDOW,
                                 m.UNIT_START+site)
            self.assertTrue(value["exact_direct_PPC_BL_source_verified"])
            self.assertEqual(value["source_call_site"],f"+0x{site:04X}")

    def test_other_direct_call_target_abstains(self):
        words=bytearray(synthetic())
        struct.pack_into(">I",words,m.WINDOW,call_src(target=0x1B74))
        with self.assertRaises(ValueError):
            m.inspect_call(bytes(words),m.UNIT_START+0x2024-m.WINDOW,
                           m.UNIT_START+0x2024)

    def test_unaligned_and_short_input_abstain(self):
        with self.assertRaises(ValueError):
            m.inspect_call(synthetic()[:-4],m.UNIT_START+0x2024-m.WINDOW,
                           m.UNIT_START+0x2024)
        with self.assertRaises(ValueError):
            m.inspect_call(synthetic(),m.UNIT_START+0x2024-m.WINDOW+4,
                           m.UNIT_START+0x2024)

    def test_calls_are_source_syntax_not_runtime_proof(self):
        raw=json.dumps(m.inspect_call(synthetic({39:d(14,3,31,0)}),
                        m.UNIT_START+0x2024-m.WINDOW,m.UNIT_START+0x2024))
        for keyword in ("0x60000000","private_session","ball-study"):
            self.assertNotIn(keyword,raw)
        self.assertIn('"last_straightline_origin_proves_runtime_argument": false',raw)

    def test_other_r3_changes_conservative_unknown(self):
        self.assertEqual(m.r3_event(x(999,3,0,2))["class"],
                         "extended_gpr_touch_uncertain")
        self.assertEqual(m.r3_event(d(46,2,31,0))["class"],
                         "lmw_overwrites_r3")

    def test_cli_missing_source_private_path_redacted(self):
        err=io.StringIO()
        with contextlib.redirect_stderr(err):
            rc=m.main(["--data-root","/missing","--private-session","SECRET_NAME"])
        self.assertEqual(rc,2)
        self.assertNotIn("SECRET_NAME",err.getvalue())


if __name__=="__main__":
    unittest.main()
