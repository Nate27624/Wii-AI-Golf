"""Synthetic PPC arithmetic source windows only; no native RAM or code banks."""
from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_golf_config_score_index_ppc_private as pp


def d(op,rt=0,ra=0,disp=0):
    return (op << 26)|(rt << 21)|(ra << 16)|(disp & 0xFFFF)


def add(rt=5,ra=3,rb=4):
    return (31 << 26)|(rt<<21)|(ra<<16)|(rb<<11)|(266<<1)


def slwi(rs=3,ra=5,shift=2):
    return (21<<26)|(rs<<21)|(ra<<16)|(shift<<11)|((31-shift)<<1)


def fixture(events=None):
    events = events or {}
    blobs={}
    for name,lo,hi in pp.FUNCTIONS:
        words=[0x60000000]*((hi-lo)//4)
        for i,word in events.get(name,{}).items():
            words[i] = word
        blobs[name]=b"".join(struct.pack(">I",w) for w in words)
    return blobs


class PpcScoreLayoutConflict(unittest.TestCase):
    def test_exact_function_sizes_and_public_config_window(self):
        rows=pp.summarize_source_windows(fixture())["source_functions"]
        self.assertEqual([r["bounded_source_instruction_count"] for r in rows],[32,26])
        self.assertFalse(rows[0]["score_index_orientation_verified"])

    def test_mulli_player_by_nine_is_source_syntax_only(self):
        x=pp.instruction_clue(d(7,5,4,9),0)
        self.assertEqual(x["opcode_class"],"mulli")
        self.assertEqual(x["sources"],["r4"])
        self.assertEqual(x["source_immediate"],9)

    def test_mulli_hole_by_four_is_source_syntax_only(self):
        x=pp.instruction_clue(d(7,5,3,4),4)
        self.assertEqual(x["sources"],["r3"])
        self.assertEqual(x["source_immediate"],4)
        self.assertEqual(x["function_relative_site"],"+0x04")

    def test_slwi_register_and_shift_are_recognized(self):
        x=pp.instruction_clue(slwi(3,5,2),0)
        self.assertEqual(x["opcode_class"],"slwi")
        self.assertEqual(x["source_shift"],2)
        self.assertEqual(x["dest"],"r5")
        self.assertEqual(x["sources"],["r3"])

    def test_add_register_sources_not_source_words(self):
        x=pp.instruction_clue(add(5,3,4),0)
        self.assertEqual(x["opcode_class"],"add")
        self.assertEqual(x["sources"],["r3","r4"])
        self.assertEqual(x["dest"],"r5")

    def test_member_load_only_reports_allowed_source_offset(self):
        self.assertEqual(pp.instruction_clue(d(32,5,3,4),0)["opcode_class"],"lwz")
        self.assertIsNone(pp.instruction_clue(d(32,5,3,0x9000),0))

    def test_branch_and_return_not_assumed_executed(self):
        words={"get_nth_hole_score":{0:0x4E800020,1:18<<26}}
        result=pp.summarize_source_windows(fixture(words))
        classes=[x["opcode_class"] for x in result["source_functions"][0]["recognized_source_syntax"]]
        self.assertIn("blr",classes)
        self.assertIn("branch",classes)
        self.assertFalse(result["one_unique_row_order_selected"])

    def test_conflicting_public_header_sources_explicit(self):
        result=pp.summarize_source_windows(fixture())
        self.assertIn("ogws_info-player-major-4x9",result["header_disagreement"])
        self.assertIn("Kokeshi-hole-major-9x4",result["header_disagreement"])
        self.assertFalse(result["training_approved"])

    def test_truncated_or_extra_function_refused(self):
        for wrong in [
            {"get_nth_hole_score":b"", "get_nth_hole_strokes":b""},
            {"get_nth_hole_score":b"\x00"*128},
            {"get_nth_hole_score":b"\x00"*128,
             "get_nth_hole_strokes":b"\x00"*105}
        ]:
            with self.assertRaises(ValueError):
                pp.summarize_source_windows(wrong)

    def test_numeric_native_words_and_addresses_never_exported(self):
        words={"get_nth_hole_score":{1:d(7,5,4,9),2:slwi(3,5,2)}}
        j=json.dumps(pp.summarize_source_windows(fixture(words)))
        for forbidden in ("0x60000000","0x8029CBD4","0x9000","private_path",
                          '"raw_words"','"actual_score"'):
            self.assertNotIn(forbidden,j)

    def test_no_local_archive_does_not_leak_filename(self):
        err=io.StringIO()
        with patch.object(pp.seven,"_check_archive",side_effect=ValueError("SECRET")):
            with contextlib.redirect_stderr(err):
                ret=pp.main(["--archive","SECRET_PRIVATE_PATH"])
        self.assertEqual(ret,2)
        self.assertNotIn("SECRET",err.getvalue())

    def test_python_isolated_help_no_game_io(self):
        script=ROOT/"scripts"/"audit_p0_golf_config_score_index_ppc_private.py"
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                             cwd=tmp,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)


if __name__=="__main__":
    unittest.main()
