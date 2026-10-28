"""Synthetic PPC tests for Golf direct RPSysLytTextBox text wrapper paths."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_layout_text_wrapper_xrefs_private as ui

UNIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
PC = 0x802A79F8

def branch(pc, dst, linked=True):
    delta = dst - pc
    if delta & 3 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("bad fixture offset")
    return (18 << 26) | (delta & 0x03FFFFFC) | int(linked)

def memory(sites):
    words = [0x60000000]*512
    for offset, dst, linked in sites:
        words[offset//4] = branch(PC+offset, dst, linked)
    return [(UNIT, PC, b"".join(x.to_bytes(4, "big") for x in words))]

class UIPPCXrefTests(unittest.TestCase):
    def test_public_formatted_message_and_text_calls(self):
        rows = ui.source_calls(memory((
            (0x04, 0x80198FD0, True),
            (0x08, 0x80199148, True),
            (0x0C, 0x8019931C, True),
        )))
        self.assertEqual(len(rows), 3)
        out = ui.summarise(rows, 25)
        self.assertEqual(sum(x["direct_bl_count"]
                             for x in out["public_ui_methods"]), 3)
        self.assertFalse(out["hitting_green_ui_producer_verified"])

    def test_pane_find_and_format_same_source_window_is_only_candidate(self):
        rows = ui.source_calls(memory((
            (0x20, 0x80196280, True),
            (0x40, 0x8019931C, True),
        )))
        out = ui.summarise(rows, 25)
        self.assertTrue(out["candidate_source_windows"][0]
                        ["find_textbox_and_formatted_text_in_same_window"])
        self.assertTrue(out["candidate_source_windows"][0]
                        ["source_window_cooccurrence_not_callgraph_or_value_proof"])
        self.assertFalse(out["typed_backing_memory_field_verified"])

    def test_pane_and_format_far_apart_no_false_joint_window(self):
        rows = ui.source_calls(memory((
            (0x00, 0x80196280, True),
            (0x600, 0x8019931C, True),
        )))
        out = ui.summarise(rows, 25)
        self.assertFalse(any(x["find_textbox_and_formatted_text_in_same_window"]
                             for x in out["candidate_source_windows"]))

    def test_layout_create_exact(self):
        rows = ui.source_calls(memory(((0x40, 0x80196A38, True),)))
        out = ui.summarise(rows, 25)
        item = next(x for x in out["public_ui_methods"]
                    if x["public_ui_method"] == "layout_create")
        self.assertEqual(item["direct_bl_count"], 1)

    def test_dont_fuzzy_match_unknown_setmessage_overload(self):
        # Public header ambiguously places two functions at 0x80198e24;
        # intentionally do not claim either overload.
        self.assertEqual(
            ui.source_calls(memory(((0x40, 0x80198E24, True),))), [])

    def test_no_generic_sprintf_is_treated_as_wrapper(self):
        self.assertEqual(
            ui.source_calls(memory(((0x40, 0x800B75D8, True),))), [])

    def test_nonlink_branch_is_not_direct_call(self):
        rows = ui.source_calls(memory(((0x40, 0x80199148, False),)))
        out = ui.summarise(rows, 25)
        method = next(x for x in out["public_ui_methods"]
                      if x["public_ui_method"] == "textbox_set_message_variadic")
        self.assertEqual(method["direct_bl_count"], 0)
        self.assertEqual(method["nonlink_b_count"], 1)

    def test_indirect_call_unresolved(self):
        data = (0x4E800421).to_bytes(4, "big")
        rows = ui.source_calls([(UNIT, PC, data)])
        self.assertEqual(rows, [])
        self.assertTrue(ui.summarise(rows, 25)["indirect_virtual_calls_unresolved"])

    def test_wrong_sport_rejected(self):
        with self.assertRaises(ui.base.UntrustedInput):
            ui.source_calls([("Pack/RPSports/RPBoxScene/foo.o", PC, b"\x00"*4)])

    def test_unaligned_bytes_rejected(self):
        with self.assertRaises(ui.base.UntrustedInput):
            ui.source_calls([(UNIT, PC, b"\x00"*5)])

    def test_no_match_is_not_absence_of_visible_ui(self):
        out = ui.summarise([], 25)
        self.assertFalse(out["hitting_green_ui_producer_verified"])
        self.assertEqual(sum(x["direct_bl_count"]
                             for x in out["public_ui_methods"]), 0)

    def test_output_offsets_bounded_and_no_raw_private_values(self):
        rows = ui.source_calls(memory(
            tuple((i*4, 0x8019931C, True) for i in range(40))))
        out = ui.summarise(rows, 25)
        entry = next(x for x in out["public_ui_methods"]
                     if x["public_ui_method"] == "textbox_set_text_variadic")
        self.assertEqual(entry["direct_bl_count"], 40)
        self.assertEqual(len(entry["published_golf_source_relative_call_sites"]), 32)
        self.assertEqual(entry["omitted_bl_sites"], 8)
        raw = json.dumps(out)
        self.assertNotIn("0x8019931C", raw)
        self.assertNotIn("0x804", raw)
        self.assertNotIn("B0-MEM1", raw)
        self.assertFalse(out["training_approved"])
        self.assertFalse(out["allowed_to_publish"])

    def test_isolated_help_without_user_banks(self):
        script = Path(ui.__file__).resolve()
        p = subprocess.run(
            [sys.executable, "-I", str(script), "--help"],
            cwd=script.parents[2], capture_output=True, text=True,
            timeout=12)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--baseline", p.stdout)

if __name__ == "__main__":
    unittest.main()
