"""Fabricated-only tests for 18-site P0 PSPVEC distance f1 and r3/r4 syntax."""
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_vec_f1_return_private as f1
import audit_p0_golf_vec_arguments_private as args

START = 0x802A79F8
CALL = START + 0x100
UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
NOP = 0x60000000


def d(op, rt, ra, imm=0):
    return ((op << 26) | (rt << 21) | (ra << 16) | (imm & 65535))


def bl(pc, dst, linked=True):
    delta = dst - pc
    assert -(1 << 25) <= delta < (1 << 25) and delta % 4 == 0
    return (18 << 26) | (delta & 0x03FFFFFC) | int(linked)


def fixture(words=()):
    data = bytearray(NOP.to_bytes(4, "big") * 400)
    layout = {CALL: bl(CALL, f1.DISTANCE)}
    layout.update(dict(words))
    for pc, insn in layout.items():
        at = pc - START
        data[at:at+4] = insn.to_bytes(4, "big")
    return bytes(data)


def f(words=()):
    return f1.inspect_f1(fixture(words), START, UNIT, CALL)


def a(words=()):
    return args.inspect_args(fixture(words), START, UNIT, CALL)


class VectorDistanceP0Tests(unittest.TestCase):
    def test_f1_stfs_source_store_detected(self):
        x = f(((CALL+4, d(52, 1, 28, 0x18)),))
        self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                         "F1_STFS_SOURCE_STORE_SYNTAX")
        self.assertTrue(x["first_event_is_direct_F1_store_syntax"])
        self.assertFalse(x["F1_matches_dynamic_PSVEC_return_verified"])

    def test_f1_stfd_and_update_source_store(self):
        for op, name in ((53, "F1_STFS_SOURCE_STORE_SYNTAX"),
                         (54, "F1_STFD_SOURCE_STORE_SYNTAX"),
                         (55, "F1_STFD_SOURCE_STORE_SYNTAX")):
            with self.subTest(op=op):
                x = f(((CALL+4, d(op, 1, 27, 0)),))
                self.assertEqual(x["first_post_BL_F1_relevant_event_class"], name)

    def test_different_fpr_store_not_false_result(self):
        x = f(((CALL+4, d(52, 2, 28, 0)),))
        self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                         "NO_RECOGNIZED_F1_CONSUMER_IN_BOUNDED_SUFFIX")

    def test_f1_overwrite_hides_later_store(self):
        x = f(((CALL+4, d(48, 1, 28, 0)),
               (CALL+8, d(52, 1, 27, 0))))
        self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                         "F1_OVERWRITTEN_BY_FPR_LOAD_BEFORE_LOCAL_STORE")
        self.assertFalse(x["first_event_is_direct_F1_store_syntax"])

    def test_call_barrier_prevents_false_store(self):
        x = f(((CALL+4, bl(CALL+4, 0x8029CCBC)),
               (CALL+8, d(52, 1, 27, 0))))
        self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                         "ABSTAIN_CONTROL_FLOW_BEFORE_F1_STORE")

    def test_return_and_branch_barriers_prevent_false_store(self):
        for word in (0x4E800020, bl(CALL+4, CALL+20, False)):
            with self.subTest(word=word):
                x = f(((CALL+4, word), (CALL+8, d(52, 1, 27, 0))))
                self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                                 "ABSTAIN_CONTROL_FLOW_BEFORE_F1_STORE")

    def test_floating_arithmetic_abstain(self):
        x = f(((CALL+4, 59 << 26),))
        self.assertEqual(x["first_post_BL_F1_relevant_event_class"],
                         "FPR_ARITHMETIC_OR_MOVE_UNRESOLVED")

    def test_args_r3_and_r4_source_syntax(self):
        row = a(((CALL-12, d(14, 3, 31, 0x20)),
                 (CALL-8, d(32, 4, 27, 0x34))))
        self.assertEqual(row["r3_nearest_local_source"], "ADDI_FROM_r31")
        self.assertEqual(row["r4_nearest_local_source"], "LOAD_GPR_FROM_BASE_r27")
        self.assertFalse(row["ball_pin_argument_or_distance_role_verified"])

    def test_arg_branch_barrier_refuses_prebranch_source(self):
        row = a(((CALL-12, d(14, 3, 31, 0x20)),
                 (CALL-8, bl(CALL-8, CALL, False)),
                 (CALL-4, d(14, 4, 29, 4))))
        self.assertEqual(row["r3_nearest_local_source"], args.UNKNOWN)
        self.assertEqual(row["r4_nearest_local_source"], "ADDI_FROM_r29")
        self.assertTrue(row["control_barrier_in_backward_window"])

    def test_arg_rA_logical_and_lmw_clobber_old_definition(self):
        for word, expected in ((d(26, 29, 3, 0),
                                "ROTATE_LOGICAL_rA_DEST_UNRESOLVED"),
                               (d(46, 2, 10, 0),
                                "LMW_RANGE_OVERWRITES_GPR"),
                               (d(37, 29, 3, 0),
                                "MEMORY_UPDATE_BASE_WRITE")):
            with self.subTest(expected=expected):
                row = a(((CALL-12, d(14, 3, 31, 0)),
                         (CALL-4, word)))
                self.assertEqual(row["r3_nearest_local_source"], expected)

    def test_arg_mr_and_nonupdate_store_no_clobber(self):
        mr = (31 << 26) | (28 << 21) | (4 << 16) | (28 << 11) | (444 << 1)
        row = a(((CALL-16, d(14, 3, 31, 0)),
                 (CALL-12, mr),
                 (CALL-4, d(36, 3, 4, 0))))
        self.assertEqual(row["r4_nearest_local_source"], "MR_FROM_r28")
        self.assertEqual(row["r3_nearest_local_source"], "ADDI_FROM_r31")

    def test_unsigned_addi_zero_base_literal(self):
        row = a(((CALL-4, d(14, 3, 0, 0x1234)),))
        self.assertEqual(row["r3_nearest_local_source"],
                         "ADD_IMMEDIATE_LITERAL_ZERO_BASE")

    def test_wrong_source_call_rejected_both(self):
        wrong = fixture(((CALL, bl(CALL, f1.DISTANCE+4)),))
        for func in (f1.inspect_f1, args.inspect_args):
            with self.subTest(func=func.__name__), self.assertRaises(ValueError):
                func(wrong, START, UNIT, CALL)

    def test_no_false_name_on_bad_unit_or_unaligned_code(self):
        for fun in (f1.inspect_f1, args.inspect_args):
            with self.subTest(fun=fun.__name__):
                with self.assertRaises(ValueError):
                    fun(fixture(), START, "OtherSports/other.o", CALL)
                with self.assertRaises(ValueError):
                    fun(fixture()+b"x", START, UNIT, CALL)

    def test_report_count_and_semantics_are_fail_closed(self):
        x, y = f(), a()
        for report, row, func in (
            ("f1", x, f1.summarize), ("args", y, args.summarize)):
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    func([row])
                r = func([row.copy() for _ in range(18)])
                self.assertEqual(r["exact_source_direct_distance_BL_count"], 18)
                self.assertFalse(r["training_approved"])
                self.assertFalse(r["allowed_to_publish"])
                self.assertFalse(r["UI_result_producer_or_backing_memory_verified"])
                dumped = json.dumps(r)
                self.assertNotIn("0x9000", dumped)
                self.assertNotIn("B0-MEM1.bin", dumped)

    def test_canonical_b0_gate_before_any_source_read(self):
        with patch.object(f1.base, "checked_private_b0",
                          side_effect=f1.base.UntrustedInput):
            for function in (f1.audit, args.audit):
                with self.subTest(function=function.__name__):
                    with self.assertRaises(f1.base.UntrustedInput):
                        function(Path("unused"), Path("Wii-AI-Golf-Data"))

    def test_two_isolated_py_cli_help(self):
        for script in (f1.__file__, args.__file__):
            with self.subTest(script=script):
                r = subprocess.run([sys.executable, "-I", script, "--help"],
                                   capture_output=True, text=True, timeout=15)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("--baseline", r.stdout)


if __name__ == "__main__":
    unittest.main()
