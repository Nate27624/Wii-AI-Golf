"""Fabricated PPC r4/r30 source writer tests; native-free and privacy-safe."""
from __future__ import annotations
from pathlib import Path
import sys
import json
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_outer_operand_r4_r30_source as h
NOP=0x60000000

def mr(d,s):
    return (31<<26)|(s<<21)|(d<<16)|(s<<11)|(444<<1)

def bl(pc,d):
    return (18<<26)|((d-pc)&0x3fffffc)|1

def dform(op,rt,ra,imm=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)

def mock():
    memory={}
    for _,entry,target,source in h.SOURCES:
        memory[entry+0x14]=mr(source,3)  # note: entry r3 may not persist to here
        memory[entry+0x18]=mr(3,source)
        memory[entry+0x20]=bl(entry+0x20,target)
    return memory

def run(m):
    return h.analyze(lambda pc:m.get(pc,NOP))

class OperandPPC(unittest.TestCase):
    def test_simple_r4_r30_mr_sources_are_only_candidates(self):
        result=run(mock())
        self.assertEqual(len(result["outer_operand_source_rows"]),2)
        for r in result["outer_operand_source_rows"]:
            self.assertEqual(r["exact_inner_bl_in_bounded_0x100_window_count"],1)
            self.assertTrue(r["mr_r3_from_expected_operand_confirmed"])
            self.assertEqual(r["nearest_pre_mr_operand_write_class"],"mr_from_r3")
            self.assertEqual(r["status"],"SOURCE_SYNTAX_CANDIDATE_NOT_CFG_PROOF")
            self.assertFalse(r["all_path_reaching_definition_verified"])
        self.assertFalse(result["real_receiver_global_or_player_ball_verified"])

    def test_control_transfer_before_operand_is_flagged(self):
        d=mock()
        entry=h.SOURCES[0][1]
        d[entry+0x04]=16<<26
        r=run(d)["outer_operand_source_rows"][0]
        self.assertEqual(r["status"],"SOURCE_SYNTAX_CANDIDATE_WITH_CONTROL_HAZARD")
        self.assertTrue(r["control_transfer_before_mr"])

    def test_intervening_call_after_operand_is_flagged(self):
        d=mock()
        entry=h.SOURCES[0][1]
        d[entry+0x16 if False else entry+0x1C]=bl(entry+0x1C,entry+0x60)
        r=run(d)["outer_operand_source_rows"][0]
        self.assertEqual(r["status"],"ABSTAIN_MR_R3_MAY_BE_CLOBBERED_AFTER_MOVE")

    def test_operand_memory_load_and_undecoded_xform(self):
        d=mock()
        entry=h.SOURCES[1][1]
        d[entry+0x14]=dform(32,30,1,0x90)
        r=run(d)["outer_operand_source_rows"][1]
        self.assertEqual(r["nearest_pre_mr_operand_write_class"],"integer_load_base_r1")
        d[entry+0x14]=(31<<26)|(30<<21)|(9<<16)|(10<<11)|(266<<1)
        r=run(d)["outer_operand_source_rows"][1]
        self.assertEqual(r["nearest_pre_mr_operand_write_class"],"unknown_X_form_write_or_operand")
        self.assertEqual(r["status"],"SOURCE_SYNTAX_CANDIDATE_WITH_CONTROL_HAZARD")

    def test_operand_update_base_and_lmw_are_writes_not_stmw(self):
        self.assertEqual(h._source_write(dform(37,0,4,16),4),
                         "update_base_register_written")
        self.assertEqual(h._source_write(dform(46,2,1,16),4),
                         "lmw_range_load_candidate")
        self.assertIsNone(h._source_write(dform(47,4,1,16),4))
        self.assertEqual(h._source_write(dform(24,4,30,0),30),
                         "rotate_or_logic_immediate_ra_writer")
        self.assertIsNone(h._source_write(dform(36,4,1,16),4))

    def test_operand_no_supported_definition_abstains(self):
        d=mock()
        entry=h.SOURCES[0][1]
        del d[entry+0x14]
        self.assertEqual(run(d)["outer_operand_source_rows"][0]["status"],
                         "ABSTAIN_NO_SUPPORTED_OPERAND_DEFINITION")

    def test_expected_mr_mismatch_and_clobber_fail(self):
        d=mock()
        entry=h.SOURCES[0][1]
        d[entry+0x18]=mr(3,30)
        self.assertEqual(run(d)["outer_operand_source_rows"][0]["status"],
                         "ABSTAIN_EXPECTED_MR_R3_NOT_LAST_MOVE")
        d=mock(); d[entry+0x1c]=dform(32,3,31,0)
        self.assertEqual(run(d)["outer_operand_source_rows"][0]["status"],
                         "ABSTAIN_MR_R3_MAY_BE_CLOBBERED_AFTER_MOVE")

    def test_exact_single_call_required(self):
        d=mock();entry,target=h.SOURCES[0][1:3]
        del d[entry+0x20]
        self.assertEqual(run(d)["outer_operand_source_rows"][0]["status"],
                         "ABSTAIN_AMBIGUOUS_OR_OUT_OF_WINDOW_INNER_CALL")
        d=mock();d[entry+0x24]=bl(entry+0x24,target)
        self.assertEqual(run(d)["outer_operand_source_rows"][0]["exact_inner_bl_in_bounded_0x100_window_count"],2)

    def test_invalid_word_and_no_reader_rejected(self):
        d=mock()
        for bad in (-1,2**32,None,3.4,True):
            d[h.SOURCES[0][1]]=bad
            with self.assertRaises(ValueError):run(d)
        with self.assertRaises(ValueError):h.analyze(None)

    def test_report_contains_no_private_words_addresses(self):
        result=json.dumps(run(mock()),sort_keys=True)
        for secret in ("0x8029B43C","0x80299ACC","0x8029A204","0x80299C20",
                       "0x900","PRIVATE_WORDS"):
            self.assertNotIn(secret,result)
        self.assertFalse(json.loads(result)["training_approved"])
        self.assertFalse(json.loads(result)["allowed_to_publish"])

if __name__=="__main__":
    unittest.main()
