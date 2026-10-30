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


    def test_target_offset_filter(self):
        source=words(d(38,3,4,0x34),d(52,1,31,0xC0))
        for off, expected in ((0x34,"stb"),(0xC0,"stfs")):
            out=scan.describe_player(source,PC,10,1,off)
            self.assertEqual(out["matching_access_total"],1)
            self.assertEqual(out["sites_in_report"][0]["access"],expected)
        with self.assertRaises(scan.prior.Abstain):
            scan.describe_player(source,PC,10,1,0x42)


    def test_source_map_config_bc_not_claimed_as_player(self):
        code=words(d(36,4,31,0xBC))
        out=scan.describe_player(code,0x8029ca4c,5,1,0xBC,scan.CONFIG)
        self.assertEqual(out["unit"],scan.CONFIG)
        self.assertEqual(out["matching_access_total"],1)
        self.assertEqual(out["sites_in_report"][0]["field_offset_hypothesis"],"+0x0BC")
        self.assertFalse(out["sites_in_report"][0]["receiver_proven"])
        with self.assertRaises(scan.prior.Abstain):
            scan.describe_player(code,0x8029ca4c,5,1,0xBC,"UNKNOWN_UNIT")


    def test_ppc_li_not_addi_r0(self):
        self.assertEqual(scan.decode(PC,d(14,0,0,0),PC,PC+16),"li r0,+0")
        self.assertEqual(scan.decode(PC,d(14,3,0,1),PC,PC+16),"li r3,+1")
        self.assertEqual(scan.decode(PC,d(14,3,3,1),PC,PC+16),"addi r3,r3,+1")

    def test_two_adjacent_flag_bytes_extract_constant_pair(self):
        # The original source has analogous pairs in RPGolPlayer.
        raw=words(d(14,3,0,1),d(14,0,0,0),
                  d(38,3,31,0x34),d(38,0,31,0x35))
        pairs=scan.flag_pair_summary(struct.unpack(">4I",raw))
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs[0]["store_34_local_li_or_unknown"],1)
        self.assertEqual(pairs[0]["store_35_local_li_or_unknown"],0)
        self.assertFalse(pairs[0]["dpad_state_or_club_index_verified"])

    def test_reverse_pair_zero_one_and_unknown_input(self):
        raw=words(d(14,3,0,0),d(14,0,0,1),
                  d(38,3,31,0x34),d(14,3,0,1),
                  d(38,0,31,0x35))
        row=scan.flag_pair_summary(struct.unpack(">5I",raw))[0]
        self.assertEqual((row["store_34_local_li_or_unknown"],
                          row["store_35_local_li_or_unknown"]),(0,1))
        incoming=words(d(14,0,0,0),d(38,4,3,0x35),d(38,0,3,0x34))
        row=scan.flag_pair_summary(struct.unpack(">3I",incoming))[0]
        self.assertEqual(row["store_34_local_li_or_unknown"],0)
        self.assertIsNone(row["store_35_local_li_or_unknown"])

    def test_config_16_slot_counted_loop(self):
        seq=words(d(32,6,3,0xBC),d(14,0,6,1),
                  d(36,0,3,0xBC),d(32,0,3,0xBC),
                  d(11,0,0,16),0x41800008)
        matches=scan.counted_loop_summary(struct.unpack(">6I",seq))
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["observed_compare_bound"],16)
        self.assertFalse(matches[0]["selected_club_semantics_verified"])

    def test_no_false_positive_for_non_loop(self):
        seq=words(d(32,6,3,0xBC),d(14,0,6,1),
                  d(36,0,3,0xBC),d(32,0,3,0xBC),
                  d(11,0,0,4),0x41800008)
        self.assertFalse(scan.counted_loop_summary(struct.unpack(">6I",seq)))

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
