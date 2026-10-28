"""Synthetic-only tests for published code-unit lookup of two post-return BLs."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_global_store_two_bl_public_units_private as p


def d(op, rt, ra, signed):
    return ((op << 26) | (rt << 21) | (ra << 16) | (signed & 65535))


def bl(pc, dest, link=True):
    diff = dest - pc
    assert diff % 4 == 0 and -(1 << 25) <= diff < (1 << 25)
    return (18 << 26) | (diff & 0x03FFFFFC) | int(link)


def bc(pc, target):
    diff = target - pc
    assert diff % 4 == 0 and -32768 <= diff < 32768
    return (16 << 26) | (12 << 21) | (2 << 16) | (diff & 0xFFFC)


def fixture():
    # +0x305C blr, +3068 li r3,positive, and exact two BLs.
    offset = -18000
    words = {
        p.RETURN: 0x4E800020,
        p.POSITIVE_LITERAL: d(14, 3, 0, 0xF4),
        p.SPLIT_BRANCH: bc(p.SPLIT_BRANCH, p.STORE),
        p.STORE: d(36, 3, 13, offset),
        p.SDA_FIELD_ANCHOR: d(32, 3, 13, p.FIELD_SDA_DISPLACEMENT),
        p.SDA_GLOBAL_LOAD: d(32, 3, 13, offset),
        p.FIRST_BL: bl(p.FIRST_BL, 0x80123400),
        p.SECOND_BL: bl(p.SECOND_BL, 0x802A0100),
    }
    index = (
        (0x80123000, 0x80123800, "Public/Generic/Allocator.o"),
        (0x8029E62C, 0x802A2210, "Pack/RPSports/RPGolScene/RPGolPlayer.o"),
    )
    return words, index


class GlobalTwoBLTests(unittest.TestCase):
    def test_positive_public_unit_lookup_and_honest_limits(self):
        words, index = fixture()
        report = p.classify_source(words.__getitem__, index)
        self.assertEqual(report["exact_bl_count"], 2)
        self.assertEqual([c["public_unit_found"] for c in report["callees"]], [True, True])
        self.assertEqual(
            report["callees"][0]["public_unit_relative_offset"], "+0x00400")
        self.assertEqual(report["callees"][1]["public_unit_relative_offset"], "+0x01AD4")
        self.assertFalse(report["callee_allocator_or_constructor_verified"])
        self.assertFalse(report["returned_r3_reaching_definition_verified"])
        self.assertFalse(report["training_approved"])

    def test_unknown_public_unit_is_not_fabricated(self):
        words, index = fixture()
        report = p.classify_source(words.__getitem__, index[1:])
        self.assertFalse(report["callees"][0]["public_unit_found"])
        self.assertIsNone(report["callees"][0]["public_source_unit"])

    def test_positive_literal_must_be_positive(self):
        for value in (0, -1):
            words, index = fixture()
            words[p.POSITIVE_LITERAL] = d(14, 3, 0, value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.classify_source(words.__getitem__, index)

    def test_prior_blr_exact_required(self):
        words, index = fixture()
        words[p.RETURN] = 0x4E800021
        with self.assertRaises(ValueError):
            p.classify_source(words.__getitem__, index)

    def test_requires_both_exact_bl(self):
        for site in (p.FIRST_BL, p.SECOND_BL):
            words, index = fixture()
            words[site] = bl(site, 0x80123400, False)
            with self.subTest(site=site), self.assertRaises(ValueError):
                p.classify_source(words.__getitem__, index)

    def test_branch_target_exact_store(self):
        words, index = fixture()
        words[p.SPLIT_BRANCH] = bc(p.SPLIT_BRANCH, p.STORE+4)
        with self.assertRaises(ValueError):
            p.classify_source(words.__getitem__, index)

    def test_store_must_match_source_global_sda_displacement(self):
        words, index = fixture()
        words[p.STORE] = d(36, 3, 13, -18004)
        with self.assertRaises(ValueError):
            p.classify_source(words.__getitem__, index)

    def test_global_read_must_be_r3_r13(self):
        words, index = fixture()
        words[p.SDA_GLOBAL_LOAD] = d(32, 4, 13, -18000)
        with self.assertRaises(ValueError):
            p.classify_source(words.__getitem__, index)

    def test_sda_field_anchor_exact(self):
        words, index = fixture()
        words[p.SDA_FIELD_ANCHOR] = d(32, 3, 12, p.FIELD_SDA_DISPLACEMENT)
        with self.assertRaises(ValueError):
            p.classify_source(words.__getitem__, index)

    def test_no_original_ram_or_source_word_leak(self):
        words, index = fixture()
        r = str(p.classify_source(words.__getitem__, index))
        for secret in ("-18000", "-23320", "0x900", "0x4E800020", "checkpoint-manifest", "original-file"):
            self.assertNotIn(secret, r)

    def test_duplicate_public_unit_matches_fail_to_guess(self):
        words, index = fixture()
        overlap = (index[0], (0x80123400, 0x80123500, "Public/Conflict.o"), index[1])
        r = p.classify_source(words.__getitem__, overlap)
        self.assertFalse(r["callees"][0]["public_unit_found"])

    def test_b0_archive_gate_before_code_read(self):
        with patch.object(p.base, "checked_private_b0",
                          side_effect=p.base.UntrustedInput):
            with self.assertRaises(p.base.UntrustedInput):
                p.audit(Path("any"), Path("Wii-AI-Golf-Data"))

    def test_cli_help_python_isolated(self):
        import subprocess
        script = Path(p.__file__)
        result = subprocess.run([sys.executable, "-I", str(script), "--help"],
                                capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--baseline", result.stdout)


if __name__ == "__main__":
    unittest.main()
