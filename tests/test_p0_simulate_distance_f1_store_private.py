"""Fabricated PPC source-only gates for ONE original source distance f1 stfs."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_simulate_distance_f1_store_private as target

PC = target.CALL_PC
UNIT = target.UNIT_NAME
BASE = target.UNIT_START


def d(op, rt, ra, imm=0):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 65535)


def b(pc, dest, lk=1):
    disp = dest - pc
    assert disp % 4 == 0 and -(1 << 25) <= disp < (1 << 25)
    return (18 << 26) | (disp & 0x03FFFFFC) | lk


def example(edits=(), ra=1, imm=16):
    words = {
        PC: b(PC, target.f1.DISTANCE),
        PC + 4: d(52, 1, ra, imm),
    }
    words.update(dict(edits))
    buffer = bytearray(b"\x60\x00\x00\x00" * 1000)
    for address, word in words.items():
        pos = address - BASE
        buffer[pos:pos+4] = word.to_bytes(4, "big")
    return bytes(buffer)


def inspect(edits=(), ra=1, imm=16):
    return target.inspect_local(example(edits, ra, imm), BASE, UNIT)


class OneDistanceF1StoreTests(unittest.TestCase):
    def test_stack_r1_store_is_not_proof_of_runtime_local(self):
        x = inspect()
        self.assertEqual(x["source_store_base_register"], "r1")
        self.assertEqual(x["source_store_base_class"], "STACK_POINTER_R1_SYNTAX")
        self.assertEqual(x["source_store_signed_D_form_displacement"], 16)
        self.assertEqual(x["exact_f1_stfs_public_source_relative"], "+0x0038C")
        self.assertFalse(x["destination_is_stack_local_verified"])
        self.assertFalse(x["squared_distance_ball_to_target_or_units_verified"])

    def test_nonstack_gpr_field_offset_is_syntax_only(self):
        x = inspect(ra=29, imm=0xB4)
        self.assertEqual(x["source_store_base_class"], "NONSTACK_GPR_BASE_UNTYPED")
        self.assertEqual(x["source_store_base_register"], "r29")
        self.assertEqual(x["source_store_signed_D_form_displacement"], 180)
        self.assertFalse(x["destination_is_golf_ball_field_verified"])

    def test_negative_signed_field(self):
        x = inspect(ra=31, imm=-20)
        self.assertEqual(x["source_store_signed_D_form_displacement"], -20)

    def test_zero_base_is_absolute_syntax_not_pointer(self):
        x = inspect(ra=0, imm=32)
        self.assertEqual(x["source_store_base_class"], "ZERO_BASE_ABSOLUTE_OFFSET_SYNTAX")

    def test_nearest_pre_call_base_write_source(self):
        x = inspect(edits=((PC - 8, d(14, 29, 30, 12)),),
                    ra=29)
        self.assertEqual(x["nearest_pre_call_base_syntactic_write"],
                         "ADDI_OR_ADDIS_FROM_r30")
        self.assertFalse(x["destination_is_golf_ball_field_verified"])

    def test_branch_barrier_invalidates_pre_call_base_writer(self):
        x = inspect(edits=((PC - 16, d(14, 29, 30, 12)),
                           (PC - 8, b(PC - 8, PC - 4, 0))), ra=29)
        self.assertEqual(x["nearest_pre_call_base_syntactic_write"], target.UNKNOWN)
        self.assertTrue(x["pre_call_source_control_barrier_seen"])

    def test_other_PPC_ra_and_lmw_possible_clobbers(self):
        for word, expected in [
            (d(26, 21, 29, 0), "LOGICAL_Ra_DEST_UNKNOWN_VALUE"),
            (d(46, 2, 20, 0), "LMW_RANGE_OVERWRITE"),
            (d(37, 22, 29, 0), "MEMORY_UPDATE_BASE_WRITE"),
        ]:
            with self.subTest(expected=expected):
                x = inspect(edits=((PC - 8, d(14, 29, 30, 12)),
                                   (PC - 4, word)), ra=29)
                self.assertEqual(x["nearest_pre_call_base_syntactic_write"], expected)

    def test_nonlinked_and_wrong_direct_call_fail(self):
        for word in (b(PC, target.f1.DISTANCE, 0),
                     b(PC, target.f1.DISTANCE + 4)):
            with self.subTest(word=word), self.assertRaises(ValueError):
                inspect(((PC, word),))

    def test_no_earlier_float_or_branch_before_f1_store(self):
        for word in (b(PC + 4, PC + 12, 0),
                     d(48, 1, 31, 4),
                     d(63, 2, 0, 0)):
            with self.subTest(word=word), self.assertRaises(ValueError):
                inspect(((PC + 4, word), (PC + 8, d(52, 1, 29, 36))))

    def test_wrong_fpr_store_or_wrong_source_unit_fails(self):
        with self.assertRaises(ValueError):
            inspect(((PC + 4, d(52, 2, 1, 4)),))
        with self.assertRaises(ValueError):
            target.inspect_local(example(), BASE, "Untrusted/Other.o")

    def test_no_private_native_memory_or_promoted_claims_in_output(self):
        x = inspect(ra=29, imm=56)
        dumped = json.dumps(x)
        for private in ("0x900", "checkpoint-manifest", "B0-MEM1",
                        "0x8029B5C8", "0xC0000000"):
            self.assertNotIn(private, dumped)
        self.assertFalse(x["store_executed_in_any_shot_verified"])
        self.assertFalse(x["training_approved"])
        self.assertFalse(x["allowed_to_publish"])

    def test_original_b0_sha_gate_blocks_code_reader(self):
        with patch.object(target.base, "checked_private_b0",
                          side_effect=target.base.UntrustedInput):
            with self.assertRaises(target.base.UntrustedInput):
                target.audit(Path("unknown"), Path("Wii-AI-Golf-Data"))

    def test_python_isolated_cli_help(self):
        script = Path(target.__file__)
        p = subprocess.run([sys.executable, "-I", str(script), "--help"],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--baseline", p.stdout)


if __name__ == "__main__":
    unittest.main()
