"""Native-free P0 Golf result/label source xref tests; fabricated PPC only."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_result_ui_xrefs_private as target

UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
START = 0x802A79F8


def ppc_branch(pc, to, link=True):
    # PPC major opcode 18, relative 26-bit signed displacement, word-aligned.
    offset = to - pc
    if offset % 4 or not -(1 << 25) <= offset < (1 << 25):
        raise ValueError("invalid synthetic branch displacement")
    return ((18 << 26) | (offset & 0x03FFFFFC) | int(link)).to_bytes(4, "big")


def window(links):
    words = [b"\x60\x00\x00\x00"] * 192
    for index, dest, link in links:
        words[index] = ppc_branch(START + 4 * index, dest, link)
    return [(UNIT, START, b"".join(words))]


class P0UIXrefTests(unittest.TestCase):
    def test_public_golf_units_selected_not_other_sports(self):
        rows = (
            (0x8028DF74, 0x8028E098,
             "Pack/RPSports/RPGolScene/RPGolScene.cpp"),
            (START, START + 0x300, UNIT),
            (0x8024E334, 0x8028DF74,
             "Pack/RPSports/RPBsbScene/RPBsbScene_unsplit.o"),
        )
        chosen = target.golf_units(rows)
        self.assertEqual(len(chosen), 2)
        self.assertEqual(chosen[1][2], UNIT)

    def test_direct_bl_exact_public_sink_and_score(self):
        w = window([
            (0, 0x8007C00C, True),
            (1, 0x8029CCBC, True),
            (2, 0x800B75D8, True),
        ])
        rows = target.classify_calls(w)
        self.assertEqual(len(rows), 3)
        report = target.summarize(rows, 1, 192)
        self.assertEqual(next(x for x in report["callees"]
                              if x["public_symbol"] == "lyt_text_set_utf8_a")
                         ["direct_bl_count"], 1)
        self.assertTrue(report["source_windows_for_followup"][0]
                        ["text_and_other_category_cooccur"])
        self.assertFalse(report["known_display_result_producer_identified"])
        self.assertFalse(report["training_approved"])

    def test_nonlink_tail_branch_not_miscounted_as_bl(self):
        rows = target.classify_calls(window([(0, 0x8007C00C, False)]))
        report = target.summarize(rows, 1, 192)
        r = next(x for x in report["callees"] if x["public_symbol"]
                 == "lyt_text_set_utf8_a")
        self.assertEqual(r["direct_bl_count"], 0)
        self.assertEqual(r["direct_nonlink_b_count"], 1)
        self.assertEqual(report["source_windows_for_followup"], [])

    def test_indirect_calls_explicitly_unresolved(self):
        # bctrl is opcode19; cannot be promoted to direct text sink.
        data = (0x4E800421).to_bytes(4, "big")
        self.assertEqual(target.classify_calls([(UNIT, START, data)]), [])
        report = target.summarize([], 1, 1)
        self.assertTrue(
            report["indirect_virtual_layout_and_custom_number_formatting_unresolved"]
        )

    def test_wrong_source_family_refused(self):
        with self.assertRaises(target.base.UntrustedInput):
            target.classify_calls([("Pack/RPBox/RPBox.cpp", START, b"\x00" * 4)])

    def test_unaligned_code_refused(self):
        with self.assertRaises(target.base.UntrustedInput):
            target.classify_calls([(UNIT, START, b"\x00" * 5)])

    def test_direct_call_to_function_interior_not_reported_as_exact_symbol(self):
        # No speculative fuzzy match to SetString+4 or score func+4.
        rows = target.classify_calls(window([(0, 0x8007C010, True),
                                             (1, 0x8029CCC0, True)]))
        self.assertEqual(rows, [])

    def test_positive_and_no_hit_outputs_do_not_emit_native_bytes(self):
        rows = target.classify_calls(window([(0, 0x800B7500, True)]))
        report = target.summarize(rows, 1, 192)
        data = json.dumps(report)
        self.assertNotIn("60000000", data)
        self.assertNotIn("private_hash", data)
        self.assertNotIn("D:\\", data)
        self.assertFalse(report["read_side_backing_memory_identified"])
        self.assertFalse(report["live_ui_value_read_or_verified"])

    def test_output_bounded_sites(self):
        rows = target.classify_calls(window(
            [(i, 0x8007C074, True) for i in range(80)]
        ))
        report = target.summarize(rows, 1, 192)
        r = next(x for x in report["callees"]
                 if x["public_symbol"] == "lyt_text_set_utf8_b")
        self.assertEqual(len(r["source_sites"]), target.MAX_DISPLAY_SITES)
        self.assertEqual(r["omitted_bl_sites"], 60)

    def test_isolated_help_without_data(self):
        cmd = [sys.executable, "-I", str(Path(target.__file__)), "--help"]
        p = subprocess.run(cmd, cwd=Path(target.__file__).resolve().parents[2],
                           capture_output=True, text=True, timeout=12)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--baseline", p.stdout)


if __name__ == "__main__":
    unittest.main()
