"""Fabricated-only, no native RAM, first-intervening-BL target tests."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_cache_cfg_first_intervening_bl_private as m

ENTRY = m.adapter.EXPECTED_CALLERS
SITES = (ENTRY[0][1] + 0x1c, ENTRY[1][1] + 0x20)
TARGETS = (0x800A3244, 0x8029AB78)
PUBLIC = (
    (0x800A3000, 0x800A3400, "egg/core/eggHeap.cpp"),
    (0x80296FD8, 0x8029B240,
     "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"),
)


def bl(pc, target):
    offset = target - pc
    assert offset % 4 == 0 and -(1 << 25) <= offset < (1 << 25)
    return (18 << 26) | (offset & 0x03FFFFFC) | 1


def fixture():
    return {
        "kind": "P0-SOURCE-AUTHENTICATED-ORIGINAL-B0-CACHE-CFG-ADAPTER",
        "original_B0_SHA_and_manifest_verified_before_after": True,
        "public_Golf_source_window_gated": True,
        "reviewed_pure_CFG_helper_commit_verified": True,
        "runtime_cache_receiver_or_executed_writer_verified": False,
        "training_approved": False,
        "source_only_two_callers": [
            {
                "public_caller": name,
                "conservative_static_cfg_status": "ABSTAIN_SOURCE_UNRESOLVED",
                "first_abstain_reason_class": "INTERVENING_CALL",
                "first_source_relative_unresolved_offset":
                    f"+0x{site-entry:04X}",
                "all_reaching_paths_preserve_entry_receiver": False,
                "exact_cache_writer_callsite_reached": False,
            }
            for (name, entry, _call), site in zip(ENTRY, SITES)
        ],
    }


def reader(words=None):
    if words is None:
        words = {site: bl(site, target)
                 for site, target in zip(SITES, TARGETS)}
    def read(pc):
        return words[pc]
    return read


class FirstCallTests(unittest.TestCase):
    def test_two_exact_direct_source_callees(self):
        r = m.classify(fixture(), reader(), PUBLIC)
        self.assertEqual(r["static_intervening_caller_count"], 2)
        rows = r["callsite_results"]
        self.assertEqual([x["source_opcode_class"] for x in rows],
                         ["DIRECT_BL_TARGET_IN_PUBLIC_SOURCE_UNIT"] * 2)
        self.assertEqual([x["public_direct_callee_object_file"] for x in rows],
                         ["egg/core/eggHeap.cpp",
                          "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"])
        self.assertEqual([x["public_callee_object_file_relative_offset"]
                          for x in rows], ["+0x0244", "+0x3BA0"])
        self.assertFalse(r["cache_writer_reachability_or_runtime_receiver_verified"])
        self.assertFalse(r["training_approved"])

    def test_wrong_opcode_not_a_call_refused(self):
        for word in (0, 0x60000000, (18 << 26), 0x4E800020):
            d = {a: bl(a, b) for a, b in zip(SITES, TARGETS)}
            d[SITES[0]] = word
            with self.subTest(word=word), self.assertRaises(m.SourceFailure):
                m.classify(fixture(), reader(d), PUBLIC)

    def test_conditional_link_is_not_guessed_as_direct_bl(self):
        d = {a: bl(a, b) for a, b in zip(SITES, TARGETS)}
        d[SITES[0]] = (16 << 26) | 1
        r = m.classify(fixture(), reader(d), PUBLIC)
        self.assertEqual(r["callsite_results"][0]["source_opcode_class"],
                         "CONDITIONAL_LINK_UNRESOLVED")
        self.assertIsNone(r["callsite_results"][0]["public_direct_callee_object_file"])

    def test_target_outside_public_index_is_not_named(self):
        d = {a: bl(a, b) for a, b in zip(SITES, TARGETS)}
        d[SITES[0]] = bl(SITES[0], 0x8029C000)
        r = m.classify(fixture(), reader(d), PUBLIC)
        self.assertEqual(r["callsite_results"][0]["source_opcode_class"],
                         "DIRECT_BL_TARGET_OUTSIDE_PUBLIC_SOURCE_INDEX")
        self.assertIsNone(r["callsite_results"][0]["public_callee_object_file_relative_offset"])

    def test_source_owner_was_substituted(self):
        bad = (
            PUBLIC[0],
            (0x80296FD8, 0x8029B240,
             "Pack/RPSports/RPGolScene/RPGolPlayer.cpp"),
        )
        with self.assertRaises(m.adapter.QualificationError):
            m.classify(fixture(), reader(), bad)

    def test_ambiguous_public_target_refused(self):
        overlap = PUBLIC + ((0x800A3200, 0x800A3300, "another.cpp"),)
        with self.assertRaises(m.SourceFailure):
            m.classify(fixture(), reader(), overlap)

    def test_wrong_input_sha_claim_refused(self):
        bad = fixture()
        bad["original_B0_SHA_and_manifest_verified_before_after"] = False
        with self.assertRaises(m.SourceFailure):
            m.classify(bad, reader(), PUBLIC)

    def test_no_runtime_promotion_ever(self):
        r = m.classify(fixture(), reader(), PUBLIC)
        for label in ("intervening_call_must_clobber_entry_r3_verified",
                      "cache_writer_reachability_or_runtime_receiver_verified",
                      "ball_world_xyz_velocity_power_impact_score_verified",
                      "training_approved"):
            self.assertFalse(r[label])
        self.assertTrue(r["possible_callee_side_effects_remain_unresolved"])

    def test_wrong_first_reason_or_source_caller_refused(self):
        for key, replacement in [
            ("first_abstain_reason_class", "UNSUPPORTED_XFORM"),
            ("conservative_static_cfg_status", "STATIC_ENTRY_R3_MUST_FLOW"),
            ("public_caller", "fn_fake"),
            ("all_reaching_paths_preserve_entry_receiver", True),
            ("exact_cache_writer_callsite_reached", True),
        ]:
            bad = fixture()
            bad["source_only_two_callers"][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(m.SourceFailure):
                m.classify(bad, reader(), PUBLIC)

    def test_malformed_and_out_of_bound_offsets(self):
        for x in ("+0xFFFF", "+0x0001", "+0x000c", "-0x001C",
                  "0x001C", "+0x0000/private", "", None, 28):
            bad = fixture()
            bad["source_only_two_callers"][0][
                "first_source_relative_unresolved_offset"] = x
            # +0x0000 is valid: first instruction could be a BL; with the
            # fabricated callback it lacks a word and fails safely.
            with self.subTest(x=str(x)), self.assertRaises(
                    (m.SourceFailure, KeyError)):
                m.classify(bad, reader(), PUBLIC)

    def test_source_relative_witness_cannot_be_at_target(self):
        bad = fixture()
        bad["source_only_two_callers"][0][
            "first_source_relative_unresolved_offset"] = "+0x0098"
        with self.assertRaises(m.SourceFailure):
            m.classify(bad, reader(), PUBLIC)

    def test_output_contains_no_native_opcodes_hashes_or_paths(self):
        text = json.dumps(m.classify(fixture(), reader(), PUBLIC))
        for forbidden in ("0x48000001", "source_private_path",
                          "MEM1.bin", "native_instruction_word",
                          "source_blob_sha", "private_sha256"):
            self.assertNotIn(forbidden, text)

    def test_clean_cli_help_with_isolated_python(self):
        script = ROOT / "scripts" / "audit_p0_cache_cfg_first_intervening_bl_private.py"
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(
                [sys.executable, "-I", "-B", str(script), "--help"],
                cwd=td, capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--helper-root", p.stdout)

    def test_source_sha_gate_before_and_after(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            bank = data / "fabricatedB0"
            bank.write_bytes(b"RSPE01\0\1" + b"\0" * 1024)
            with (patch.object(m.adapter, "audit", return_value=fixture()),
                  patch.object(m.source, "checked_private_b0",
                               side_effect=[bank, bank]) as check,
                  patch.object(m.source, "load_public_text_units",
                               return_value=PUBLIC)):
                # Avoid building a real 24MiB data file in a synthetic.
                with patch.object(m, "classify", return_value={
                        "kind": m.KIND}):
                    out = m.audit(data, data, data)
        self.assertEqual(check.call_count, 2)
        self.assertEqual(out["kind"], m.KIND)

    def test_changed_after_sha_refused(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            bank = data / "fabricatedB0"
            bank.write_bytes(b"none")
            with (patch.object(m.adapter, "audit", return_value=fixture()),
                  patch.object(m.source, "checked_private_b0",
                               side_effect=[bank, data / "other"]),
                  patch.object(m.source, "load_public_text_units",
                               return_value=PUBLIC),
                  patch.object(m, "classify", return_value={"kind":m.KIND})):
                with self.assertRaises(m.SourceFailure):
                    m.audit(data, data, data)


if __name__ == "__main__":
    unittest.main()
