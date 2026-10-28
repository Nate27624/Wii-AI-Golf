"""Source-only fabricated PPC path fixtures; no native game memory in CI."""
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_r31_qualified_local_paths_private as m


def d(op,rt=0,ra=0,disp=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&65535)


def mr():
    return (31<<26)|(3<<21)|(31<<16)|(3<<11)|(444<<1)


def bc(index,target):
    pc=m.COPY+index*4
    dst=m.COPY+target*4
    return (16<<26)|((dst-pc)&0xFFFC)


def bl(index):
    pc=m.COPY+index*4
    dst=m.COPY+0x200
    return (18<<26)|((dst-pc)&0x03FFFFFC)|1


def sample(extra=None):
    words=[0x60000000]*m.COUNT
    words[0]=mr()
    words[-1]=d(52,0,31,0x90)
    for k,v in (extra or {}).items():
        words[k]=v
    return b"".join(struct.pack(">I",w) for w in words)


class QualifiedPaths(unittest.TestCase):
    def test_straightline_path_without_calls(self):
        r=m.analyze(sample())
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])
        self.assertTrue(r["all_linked_calls_assumed_EABI_r31_preserved"]["store_path_with_copy_still_intact_possible"])

    def test_cmpi_is_not_clobber(self):
        r=m.analyze(sample({6:d(11,31,31,42)}))
        self.assertFalse(next(q["direct_r31_write"] for q in r["known_source_instruction_classes"] if q["source_site"]=="+0x1C00"))
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])

    def test_call_strict_unknown_abi_possible(self):
        r=m.analyze(sample({5:bl(5)}))
        self.assertFalse(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_unknown_r31_possible"])
        self.assertTrue(r["all_linked_calls_assumed_EABI_r31_preserved"]["store_path_with_copy_still_intact_possible"])
        self.assertFalse(r["EABI_callee_assumption_verified_by_this_source_study"])

    def test_branch_bypasses_call_and_preserves_without_assumption(self):
        r=m.analyze(sample({3:bc(3,6),5:bl(5),6:d(11,31,31,9)}))
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_unknown_r31_possible"])

    def test_nonreg_writer_does_not_taint(self):
        r=m.analyze(sample({6:d(52,31,31,0x90)}))
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])

    def test_definite_clobber_before_store(self):
        r=m.analyze(sample({6:d(14,31,3,4)}))
        self.assertFalse(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_postcopy_r31_write_possible"])

    def test_unknown_effect_abstains_as_unknown(self):
        r=m.analyze(sample({6:2<<26}))
        self.assertFalse(r["no_callee_preservation_assumed"]["store_path_with_copy_still_intact_possible"])
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_with_unknown_r31_possible"])

    def test_conditional_branch_outside_slice_does_not_imply_store_executes(self):
        pc=m.COPY+7*4
        disp=0x80
        branch=(16<<26)|(disp&0xFFFC)
        r=m.analyze(sample({7:branch}))
        self.assertTrue(r["no_callee_preservation_assumed"]["store_path_exists"])
        self.assertIn("local_path_exits_window",r["no_callee_preservation_assumed"]["incomplete_reasons"])
        self.assertFalse(r["runtime_r31_store_executes_during_wedge_verified"])

    def test_indirect_source_branch_loses_path(self):
        r=m.analyze(sample({7:(19<<26)|(16<<1)}))
        self.assertFalse(r["no_callee_preservation_assumed"]["store_path_exists"])

    def test_malformed_exact_copy_or_store_abstains(self):
        for data in (sample()[:-1],sample({0:0x60000000}),sample({m.COUNT-1:d(52,0,30,0x90)})):
            with self.assertRaises(ValueError):
                m.analyze(data)

    def test_source_only_no_raw_opcode_or_golf_capture(self):
        report=json.dumps(m.analyze(sample()))
        for s in ("0x60000000","0x802A","ball-study-2026","original_B0_SHA256"):
            self.assertNotIn(s,report)
        self.assertFalse(m.analyze(sample())["approved_for_training"])

    def test_cli_missing_archive_no_private_path(self):
        out=io.StringIO()
        with contextlib.redirect_stderr(out):
            ret=m.main(["--data-root","/missing","--private-session","PRIVATE_SECRET"])
        self.assertEqual(ret,2)
        self.assertNotIn("PRIVATE_SECRET",out.getvalue())


if __name__=="__main__":
    unittest.main()
