"""Fabricated P0 Golf OnUserDraw source thunk source+archive guard tests."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_golf_onuserdraw_dispatch_private as d

def lwz_main():
    return (32 << 26)|(3 << 21)|(3 << 16)|0x9C

def branch(pc,target,link=False,absolute=False):
    disp = target if absolute else target-pc
    return (18 << 26)|(disp & 0x03FFFFFC)|(2 if absolute else 0)|(1 if link else 0)


class DrawThunkTests(unittest.TestCase):
    def test_source_exact_two_word_main_draw_thunk(self):
        dst=d.prior.MAIN_UNIT_LO + 0x100
        result=d.classify_draw_two_words([lwz_main(),branch(d.DRAW_PC+4,dst)])
        self.assertEqual(result["status"],
                         "SOURCE_TWO_WORD_DRAW_MAIN_TAILCALL_CANDIDATE")
        self.assertTrue(result["source_draw_main_tailcall_candidate"])
        self.assertEqual(result["qualified_target_public_PPC_code_PC"],
                         f"0x{dst:08X}")
        for key in ("runtime_vtable_slot_verified","game_draw_callback_executed_verified",
                    "actual_ball_render_submission_verified",
                    "visual_rendered_ball_correspondence_verified",
                    "guest_game_physics_frame_clock_verified","training_approved",
                    "allowed_to_publish"):
            self.assertFalse(result[key])

    def test_wrong_field_offset_is_negative_not_renderer_proof(self):
        wrong=lwz_main()+4
        result=d.classify_draw_two_words([
            wrong, branch(d.DRAW_PC+4,d.prior.MAIN_UNIT_LO)])
        self.assertFalse(result["source_draw_main_tailcall_candidate"])
        self.assertIsNone(result["qualified_target_public_PPC_code_PC"])

    def test_wrong_register_load_and_store_not_matched(self):
        for word in ((32<<26)|(4<<21)|(3<<16)|0x9C,
                     (32<<26)|(3<<21)|(4<<16)|0x9C,
                     (36<<26)|(3<<21)|(3<<16)|0x9C):
            with self.subTest(word=word):
                self.assertFalse(d.classify_draw_two_words([
                    word,branch(d.DRAW_PC+4,d.prior.MAIN_UNIT_LO)])[
                       "source_draw_main_tailcall_candidate"])

    def test_nonlink_branch_only(self):
        target=d.prior.MAIN_UNIT_LO+0x14
        self.assertFalse(d.classify_draw_two_words([
            lwz_main(), branch(d.DRAW_PC+4,target,link=True)])[
                "source_draw_main_tailcall_candidate"])

    def test_outside_main_is_not_validated_as_renderer(self):
        target=d.prior.MAIN_UNIT_HI+0x10
        x=d.classify_draw_two_words([
            lwz_main(),branch(d.DRAW_PC+4,target)])
        self.assertFalse(x["branch_target_in_published_RPGolMain_text"])
        self.assertIsNone(x["qualified_target_public_PPC_code_PC"])

    def test_low_pc_absolute_branch_is_refused(self):
        x=d.classify_draw_two_words([lwz_main(),branch(
            d.DRAW_PC+4,0x1000,absolute=True)])
        self.assertFalse(x["source_draw_main_tailcall_candidate"])

    def test_return_indirect_conditional_unknown(self):
        for word in (0x4E800020,0x4E800420,0x41820008):
            with self.subTest(word=word):
                self.assertFalse(d.classify_draw_two_words([
                    lwz_main(),word])["source_draw_main_tailcall_candidate"])

    def test_exact_source_two_word_bounds(self):
        self.assertEqual(d.NEXT_NAMED_ENTRY-d.DRAW_PC,8)
        self.assertEqual(d.DRAW_PC,0x8028DF78)
        self.assertEqual(d.prior.SCENE_MAIN_OFFSET,0x9C)

    def test_input_malformed_source_words_abstain(self):
        for words in ([],[0],[0,0,0],[-1,0],[2**32,0],[0.0,0],[True,0]):
            with self.subTest(words=words),self.assertRaises(ValueError):
                d.classify_draw_two_words(words)

    def test_original_bank_integrity_refusal_occurs_before_read(self):
        with patch.object(d.prior.seven,"_check_archive",
                          side_effect=ValueError("PRIVATE_ARCHIVE_0x9000")):
            with self.assertRaises(ValueError):
                d.analyze(Path("FAKE_PRIVATE"))
        with patch.object(d,"analyze",side_effect=ValueError("PRIVATE_ARCHIVE_0x9000")):
            from io import StringIO
            with patch("sys.stdout",new_callable=StringIO) as out:
                self.assertEqual(d.main(["--archive","/absent"]),2)
                self.assertNotIn("PRIVATE_ARCHIVE_0x9000",out.getvalue())

    def test_only_static_code_target_and_booleans_returned(self):
        x=json.dumps(d.classify_draw_two_words([
            lwz_main(),branch(d.DRAW_PC+4,d.prior.MAIN_UNIT_LO)]))
        for bad in ("private_ram","runtime_ball_ptr","model_drawn","MEM1.raw",
                    "0x90000000","scene_runtime_ptr"):
            self.assertNotIn(bad,x)

    def _run_fabricated_seven_with_calculate_target(self, calculate_target, *, expect_success):
        # In-memory mock source words; seven 4-byte fabricated files ONLY.
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for n in range(1,8):
                for bank in (1,2):
                    (root/f"{n}.{bank}.raw").write_bytes(b"MOCK")
            def fake_get(pc):
                vals={
                    0x804BF4D8:0x80001000,
                    0x8000100C:0x90002000,
                    0x9000201C:5,
                    0x90002054:2,
                    0x9000209C:0x90002200,
                    d.DRAW_PC:lwz_main(),
                    d.DRAW_PC+4:branch(d.DRAW_PC+4,0x8028E0B0),
                    0x8028E0B0:0x60000000,
                    d.prior.CALCULATE_PC:lwz_main(),
                    d.prior.CALCULATE_PC+4:branch(
                        d.prior.CALCULATE_PC+4,calculate_target),
                }
                return vals.get(pc,0)
            chk={n:root for n in range(1,8)}
            with patch.object(d.prior.seven,"_check_archive",side_effect=[chk,chk]) as check, \
                 patch.object(d.prior.seven,"SIZE",(4,4)), \
                 patch.object(d.prior.seven.src,"_file",
                     side_effect=lambda folder,name,size:folder/name), \
                 patch.object(d.prior.roster,"TwoBankReader",
                     side_effect=lambda *args:SimpleNamespace(u32=fake_get)), \
                 patch.object(d.prior.seven,"_get",return_value={"hole":0}), \
                 patch.object(d.prior.roster,"_bank",
                     side_effect=lambda ptr,size:
                     "MEM1" if ptr==0x80001000 else "MEM2"):
                if not expect_success:
                    with self.assertRaisesRegex(ValueError, "exact Calculate"):
                        d.analyze(root)
                    self.assertEqual(check.call_count,1)
                    return
                result=d.analyze(root)
                self.assertEqual(check.call_count,2)
                self.assertTrue(result["original_14_native_bank_SHA_pre_and_post_verified"])
                self.assertTrue(result["source_draw_main_tailcall_candidate"])
                self.assertEqual(result["source_draw_main_13_word_census"]["published_function_size_PPC_words"],13)
                self.assertEqual(result["source_draw_main_13_word_census"]["source_direct_BL_count"],0)
                self.assertFalse(result["source_draw_main_13_word_census"]["render_object_submit_function_typed_and_verified"])
                self.assertFalse(result["actual_ball_render_submission_verified"])
                self.assertFalse(result["guest_game_physics_frame_clock_verified"])

    def test_fabricated_full_seven_sha_before_after_and_two_word_scene(self):
        self._run_fabricated_seven_with_calculate_target(
            0x8028E158,expect_success=True)

    def test_in_unit_but_noncanonical_calculate_target_abstains(self):
        # Published RPGolMain unit membership is insufficient: user's real
        # canonical original source target was exactly 0x8028E158, not E1B8.
        self._run_fabricated_seven_with_calculate_target(
            0x8028E1B8,expect_success=False)

    def test_isolated_help_from_other_cwd(self):
        p=Path(__file__).resolve().parents[1]/"scripts"/"audit_p0_golf_onuserdraw_dispatch_private.py"
        with tempfile.TemporaryDirectory() as temp:
            run=subprocess.run([sys.executable,"-I",str(p),"--help"],
                              cwd=temp,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("--archive",run.stdout)


if __name__=="__main__":
    unittest.main()
