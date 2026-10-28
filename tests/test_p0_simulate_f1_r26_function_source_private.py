"""Native-free tests for published fn_8029B57C r26 code-origin P0 probe."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_simulate_f1_r26_function_source_private as target

START = target.UNIT_START
ENTRY = target.FUNCTION_ENTRY
CALL = target.CALL_PC
STORE = target.STORE_PC
NOP = 0x60000000


def d(op, rt, ra, immediate=0):
    return (op << 26) | (rt << 21) | (ra << 16) | (immediate & 0xffff)


def bl(pc, dest, link=True):
    disp = dest-pc
    assert -(1 << 25) <= disp < (1 << 25) and disp % 4 == 0
    return (18 << 26) | (disp & 0x03fffffc) | int(link)


def mr(dst, src):
    return (31 << 26) | (src << 21) | (dst << 16) | (src << 11) | (444 << 1)


def program(changes=()):
    code = bytearray(NOP.to_bytes(4, "big") * 1024)
    words = {CALL: bl(CALL, target.previous.f1.DISTANCE),
             STORE: d(52, 1, 26, 0)}
    words.update(dict(changes))
    for pc, word in words.items():
        offset = pc - START
        code[offset:offset+4] = word.to_bytes(4, "big")
    return bytes(code)


def inspect(changes=()):
    return target.inspect(program(changes), START, target.UNIT)


class R26SourceTests(unittest.TestCase):
    def test_unassigned_r26_is_not_fabricated(self):
        result = inspect()
        self.assertEqual(result["source_prefix_instructions"], 19)
        self.assertEqual(result["r26_syntactic_write_count"], 0)
        self.assertEqual(result["r26_last_syntactic_definition"],
                         "INCOMING_R26_UNRESOLVED")
        self.assertFalse(result["r26_runtime_base_object_or_pointer_verified"])

    def test_mr_r26_r3_from_published_function_prefix(self):
        result = inspect(((ENTRY + 0x10, mr(26, 3)),))
        self.assertEqual(result["r26_last_syntactic_definition"], "mr_from_r3")
        self.assertEqual(result["r26_last_write_source_relative"], "+0x0034C")
        self.assertEqual(result["source_stfs_f1_zero_r26_verified"], True)
        self.assertFalse(result["callee_preservation_or_all_path_r26_flow_verified"])

    def test_lwz_r26_struct_offset_from_r29(self):
        result = inspect(((ENTRY + 0x14, d(32, 26, 29, 0x88)),))
        self.assertEqual(result["r26_last_syntactic_definition"],
                         "integer_load_from_r29_offset_+136")

    def test_conservative_store_update_Ra_clobber(self):
        result = inspect(((ENTRY + 0x10, mr(26, 3)),
                          (ENTRY + 0x14, d(37, 2, 26, 0x10))))
        self.assertEqual(result["r26_last_syntactic_definition"],
                         "memory_update_base_write_untyped")
        self.assertEqual(result["r26_syntactic_write_count"], 2)

    def test_conservative_lmw_range_clobber(self):
        result = inspect(((ENTRY + 0x10, mr(26, 3)),
                          (ENTRY + 0x14, d(46, 19, 1, 4))))
        self.assertEqual(result["r26_last_syntactic_definition"],
                         "lmw_GPR_range_overwrite")

    def test_lmw_above_r26_does_not_touch_r26(self):
        result = inspect(((ENTRY + 0x10, mr(26, 3)),
                          (ENTRY + 0x14, d(46, 27, 1, 4))))
        self.assertEqual(result["r26_last_syntactic_definition"], "mr_from_r3")

    def test_control_hazard_after_nearest_r26_write(self):
        result = inspect(((ENTRY + 0x08, mr(26, 4)),
                          (ENTRY + 0x10, bl(ENTRY + 0x10, ENTRY + 0x30, False))))
        self.assertEqual(result["control_transfers_after_last_r26_definition"], 1)
        self.assertEqual(result["source_prefix_control_transfer_count"], 1)
        self.assertFalse(result["callee_preservation_or_all_path_r26_flow_verified"])

    def test_other_bl_hazard_without_claiming_r26_clobber(self):
        result = inspect(((ENTRY + 0x08, mr(26, 4)),
                          (ENTRY + 0x10, bl(ENTRY + 0x10, 0x8029B2FC))))
        self.assertEqual(result["source_prefix_other_direct_calls_seen"], 1)
        self.assertEqual(result["r26_last_syntactic_definition"], "mr_from_r4")

    def test_exact_distance_and_store_must_be_unchanged(self):
        for pc, word in ((CALL, bl(CALL, target.previous.f1.DISTANCE+4)),
                         (STORE, d(52, 1, 25, 0)),
                         (STORE, d(52, 1, 26, 4)),
                         (STORE, d(54, 1, 26, 0))):
            with self.subTest(pc=pc, word=word):
                with self.assertRaises(ValueError):
                    inspect(((pc, word),))

    def test_wrong_public_source_unit_fails(self):
        with self.assertRaises(ValueError):
            target.inspect(program(), START, "OtherSource.o")
        with self.assertRaises(ValueError):
            target.inspect(program(), START+4, target.UNIT)

    def test_malformed_source_and_unknown_word_refused(self):
        with self.assertRaises(ValueError):
            target.inspect(program()[:-1], START, target.UNIT)
        with self.assertRaises(ValueError):
            target._write_class(-1, 26)

    def test_no_private_memory_or_verified_physics_in_output(self):
        report = inspect(((ENTRY + 8, mr(26, 3)),))
        public = str(report)
        self.assertNotIn("B0-MEM1.bin", public)
        self.assertNotIn("checkpoint-manifest-PRIVATE", public)
        self.assertNotIn("0x900", public)
        for key in ("r26_runtime_base_object_or_pointer_verified",
                    "real_squared_distance_or_UI_result_verified",
                    "physical_ball_world_XYZ_velocity_impact_power_score_verified",
                    "same_guest_frame_or_execution_verified",
                    "training_approved",
                    "allowed_to_publish"):
            self.assertFalse(report[key])

    def test_native_gate_precedes_source_reads(self):
        with patch.object(target.base, "checked_private_b0",
                          side_effect=target.base.UntrustedInput):
            with self.assertRaises(target.base.UntrustedInput):
                target.audit(Path("missing"), Path("Wii-AI-Golf-Data"))

    def test_cli_isolated_help(self):
        script = Path(target.__file__).resolve()
        r = subprocess.run([sys.executable, "-I", str(script), "--help"],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--baseline", r.stdout)


if __name__ == "__main__":
    unittest.main()
