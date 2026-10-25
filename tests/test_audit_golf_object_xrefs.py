"""Synthetic, license-safe tests for bounded Rev1 golf module xrefs."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
from io import StringIO
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "golf_object_xrefs", ROOT / "scripts" / "audit_golf_object_xrefs.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _dform(op, rd, ra, offset):
    return (op << 26) | (rd << 21) | (ra << 16) | (offset & 0xFFFF)


def _bl(src, dest):
    delta = dest - src
    assert delta % 4 == 0 and -(1 << 25) <= delta < (1 << 25)
    return (18 << 26) | (delta & 0x03FFFFFC) | 1


def fixture(*, add_edges=True, add_data=True):
    text_size = sum(end-start for (start, end), _ in mod.MODULES.values())
    data_size = sum(end-start for _, (start, end) in mod.MODULES.values())
    dol = bytearray(0x100 + text_size + data_size)
    locs = {}
    offset = 0x100
    for idx, (name, (code, data)) in enumerate(mod.MODULES.items()):
        code_start, code_end = code
        length = code_end - code_start
        struct.pack_into(">I", dol, idx * 4, offset)
        struct.pack_into(">I", dol, 0x48 + idx * 4, code_start)
        struct.pack_into(">I", dol, 0x90 + idx * 4, length)
        locs[name] = (offset, code_start, length)
        offset += length
    data_locs = {}
    for idx, (name, (_, segment)) in enumerate(mod.MODULES.items()):
        data_start, data_end = segment
        length = data_end - data_start
        struct.pack_into(">I", dol, 0x1C + idx * 4, offset)
        struct.pack_into(">I", dol, 0x64 + idx * 4, data_start)
        struct.pack_into(">I", dol, 0xAC + idx * 4, length)
        data_locs[name] = offset
        offset += length

    def instruction(module, local, word):
        file_offset, text_start, length = locs[module]
        assert local % 4 == 0 and local + 4 <= length
        struct.pack_into(">I", dol, file_offset + local, word)

    main_start = mod.MODULES["RPGolMain"][0][0]
    player_start = mod.MODULES["RPGolPlayer"][0][0]
    manager_start = mod.MODULES["RPGolPlayerManager"][0][0]
    if add_edges:
        instruction("RPGolMain", 0, _bl(main_start, manager_start + 0x20))
        instruction("RPGolPlayerManager", 0,
                    _bl(manager_start, player_start + 0x40))
    instruction("RPGolMain", 4, _dform(32, 4, 3, 0x34))
    instruction("RPGolMain", 8, _dform(36, 5, 3, 0x40))
    instruction("RPGolMain", 12, _dform(32, 5, 1, 0x70))  # stack, not r3
    instruction("RPGolMain", 16, _dform(32, 5, 3, -4))    # signed negative
    instruction("RPGolMain", 20, 0x4E800421)               # indirect bctrl
    instruction("RPGolPlayerManager", 4, _dform(48, 1, 3, 0x28))
    instruction("RPGolPlayer", 0, _dform(32, 6, 3, 0x30))
    if add_data:
        struct.pack_into(">I", dol, data_locs["RPGolMain"], main_start)
        struct.pack_into(">I", dol, data_locs["RPGolPlayer"], player_start)
        struct.pack_into(">I", dol, data_locs["RPGolPlayerManager"] + 4,
                         manager_start)
    return bytes(dol)


class GolfObjectXrefTests(unittest.TestCase):
    def test_two_bounded_cross_unit_direct_branch_edges(self):
        result = mod.analyze(fixture())
        edges = {(x["caller_unit"], x["callee_unit"]): x
                 for x in result["direct_cross_unit_calls"]}
        self.assertEqual(
            set(edges), {("RPGolMain", "RPGolPlayerManager"),
                         ("RPGolPlayerManager", "RPGolPlayer")})
        self.assertEqual(edges[("RPGolMain", "RPGolPlayerManager")]["direct_bl_count"], 1)
        self.assertTrue(all(not edge["ownership_or_class_identity_proven"]
                            for edge in edges.values()))

    def test_r3_member_candidates_are_not_verified_this(self):
        report = mod.analyze(fixture())
        hints = report["r3_relative_memory_operand_hints"]
        main = [v for v in hints if v["code_unit"] == "RPGolMain"]
        self.assertEqual({v["r3_relative_displacement"] for v in main},
                         {"+0x034", "+0x040"})
        self.assertTrue(all(v["receiver_identity"] == "unverified_r3_base"
                            for v in main))
        self.assertTrue(all(v["within_four_instructions_of_other_unit_bl"] == 1
                            for v in main))
        self.assertFalse(report["confirmed_player_or_club_member_offsets"])

    def test_code_pointer_shaped_data_is_not_confirmed_vtable(self):
        report = mod.analyze(fixture())
        main = report["source_data_function_pointer_hints"]["RPGolMain"]
        self.assertEqual(main["aligned_code_pointers_by_target_unit"][0]["count"], 1)
        self.assertEqual(main["aligned_code_pointers_by_target_unit"][0]
                         ["data_relative_word_offsets"], ["+0x000"])
        self.assertFalse(main["exact_vtable_start_or_dynamic_type_verified"])

    def test_no_direct_edges_does_not_invent_object_ownership(self):
        result = mod.analyze(fixture(add_edges=False))
        self.assertEqual(result["direct_cross_unit_calls"], [])
        self.assertEqual(result["code_unit_counts"]["RPGolMain"]
                         ["direct_other_unit_bl_count"], 0)
        self.assertFalse(result["confirmed_rpgolmain_instance_type"])

    def test_wrong_or_dynamic_branch_not_direct_call(self):
        start = mod.MODULES["RPGolMain"][0][0]
        target = mod.MODULES["RPGolPlayerManager"][0][0]
        word = _bl(start, target)
        self.assertEqual(mod._branch_target(start, word), target)
        self.assertIsNone(mod._branch_target(start, word & ~1))  # b, not bl
        self.assertIsNone(mod._branch_target(start, word | 2))   # absolute bla
        self.assertIsNone(mod._branch_target(start, 0x4E800421))  # bctrl

    def test_signed_backward_call_to_player(self):
        start = mod.MODULES["RPGolPlayerManager"][0][0]
        target = mod.MODULES["RPGolPlayer"][0][0] + 0x40
        self.assertEqual(mod._branch_target(start, _bl(start, target)), target)

    def test_negative_displacement_and_stack_do_not_count(self):
        report = mod.analyze(fixture())
        offsets = [v["r3_relative_displacement"]
                   for v in report["r3_relative_memory_operand_hints"]]
        self.assertNotIn("-0x004", offsets)
        self.assertNotIn("+0x070", offsets)

    def test_missing_documented_data_segment_fails_closed(self):
        dol = bytearray(fixture())
        struct.pack_into(">I", dol, 0xAC, 0)  # remove first data section
        with self.assertRaisesRegex(ValueError, "data range not mapped"):
            mod.analyze(bytes(dol))

    def test_missing_code_segment_fails_closed(self):
        dol = bytearray(fixture())
        struct.pack_into(">I", dol, 0x90, 0)
        with self.assertRaisesRegex(ValueError, "range not mapped"):
            mod.analyze(bytes(dol))

    def test_cli_uses_private_dol_and_does_not_echo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PRIVATE-DONT-SHARE-main.dol"
            path.write_bytes(fixture())
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(mod.main(["--dol", str(path)]), 0)
            text = out.getvalue()
            report = json.loads(text)
            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["kind"],
                             "offline_rev1_golf_object_code_xref_triage")
            self.assertNotIn(str(path), text)
            self.assertNotIn("PRIVATE-DONT-SHARE", text)
            self.assertFalse(report["disc_revision_independently_verified"])
            self.assertFalse(report["confirmed_golf_power_address"])

    def test_malformed_private_dol_cli_redacts_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret-ROM-path.dol"
            path.write_bytes(b"bad")
            err = StringIO()
            with redirect_stderr(err):
                self.assertEqual(mod.main(["--dol", str(path)]), 1)
            self.assertNotIn("secret-ROM-path", err.getvalue())
            self.assertIn("incompatible private Rev1 DOL", err.getvalue())

    def test_json_contains_no_raw_dol_bytes(self):
        output = json.dumps(mod.analyze(fixture()))
        self.assertNotIn("bytes_hex", output)
        self.assertNotIn("raw_dol", output)
        self.assertNotIn("power_verified\": true", output.lower())


if __name__ == "__main__":
    unittest.main()
