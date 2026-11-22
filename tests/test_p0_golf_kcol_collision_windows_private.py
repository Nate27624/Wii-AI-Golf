"""Synthetic-only exact source anchors and bounded Wii Golf KCL query windows."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location(
    "golf_kcol_windows",SCRIPTS/"p0_golf_kcol_collision_windows_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def lwz(rt,ra,off):
    return (32<<26)|(rt<<21)|(ra<<16)|(off&0xffff)


def lfs(ft,ra,off):
    return (48<<26)|(ft<<21)|(ra<<16)|(off&0xffff)


def stfs(ft,ra,off):
    return (52<<26)|(ft<<21)|(ra<<16)|(off&0xffff)


def synthetic_source():
    words={m.KCOL_LO+offset:word for offset,word in m.ANCHORS.items()}
    words[m.KCOL_LO+0x1550]=lfs(4,3,0x54)
    words[m.KCOL_LO+0x1554]=stfs(1,4,0x40)
    words[m.KCOL_LO+0x1560]=(63<<26)
    words[m.KCOL_LO+0x20B0]=lwz(2,6,0x1C)
    return words, lambda addr:words.get(addr,0)


class KColWindowsTests(unittest.TestCase):
    def test_public_source_boundaries(self):
        self.assertEqual(m.KCOL_LO,0x802A3DE4)
        self.assertEqual(m.KCOL_HI,0x802A7444)
        self.assertEqual(len(m.WINDOWS),5)
        self.assertLessEqual(sum((hi-lo)//4 for _,lo,hi in m.WINDOWS),m.MAX_WORDS)

    def test_exact_original_control_links(self):
        d,r=synthetic_source()
        self.assertTrue(m.verify_anchors(r))
        self.assertEqual(m.branch_to(r(m.KCOL_LO+0x0034),m.KCOL_LO+0x0034),
                         (m.KCOL_LO+0x1540,True))
        self.assertEqual(m.branch_to(r(m.KCOL_LO+0x1AE4),m.KCOL_LO+0x1AE4),
                         (m.KCOL_LO+0x2090,False))

    def test_weak_provenance_anchor_changes_abstain(self):
        d,r=synthetic_source()
        for off in m.ANCHORS:
            with self.subTest(offset=off):
                w=dict(d)
                w[m.KCOL_LO+off]^=4
                with self.assertRaises(ValueError):
                    m.summarize(lambda x:w.get(x,0))

    def test_five_bounded_source_windows(self):
        d,r=synthetic_source()
        reports=m.summarize(r)
        self.assertEqual(len(reports),5)
        self.assertEqual(reports[0]["window"],"kcl_query_entry")
        self.assertEqual(reports[2]["window"],"ball_query_wrapper")
        self.assertEqual(reports[3]["window"],"collision_triangle_narrowphase")
        self.assertFalse(any(x["ball_tree_contact_verified"] for x in reports))

    def test_float_sanity_cues_are_not_tree_hitboxes(self):
        d,r=synthetic_source()
        reports=m.summarize(r)
        found=reports[1]
        self.assertEqual(found["floating_compares"],["+0x1560"])
        self.assertIn({"source_offset":"+0x1550","mnemonic":"lfs",
                       "base_register":"r3","offset_bytes":84},
                      found["selected_float_member_accesses"])
        self.assertFalse(found["source_tree_receiver_verified"])

    def test_optional_details_have_fixed_lengths(self):
        d,r=synthetic_source()
        reports=m.summarize(r,detail=True)
        for expected,report in zip(m.WINDOWS,reports):
            _,low,hi=expected
            self.assertEqual(len(report["source_code_lines"]),(hi-low)//4)
            self.assertTrue(all("GolfKCol+0x" in line for line in report["source_code_lines"]))

    def test_plain_summary_does_not_publish_original_opcodes(self):
        d,r=synthetic_source()
        reports=m.summarize(r)
        import json
        text=json.dumps(reports)
        self.assertNotIn("9421FFB0",text)
        self.assertNotIn('"source_code_lines"',text)
        self.assertNotIn("0x9000",text)

    def test_no_collision_claim_without_dataflow(self):
        d,r=synthetic_source()
        reports=m.summarize(r)
        self.assertTrue(m.NO_TREE_HITBOX_PROOF)
        self.assertTrue(all(not x["source_tree_receiver_verified"] and
                            not x["ball_tree_contact_verified"] for x in reports))

    def test_window_enforces_public_source_unit(self):
        d,r=synthetic_source()
        old=m.WINDOWS
        try:
            m.WINDOWS=(("bad_window",0x3400,0x4000),)
            with self.assertRaises(ValueError):
                m.summarize(r)
        finally:
            m.WINDOWS=old

    def test_branch_decoder_ignores_nonbranch(self):
        self.assertIsNone(m.branch_to(lwz(2,3,0x30),m.KCOL_LO))

    def test_float_comparison_not_confused_with_integer(self):
        d,r=synthetic_source()
        report=m.summarize(r)
        self.assertEqual(report[0]["floating_compares"],[])
        self.assertEqual(report[1]["floating_compares"],["+0x1560"])


if __name__=="__main__":
    unittest.main()
