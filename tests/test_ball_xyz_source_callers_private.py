"""Pure synthetic PPC BL callsite regressions for S002 offline source audit."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "audit_ball_xyz_source_callers_private",
    ROOT / "scripts" / "audit_ball_xyz_source_callers_private.py")
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def branch(pc: int, target: int, *, link=True, absolute=False) -> int:
    delta = target if absolute else target - pc
    assert -(1 << 25) <= delta < (1 << 25) and delta % 4 == 0
    return (18 << 26) | (delta & 0x03FFFFFC) | (2 if absolute else 0) | int(link)


class PPCStaticTests(unittest.TestCase):
    def test_relative_bl_positive_and_negative(self):
        for pc, dst in ((0x80290000, 0x802A0388),
                        (0x802A2000, 0x8029F300)):
            self.assertEqual(m.decode_ppc_branch(pc, branch(pc, dst)),
                             (dst, True))

    def test_nonlink_branch_is_not_call(self):
        pc, dst = 0x8029E640, 0x802A0388
        self.assertEqual(m.decode_ppc_branch(pc, branch(pc, dst, link=False)),
                         (dst, False))

    def test_non_branch_opcodes_not_calls(self):
        self.assertIsNone(m.decode_ppc_branch(0x80290000, 0))
        self.assertIsNone(m.decode_ppc_branch(0x80290000, 0x4E800020))
        self.assertIsNone(m.decode_ppc_branch(0x80290000, 0x7C0802A6))

    def test_unsupported_out_of_scope_source_excluded(self):
        pc = m.UNITS[0][1] - 4
        code = struct.pack(">I", branch(pc, 0x802A0388))
        res = m.summarize_code(code, pc)
        writer = res["targets"][0]
        self.assertEqual(writer["direct_bl_into_window_count"], 0)

    def test_full_source_window_finds_code_owners(self):
        lo = min(x[1] for x in m.UNITS)
        hi = max(x[2] for x in m.UNITS)
        code = bytearray(hi - lo)
        sites = [
            (m.UNITS[0][1] + 0x40, 0x802A0388),
            (m.UNITS[2][1] + 0x80, 0x80299C70),
            (m.UNITS[4][1] + 0x100, 0x8029F300),
            (m.UNITS[3][1] + 0x44, 0x802922EC),
        ]
        for pc, dst in sites:
            struct.pack_into(">I", code, pc - lo, branch(pc, dst))
        report = m.summarize_code(code, lo)
        names = {t["target"]: t for t in report["targets"]}
        self.assertEqual(names["player_to_ball_translation_write"]["direct_bl_into_window_count"], 1)
        self.assertEqual(names["ball_to_player_position_read"]["direct_bl_into_window_count"], 1)
        self.assertEqual(names["ball_unit_goal_cache_update"]["direct_bl_into_window_count"], 1)
        self.assertEqual(names["field_start_position_getter"]["direct_bl_into_window_count"], 1)
        self.assertEqual(names["player_to_ball_translation_write"]["source_units"][0]["source_unit"], "RPGolMain")
        self.assertEqual(names["player_to_ball_translation_write"]["source_units"][0]["source_relative_callsite_offsets"], ["+0x0040"])
        self.assertFalse(report["real_inflight_ball_world_xyz_verified"])
        self.assertFalse(report["approved_for_model_training"])

    def test_nonlink_and_absence_do_not_imply_unused(self):
        lo = min(x[1] for x in m.UNITS)
        src = m.UNITS[4][1] + 0x30
        code = bytearray(src + 4 - lo)
        struct.pack_into(">I", code, src - lo,
                         branch(src, 0x802A0388, link=False))
        report = m.summarize_code(code, lo)
        writer = report["targets"][0]
        self.assertEqual(writer["direct_bl_into_window_count"], 0)
        self.assertEqual(writer["nonlink_branches_into_window_count"], 1)
        self.assertTrue(writer["no_direct_call_cannot_disprove_indirect_dispatch"])

    def test_source_overlap_and_invalid_word_count_rejected(self):
        with self.assertRaises(m.UntrustedInput):
            m.summarize_code(b"\x00" * 5, 0x80290000)
        with self.assertRaises(m.UntrustedInput):
            m.summarize_code(b"\x00" * 4, 0x80290002)

    def test_capped_callsite_output_never_exposes_words(self):
        pc = m.UNITS[0][1]
        code = b"".join(struct.pack(">I", branch(pc + 4*i, 0x802A0388))
                        for i in range(24))
        result = m.summarize_code(code, pc)
        hits = result["targets"][0]["source_units"][0]
        self.assertEqual(hits["direct_bl_count"], 24)
        self.assertEqual(len(hits["source_relative_callsite_offsets"]), 16)
        self.assertEqual(hits["additional_callsites_omitted"], 8)
        out = json.dumps(result)
        self.assertNotIn("0x802A0388", out)
        self.assertNotIn("0x8028E098", out)
        self.assertNotIn("0x91BF3E94", out)
        self.assertNotIn("Wii-AI-Golf-Data", out)
        self.assertNotIn("native_sha256", out)
        self.assertIn("NOT_UPLOADED", out)

    def test_invalid_private_root_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data = Path(root) / "random-directory"
            data.mkdir()
            session = data / "shot"
            session.mkdir()
            with self.assertRaises(m.UntrustedInput):
                m.checked_private_b0(session, data)

    def test_corrupted_original_hash_and_then_valid_native(self):
        with tempfile.TemporaryDirectory() as root:
            data = Path(root) / "Wii-AI-Golf-Data"
            data.mkdir()
            session = data / "ball-study-20261027-212633"
            session.mkdir()
            file = session / "B0-MEM1.bin"
            with file.open("wb") as f:
                f.truncate(m.MEM1_LEN)
                f.seek(0)
                f.write(b"RSPE01\x00\x01")
                for pc in (0x802A0388, 0x8029F300, 0x80299C70):
                    f.seek(pc - m.MEM1_START)
                    f.write(struct.pack(">I", 0x9421FFF0))
                call = m.UNITS[0][1] + 0x20
                f.seek(call - m.MEM1_START)
                f.write(struct.pack(">I", branch(call, 0x802A0388)))
            stage = {
                "phase_operator_label": "idle_baseline",
                "native_sizes_valid": True,
                "scene_source_chain_gated": True,
                "operator_reports_gui_paused": True,
                "observed_game_mode": 4,
                "sha256": {"MEM1": "0" * 64},
            }
            manifest = {
                "kind": "local-private-golf-paired-checkpoints",
                "schema_version": 1,
                "checkpoints": {"B0": stage},
            }
            info = session / "checkpoint-manifest-PRIVATE.json"
            info.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(m.UntrustedInput):
                m.audit(session, data)
            sha = hashlib.sha256()
            with file.open("rb") as f:
                for part in iter(lambda: f.read(1024 * 1024), b""):
                    sha.update(part)
            stage["sha256"]["MEM1"] = sha.hexdigest()
            info.write_text(json.dumps(manifest), encoding="utf-8")
            safe = m.audit(session, data)
            self.assertTrue(safe["native_source_b0_sha256_verified"])
            self.assertEqual(safe["targets"][0]["direct_bl_into_window_count"], 1)
            self.assertFalse(safe["real_inflight_ball_world_xyz_verified"])

    def test_wrong_game_revision_and_phase_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data = Path(root) / "Wii-AI-Golf-Data"
            data.mkdir()
            session = data / "case"
            session.mkdir()
            file = session / "B0-MEM1.bin"
            with file.open("wb") as f:
                f.truncate(m.MEM1_LEN)
                f.write(b"RSPE01\x00\x00")
            sha = hashlib.sha256()
            with file.open("rb") as f:
                for part in iter(lambda: f.read(1024 * 1024), b""):
                    sha.update(part)
            entry = {"phase_operator_label": "idle_baseline",
                     "operator_reports_gui_paused": True,
                     "scene_source_chain_gated": True,
                     "native_sizes_valid": True, "observed_game_mode": 4,
                     "sha256": {"MEM1": sha.hexdigest()}}
            mf = session / "checkpoint-manifest-PRIVATE.json"
            mf.write_text(json.dumps({
                "schema_version": 1,
                "kind": "local-private-golf-paired-checkpoints",
                "checkpoints": {"B0": entry},
            }), encoding="utf-8")
            with self.assertRaises(m.UntrustedInput):
                m.audit(session, data)
            entry["phase_operator_label"] = "flight"
            mf.write_text(json.dumps({
                "schema_version": 1,
                "kind": "local-private-golf-paired-checkpoints",
                "checkpoints": {"B0": entry},
            }), encoding="utf-8")
            with self.assertRaises(m.UntrustedInput):
                m.audit(session, data)



    def test_public_split_index_uses_exact_committed_blob_not_claimed_sha(self):
        # A locally modified unit name with intact metadata must fail closed.
        expected = m.load_public_text_units()
        self.assertEqual(len(expected), m.PUBLIC_UNIT_COUNT)
        with tempfile.TemporaryDirectory() as root:
            modified = json.loads(m.PUBLIC_INDEX.read_text("utf-8"))
            self.assertEqual(modified["source_blob_sha"], m.PUBLIC_SPLITS_SHA)
            modified["intervals"][0][2] = "ForgedSource.cpp"
            candidate = Path(root) / "source-index.json"
            candidate.write_text(json.dumps(modified), encoding="utf-8")
            with self.assertRaises(m.UntrustedInput):
                m.load_public_text_units(candidate)

    def test_public_split_index_windows_crlf_normalization(self):
        # CRLF checkout does not affect canonical committed Git object identity.
        with tempfile.TemporaryDirectory() as root:
            candidate = Path(root) / "source-index.json"
            raw = m.PUBLIC_INDEX.read_bytes().replace(b"\r\n", b"\n")
            candidate.write_bytes(raw.replace(b"\n", b"\r\n"))
            self.assertEqual(m.load_public_text_units(candidate),
                             m.load_public_text_units())

    def test_public_rev1_entry_symbols_and_caller_crosswalk(self):
        # Mimics the OPERATOR'S source-unit-relative reported callsites.
        # Labels only: no operator ROM/RAM bytes or runtime addresses.
        lo = min(item[1] for item in m.UNITS)
        hi = max(item[2] for item in m.UNITS)
        code = bytearray(hi - lo)
        callsites = [
            (m.UNITS[5][1] + 0x09F4, 0x802A0318),
            (m.UNITS[5][1] + 0x0F2C, 0x802A0320),
            (m.UNITS[2][1] + 0x2B8C, 0x80299C70),
            (m.UNITS[2][1] + 0x2C80, 0x80299C70),
        ]
        for pc, dst in callsites:
            struct.pack_into(">I", code, pc - lo, branch(pc, dst))
        # Exact 8-byte fn_802A0318 trampoline must actually forward.
        struct.pack_into(">I", code, 0x802A0318 - lo, 0x60000000)
        struct.pack_into(">I", code, 0x802A031C - lo,
                         branch(0x802A031C, 0x802A0320, link=False))
        result = m.summarize_code(code, lo)
        names = {v["target"]: v for v in result["targets"]}
        for name in ("player_to_ball_translation_write",
                     "ball_unit_goal_cache_update"):
            self.assertEqual(names[name]["direct_bl_at_known_function_entry_count"], 2)
            self.assertEqual(names[name]["direct_bl_to_function_interior_count"], 0)
        self.assertTrue(
            result["short_player_writer_entry_thunk_branches_to_main_function"])
        self.assertTrue(
            result["source_function_call_does_not_prove_conditional_stores_executed"])
        self.assertFalse(result["real_inflight_ball_world_xyz_verified"])

    def test_thunk_forwarding_is_not_inferred_from_symbol_names(self):
        lo = 0x802A0318
        self.assertIsNone(m.source_thunk_forwards_to_writer(b"", lo))
        false_thunk = struct.pack(">II", 0x60000000, 0x60000000)
        self.assertFalse(m.source_thunk_forwards_to_writer(false_thunk, lo))
        true_thunk = struct.pack(">II", 0x60000000,
                                 branch(lo + 4, 0x802A0320, link=False))
        self.assertTrue(m.source_thunk_forwards_to_writer(true_thunk, lo))

    def test_interior_caller_does_not_get_entry_proof(self):
        pc = m.UNITS[5][1] + 0x0100
        code = struct.pack(">I", branch(pc, 0x802A0388))
        data = m.summarize_code(code, pc)
        writer = data["targets"][0]
        self.assertEqual(writer["direct_bl_into_window_count"], 1)
        self.assertEqual(writer["direct_bl_at_known_function_entry_count"], 0)
        self.assertEqual(writer["direct_bl_to_function_interior_count"], 1)


    def test_tiny_writer_entry_can_fallthrough_without_direct_b(self):
        entry = 0x802A0318
        # Two valid noncontrol PPC operations (nop) continue to adjacent PC.
        data = struct.pack(">II", 0x60000000, 0x60000000)
        self.assertFalse(m.source_thunk_forwards_to_writer(data, entry))
        self.assertEqual(m.classify_short_writer_entry(data, entry),
                         "straightline_fallthrough_to_adjacent_entry_candidate")

    def test_short_writer_entry_return_branch_conditional_and_call(self):
        pc = 0x802A0318
        forms = [
            ((0x60000000, 0x4E800020), "return_exception_or_indirect_branch"),
            ((0x60000000, 0x4E800420), "return_exception_or_indirect_branch"),
            ((0x60000000, 16 << 26), "conditional_branch_or_fallthrough_unresolved"),
            ((0x60000000, branch(pc + 4, 0x802A0320, link=False)),
             "direct_branch_into_main_writer_entry"),
            ((0x60000000, branch(pc + 4, pc + 0x100, link=False)),
             "unconditional_branch_elsewhere"),
            ((0x60000000, branch(pc + 4, pc + 0x100, link=True)),
             "linked_call_before_entry_end_unresolved"),
        ]
        for words, expected in forms:
            with self.subTest(expected=expected):
                self.assertEqual(
                    m.classify_short_writer_entry(struct.pack(">II", *words), pc),
                    expected)

    def test_upstream_entry_call_edges_grouped_with_source_unit(self):
        # Simulated two-hop code, no native bytes. The public caller starts
        # already have exact known function names and signatures.
        pc = m.UNITS[4][1] + 0x0180
        code = struct.pack(">III",
            branch(pc, 0x802A28DC),
            branch(pc + 4, 0x80299ACC),
            branch(pc + 8, 0x80299C20))
        report = m.summarize_code(code, pc)
        names = {row["callee"]: row for row in report["upstream_function_entry_calls"]}
        self.assertEqual(names["player_manager_short_entry_caller"][
            "direct_bl_at_exact_entry_count"], 1)
        self.assertEqual(names["ball_unit_cache_caller_a"][
            "direct_bl_at_exact_entry_count"], 1)
        self.assertEqual(names["ball_unit_cache_caller_b"][
            "source_units"][0]["source_unit"], "RPGolPlayer")
        self.assertTrue(report["upstream_calls_do_not_prove_actual_game_update"])
        self.assertFalse(report["real_inflight_ball_world_xyz_verified"])

    def test_no_assumed_upstream_entry_or_fallthrough_from_zero_fixture(self):
        entry = 0x802A0318
        self.assertEqual(
            m.classify_short_writer_entry(b"\x00" * 8, entry),
            "unclassified_zero_word")
        self.assertEqual(
            m.classify_short_writer_entry(b"", entry),
            "not_captured")
        report = m.summarize_code(b"\x00" * 8, entry)
        self.assertEqual(
            sum(row["direct_bl_at_exact_entry_count"]
                for row in report["upstream_function_entry_calls"]), 0)
        self.assertFalse(report["approved_for_model_training"])


    def test_short_entry_reports_real_direct_branch_target_as_source_offset(self):
        entry = 0x802A0318
        target = 0x802A0200  # Earlier publicly mapped RPGolPlayer function
        data = struct.pack(">II", 0x60000000,
                           branch(entry + 4, target, link=False))
        output = m.short_entry_unconditional_destination(data, entry)
        self.assertTrue(output["found"])
        self.assertEqual(output["instruction_index"], 1)
        self.assertEqual(output["destination_source_unit"], "RPGolPlayer")
        self.assertEqual(output["destination_source_relative_offset"],
                         f"+0x{target-m.UNITS[4][1]:04X}")
        self.assertFalse(output["is_main_writer_function_entry"])
        self.assertFalse(output["is_main_writer_function_interior"])
        serialized = json.dumps(output)
        self.assertNotIn("0x802A0200", serialized)
        self.assertNotIn("mem1", serialized.lower())

    def test_short_entry_branches_directly_to_writer_or_interior(self):
        entry = 0x802A0318
        for target, expected in ((0x802A0320, "is_main_writer_function_entry"),
                                 (0x802A0388, "is_main_writer_function_interior")):
            with self.subTest(target=target):
                data = struct.pack(">II", branch(entry, target, link=False),
                                   0x60000000)
                result = m.short_entry_unconditional_destination(data, entry)
                self.assertTrue(result["found"])
                self.assertTrue(result[expected])
                self.assertEqual(result["destination_source_unit"], "RPGolPlayer")

    def test_short_entry_branch_outside_known_units_does_not_leak_dest(self):
        entry = 0x802A0318
        outside = 0x80280000
        data = struct.pack(">II", 0x60000000,
                           branch(entry + 4, outside, link=False))
        result = m.short_entry_unconditional_destination(data, entry)
        self.assertTrue(result["found"])
        self.assertFalse(result["destination_in_scanned_golf_units"])
        self.assertIsNone(result["destination_source_relative_offset"])
        self.assertNotIn("0x80280000", json.dumps(result))

    def test_short_entry_no_branch_is_not_invented(self):
        entry = 0x802A0318
        self.assertEqual(
            m.short_entry_unconditional_destination(struct.pack(">II",
                0x60000000, 0x60000000), entry),
            {"found": False, "reason": "no_direct_unconditional_branch"})
        self.assertEqual(
            m.short_entry_unconditional_destination(b"", entry),
            {"found": False, "reason": "not_captured"})
        called = struct.pack(">II", 0x60000000,
                             branch(entry + 4, 0x802A0320, link=True))
        self.assertEqual(
            m.short_entry_unconditional_destination(called, entry),
            {"found": False, "reason": "linked_call_not_direct_jump"})


    def test_public_code_split_index_is_pinned_and_has_all_source_units(self):
        rows = m.load_public_text_units()
        self.assertEqual(len(rows), 832)
        self.assertTrue(any(name.endswith("RPGolPlayer.cpp")
                            for _a, _b, name in rows))
        self.assertTrue(any(name.endswith(".o") for _a, _b, name in rows))
        self.assertTrue(all(rows[i][1] <= rows[i + 1][0]
                            for i in range(len(rows) - 1)))

    def test_short_branch_target_uses_complete_public_source_map(self):
        entry = 0x802A0318
        target = 0x802A0200
        fake_bytes = struct.pack(">II", 0x60000000,
                                 branch(entry + 4, target, link=False))
        public = ((0x802A0000, 0x802A0300, "Pack/RPSports/RPGolScene/SyntheticPlayer.cpp"),)
        result = m.public_branch_destination(fake_bytes, entry, public)
        self.assertEqual(result["destination_public_source_file"],
                         "Pack/RPSports/RPGolScene/SyntheticPlayer.cpp")
        self.assertEqual(result["destination_public_source_relative_offset"], "+0x0200")
        self.assertTrue(result["within_original_six_golf_units"])
        self.assertFalse(result["source_execution_during_shot_verified"])
        self.assertNotIn("0x802A0200", json.dumps(result))

    def test_short_branch_outside_all_source_units_stays_unknown(self):
        entry = 0x802A0318
        fake_bytes = struct.pack(">II", 0x60000000,
                                 branch(entry + 4, 0x80280000, link=False))
        rows = ((0x802A0000, 0x802A1000, "Pack/RPSports/RPGolScene/SyntheticPlayer.cpp"),)
        result = m.public_branch_destination(fake_bytes, entry, rows)
        self.assertFalse(result["public_code_owner_found"])
        self.assertEqual(result["reason"], "outside_all_832_published_rev1_text_units")

    def test_public_split_tamper_and_missing_index_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "public_index.json"
            self.assertRaises(m.UntrustedInput, m.load_public_text_units, p)
            data = json.loads(m.PUBLIC_INDEX.read_text(encoding="utf-8"))
            data["source_blob_sha"] = "0" * 40
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertRaises(m.UntrustedInput, m.load_public_text_units, p)
            data["source_blob_sha"] = m.PUBLIC_SPLITS_SHA
            data["intervals"][1][0] = data["intervals"][0][0]
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertRaises(m.UntrustedInput, m.load_public_text_units, p)

if __name__ == "__main__":
    unittest.main()
