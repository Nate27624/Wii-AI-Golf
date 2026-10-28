"""Fabricated-only PPC tests for bounded sprintf r31/variadic argument syntax."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_sprintf_r31_variadics_private as triage

UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
START = 0x802A79F8
CALL = START + 0x1000


def d_form(op, rt, ra, imm=0):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 65535)


def bl(pc, target, link=True):
    delta = target - pc
    if delta % 4 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("PPC branch fixture offset out of range")
    return (18 << 26) | (delta & 0x03FFFFFC) | int(link)


def fixture(mods=(), call=CALL):
    code = bytearray(b"\x60\x00\x00\x00" * 0x1200)
    rows = {call: bl(call, triage.prior.SPRINTF),
            call - 8: d_form(14, 4, 31, 0x14),
            call - 4: d_form(14, 3, 1, 0x40)}
    rows.update(dict(mods))
    for pc, word in rows.items():
        at = pc - START
        code[at:at+4] = word.to_bytes(4, "big")
    return bytes(code)


def examine(mods=()):
    return triage.bounded_site(fixture(mods), START, UNIT, CALL)


class R31SprintfTriageTests(unittest.TestCase):
    def test_gpr_variadic_r5_from_source_object_is_syntactic(self):
        row = examine(((CALL - 12, d_form(32, 5, 29, 0x30)),))
        self.assertEqual(
            row["r5_r6_r7_post_last_barrier_syntax"]["r5_last_syntactic_def"],
            "integer_load_from_r29")
        self.assertFalse(row["visible_hitting_green_result_verified"])
        self.assertFalse(row["function_entry_or_cfg_reaching_def_verified"])

    def test_const_high_low_r31_pattern_is_candidate_only(self):
        row = examine((
            (CALL - 0x200, d_form(15, 31, 0, 0x804A)),
            (CALL - 0x1FC, d_form(14, 31, 31, 0x3000)),
        ))
        self.assertEqual(row["r31_constant_pair_syntax_only"],
                         "addis_r31_r0_then_addi_r31_r31_candidate")
        self.assertFalse(row["format_string_bytes_or_types_read"])
        self.assertEqual(row["r31_last_recognized_definition_syntax"],
                         "addi_from_r31")

    def test_r31_candidate_with_intervening_branch_is_not_proof(self):
        row = examine((
            (CALL - 0x200, d_form(15, 31, 0, 0x804A)),
            (CALL - 0x1FC, d_form(14, 31, 31, 0x3000)),
            (CALL - 0x100, bl(CALL - 0x100, CALL - 4, False)),
        ))
        self.assertTrue(
            row["control_transfer_after_candidate_r31_definition"])
        self.assertFalse(row["r4_from_r31_verified_reaching_definition"])

    def test_no_r31_def_stays_unknown(self):
        row = examine()
        self.assertEqual(row["r31_last_recognized_definition_syntax"],
                         triage.UNKNOWN)
        self.assertIsNone(row["control_transfer_after_candidate_r31_definition"])

    def test_r31_outside_bounded_window_not_fabricated(self):
        row = examine(((CALL - triage.LOOKBACK - 4,
                       d_form(15, 31, 0, 0x8000)),))
        self.assertEqual(row["r31_last_recognized_definition_syntax"],
                         triage.UNKNOWN)

    def test_last_recognized_r31_write_wins_within_window(self):
        row = examine((
            (CALL - 0x200, d_form(15, 31, 0, 0x8000)),
            (CALL - 0x100, d_form(14, 31, 28, 0x20)),
        ))
        self.assertEqual(row["r31_last_recognized_definition_syntax"],
                         "addi_from_r28")
        self.assertNotEqual(
            row["r31_constant_pair_syntax_only"],
            "addis_r31_r0_then_addi_r31_r31_candidate")

    def test_r5_before_branch_is_not_local_suffix_source(self):
        row = examine((
            (CALL - 24, d_form(14, 5, 29, 0x30)),
            (CALL - 16, bl(CALL-16, CALL-4, False)),
        ))
        self.assertEqual(
            row["r5_r6_r7_post_last_barrier_syntax"]["r5_last_syntactic_def"],
            triage.UNKNOWN)

    def test_r5_after_branch_is_only_local_syntactic_candidate(self):
        row = examine((
            (CALL - 24, d_form(14, 5, 29, 0x30)),
            (CALL - 16, bl(CALL-16, CALL-8, False)),
            (CALL - 12, d_form(14, 5, 28, 0x40)),
        ))
        self.assertEqual(
            row["r5_r6_r7_post_last_barrier_syntax"]["r5_last_syntactic_def"],
            "addi_from_r28")

    def test_r6_and_r7_source_classes_distinct(self):
        row = examine((
            (CALL - 20, d_form(14, 6, 0, 33)),
            (CALL - 12, d_form(32, 7, 30, 0x10)),
        ))
        a = row["r5_r6_r7_post_last_barrier_syntax"]
        self.assertEqual(a["r6_last_syntactic_def"], "addi_from_r0")
        self.assertEqual(a["r7_last_syntactic_def"], "integer_load_from_r30")

    def test_no_nearby_load_not_absence_of_integer_format(self):
        row = examine()
        self.assertEqual(
            row["r5_r6_r7_post_last_barrier_syntax"]["r5_last_syntactic_def"],
            triage.UNKNOWN)
        self.assertFalse(row["format_string_bytes_or_types_read"])

    def test_nonlink_and_wrong_call_target_fail_closed(self):
        for bad_target, link in (
            (triage.prior.SPRINTF, False),
            (triage.prior.SPRINTF + 4, True),
        ):
            code = bytearray(fixture())
            at = CALL - START
            code[at:at+4] = bl(CALL, bad_target, link).to_bytes(4, "big")
            with self.subTest(target=bad_target, link=link):
                with self.assertRaises(triage.base.UntrustedInput):
                    triage.bounded_site(bytes(code), START, UNIT, CALL)

    def test_wrong_unit_and_malformed_code_fail_closed(self):
        with self.assertRaises(triage.base.UntrustedInput):
            triage.bounded_site(fixture(), START, "OtherSports.cpp", CALL)
        with self.assertRaises(triage.base.UntrustedInput):
            triage.bounded_site(fixture() + b"0", START, UNIT, CALL)

    def test_fourteen_sites_report_is_source_only(self):
        row = examine(((CALL - 12, d_form(14, 5, 30, 123)),))
        report = triage.summarize([copy.deepcopy(row) for _ in range(14)])
        self.assertEqual(report["exact_direct_sprintf_call_count"], 14)
        self.assertEqual(report["r5_syntactic_definition_in_suffix_count"], 14)
        self.assertFalse(report["static_format_string_or_units_identified"])
        self.assertFalse(report["ui_result_dataflow_and_backing_memory_verified"])
        self.assertFalse(report["training_approved"])
        raw = json.dumps(report)
        self.assertNotIn("0x9000", raw)
        self.assertNotIn("0x800B75D8", raw)
        self.assertNotIn("PRIVATE.json", raw)

    def test_unexpected_site_count_abstains(self):
        with self.assertRaises(triage.base.UntrustedInput):
            triage.summarize([])
        with self.assertRaises(triage.base.UntrustedInput):
            triage.summarize([examine()])

    def test_cli_help_isolated_without_raw_files(self):
        path = Path(triage.__file__).resolve()
        res = subprocess.run(
            [sys.executable, "-I", str(path), "--help"],
            cwd=path.parents[2], capture_output=True, text=True, timeout=15)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("--baseline", res.stdout)


if __name__ == "__main__":
    unittest.main()
