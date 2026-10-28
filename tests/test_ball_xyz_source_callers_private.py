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


if __name__ == "__main__":
    unittest.main()
