"""Fabricated PPC source only; no native memory or Dolphin in CI."""
from __future__ import annotations
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_r31_store_slice_private as s


def w(op, rt, ra, d):
    return (op << 26) | (rt << 21) | (ra << 16) | (d & 0xFFFF)


def blob(altered=False):
    words = [0x60000000] * 8
    words[1] = w(32, 31, 3, 0x88)
    words[2] = 18 << 26
    words[4] = ((31 << 26) | (3 << 21) | (31 << 16) |
                (3 << 11) | (444 << 1))
    words[7] = w(52, 2, 30 if altered else 31, 0x90)
    return b"".join(struct.pack(">I", x) for x in words)


class Tests(unittest.TestCase):
    def test_source_slice_counts_but_no_owner_claim(self):
        out = s.scan_slice(blob(), 0x80001000, 0x8000101C, 0x80001000)
        self.assertEqual(out["source_relative_store_site"], "+0x001C")
        self.assertEqual(out["store_float_reg"], "f2")
        self.assertEqual(out["control_flow_hazard_count"], 1)
        self.assertEqual(out["nearest_hazard_or_definition"]["class"],
                         "register_copy_mr")
        self.assertFalse(out["r31_is_selected_player_record_verified"])
        self.assertFalse(out["approved_for_training"])

    def test_unexpected_receiver_abstains(self):
        with self.assertRaises(ValueError):
            s.scan_slice(blob(True), 0x80001000, 0x8000101C, 0x80001000)

    def test_branch_hazard_not_treated_as_dominator(self):
        out = s.scan_slice(blob(), 0x80001000, 0x8000101C, 0x80001000)
        self.assertFalse(out["branch_aware_cfg_dominance_verified"])
        self.assertTrue(any(x["class"] == "control_flow_hazard" for x
                            in out["event_sites_nearest_first"]))

    def test_bad_bounds_refuses(self):
        cases = [(blob()[:-1], 0x80001000, 0x8000101C, 0x80001000),
                 (blob(), 0x80001004, 0x8000101C, 0x80001000),
                 (blob(), 0x80001000, 0x8000101C, 0x80001004)]
        for b, start, site, unit in cases:
            with self.assertRaises(ValueError):
                s.scan_slice(b, start, site, unit)

    def test_float_store_cannot_be_gpr_definition(self):
        self.assertIsNone(s.decode_word(w(52, 31, 31, 0x90)))

    def test_unknown_opcode_is_hazard(self):
        self.assertEqual(s.decode_word(2 << 26)["class"],
                         "unclassified_opcode_hazard")

    def test_output_suppresses_raw_words_and_private_pointers(self):
        raw = json.dumps(s.scan_slice(blob(), 0x80001000,
                                      0x8000101C, 0x80001000))
        self.assertNotIn("0x80001000", raw)
        self.assertNotIn("0x60000000", raw)
        self.assertNotIn("private-session", raw)

    def test_cli_failure_redacted(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status = s.main(["--data-root", "/missing",
                             "--private-session", "SECRET_PATH"])
        self.assertEqual(status, 2)
        self.assertNotIn("SECRET_PATH", err.getvalue())


if __name__ == "__main__":
    unittest.main()
