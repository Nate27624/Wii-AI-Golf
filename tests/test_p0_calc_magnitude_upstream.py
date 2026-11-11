"""Offline synthetic tests: do not open original game archives or Dolphin."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_calc_magnitude_upstream_private.py"
spec = importlib.util.spec_from_file_location("p0_calc_magnitude_upstream_private", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def dform(op, rt, ra, disp):
    return ((op << 26) | (rt << 21) | (ra << 16) | (disp & 0xFFFF))


def mr(dest, src):
    return (31 << 26 | src << 21 | dest << 16 |
            src << 11 | 444 << 1)


def bl(pc, target):
    diff = target - pc
    if diff % 4 or not -(1 << 25) <= diff < (1 << 25):
        raise ValueError("not representable")
    return 18 << 26 | (diff & 0x03FFFFFC) | 1


def fixture():
    words = {}
    for pc in range(*m.EXCERPT, 4):
        words[pc] = dform(14, 1, 1, 0)
    for pc, (freg, base, disp) in m.STFS_GATES.items():
        words[pc] = dform(52, freg, base, disp)
    for pc, (freg, base, disp) in m.LFS_GATES.items():
        words[pc] = dform(48, freg, base, disp)
    for pc, (reg, base, disp) in m.STW_GATES.items():
        words[pc] = dform(36, reg, base, disp)
    for pc, dest in m.CALL_GATES.items():
        words[pc] = bl(pc, dest)
    for pc, (dest, src) in m.MR_GATES.items():
        words[pc] = mr(dest, src)
    # Known candidate intermediate r24-relative stores (synthetic payload).
    words[0x802B482C] = dform(52, 1, 24, 0x18)
    words[0x802B4840] = dform(52, 2, 24, 0x1C)
    words[0x802B4880] = dform(52, 3, 24, 0x28)
    words[0x802B4894] = dform(52, 4, 24, 0x2C)
    words[0x802B4900] = (
        (63 << 26) | (30 << 21) | (28 << 16) |
        (29 << 11) | (27 << 6) | (29 << 1)
    )
    return words


class Tests(unittest.TestCase):
    def test_exact_peak_latch_and_static_call_gates(self):
        words = fixture()
        result = m.verify_static_gates(words.__getitem__)
        self.assertEqual(result["calc_peak_writer_at"], "0x802B4924")
        self.assertEqual(result["calc_state3_latch_writer_at"], "0x802B31C4")
        self.assertTrue(result["two_direct_bl_edges_exact"])
        self.assertTrue(result["four_explicit_mr_receiver_copies_exact"])
        self.assertEqual(m._branch(0x802B4938, words[0x802B4938])["dest"],
                         0x802B3BA0)

    def test_rejects_wrong_object_register_or_peak_source(self):
        for pc in m.STFS_GATES:
            words = fixture()
            words[pc] = dform(52, 31, 24, 0x0C)
            with self.assertRaisesRegex(m.Abstain, "gate_failed"):
                m.verify_static_gates(words.__getitem__)

    def test_rejects_changed_call_target_and_nonlink(self):
        for pc in m.CALL_GATES:
            words = fixture()
            words[pc] = bl(pc, m.CALL_GATES[pc] + 4)
            with self.assertRaisesRegex(m.Abstain, "calc_call_chain"):
                m.verify_static_gates(words.__getitem__)
            words[pc] = bl(pc, m.CALL_GATES[pc]) & ~1
            with self.assertRaisesRegex(m.Abstain, "calc_call_chain"):
                m.verify_static_gates(words.__getitem__)

    def test_calc_receiver_four_mr_hops_are_exact(self):
        for pc, (dest, source) in m.MR_GATES.items():
            words = fixture()
            self.assertTrue(m._mr_matches(words[pc], dest, source))
            words[pc] = mr(dest, (source + 1) % 32)
            with self.assertRaisesRegex(m.Abstain, "receiver_identity_chain"):
                m.verify_static_gates(words.__getitem__)

    def test_rejects_uncorroborated_latch_state(self):
        words = fixture()
        words[0x802B31C0] = dform(36, 0, 27, 0x18C)
        with self.assertRaisesRegex(m.Abstain, "calc_state_gate"):
            m.verify_static_gates(words.__getitem__)

    def test_symbolic_fp_producer_and_source_owner(self):
        words = fixture()
        line = m.symbolize(0x802B4900, words[0x802B4900])
        self.assertEqual(line["class"], "fp_opcode63")
        self.assertEqual((line["fd"], line["fa"], line["fb"], line["fc"]),
                         (30, 28, 29, 27))
        with self.assertRaisesRegex(m.Abstain, "source_window"):
            m.symbolize(0x80000100, 0)
        self.assertEqual(m.symbolize(0x802B4924, words[0x802B4924])["class"],
                         "stfs")

    def test_bounded_producer_excerpt_and_store_inventory(self):
        report = m.source_slice(fixture().__getitem__)
        self.assertEqual(report["status"], "REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS")
        self.assertFalse(report["calc_0x0C_accepted_power_verified"])
        self.assertFalse(report["game_input_consumption_verified"])
        self.assertEqual(
            {row["field"] for row in report["r24_candidate_calculation_stores"]},
            {"+0x18", "+0x1C", "+0x28", "+0x2C", "+0x8", "+0xC"})
        self.assertEqual(report["public_unit"], m.PUBLIC_OWNER)
        self.assertGreater(len(report["fp_reaching_definitions_source_excerpt"]), 20)
        serialized = json.dumps(report)
        self.assertNotIn("0x91BF", serialized)
        self.assertNotIn("PRIVATE-SHA", serialized)
        self.assertNotIn("0xFC", serialized)
        self.assertNotIn('"word"', serialized)
        self.assertFalse(report["training_approved"])

    def test_wrong_bank_or_unaligned_source_address_abstains(self):
        fake = bytes(64)
        with self.assertRaisesRegex(m.Abstain, "source_window"):
            m._word(fake, 0x802B4915)
        with self.assertRaisesRegex(m.Abstain, "source_word_unmapped"):
            m._word(fake, 0x802B4914)

    def test_archive_auto_discovery_requires_one_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "Wii-AI-Golf-Data"
            captures = root / "captures"
            captures.mkdir(parents=True)
            with self.assertRaisesRegex(m.Abstain, "expected_one"):
                m._default_archive(root)
            for name in ("a","b"):
                p = captures / name
                p.mkdir()
                (p / "manifest-PRIVATE.json").write_text(
                    json.dumps({"kind":"p0-private-numbered-capture-inventory",
                                "capture_count":7}), encoding="utf-8")
                if name == "a":
                    self.assertEqual(m._default_archive(root),p)
                else:
                    with self.assertRaisesRegex(m.Abstain, "expected_one"):
                        m._default_archive(root)

    def test_main_without_archive_fails_closed_and_never_calls_controller(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m, "DATA", Path(d)), \
                 patch.object(m, "run", side_effect=AssertionError(
                     "must not open original archive on missing root")):
                self.assertEqual(m.main([]), 2)


if __name__ == "__main__":
    unittest.main()
