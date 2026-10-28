"""Fully fabricated PPC + no-emulator score/metadata stride disambiguation tests."""
from __future__ import annotations
import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_golf_config_getter_suffix_private as m


def d(op,rt=0,ra=0,imm=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)


def x(xo,dst,a,b):
    return (31<<26)|(dst<<21)|(a<<16)|(b<<11)|(xo<<1)


def slwi(src,dest,shift):
    return (21<<26)|(src<<21)|(dest<<16)|(shift<<11)|((31-shift)<<1)


def source_fixture():
    data={}
    for name,start,end in m.prev.FUNCTIONS:
        words=[0x60000000]*((end-start)//4)
        words[-1]=0x4E800020
        data[name]=words
    a=data["get_nth_hole_score"]
    b=data["get_nth_hole_strokes"]
    for i,w in {
        0x40:d(32,7,13,-1852),
        0x48:d(14,0,0,0),
        0x50:d(15,6,0,0x803c),
        0x54:d(7,5,3,36),
        0x58:slwi(4,0,2),
        0x5c:slwi(3,3,4),
        0x60:d(14,6,6,0x7aa0),
        0x64:x(266,3,7,3),
        0x68:x(266,4,6,5),
        0x6c:x(266,3,3,0),
        0x70:d(32,4,4,4),
        0x74:d(32,0,3,4),
        0x78:x(40,3,4,0),
    }.items():
        a[i//4]=w
    for i,w in {
        0x40:d(32,5,13,-1852),
        0x48:d(14,0,0,0),
        0x50:slwi(4,0,2),
        0x54:slwi(3,3,4),
        0x58:x(266,3,5,3),
        0x5c:x(266,3,3,0),
        0x60:d(32,3,3,4),
    }.items():
        b[i//4]=w
    return {n:b"".join(struct.pack(">I",w) for w in xs) for n,xs in data.items()}


def replace_word(window,name,offset,w):
    arr=bytearray(window[name])
    struct.pack_into(">I",arr,offset,w)
    return {**window,name:bytes(arr)}


class GetterSuffixReview(unittest.TestCase):
    def test_fabricated_two_indexed_paths_support_syntax_only(self):
        z=m.evaluate_windows(source_fixture())
        self.assertTrue(z["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])
        self.assertTrue(z["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])
        self.assertTrue(z["second_getter_16byte_row_4byte_player_column_candidate"])
        self.assertFalse(z["typed_score_row_orientation_fully_verified"])
        self.assertFalse(z["training_approved"])

    def test_multiplication_36_not_9(self):
        blobs=source_fixture()
        x=m.evaluate_windows(replace_word(blobs,"get_nth_hole_score",0x54,d(7,5,3,9)))
        self.assertFalse(x["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])

    def test_wrong_shift_for_hole_record_is_rejected(self):
        z=m.evaluate_windows(replace_word(source_fixture(),"get_nth_hole_score",0x5c,slwi(3,3,2)))
        self.assertFalse(z["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])

    def test_load_register_receiver_must_match(self):
        z=m.evaluate_windows(replace_word(source_fixture(),"get_nth_hole_score",0x74,d(32,3,4,4)))
        self.assertFalse(z["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])

    def test_actual_rev1_r0_load_and_subf_registers_required(self):
        # Real Rev1 source reported +0x74 lwz r0,4(r3),
        # +0x78 subf r3,r4,r0. Earlier test fixture used r3 incorrectly.
        real=m.evaluate_windows(source_fixture())
        self.assertTrue(real["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])
        self.assertTrue(real["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])
        wrong_load=m.evaluate_windows(replace_word(
            source_fixture(),"get_nth_hole_score",0x74,d(32,3,3,4)))
        self.assertFalse(wrong_load["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])
        wrong_subf=m.evaluate_windows(replace_word(
            source_fixture(),"get_nth_hole_score",0x78,x(40,3,4,3)))
        self.assertFalse(wrong_subf["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])
        self.assertFalse(real["typed_score_row_orientation_fully_verified"])

    def test_subtract_direction_must_match(self):
        z=m.evaluate_windows(replace_word(source_fixture(),"get_nth_hole_score",0x78,x(40,3,3,4)))
        self.assertTrue(z["first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate"])
        self.assertFalse(z["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])

    def test_branch_in_suffix_abstains(self):
        z=m.evaluate_windows(replace_word(source_fixture(),"get_nth_hole_score",0x60,18<<26))
        self.assertFalse(z["source_suffix_branch_free"])
        self.assertFalse(z["first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value"])

    def test_second_getter_wrong_register_add_abstains(self):
        z=m.evaluate_windows(replace_word(source_fixture(),"get_nth_hole_strokes",0x58,x(266,3,6,3)))
        self.assertFalse(z["second_getter_16byte_row_4byte_player_column_candidate"])

    def test_external_static_sda_load_role_only(self):
        z=m.evaluate_windows(source_fixture())
        fst=z["two_getter_source_clue_sites"][0]["focused_sites"]
        self.assertEqual(fst[1]["opcode_class"],"addis")
        self.assertEqual(fst[1]["source_registers"],["r0"])
        self.assertEqual(fst[1]["address_role"],"zero_base_literal")
        self.assertTrue(z["both_getters_load_candidate_config_root_from_same_r13_slot"])
        self.assertEqual(z["score_getter_r7_r13_load_sites"],["+0x40"])
        self.assertEqual(z["strokes_getter_r5_r13_load_sites"],["+0x40"])
        self.assertIs(z["config_score_root_r7_function1_and_r5_function2_verified"],False)

    def test_published_HoleInfo_literal_is_source_matched_not_runtime_typed(self):
        x=m.evaluate_windows(source_fixture())
        self.assertTrue(x["public_HoleInfo_static_root_literal_matches_source_rev1_symbol"])
        self.assertFalse(x["metadata_root_r6_function1_verified"])
        wrong=m.evaluate_windows(replace_word(
            source_fixture(),"get_nth_hole_score",0x60,d(14,6,6,0x7aa4)))
        self.assertFalse(wrong["public_HoleInfo_static_root_literal_matches_source_rev1_symbol"])

    def test_different_config_sda_load_displacements_are_not_equivalent(self):
        x=m.evaluate_windows(replace_word(
            source_fixture(),"get_nth_hole_strokes",0x40,d(32,5,13,-1856)))
        self.assertFalse(x["both_getters_load_candidate_config_root_from_same_r13_slot"])
        self.assertFalse(x["actual_sda_runtime_pointer_value_verified"])

    def test_two_root_loads_in_first_function_are_ambiguous(self):
        x=m.evaluate_windows(replace_word(
            source_fixture(),"get_nth_hole_score",0x24,d(32,7,13,-1852)))
        self.assertFalse(x["both_getters_load_candidate_config_root_from_same_r13_slot"])

    def test_no_raw_native_source_words_or_paths(self):
        s=json.dumps(m.evaluate_windows(source_fixture()))
        for key in ("private_archive","0x60000000","0x9000", "0x803c",
                    '"native_opcode_words"', "source_sha256", '"score_values"'):
            self.assertNotIn(key,s)

    def test_missing_original_archive_is_redacted(self):
        err=io.StringIO()
        with patch.object(m.prev.seven,"_check_archive",
                          side_effect=ValueError("SECRET")):
            with contextlib.redirect_stderr(err):
                rc=m.main(["--archive","SECRET"])
        self.assertEqual(rc,2)
        self.assertNotIn("SECRET",err.getvalue())

    def test_window_length_and_wrong_function_rejected(self):
        f=source_fixture()
        with self.assertRaises(ValueError):
            m.evaluate_windows({"get_nth_hole_score":f["get_nth_hole_score"]})
        f["get_nth_hole_strokes"]=f["get_nth_hole_strokes"][:-4]
        with self.assertRaises(ValueError):
            m.evaluate_windows(f)

    def test_isolated_cli_help_safe(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,"-I",str(ROOT/"scripts"/"audit_p0_golf_config_getter_suffix_private.py"),"--help"],
                             cwd=td,text=True,capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)


if __name__=="__main__":
    unittest.main()
