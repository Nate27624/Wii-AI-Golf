"""Synthetic source-owner, historical Rev0 address and privacy regressions.

All fake RAM is created from scratch. No operator ROM, MEM1/MEM2 or traces.
"""
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
    "audit_legacy_ball_xyz_anchor_private", ROOT / "scripts" /
    "audit_legacy_ball_xyz_anchor_private.py")
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def f32(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


class FakeBanks:
    def __init__(self, *, alias_legacy=False):
        self.memory = {}
        self.alias_legacy = alias_legacy
        self.manager = 0x80012000
        self.scene = 0x90010000
        self.config = 0x90011000
        self.pm = 0x90020000
        self.rec = self.pm + 4
        self.field = 0x90012000
        self.tee = 0x90013000
        self.pin = 0x90014000
        self.ball = m.LEGACY_V0_XYZ - 0x30 if alias_legacy else 0x90030000
        self.selected_xyz = [f32(2.2), f32(-5.5), f32(-318.0)]
        self.legacy_xyz = list(self.selected_xyz if alias_legacy else [
            f32(9.0), f32(10.0), f32(11.0)])
        self.setup()

    def write(self, address, payload):
        for i, b in enumerate(payload):
            self.memory[address + i] = b

    def u32write(self, addr, value):
        self.write(addr, struct.pack(">I", value))

    def triplet(self, addr, data):
        self.write(addr, struct.pack(">III", *data))

    def setup(self):
        self.write(m.MEM1_BASE, b"RSPE01\x00\x01")
        self.u32write(0x804BF4D8, self.manager)
        self.u32write(self.manager + 0x0C, self.scene)
        self.u32write(self.manager + 0x18, 5)
        self.u32write(self.scene + 0x1C, 5)
        self.u32write(self.scene + 0x20, self.manager)
        self.u32write(self.scene + 0x54, 2)
        self.u32write(0x804BF8C4, self.config)
        self.u32write(self.config + 0x94, 4)
        self.u32write(self.config + 0x98, 1)
        self.u32write(0x804BF8D0, self.pm)
        self.u32write(self.pm, 0x803C7DD0)
        self.u32write(self.pm + 0x334, self.rec)
        self.u32write(self.rec + 0x88, self.ball)
        self.u32write(self.ball, 0x803C7918)
        self.u32write(self.ball + 0x4C, self.ball + 0x30)
        self.triplet(self.ball + 0x30, self.selected_xyz)
        self.triplet(self.rec + 0x54, self.selected_xyz)
        self.triplet(self.rec + 0x60, self.selected_xyz)
        self.u32write(0x804BF868, self.field)
        self.u32write(self.field + 0x50, self.tee)
        self.u32write(self.field + 0x44, self.pin)
        self.u32write(self.tee + 0x48, self.tee + 0x0C)
        self.u32write(self.tee + 0x4C, self.tee + 0x30)
        self.triplet(self.tee + 0x30, self.selected_xyz)
        self.u32write(self.pin + 0x4C, self.pin + 0x30)
        self.triplet(self.pin + 0x30, [f32(30.0), f32(40.0), f32(50.0)])
        self.triplet(m.LEGACY_V0_XYZ, self.legacy_xyz)

    def read(self, address, count):
        return bytes(self.memory.get(address + i, 0) for i in range(count))

    def words(self, address):
        return struct.unpack(">III", self.read(address, 12))

    def u32(self, address):
        return struct.unpack(">I", self.read(address, 4))[0]


class LegacyXYZTests(unittest.TestCase):
    def test_known_source_exact_same_address(self):
        source = FakeBanks(alias_legacy=True)
        evidence = m.read_source_identity(source)
        self.assertTrue(evidence["historical_location_is_source_selected_ball_translation"])
        self.assertEqual(evidence["historical_matches_selected_ball_components"], 3)
        self.assertEqual(evidence["historical_matches_tee_components"], 3)
        result = m.classify([evidence])
        self.assertTrue(result["legacy_equals_resolved_ball_vector_all"])
        self.assertFalse(result["confirmed_inflight_ball_xyz"])
        self.assertFalse(result["training_approved"])

    def test_cross_revision_different_location_not_falsely_promoted(self):
        source = FakeBanks()
        evidence = m.read_source_identity(source)
        self.assertFalse(evidence["historical_location_is_source_selected_ball_translation"])
        self.assertEqual(evidence["historical_matches_selected_ball_components"], 0)
        self.assertTrue(evidence["historical_triplet_finite_bounded"])
        self.assertFalse(m.classify([evidence])["historical_address_cross_version_verified"])

    def test_zero_deltas_in_idle_capture_do_not_prove_motion(self):
        snap = m.read_source_identity(FakeBanks())
        result = m.classify([snap, snap])
        self.assertEqual(result["legacy_changed_components_from_first"], [0])
        self.assertFalse(result["shot_motion_observed_in_this_study"])
        self.assertFalse(result["confirmed_inflight_ball_xyz"])

    def test_only_legacy_changes_do_not_prove_selected_ball(self):
        first = FakeBanks()
        after = FakeBanks()
        after.triplet(m.LEGACY_V0_XYZ, [f32(100.0), f32(101.0), f32(102.0)])
        result = m.classify([m.read_source_identity(first), m.read_source_identity(after)])
        self.assertEqual(result["legacy_changed_components_from_first"], [3])
        self.assertEqual(result["source_selected_changed_components_from_first"], [0])
        self.assertFalse(result["confirmed_inflight_ball_xyz"])

    def test_dynamic_selected_pointer_disappearance_rejected(self):
        fake = FakeBanks()
        fake.u32write(fake.pm + 0x334, 0)
        with self.assertRaises(m.InvalidEvidence):
            m.read_source_identity(fake)

    def test_source_self_reference_violation_rejected(self):
        fake = FakeBanks()
        fake.u32write(fake.ball + 0x4C, fake.ball + 0x34)
        with self.assertRaises(m.InvalidEvidence):
            m.read_source_identity(fake)

    def test_wrong_revision_rejected(self):
        fake = FakeBanks()
        fake.write(m.MEM1_BASE + 7, b"\x00")
        with self.assertRaises(m.InvalidEvidence):
            m.read_source_identity(fake)

    def test_wrong_mode_or_scene_rejected(self):
        for address, value in [(0x90011000 + 0x94, 0),
                               (0x90010000 + 0x1C, 9)]:
            fake = FakeBanks()
            fake.u32write(address, value)
            with self.assertRaises(m.InvalidEvidence):
                m.read_source_identity(fake)

    def test_false_finite_historical_address_does_not_imply_xyz(self):
        fake = FakeBanks()
        fake.triplet(m.LEGACY_V0_XYZ, [0x7F800000, f32(1.0), f32(2.0)])
        result = m.classify([m.read_source_identity(fake)])
        self.assertFalse(result["historical_triplet_finite_bounded_all"])
        self.assertFalse(result["confirmed_inflight_ball_xyz"])

    def test_private_output_never_contains_native_words_or_addresses(self):
        fake = FakeBanks()
        report = json.dumps(m.classify([m.read_source_identity(fake)]))
        self.assertNotIn("0x91BF3E94", report)
        self.assertNotIn("0x90030000", report)
        self.assertNotIn("0x803C7918", report)
        self.assertNotIn("2.200", report)
        self.assertNotIn("Wii-AI-Golf-Data", report)
        self.assertNotIn("_legacy_words", report)
        self.assertIn('"training_approved": false', report)
        self.assertIn("NOT_UPLOADED", report)

    def test_cohort_mismatched_owner_rejected(self):
        a, b = FakeBanks(), FakeBanks()
        b.u32write(b.pm + 0x334, b.pm + 4 + 0xCC)
        b.u32write(b.pm + 4 + 0xCC + 0x88, b.ball)
        with self.assertRaises(m.InvalidEvidence):
            m.classify([m.read_source_identity(a), m.read_source_identity(b)])

    def test_bad_manifest_hash_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Wii-AI-Golf-Data"
            root.mkdir()
            session = root / "ball-study-20261027-212633"
            session.mkdir()
            fake = FakeBanks()
            files = {}
            for name, base, size in (("MEM1", m.MEM1_BASE, m.MEM1_SIZE),
                                     ("MEM2", m.MEM2_BASE, m.MEM2_SIZE)):
                path = session / f"B0-{name}.bin"
                with path.open("wb") as f:
                    f.truncate(size)
                    for addr, byte in fake.memory.items():
                        if base <= addr < base + size:
                            f.seek(addr - base)
                            f.write(bytes([byte]))
                files[name] = path
            info = {
                "phase_operator_label": "idle_baseline",
                "operator_reports_gui_paused": True,
                "scene_source_chain_gated": True,
                "native_sizes_valid": True,
                "observed_game_mode": 4,
                "sha256": {"MEM1": "0" * 64, "MEM2": "0" * 64},
            }
            manifest = {
                "schema_version": 1,
                "kind": "local-private-golf-paired-checkpoints",
                "checkpoints": {"B0": info},
            }
            (session / "checkpoint-manifest-PRIVATE.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(m.InvalidEvidence):
                m.audit(session, root, ["B0"])
            for name in files:
                h = hashlib.sha256()
                with files[name].open("rb") as f:
                    for part in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(part)
                info["sha256"][name] = h.hexdigest()
            (session / "checkpoint-manifest-PRIVATE.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            result = m.audit(session, root, ["B0"])
            self.assertEqual(result["snapshot_count"], 1)
            self.assertTrue(result["native_bank_sha256_verified"])
            self.assertFalse(result["training_approved"])


if __name__ == "__main__":
    unittest.main()
