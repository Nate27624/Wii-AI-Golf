"""Offline synthetic PPC opcode gates only; never native/game execution."""
import struct
import sys
import types
import unittest
from pathlib import Path

# Use a deliberately minimal preflight stub to test source-operand logic
# without touching private original bank files or filesystem discovery.
stub = types.ModuleType("audit_p0_localops_rev1_study")
class Abstain(Exception):
    def __init__(self, code):
        self.code = code
stub.Abstain = Abstain
sys.modules.setdefault("audit_p0_localops_rev1_study", stub)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_p0_native_transfer_sources_private as study

def direct_bl(pc, target):
    return (18 << 26) | ((target-pc) & 0x03fffffc) | 1

def dform(op, fr, base, disp):
    return (op << 26) | (fr << 21) | (base << 16) | (disp & 0xffff)

class TestNativeTransferSources(unittest.TestCase):
    def blank(self, kind):
        return {w: bytearray(w[1]-w[0]) for w in study.WINDOWS[kind]}
    def set_pc(self, blocks, pc, word):
        lo, hi = next(r for r in blocks if r[0] <= pc < r[1])
        struct.pack_into(">I", blocks[lo,hi], pc-lo, word)

    def test_wind_direct_call_and_candidate(self):
        blocks = self.blank("wind")
        self.set_pc(blocks, 0x8029128C, direct_bl(0x8029128C,0x802B8728))
        self.set_pc(blocks, 0x80298FF0, dform(48,1,29,0x84))
        result = study.analyze_source("wind",blocks)
        self.assertTrue(result["target_presence"]["0x802B8728"])
        self.assertEqual(result["field_counts"]["lfs"],1)
        self.assertEqual(result["wind_reaches_selected_ball_velocity"],"UNKNOWN")

    def test_kcol_direct_call_and_candidate(self):
        blocks = self.blank("contact")
        self.set_pc(blocks, 0x802974B0, direct_bl(0x802974B0,0x802A3DE4))
        self.set_pc(blocks, 0x802974B4, dform(52,2,30,0x78))
        result = study.analyze_source("contact",blocks)
        self.assertTrue(result["target_presence"]["0x802A3DE4"])
        self.assertEqual(result["field_counts"]["stfs"],1)
        self.assertEqual(result["query_radius_is_ball_radius"],"UNPROVEN")

    def test_branch_without_link_is_not_call(self):
        word = direct_bl(0x8029128C,0x802B8728)
        self.assertIsNone(study.direct_bl(0x8029128C,word & ~1))

    def test_negative_signed_displacement(self):
        self.assertEqual(study.signed16(dform(48,1,2,-20)),-20)

    def test_missing_source_windows_fail(self):
        with self.assertRaises(KeyError):
            study.analyze_source("wind",{})

    def test_bad_stage_abstains(self):
        with self.assertRaises(study.source.Abstain):
            study.analyze_source("unsupported",{})

    def test_never_promotes_selected_ball_or_training(self):
        for kind in study.WINDOWS:
            row = study.analyze_source(kind,self.blank(kind))
            self.assertFalse(row["source_register_receiver_proven"])
            self.assertFalse(row["same_selected_ball_execution_proven"])
            self.assertFalse(row["native_kcol_collision_parity"])
            self.assertFalse(row["training_approved"])

if __name__ == "__main__":
    unittest.main()
