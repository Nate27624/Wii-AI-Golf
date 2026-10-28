"""Synthetic-only GetWind source table gates. No private ROM/RAM fixtures."""
from __future__ import annotations

import importlib.util
from io import StringIO
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.audit.golf_wind_table import (
    WIND_DIRECTION_TABLE, WIND_SPEED_TABLE, WIND_SLOTS, audit_wind_source_tables,
)

spec = importlib.util.spec_from_file_location(
    "wind_cli", ROOT / "scripts" / "audit_golf_wind_table_private.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def put(mem, base, addr, value):
    struct.pack_into(">I", mem, addr - base, value)


def fake_banks():
    mem1 = bytearray(0x4BF8D4)
    mem2 = bytearray(0x6000)
    mem1[:8] = b"RSPE01\x00\x01"
    for addr, value in {
        0x804BF4D8: 0x80001000,  # manager singleton slot
        0x804BF4DC: 0,           # no second manager candidate
        0x804BF8C4: 0x90001000,  # golf config
        0x804BF868: 0x90001100,  # field
        0x804BF8D0: 0x90001200,  # player manager
        0x80001018: 5,           # manager active scene id
        0x8000100C: 0x90000100,
    }.items():
        put(mem1, 0x80000000, addr, value)
    for addr, value in {
        0x9000011C: 5,
        0x90000120: 0x80001000,
        0x90000154: 2,
        0x9000019C: 0x90000300,
        0x90001094: 4,          # hitting the green
        0x90001098: 1,          # index, NOT display hole number
        0x9000113C: 6,          # pin count
        0x90001148: 31,         # start count
    }.items():
        put(mem2, 0x90000000, addr, value)
    for i, raw in enumerate([0, 2, 4, 6, 8, 10, 12, 14, 16]):
        put(mem1, 0x80000000, WIND_DIRECTION_TABLE + 4*i, raw)
    for i, raw in enumerate([0, 0, 4, 4, 0, 1, 1, 0, 0]):
        put(mem1, 0x80000000, WIND_SPEED_TABLE + 4*i, raw)
    return mem1, mem2


class GetWindSourceTests(unittest.TestCase):
    def test_read_only_shape_and_distinct_entries(self):
        a, b = fake_banks()
        before = (bytes(a), bytes(b))
        got = audit_wind_source_tables(a, b, strict_size=False)
        self.assertEqual(before, (bytes(a), bytes(b)))
        self.assertEqual(got["table_slots_read"], WIND_SLOTS)
        self.assertEqual(got["direction_table_distinct_raw_word_count"], 9)
        self.assertEqual(got["speed_table_distinct_raw_word_count"], 3)
        self.assertEqual(got["direction_table_nonzero_word_count"], 8)
        self.assertEqual(got["speed_table_nonzero_word_count"], 4)
        self.assertTrue(got["selected_direction_raw_word_nonzero"])
        self.assertFalse(got["selected_speed_raw_word_nonzero"])
        self.assertFalse(got["approved_for_model_training"])
        self.assertFalse(got["same_emulated_frame_pair_verified"])

    def test_current_hole_index_selects_only_that_table_entry(self):
        a, b = fake_banks()
        put(b, 0x90000000, 0x90001098, 2)
        got = audit_wind_source_tables(a, b, strict_size=False)
        self.assertTrue(got["selected_speed_raw_word_nonzero"])
        self.assertTrue(got["selected_direction_raw_word_nonzero"])
        self.assertFalse(got["raw_hole_index_exposed"])

    def test_out_of_bounds_index_rejected_without_wrap_or_clamping(self):
        for bad in (9, 0xFFFFFFFF):
            a, b = fake_banks()
            put(b, 0x90000000, 0x90001098, bad)
            with self.assertRaisesRegex(ValueError, "nine-slot"):
                audit_wind_source_tables(a, b, strict_size=False)

    def test_wrong_mode_and_disc_revision_fail_source_gate(self):
        a, b = fake_banks()
        put(b, 0x90000000, 0x90001094, 3)
        with self.assertRaises(ValueError):
            audit_wind_source_tables(a, b, strict_size=False)
        a, b = fake_banks()
        a[7] = 2
        with self.assertRaises(ValueError):
            audit_wind_source_tables(a, b, strict_size=False)

    def test_missing_scene_backlink_is_not_accepted(self):
        a, b = fake_banks()
        put(b, 0x90000000, 0x90000120, 0x80002000)
        with self.assertRaises(ValueError):
            audit_wind_source_tables(a, b, strict_size=False)

    def test_constant_zero_tables_are_shape_valid_not_semantics(self):
        a, b = fake_banks()
        for i in range(WIND_SLOTS):
            put(a, 0x80000000, WIND_DIRECTION_TABLE + 4*i, 0)
            put(a, 0x80000000, WIND_SPEED_TABLE + 4*i, 0)
        got = audit_wind_source_tables(a, b, strict_size=False)
        self.assertTrue(got["speed_raw_all_entries_equal"])
        self.assertEqual(got["speed_table_nonzero_word_count"], 0)
        self.assertFalse(got["runtime_gameplay_wind_verified"])

    def test_stdout_schema_has_no_private_wind_values_or_addresses(self):
        a, b = fake_banks()
        result = json.dumps(audit_wind_source_tables(a, b, strict_size=False))
        for secret in ("0x804A8B54", "0x90001000",
                       "raw_wind_integer_values\": [", "speed_mph",
                       "wind_direction_degrees"):
            self.assertNotIn(secret, result)
        self.assertIn('"raw_wind_integer_values_exposed": false', result)

    def test_cli_missing_private_file_error_redacts_paths(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "SECRET-0x81234560-mem1.raw"
            err = StringIO()
            with redirect_stderr(err):
                code = cli.main(["--mem1", str(path), "--mem2", str(path),
                                 "--private-root", td])
            self.assertEqual(code, 1)
            self.assertNotIn(td, err.getvalue())
            self.assertNotIn("0x81234560", err.getvalue())


if __name__ == "__main__":
    unittest.main()
