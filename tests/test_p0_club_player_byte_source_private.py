"""Synthetic bounded PPC Golf Player source contexts; never contacts Dolphin."""
import importlib.util
from pathlib import Path
import struct
import unittest

P = Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_club_player_byte_source_private.py"
spec = importlib.util.spec_from_file_location("club_player_source", P)
import sys
sys.path.insert(0, str(P.parent))
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

PC = 0x8029e62c
def words(*v):
    return struct.pack(">"+"I"*len(v), *v)
def d(op, rs=3, ra=3, imm=0):
    return (op<<26)|(rs<<21)|(ra<<16)|(imm & 65535)

class TestPlayerClubSource(unittest.TestCase):
    def test_byte_store_target_with_nearby_source(self):
        out=scan.describe_player(words(d(14,3,0,2),d(11,3,0,2),
                                        d(38,3,4,0x34),0x4e800020),PC,3,2)
        self.assertEqual(out["matching_access_total"],1)
        row=out["sites_in_report"][0]
        self.assertEqual(row["site"],"+0x00008")
        self.assertEqual(row["access"],"stb")
        self.assertEqual(row["base_register"],"r4")
        self.assertTrue(any(line["is_target"] for line in row["context"]))
        self.assertFalse(row["receiver_proven"])

    def test_fp_store_hypothesis(self):
        out=scan.describe_player(words(d(52,1,31,0xC0)),PC,5,2)
        self.assertEqual(out["sites_in_report"][0]["access"],"stfs")
        self.assertEqual(out["sites_in_report"][0]["stored_or_loaded_register"],"f1")

    def test_load_and_store_distinct(self):
        out=scan.describe_player(words(d(34,4,3,0x34),d(38,4,3,0x34)),PC,5,1)
        self.assertEqual(out["matching_access_total"],2)
        self.assertEqual(sorted(r["access"] for r in out["sites_in_report"]),["lbz","stb"])

    def test_stack_and_unrelated_excluded(self):
        out=scan.describe_player(words(d(38,3,1,0x34),d(36,3,0,0x34),
                                        d(36,3,4,0x18)),PC,5,1)
        self.assertEqual(out["matching_access_total"],0)

    def test_relative_ppc_branch(self):
        s=scan.decode(PC,0x48000004,PC,PC+16)
        self.assertEqual(s,"b +0x00004")
        self.assertEqual(scan.decode(PC,0x4e800020,PC,PC+16),"blr")

    def test_signed_immediate(self):
        self.assertIn("-1",scan.decode(PC,d(14,3,3,-1),PC,PC+16))

    def test_bad_native_window_abstains(self):
        with self.assertRaises(scan.prior.Abstain):
            scan.describe_player(b"\x00",PC)
        with self.assertRaises(scan.prior.Abstain):
            scan.describe_player(words(d(38,3,4,0x34)),PC,0)

    def test_typed_gates_not_evidence(self):
        out=scan.describe_player(words(d(38,3,4,0x34)),PC,1)
        self.assertFalse(out["native_selected_club_field_verified"])
        self.assertFalse(out["pc_or_runtime_execution_verified"])
        self.assertFalse(out["training_approved"])

if __name__=="__main__":
    unittest.main()
