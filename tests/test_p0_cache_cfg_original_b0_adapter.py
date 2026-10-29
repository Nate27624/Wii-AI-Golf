"""Native-free synthetic tests for original B0-to-existing-CFG adapter."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_cache_cfg_original_b0_adapter as adapter

PUBLIC = ((0x80296FD8, 0x8029B240,
           "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"),)


class FakeCFG:
    CALLERS = adapter.EXPECTED_CALLERS
    CACHE_TARGET = 0x80299C70

    def inspect_known_callers(self, rd):
        rows = []
        for n, entry, callsite in self.CALLERS:
            # Demand correct bounded callback for both windows.
            if rd(entry) != 0x60000000 or rd(callsite) != 0x4BFFFFFF:
                raise adapter.QualificationError()
            rows.append({
                "kind": "P0-STATIC-PPC-R31-CALLSITE-MUSTDEF",
                "published_source_function": n,
                "status": "ABSTAIN_SOURCE_UNRESOLVED",
                "abstain_reason_category": "UNSUPPORTED_XFORM",
                "first_encountered_unresolved_source_relative_offset": "+0x000C",
                "known_exact_cache_writer_callsite_reached": False,
                "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3": False,
                "runtime_receiver_object_verified": False,
                "executed_cache_write_verified": False,
                "training_approved": False,
            })
        return {
            "kind": "P0-STATIC-TWO-CALLER-R31-MUSTDEF-REVIEW",
            "sources": rows,
            "runtime_receiver_verified": False,
            "training_approved": False,
        }


def synthetic_b0(tmp: Path) -> Path:
    file = tmp / "B0-fabricated"
    with file.open("wb") as fh:
        fh.truncate(adapter.source.MEM1_LEN)
        fh.seek(0)
        fh.write(b"RSPE01\x00\x01")
        for _, entry, call in adapter.EXPECTED_CALLERS:
            fh.seek(entry - adapter.source.MEM1_START)
            fh.write(struct.pack(">I", 0x60000000))
            fh.seek(call - adapter.source.MEM1_START)
            fh.write(struct.pack(">I", 0x4BFFFFFF))
    return file


class AdapterTests(unittest.TestCase):
    def test_two_authentic_source_windows_are_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            r = adapter.report_from_bytes(bank, FakeCFG(), public_units=PUBLIC)
        self.assertEqual(len(r["source_only_two_callers"]), 2)
        self.assertFalse(r["public_Golf_source_window_gated"])
        self.assertFalse(r["original_B0_SHA_and_manifest_verified_before_after"])
        self.assertFalse(r["reviewed_pure_CFG_helper_commit_verified"])
        self.assertTrue(all(x["conservative_static_cfg_status"]
                            == "ABSTAIN_SOURCE_UNRESOLVED"
                            for x in r["source_only_two_callers"]))
        self.assertFalse(r["runtime_cache_receiver_or_executed_writer_verified"])
        self.assertFalse(r["training_approved"])

    def test_exact_sanitized_reason_category_passed_from_cfg_owner(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            r = adapter.report_from_bytes(bank, FakeCFG(), public_units=PUBLIC)
        for row in r["source_only_two_callers"]:
            self.assertEqual(row["first_abstain_reason_class"], "UNSUPPORTED_XFORM")
            self.assertEqual(row["first_source_relative_unresolved_offset"], "+0x000C")
            self.assertTrue(row["diagnostic_witness_is_static_not_executed"])
            self.assertFalse(row["exact_cache_writer_callsite_reached"])

    def test_invalid_reason_category_does_not_escape_to_operator(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            class Unsafe(FakeCFG):
                def inspect_known_callers(self, read):
                    out = super().inspect_known_callers(read)
                    out["sources"][0]["abstain_reason_category"] = "PPC_BYTE_SECRET"
                    return out
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, Unsafe(), public_units=PUBLIC)

    def test_malformed_or_out_of_window_diagnostic_offset_refused(self):
        for bad in ("0xFFFF", "+0x9999", "+0x000c", "+0x000Z",
                    "+0xFFFF/private", "", 17, None):
            with self.subTest(bad=str(bad)), tempfile.TemporaryDirectory() as td:
                bank = synthetic_b0(Path(td))
                class Unsafe(FakeCFG):
                    def inspect_known_callers(self, read):
                        out = super().inspect_known_callers(read)
                        out["sources"][0]["first_encountered_unresolved_source_relative_offset"] = bad
                        return out
                # None is a valid exception: an unsupported decoder can
                # report no safe source-relative location.
                if bad is None:
                    r = adapter.report_from_bytes(bank, Unsafe(), public_units=PUBLIC)
                    self.assertIsNone(r["source_only_two_callers"][0][
                        "first_source_relative_unresolved_offset"])
                else:
                    with self.assertRaises(adapter.QualificationError):
                        adapter.report_from_bytes(bank, Unsafe(), public_units=PUBLIC)

    def test_source_reason_absent_on_unresolved_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            class Unsafe(FakeCFG):
                def inspect_known_callers(self, read):
                    out = super().inspect_known_callers(read)
                    out["sources"][0].pop("abstain_reason_category")
                    return out
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, Unsafe(), public_units=PUBLIC)

    def test_wrong_public_owner_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            bad = ((0x80296FD8, 0x8029B240,
                    "Pack/RPBox/RPGolMapObjBall.cpp"),)
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=bad)

    def test_same_golf_family_wrong_object_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            bad = ((0x80296FD8, 0x8029B240,
                    "Pack/RPSports/RPGolScene/RPGolPlayer.cpp"),)
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=bad)

    def test_overlapping_duplicate_source_owners_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            bad = PUBLIC + ((0x80296FD8, 0x8029B240,
                             "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"),)
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=bad)

    def test_incomplete_source_bounds_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            bad = ((0x80296FD8, 0x80299B64,
                    "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"),)
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=bad)

    def test_bad_revision_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            with bank.open("r+b") as f:
                f.seek(7)
                f.write(b"\x02")
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=PUBLIC)

    def test_callsite_reached_requires_literal_bool(self):
        # bool("false") is True; never promote an untrusted helper string
        # or integer to an affirmative source-reachability conclusion.
        for invalid in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(invalid=repr(invalid)), tempfile.TemporaryDirectory() as td:
                bank = synthetic_b0(Path(td))

                class Unsafe(FakeCFG):
                    def inspect_known_callers(self, read):
                        report = super().inspect_known_callers(read)
                        report["sources"][0][
                            "known_exact_cache_writer_callsite_reached"
                        ] = invalid
                        return report

                with self.assertRaises(adapter.QualificationError):
                    adapter.report_from_bytes(bank, Unsafe(), public_units=PUBLIC)

    def test_explicit_true_callsite_flag_not_coerced(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))

            class LiteralBoolean(FakeCFG):
                def inspect_known_callers(self, read):
                    report = super().inspect_known_callers(read)
                    row = report["sources"][0]
                    row["status"] = "NOT_PROVEN_FOR_ALL_REACHING_PATHS"
                    row["abstain_reason_category"] = None
                    row["first_encountered_unresolved_source_relative_offset"] = None
                    row["known_exact_cache_writer_callsite_reached"] = True
                    return report

            report = adapter.report_from_bytes(
                bank, LiteralBoolean(), public_units=PUBLIC)
        self.assertIs(report["source_only_two_callers"][0][
            "exact_cache_writer_callsite_reached"], True)

    def test_contradictory_cfg_proof_fields_rejected(self):
        # Every status must agree with reached/must-flow/reason fields.
        invalid = (
            {"status": "STATIC_ENTRY_R3_MUST_FLOW",
             "known_exact_cache_writer_callsite_reached": True,
             "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3": False,
             "abstain_reason_category": None,
             "first_encountered_unresolved_source_relative_offset": None},
            {"status": "STATIC_ENTRY_R3_MUST_FLOW",
             "known_exact_cache_writer_callsite_reached": False,
             "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3": True,
             "abstain_reason_category": None,
             "first_encountered_unresolved_source_relative_offset": None},
            {"status": "NOT_PROVEN_FOR_ALL_REACHING_PATHS",
             "known_exact_cache_writer_callsite_reached": False,
             "abstain_reason_category": None,
             "first_encountered_unresolved_source_relative_offset": None},
            {"status": "ABSTAIN_TARGET_UNREACHABLE",
             "known_exact_cache_writer_callsite_reached": True,
             "abstain_reason_category": "NO_REACHABLE_TARGET_PATH",
             "first_encountered_unresolved_source_relative_offset": None},
            {"status": "ABSTAIN_SOURCE_UNRESOLVED",
             "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3": True},
            {"status": "NOT_PROVEN_FOR_ALL_REACHING_PATHS",
             "known_exact_cache_writer_callsite_reached": True,
             "abstain_reason_category": "INTERVENING_CALL",
             "first_encountered_unresolved_source_relative_offset": None},
            {"status": "ABSTAIN_TARGET_UNREACHABLE",
             "abstain_reason_category": None,
             "first_encountered_unresolved_source_relative_offset": None},
        )
        for changes in invalid:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as td:
                bank = synthetic_b0(Path(td))

                class Contradictory(FakeCFG):
                    def inspect_known_callers(self, read):
                        report = super().inspect_known_callers(read)
                        report["sources"][0].update(changes)
                        return report

                with self.assertRaises(adapter.QualificationError):
                    adapter.report_from_bytes(
                        bank, Contradictory(), public_units=PUBLIC)

    def test_invalid_helper_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            class Bogus:
                def inspect_known_callers(self, rd):
                    del rd
                    return {
                        "kind": "P0-STATIC-TWO-CALLER-R31-MUSTDEF-REVIEW",
                        "sources": [],
                        "runtime_receiver_verified": True,
                        "training_approved": False,
                    }
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, Bogus(), public_units=PUBLIC)

    def test_invalid_helper_false_promotion_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            class Bogus(FakeCFG):
                def inspect_known_callers(self, rd):
                    x = super().inspect_known_callers(rd)
                    x["sources"][0]["training_approved"] = True
                    return x
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, Bogus(), public_units=PUBLIC)

    def test_wrong_helper_git_commit_refused(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
                adapter, "_git", side_effect=["1"*40, "", "blob", "blob"]):
            root = Path(td)
            (root / "scripts").mkdir()
            (root / adapter.CFG_RELATIVE).write_text("# fabricated\n")
            with self.assertRaises(adapter.QualificationError):
                adapter.qualified_helper_root(root)

    def test_dirty_helper_worktree_refused(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
                adapter, "_git", side_effect=[adapter.CFG_SHA, " M scripts/helper.py"]):
            root = Path(td)
            (root / "scripts").mkdir()
            (root / adapter.CFG_RELATIVE).write_text("# fabricated\n")
            with self.assertRaises(adapter.QualificationError):
                adapter.qualified_helper_root(root)

    def test_helper_blob_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
                adapter, "_git", side_effect=[adapter.CFG_SHA, "", "a"*40, "b"*40]):
            root = Path(td)
            (root / "scripts").mkdir()
            (root / adapter.CFG_RELATIVE).write_text("# fabricated\n")
            with self.assertRaises(adapter.QualificationError):
                adapter.qualified_helper_root(root)

    def test_source_sha_checked_before_and_after_read(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            with (patch.object(adapter, "load_helper", return_value=FakeCFG()),
                  patch.object(adapter.source, "checked_private_b0",
                               side_effect=[bank, bank]) as checked,
                  patch.object(adapter.source, "load_public_text_units",
                               return_value=PUBLIC)):
                r = adapter.audit(Path(td), Path(td), Path(td))
        self.assertEqual(checked.call_count, 2)
        self.assertTrue(r["original_B0_SHA_and_manifest_verified_before_after"])
        self.assertTrue(r["public_Golf_source_window_gated"])
        self.assertTrue(r["reviewed_pure_CFG_helper_commit_verified"])

    def test_postread_changed_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            with (patch.object(adapter, "load_helper", return_value=FakeCFG()),
                  patch.object(adapter.source, "checked_private_b0",
                               side_effect=[bank, bank.parent / "other"]),
                  patch.object(adapter.source, "load_public_text_units",
                               return_value=PUBLIC)):
                with self.assertRaises(adapter.QualificationError):
                    adapter.audit(Path(td), Path(td), Path(td))

    def test_no_private_source_words_paths_or_heap_pointers_in_report(self):
        with tempfile.TemporaryDirectory() as td:
            bank = synthetic_b0(Path(td))
            r = adapter.report_from_bytes(bank, FakeCFG(), public_units=PUBLIC)
        out = json.dumps(r)
        for forbidden in ("0x4BFFFFFF", "1073741823", "private-session",
                          "MEM1.bin", "sha256_digest", "runtime_heap_pointer"):
            self.assertNotIn(forbidden, out)
        self.assertFalse(r["rendered_physical_ball_XYZ_velocity_power_impact_score_verified"])
        self.assertFalse(r["entry_r3_object_class_or_identity_verified"])

    def test_missing_bad_bank_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bank = Path(td) / "invalid"
            bank.write_bytes(b"RSPE01\x00\x01")
            with self.assertRaises(adapter.QualificationError):
                adapter.report_from_bytes(bank, FakeCFG(), public_units=PUBLIC)


if __name__ == "__main__":
    unittest.main()
