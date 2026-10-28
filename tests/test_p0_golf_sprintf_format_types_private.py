"""Fabricated only PPC branch and bounded format-type audit tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_sprintf_format_types_private as triage

UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
START = 0x802A79F8
CALL = START + 0x1200
GUEST = 0x80400130


def d(op, rd, ra, imm=0):
    return (op << 26) | (rd << 21) | (ra << 16) | (imm & 0xFFFF)


def bl(pc, dest, link=True):
    delta = dest - pc
    if delta % 4 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("fixture branch overflow")
    return (18 << 26) | (delta & 0x03FFFFFC) | int(link)


def synthetic(parts=(), via_r6=True):
    code = bytearray(b"\x60\x00\x00\x00" * 0x1400)
    src = 6 if via_r6 else 31
    words = {
        CALL - 24: d(15, src, 0, 0x8040),     # signed high half
        CALL - 20: d(14, 31, src, 0x0120),   # low half
        CALL - 16: d(14, 4, 31, 0x0010),     # format r4 from r31
        CALL: bl(CALL, triage.prior.SPRINTF),
    }
    words.update(dict(parts))
    for pc, word in words.items():
        offset = pc - START
        code[offset:offset + 4] = word.to_bytes(4, "big")
    return bytes(code)


def inspect(parts=(), via_r6=True, text=b"result=%d ft\x00"):
    def read_at(addr, length):
        if addr != GUEST:
            raise ValueError("wrong candidate")
        return (text + b"\x00" * length)[:length]

    return triage.examine(
        synthetic(parts, via_r6), START, UNIT, CALL, read_at)


class StrictFormatTypeTests(unittest.TestCase):
    def test_linear_lis_r6_then_r31_and_format_numeric(self):
        result = inspect()
        self.assertEqual(result["static_format_candidate_status"],
                         "bounded_linear_constant_candidate")
        c = result["format_buffer_class"]
        self.assertTrue(c["has_integer_conversion"])
        self.assertFalse(c["has_float_conversion"])
        self.assertFalse(c["literal_content_exposed"])
        self.assertFalse(result["visible_result_or_backing_state_verified"])

    def test_linear_lis_r31_then_addi_r31_then_r4(self):
        result = inspect(via_r6=False, text=b"%1.1f\x00")
        self.assertEqual(result["static_format_candidate_status"],
                         "bounded_linear_constant_candidate")
        self.assertTrue(result["format_buffer_class"]["has_float_conversion"])

    def test_branch_between_high_and_low_abstains(self):
        r = inspect(parts=((CALL - 22 * 4, bl(CALL - 22 * 4,
                                              CALL - 20, False)),))
        self.assertNotEqual(r["static_format_candidate_status"],
                            "bounded_linear_constant_candidate")
        self.assertEqual(r["format_buffer_class"]["status"], "not_qualified")

    def test_call_barrier_after_high_cannot_prove_const(self):
        r = inspect(parts=((CALL - 22, bl(CALL - 24, CALL - 20, True)),))
        # Misaligned fixture key intentionally rejected by synthetic()
        self.assertEqual(r["format_buffer_class"]["status"], "not_qualified")

    def test_last_r4_xori_write_invalidates_pointer(self):
        r = inspect(parts=((CALL - 4, d(26, 19, 4, 0x12)),))
        self.assertEqual(r["static_format_candidate_status"],
                         "r4_last_def_not_addi_r31")

    def test_last_r4_lmw_range_invalidates_pointer(self):
        r = inspect(parts=((CALL - 4, d(46, 3, 1, 0x10)),))
        self.assertEqual(r["static_format_candidate_status"],
                         "r4_last_def_not_addi_r31")

    def test_last_r4_stwu_ra_update_invalidates_pointer(self):
        r = inspect(parts=((CALL - 4, d(37, 1, 4, 0x10)),))
        self.assertEqual(r["static_format_candidate_status"],
                         "r4_last_def_not_addi_r31")

    def test_r31_other_write_before_r4_blocks_chained_const(self):
        r = inspect(parts=((CALL - 18, d(14, 31, 28, 0)),))
        self.assertNotEqual(r["static_format_candidate_status"],
                            "bounded_linear_constant_candidate")

    def test_high_half_not_lis_fails_closed(self):
        r = inspect(parts=((CALL - 24, d(14, 6, 0, 0x8000)),))
        self.assertEqual(r["static_format_candidate_status"],
                         "high_half_not_source_lis")

    def test_pointer_out_of_mem1_fails_without_read(self):
        r = inspect(parts=((CALL - 24, d(15, 6, 0, 0x7000)),))
        self.assertEqual(r["static_format_candidate_status"],
                         "candidate_pointer_outside_original_mem1")
        self.assertEqual(r["format_buffer_class"]["status"], "not_qualified")

    def test_format_string_utf8_nonascii_not_interpreted(self):
        r = inspect(text=b"\xff %d\x00")
        self.assertEqual(r["format_buffer_class"]["status"],
                         "not_printable_ascii_cstring")

    def test_nonterminated_string_safe_unknown(self):
        r = inspect(text=b"A" * 100)
        self.assertEqual(r["format_buffer_class"]["status"],
                         "no_nul_within_96_bytes")

    def test_floats_strings_and_percent_escape_types_only(self):
        r = inspect(text=b"%% %6.2f %s %p\x00")
        c = r["format_buffer_class"]
        self.assertTrue(c["has_float_conversion"])
        self.assertTrue(c["has_string_conversion"])
        self.assertTrue(c["has_pointer_conversion"])
        self.assertFalse(c["has_integer_conversion"])
        self.assertEqual(c["conversion_count"], 3)

    def test_string_without_format_conversion_not_numeric(self):
        r = inspect(text=b"a static file name\x00")
        self.assertFalse(r["format_buffer_class"]["has_integer_conversion"])
        self.assertFalse(r["format_buffer_class"]["has_float_conversion"])

    def test_source_unsupported_and_wrong_sprintf_rejected(self):
        code = synthetic()
        with self.assertRaises(triage.base.UntrustedInput):
            triage.examine(code, START, "SomeOtherSport.cpp", CALL,
                           lambda addr, size: b"\x00"*size)
        b = bytearray(code)
        b[CALL-START:CALL-START+4] = bl(
            CALL, triage.prior.SPRINTF+4).to_bytes(4, "big")
        with self.assertRaises(triage.base.UntrustedInput):
            triage.examine(bytes(b), START, UNIT, CALL,
                           lambda addr, size: b"\x00"*size)

    def test_report_pinned_fourteen_and_no_private_content(self):
        row = inspect()
        data = triage.summarize([copy.deepcopy(row) for _ in range(14)])
        raw = json.dumps(data)
        self.assertEqual(data["bounded_linear_constant_candidates"], 14)
        self.assertEqual(data["candidate_printf_numeric_type_count"], 14)
        self.assertNotIn("result=%d", raw)
        self.assertNotIn("0x80400130", raw)
        self.assertFalse(data["format_literal_address_or_cfg_proven"])
        self.assertFalse(data["training_approved"])
        with self.assertRaises(triage.base.UntrustedInput):
            triage.summarize([])

    def test_python_isolated_help(self):
        p = Path(triage.__file__).resolve()
        result = subprocess.run([sys.executable, "-I", str(p), "--help"],
                                cwd=p.parents[2], capture_output=True,
                                text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--baseline", result.stdout)


if __name__ == "__main__":
    unittest.main()
