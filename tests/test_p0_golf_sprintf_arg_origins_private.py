"""Fabricated PPC tests for 14 exact Golf sprintf site argument syntax."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_sprintf_arg_origins_private as target

START = 0x802A79F8
UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
SITE = START + 0x100


def d(op, rt, ra, imm=0):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 0xffff)


def branch(pc, dst, link=True):
    delta = dst - pc
    if delta % 4 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("out of range branch fixture")
    return (18 << 26) | (delta & 0x03fffffc) | int(link)


def fixture(writes=(), site=SITE):
    words = {site: branch(site, target.SPRINTF)}
    words.update(dict(writes))
    out = bytearray(b"\x60\x00\x00\x00" * 160)
    for pc, word in words.items():
        at = pc - START
        out[at:at+4] = word.to_bytes(4, "big")
    return bytes(out)


def inspect(writes=(), site=SITE):
    return target.local_sprintf_syntax(
        fixture(writes, site), START, UNIT, site)


class SprintfArgTests(unittest.TestCase):
    def test_detect_r3_buffer_r4_format_and_fpr_load(self):
        result = inspect((
            (SITE-12, d(14, 3, 1, 0x40)),
            (SITE-8, d(14, 4, 31, 0x44)),
            (SITE-4, d(48, 1, 30, 0x10)),
        ))
        self.assertEqual(result["output_buffer_r3_last_syntactic_definition"],
                         "addi_from_r1")
        self.assertEqual(result["format_pointer_r4_last_syntactic_definition"],
                         "addi_from_r31")
        self.assertEqual(result["fpr_load_class_count"], 1)
        self.assertTrue(result["nearby_fpr_activity_possible_numeric_format_lead"])
        self.assertFalse(result["format_string_literal_or_specifiers_decoded"])

    def test_branch_barrier_refuses_prebranch_nearest_def(self):
        result = inspect((
            (SITE-16, d(14, 4, 31, 4)),
            (SITE-12, branch(SITE-12, SITE-4, False)),
            (SITE-8, d(14, 3, 1, 0x50)),
        ))
        self.assertTrue(result["control_barrier_seen_before_call"])
        self.assertEqual(result["format_pointer_r4_last_syntactic_definition"],
                         "not_recognized_in_bounded_straightline_suffix")
        self.assertEqual(result["output_buffer_r3_last_syntactic_definition"],
                         "addi_from_r1")

    def test_nearby_other_bl_is_clobber_barrier(self):
        result = inspect((
            (SITE-12, d(15, 4, 0, 0x8000)),
            (SITE-8, branch(SITE-8, 0x8029CCBC, True)),
        ))
        self.assertTrue(result["control_barrier_seen_before_call"])
        self.assertEqual(result["format_pointer_r4_last_syntactic_definition"],
                         "not_recognized_in_bounded_straightline_suffix")

    def test_a_nonlink_branch_is_not_sprintf(self):
        data = bytearray(fixture())
        at = SITE - START
        data[at:at+4] = branch(SITE, target.SPRINTF, False).to_bytes(4,"big")
        with self.assertRaises(target.base.UntrustedInput):
            target.local_sprintf_syntax(bytes(data), START, UNIT, SITE)

    def test_exact_call_required(self):
        data = bytearray(fixture())
        at = SITE - START
        data[at:at+4] = branch(SITE, target.SPRINTF+4).to_bytes(4,"big")
        with self.assertRaises(target.base.UntrustedInput):
            target.local_sprintf_syntax(bytes(data), START, UNIT, SITE)

    def test_other_source_unit_refused(self):
        with self.assertRaises(target.base.UntrustedInput):
            target.local_sprintf_syntax(fixture(), START,
                                        "Pack/RPSports/RPBoxScene/Box.cpp", SITE)

    def test_unaligned_bytes_refused(self):
        with self.assertRaises(target.base.UntrustedInput):
            target.local_sprintf_syntax(fixture()+b"\x00", START, UNIT, SITE)

    def test_last_syntax_in_bounded_window_not_prior_code(self):
        result=inspect(((SITE-0x84,d(14,4,31,4)),))
        self.assertEqual(result["format_pointer_r4_last_syntactic_definition"],
                         "not_recognized_in_bounded_straightline_suffix")
        self.assertEqual(result["source_window_bytes_examined"], target.WINDOW)

    def test_fp_store_is_not_numeric_argument_proof(self):
        result=inspect(((SITE-4, d(52,1,31,0x10)),))
        self.assertEqual(result["fpr_store_class_count"], 1)
        self.assertFalse(result["nearby_fpr_activity_possible_numeric_format_lead"])

    def test_no_results_cannot_claim_display_producer(self):
        with self.assertRaises(target.base.UntrustedInput):
            target.summarize([])

    def test_private_syntax_is_bounded_and_semantics_remain_false(self):
        data = [inspect(((SITE-4,d(48,1,31,0)),))]
        report = target.summarize(data)
        raw=json.dumps(report)
        self.assertEqual(report["exact_sprintf_direct_bl_sites"], 1)
        self.assertNotIn("800b75d8",raw.lower())
        self.assertNotIn("0x9000",raw.lower())
        self.assertFalse(report["result_distance_memory_state_verified"])
        self.assertFalse(report["training_approved"])
        self.assertFalse(report["displayed_result_producer_verified"])

    def test_python_isolated_help_no_memory(self):
        script=Path(target.__file__).resolve()
        r=subprocess.run([sys.executable,"-I",str(script),"--help"],
                         cwd=script.parents[2],capture_output=True,
                         text=True,timeout=12)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("--baseline",r.stdout)


if __name__=="__main__":
    unittest.main()
