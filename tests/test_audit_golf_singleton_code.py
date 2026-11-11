"""Synthetic DOL fixtures; no copyrighted executable bytes in tests."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "singleton_code", ROOT / "scripts" / "audit_golf_singleton_code.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(shared=True):
    dol = bytearray(0x1800)
    struct.pack_into(">I", dol, 0x00, 0x100)       # first text section file offset
    struct.pack_into(">I", dol, 0x48, 0x80184000)  # first text section virtual address
    struct.pack_into(">I", dol, 0x90, 0x1600)      # size
    for index, (name, (address, _size)) in enumerate(mod.TARGETS.items()):
        displacement = -0x1C if shared else (-0x1C - 0x10 * index)
        word = (32 << 26) | (3 << 21) | (13 << 16) | (displacement & 0xFFFF)
        struct.pack_into(">I", dol, 0x100 + address - 0x80184000, word)
    return bytes(dol)


class SingletonCodeTests(unittest.TestCase):
    def test_shared_sda_load_across_three_source_backed_functions(self):
        result = mod.analyze(fixture())
        self.assertEqual(len(result["shared_r13_displacements"]), 1)
        candidate = result["shared_r13_displacements"][0]
        self.assertEqual(candidate["sda_displacement"], "-0x1C")
        self.assertEqual(candidate["independent_callsite_count"], 3)
        self.assertIsNone(result["scene_manager_singleton_storage_address"])
        self.assertFalse(result["runtime_pointer_verified"])

    def test_no_common_load_means_no_address_guess(self):
        report = mod.analyze(fixture(shared=False))
        self.assertEqual(report["shared_r13_displacements"], [])
        self.assertIsNone(report["scene_manager_singleton_storage_address"])

    def test_ppc_lwz_must_use_r13(self):
        wrong = (32 << 26) | (3 << 21) | (12 << 16) | 0x14
        self.assertEqual(mod.load_references(struct.pack(">I", wrong)), set())

    def test_negative_sda_displacement_is_signed(self):
        word = (32 << 26) | (4 << 21) | (13 << 16) | 0xFFFC
        self.assertEqual(mod.load_references(struct.pack(">I", word)), {-4})

    def test_source_range_outside_section_is_rejected(self):
        data = bytearray(fixture())
        struct.pack_into(">I", data, 0x90, 0x100)
        with self.assertRaisesRegex(ValueError, "not mapped"):
            mod.analyze(bytes(data))

    def test_data_region_is_not_accepted_as_executable(self):
        data = bytearray(fixture())
        struct.pack_into(">I", data, 0x90, 0)          # remove text section
        struct.pack_into(">I", data, 0x1C, 0x100)      # first data section file offset
        struct.pack_into(">I", data, 0x64, 0x80184000) # data mapped over symbols
        struct.pack_into(">I", data, 0xAC, 0x1600)
        with self.assertRaisesRegex(ValueError, "not mapped"):
            mod.analyze(bytes(data))

    def test_malformed_dol_header_fails_closed(self):
        with self.assertRaises(ValueError):
            mod.analyze(b"not a dol")
        data = bytearray(fixture())
        struct.pack_into(">I", data, 0x00, 0xFFFFFFF0)
        with self.assertRaisesRegex(ValueError, "section bounds"):
            mod.analyze(bytes(data))

    def test_cli_on_synthetic_dol_without_memory_or_network(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "fake-main.dol"
            local.write_bytes(fixture())
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(mod.main(["--dol", str(local)]), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["kind"], "offline_rev1_scene_singleton_code_reference_triage")
            self.assertNotIn(str(local), output.getvalue())
            self.assertNotIn("0x80184000", output.getvalue())


if __name__ == "__main__":
    unittest.main()
