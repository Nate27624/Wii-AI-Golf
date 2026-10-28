"""Native-free fail-closed PPC destination tests for Golf sprintf argument audit.

Only syntactic r4 integrity. No real ROM/RAM, game or UI linkage.
"""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_sprintf_arg_origins_private as arg

START = 0x802A79F8
SITE = START + 0x100
UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"


def d(op, rt, ra, imm=0):
    return ((op << 26) | (rt << 21) | (ra << 16) | (imm & 0xFFFF))


def program(after):
    words = {SITE - 12: d(14, 4, 31, 0x40),
             SITE - 8: after,
             SITE: ((18 << 26) | ((arg.SPRINTF - SITE) & 0x03FFFFFC) | 1)}
    image = bytearray(b"\x60\x00\x00\x00" * 160)  # nop
    for pc, value in words.items():
        off = pc - START
        image[off:off + 4] = value.to_bytes(4, "big")
    return arg.local_sprintf_syntax(bytes(image), START, UNIT, SITE)


class SourceGprDestinationReview(unittest.TestCase):
    def assert_last_is_untyped_clobber(self, word, expected):
        row = program(word)
        self.assertEqual(row["format_pointer_r4_last_syntactic_definition"], expected)
        self.assertNotEqual(row["format_pointer_r4_last_syntactic_definition"],
                            "addi_from_r31")
        self.assertFalse(row["format_string_literal_or_specifiers_decoded"])
        self.assertFalse(row["output_text_is_hitting_the_green_distance_proven"])

    def test_original_addi_r31_remains_when_untouched(self):
        row = program(d(36, 4, 31, 0x10))  # stw r4, d(r31): READ r4
        self.assertEqual(row["format_pointer_r4_last_syntactic_definition"],
                         "addi_from_r31")

    def test_rotate_rA_writes_do_not_preserve_stale_format_origin(self):
        for op in (20, 21, 23):
            with self.subTest(op=op):
                self.assert_last_is_untyped_clobber(
                    d(op, 7, 4, 0),
                    "rotate_or_logical_immediate_rA_write_unknown_value")

    def test_logical_immediates_rA_dest_including_xori(self):
        for op in (24, 25, 26, 27, 28, 29):
            with self.subTest(op=op):
                self.assert_last_is_untyped_clobber(
                    d(op, 7, 4, 0),
                    "rotate_or_logical_immediate_rA_write_unknown_value")

    def test_lmw_range_includes_r4(self):
        for first in (0, 1, 2, 3, 4):
            with self.subTest(first=first):
                self.assert_last_is_untyped_clobber(
                    d(46, first, 9, 0),
                    "lmw_range_includes_register")

    def test_lmw_from_r5_does_not_touch_r4(self):
        row = program(d(46, 5, 9, 0))
        self.assertEqual(row["format_pointer_r4_last_syntactic_definition"],
                         "addi_from_r31")

    def test_stmw_does_not_touch_r4(self):
        row = program(d(47, 3, 9, 0))
        self.assertEqual(row["format_pointer_r4_last_syntactic_definition"],
                         "addi_from_r31")

    def test_store_update_rA_writes(self):
        for op in (37, 39, 45, 49, 51, 53, 55):
            with self.subTest(op=op):
                self.assert_last_is_untyped_clobber(
                    d(op, 2, 4, 0),
                    "memory_update_base_rA_write_unknown_value")

    def test_gpr_load_update_rA_writes_when_dest_is_other_reg(self):
        for op in (33, 35, 41, 43):
            with self.subTest(op=op):
                self.assert_last_is_untyped_clobber(
                    d(op, 2, 4, 0),
                    "integer_load_update_base_rA_write")

    def test_nonupdate_fpr_or_plain_store_no_r4_writer(self):
        for op in (36, 38, 44, 48, 50, 52, 54):
            with self.subTest(op=op):
                row = program(d(op, 4, 7, 0))
                self.assertEqual(
                    row["format_pointer_r4_last_syntactic_definition"],
                    "addi_from_r31")

    def test_addi_zero_base_is_literal_not_r0_provenance(self):
        for op, expected in ((14, "addi_or_addis_from_literal_zero_base"),
                             (15, "addi_or_addis_from_literal_zero_base")):
            with self.subTest(op=op):
                self.assertEqual(arg._reg_def_class(d(op, 4, 0, 44), 4), expected)

    def test_unverified_semantics_still_false_in_summary(self):
        report = arg.summarize([program(d(26, 7, 4, 0))])
        self.assertFalse(report["source_r4_is_verified_format_literal"])
        self.assertFalse(report["ui_render_call_link_verified"])
        self.assertFalse(report["result_distance_memory_state_verified"])
        self.assertFalse(report["training_approved"])
        self.assertFalse(report["allowed_to_publish"])


if __name__ == "__main__":
    unittest.main()
