"""Only fabricated PPC words; never read Wii RAM or ROM in CI."""
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_r31_opcode_classes_private as o


def d(op,rt=0,ra=0,disp=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&65535)


def x(xo,rs=0,ra=0,rb=0):
    return (31<<26)|(rs<<21)|(ra<<16)|(rb<<11)|(xo<<1)


def sample(at_1c00=0x60000000):
    words=[0x60000000]*13
    words[0]=x(444,rs=3,ra=31,rb=3)
    words[6]=at_1c00
    words[-1]=d(52,0,31,0x90)
    return b"".join(struct.pack(">I",w) for w in words)


class R31OpCodes(unittest.TestCase):
    def test_cmpi_and_cr_logic_not_gpr_writer(self):
        for word in (d(11,31,31,9),d(10,31,31,9),(19<<26)|(193<<1)):
            self.assertFalse(o.classify_gpr31(word)["r31_direct_instruction_write_confirmed"])
            self.assertFalse(o.classify_gpr31(word)["r31_gpr_write_possible_unknown"])

    def test_andi_targets_ra_not_rs(self):
        self.assertTrue(o.classify_gpr31(d(28,4,31,0xFF))["r31_direct_instruction_write_confirmed"])
        self.assertFalse(o.classify_gpr31(d(28,31,4,0xFF))["r31_direct_instruction_write_confirmed"])

    def test_mr_write_to_r31_and_unrelated_mr(self):
        self.assertTrue(o.classify_gpr31(x(444,3,31,3))["r31_direct_instruction_write_confirmed"])
        self.assertFalse(o.classify_gpr31(x(444,3,30,3))["r31_direct_instruction_write_confirmed"])

    def test_lfs_vs_lfsu_base_update(self):
        self.assertFalse(o.classify_gpr31(d(48,4,31,0x30))["r31_direct_instruction_write_confirmed"])
        self.assertTrue(o.classify_gpr31(d(49,4,31,0x30))["r31_direct_instruction_write_confirmed"])

    def test_stfs_and_stfsu(self):
        self.assertFalse(o.classify_gpr31(d(52,31,31,0x90))["r31_direct_instruction_write_confirmed"])
        self.assertTrue(o.classify_gpr31(d(53,4,31,0x90))["r31_direct_instruction_write_confirmed"])

    def test_lmw_overwrites_r31_and_stmw_does_not(self):
        self.assertTrue(o.classify_gpr31(d(46,5,31,0))["r31_direct_instruction_write_confirmed"])
        self.assertFalse(o.classify_gpr31(d(47,5,31,0))["r31_direct_instruction_write_confirmed"])

    def test_unknown_opcode_abstains(self):
        v=o.classify_gpr31(2<<26)
        self.assertTrue(v["r31_gpr_write_possible_unknown"])
        self.assertFalse(v["r31_direct_instruction_write_confirmed"])

    def test_unknown_extended_abstains(self):
        v=o.classify_gpr31(x(999,0,31,0))
        self.assertTrue(v["r31_gpr_write_possible_unknown"])

    def test_fabricated_slice_has_no_owner_promotion(self):
        report=o.analyze_window(sample())
        self.assertEqual(report["kind"],"S002-P0-R31-OPCODE-QUALIFIED-LOCAL-SLICE")
        self.assertEqual(report["target_site"],"+0x1C00")
        self.assertFalse(report["source_receiver_is_selected_player_record_verified"])
        self.assertFalse(report["approved_for_training"])

    def test_fabricated_target_is_recognized_gpr_write(self):
        report=o.analyze_window(sample(d(14,31,30,4)))
        self.assertTrue(report["target_r31_direct_write_confirmed"])

    def test_mutated_copy_store_and_bad_len_refused(self):
        for raw in (sample()[:-4],sample().replace(struct.pack(">I",x(444,3,31,3)),struct.pack(">I",0x60000000)),
                    sample()[:-4]+struct.pack(">I",d(52,1,31,0x90))):
            with self.assertRaises(ValueError):o.analyze_window(raw)

    def test_no_raw_memory_or_native_source_word_export(self):
        raw=json.dumps(o.analyze_window(sample(d(11,31,31,3))))
        self.assertNotIn("0x60000000",raw)
        self.assertNotIn("0x802A",raw)
        self.assertNotIn("ball-study",raw)

    def test_cli_bad_private_archive_redacted(self):
        error=io.StringIO()
        with contextlib.redirect_stderr(error):
            code=o.main(["--data-root","/missing","--private-session","SECRET_PATH"])
        self.assertEqual(code,2)
        self.assertNotIn("SECRET_PATH",error.getvalue())


if __name__=="__main__":
    unittest.main()
