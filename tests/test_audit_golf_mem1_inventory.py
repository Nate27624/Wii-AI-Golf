"""Synthetic-only private snapshot checks for source-root inventory."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "single_mem1_inventory", ROOT / "scripts" / "audit_golf_mem1_inventory.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def put(buf, addr, word):
    struct.pack_into(">I", buf, addr - audit.MEM1_BASE, word)


def fake_mem1():
    mem = bytearray(audit.MEM1_LEN)
    mem[:8] = audit.GAME_HEADER
    for address, word in {
        audit.CONFIG_SLOT: 0x80010000,
        0x80010094: 4,
        0x80010098: 1,
        audit.MANAGER_SLOT: 0x80020000,
        0x8002000C: 0x80030000,
        0x80020018: 5,
        0x8003001C: 5,
        0x80030020: 0x80020000,
        0x80030054: 2,
        0x8003009C: 0x80040000,
        audit.FIELD_SLOT: 0x80050000,
        0x8005003C: 6,
        0x80050048: 31,
        0x80050044: 0x80060000,
        0x80050050: 0x80061000,
        0x80050054: 0x80062000,
        0x80050068: 0x90001000,
        0x80050070: 0x80063000,
        0x80050018: 0x80064000,
    }.items():
        put(mem, address, word)
    return mem


class SingleMem1InventoryTests(unittest.TestCase):
    def test_source_root_and_field_refs_are_only_candidates(self):
        report = audit.audit(fake_mem1())
        self.assertTrue(report["hitting_the_green_mode_verified"])
        self.assertTrue(report["current_golf_scene_and_backlink_verified_in_snapshot"])
        self.assertEqual(report["current_hole_raw_source_candidate"], 1)
        self.assertTrue(report["candidate_main_pointer_wii_ram_shape"])
        self.assertFalse(report["candidate_main_is_rpgolmain_verified"])
        self.assertFalse(report["shot_power_verified"])
        self.assertFalse(report["ball_xyz_verified"])
        self.assertFalse(report["allowed_to_publish_to_github"])
        self.assertTrue(report["field_member_refs"]["pin"]["referenced_bank_supplied"])
        self.assertTrue(report["field_member_refs"]["wind_object"]["wii_ram_address_shape"])
        self.assertFalse(report["field_member_refs"]["wind_object"]["referenced_bank_supplied"])
        serialized = json.dumps(report)
        self.assertNotIn("0x80050000", serialized)
        self.assertNotIn("0x90001000", serialized)
        self.assertNotIn("RAW-PRIVATE", serialized)

    def test_game_revision_and_mode_rejected(self):
        mem = fake_mem1()
        mem[7] = 2
        with self.assertRaisesRegex(ValueError, "Rev1"):
            audit.audit(mem)
        mem = fake_mem1()
        put(mem, 0x80010094, 5)
        with self.assertRaisesRegex(ValueError, "mode"):
            audit.audit(mem)

    def test_scene_backlink_and_manager_scene_id_rejected(self):
        mem = fake_mem1()
        put(mem, 0x80030020, 0x80020100)
        with self.assertRaisesRegex(ValueError, "backlink"):
            audit.audit(mem)
        mem = fake_mem1()
        put(mem, 0x80020018, 3)
        with self.assertRaisesRegex(ValueError, "not Golf"):
            audit.audit(mem)

    def test_source_field_absent_is_explicit_not_fabricated(self):
        mem = fake_mem1()
        put(mem, audit.FIELD_SLOT, 0)
        report = audit.audit(mem)
        self.assertFalse(report["field_manager_object_available_in_supplied_banks"])
        self.assertEqual(report["field_member_refs"], {})
        self.assertEqual(report["field_object_counts"], {})

    def test_optional_mem2_companion_proves_mapping_not_semantics(self):
        report = audit.audit(fake_mem1(), bytes(audit.MEM2_LEN))
        self.assertTrue(report["mem2_companion_supplied"])
        self.assertTrue(report["field_member_refs"]["wind_object"]["referenced_bank_supplied"])
        self.assertFalse(report["wind_vector_verified"])

    def test_cli_is_private_and_redacts_path(self):
        with tempfile.TemporaryDirectory() as d:
            private = Path(d) / "Wii-AI-Golf-Data"
            private.mkdir()
            p = private / "mem1.raw"
            mem = fake_mem1()
            p.write_bytes(mem)
            out, err = StringIO(), StringIO()
            with patch.object(audit, "PRIVATE_ROOT", private):
                with redirect_stdout(out), redirect_stderr(err):
                    status = audit.main(["--mem1", str(p)])
            self.assertEqual(status, 0, err.getvalue())
            result = json.loads(out.getvalue())
            self.assertTrue(result["current_golf_scene_and_backlink_verified_in_snapshot"])
            self.assertNotIn(str(private), out.getvalue())
            self.assertNotIn("0x80050000", out.getvalue())
            with patch.object(audit, "PRIVATE_ROOT", private):
                with redirect_stderr(err):
                    failure = audit.main(["--mem1", str(Path(d) / "outside.raw")])
            self.assertEqual(failure, 1)
            self.assertNotIn(str(d), err.getvalue())

    def test_unsupported_dump_formats_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported MEM1"):
            audit.audit(bytes(100))
        with self.assertRaisesRegex(ValueError, "unsupported MEM2"):
            audit.audit(fake_mem1(), bytes(4))


if __name__ == "__main__":
    unittest.main()
