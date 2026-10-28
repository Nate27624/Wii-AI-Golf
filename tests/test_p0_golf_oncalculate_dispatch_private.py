"""Entirely synthetic source dispatch decoder and privacy tests (no Dolphin/RAM)."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(HERE))
import audit_p0_golf_oncalculate_dispatch_private as study


def lwz_main():
    return (32 << 26) | (3 << 21) | (3 << 16) | 0x9C


def b_rel(to, *, pc=study.CALCULATE_PC + 4, link=False, absolute=False):
    li = (to - pc) if not absolute else to
    return (18 << 26) | (li & 0x03FFFFFC) | (2 if absolute else 0) | (1 if link else 0)


class GolfDispatchTests(unittest.TestCase):
    def test_positive_typed_main_load_and_direct_branch(self):
        target = study.MAIN_UNIT_LO + 0x120
        r = study.classify_two_word_source((lwz_main(), b_rel(target)))
        self.assertTrue(r["source_first_word_lwz_r3_scene_plus_0x9c"])
        self.assertTrue(r["oncalculate_to_main_direct_thunk_supported"])
        self.assertEqual(r["candidate_target_public_code_pc"], f"0x{target:08X}")
        self.assertFalse(r["one_callback_equals_one_guest_physics_step_verified"])

    def test_direct_b_without_link_required(self):
        target = study.MAIN_UNIT_LO
        a = study.classify_two_word_source((lwz_main(), b_rel(target, link=True)))
        self.assertFalse(a["source_second_word_direct_nonlinking_b"])
        self.assertFalse(a["oncalculate_to_main_direct_thunk_supported"])

    def test_wrong_scene_field_displacement_refused(self):
        word = (32 << 26) | (3 << 21) | (3 << 16) | 0x98
        r = study.classify_two_word_source((word, b_rel(study.MAIN_UNIT_LO)))
        self.assertFalse(r["source_first_word_lwz_r3_scene_plus_0x9c"])
        self.assertFalse(r["oncalculate_to_main_direct_thunk_supported"])

    def test_wrong_register_or_opcode_refused(self):
        bad = [(32 << 26) | (4 << 21) | (3 << 16) | 0x9C,
               (32 << 26) | (3 << 21) | (4 << 16) | 0x9C,
               (36 << 26) | (3 << 21) | (3 << 16) | 0x9C]
        for word in bad:
            with self.subTest(word=word):
                self.assertFalse(study.classify_two_word_source(
                    (word, b_rel(study.MAIN_UNIT_LO))
                )["oncalculate_to_main_direct_thunk_supported"])

    def test_not_in_main_text_is_not_classified_main(self):
        r = study.classify_two_word_source(
            (lwz_main(), b_rel(study.MAIN_UNIT_HI + 4)))
        self.assertTrue(r["source_second_word_direct_nonlinking_b"])
        self.assertFalse(r["direct_branch_target_in_published_RPGolMain_text"])
        self.assertFalse(r["oncalculate_to_main_direct_thunk_supported"])
        self.assertIsNone(r["candidate_target_public_code_pc"])

    def test_absolute_branch_to_low_pc_abstains(self):
        # PPC I-form absolute branch spans only +/-32 MB, not 0x8028....
        r = study.classify_two_word_source((lwz_main(), b_rel(0x1024, absolute=True)))
        self.assertFalse(r["direct_branch_target_in_published_RPGolMain_text"])

    def test_signed_negative_relative_target_decoder(self):
        pc = study.CALCULATE_PC + 4
        earlier = pc - 0x10
        self.assertEqual(study.decode_b_target(b_rel(earlier), pc), earlier)

    def test_indirect_branch_and_conditional_branch_abstain(self):
        self.assertIsNone(study.decode_b_target(0x4E800420, study.CALCULATE_PC + 4))
        self.assertIsNone(study.decode_b_target(0x41820010, study.CALCULATE_PC + 4))

    def test_malformed_two_word_source_rejected(self):
        for value in ((), (0,), (0, 0, 0), (-1, 0), (2**32, 0), (1.0, 0)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                study.classify_two_word_source(value)

    def test_source_scope_two_words_only(self):
        self.assertEqual(study.NEXT_CALLBACK_PC - study.CALCULATE_PC, 8)
        self.assertEqual(study.SCENE_MAIN_OFFSET, 0x9C)

    def test_archive_sha_failure_abstains_before_private_sample(self):
        with patch.object(study.seven, "_check_archive",
                          side_effect=ValueError("bad SHA")):
            with self.assertRaises(ValueError):
                study.analyze(Path("not-a-capture"))

    def test_output_privacy_and_no_training(self):
        r = study.classify_two_word_source(
            (lwz_main(), b_rel(study.MAIN_UNIT_LO)))
        s = json.dumps(r)
        for marker in ('"raw_words"', '"heap_pointer"', '"private_path"',
                       '"ball_translation"', '"frame_id"'):
            self.assertNotIn(marker, s)
        self.assertFalse(r["one_callback_equals_one_guest_physics_step_verified"])

    def test_python_isolated_help_off_root(self):
        script = HERE / "audit_p0_golf_oncalculate_dispatch_private.py"
        with tempfile.TemporaryDirectory() as td:
            x = subprocess.run(
                [sys.executable, "-I", str(script), "--help"],
                cwd=td, text=True, capture_output=True, timeout=20
            )
        self.assertEqual(x.returncode, 0, x.stderr)
        self.assertIn("--archive", x.stdout)


    def test_main_prefix_source_call_is_not_execution_proof(self):
        words = [0x60000000] * 64
        dest = 0x8029B270
        delta = dest - study.CONFIRMED_MAIN_TARGET
        words[0] = (18 << 26) | (delta & 0x03fffffc) | 1
        summary = study.classify_main_prefix(words)
        self.assertEqual(summary["source_direct_bl_to_simulation_unit_count"], 1)
        self.assertFalse(summary["all_reported_BL_sites_execute_in_game"])
        self.assertFalse(summary["one_main_callback_one_physics_update_verified"])

    def test_main_prefix_malformed_and_indirect_only(self):
        with self.assertRaises(ValueError):
            study.classify_main_prefix([0x60000000]*63)
        words = [0x60000000] * 64
        words[0] = 0x4e800421
        summary = study.classify_main_prefix(words)
        self.assertEqual(summary["source_direct_bl_lexical_count"], 0)
        self.assertEqual(summary["source_indirect_bclr_or_bcctr_lexical_count"], 1)

if __name__ == "__main__":
    unittest.main()
