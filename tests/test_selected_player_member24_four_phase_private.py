"""Only synthetic source words, record values and phase summaries."""
import json
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))
import audit_selected_player_member24_four_phase_private as mod
from test_selected_ball_start_link_private import fixture
from test_golf_two_bank_roster_private import dform,mr


def make(word=1):
    w,refs=fixture()
    w[mod.RECEIVER_SITE]=mr(29,3)
    for li,stw,n,base in mod.LITERAL_AND_STORE:
        w[li]=dform(14,0,0,n)
        w[stw]=dform(36,0,base,0x24)
    w[refs["pm"]+4+mod.STATE_MEMBER]=word
    return w,refs


def reader(words):
    def read(addr):
        if 0x80200000<=addr<0x80300000:
            return words.get(addr,0)
        return words[addr]
    return read


def one(word=1):
    words,_=make(word)
    return mod.inspect_one(reader(words),b"RSPE01\x00\x01")


def bank_changes():
    return [{"MEM1":True,"MEM2":True} for _ in range(3)]


class SourceMember24Tests(unittest.TestCase):
    def test_source_opcode_and_selected_record_gate(self):
        words,_=make()
        self.assertTrue(mod.source_write_sites_match(reader(words)))
        self.assertTrue(mod.inspect_one(reader(words),b"RSPE01\x00\x01")["in_written_literal_set"])

    def test_stable_no_shot_is_not_gameplay_state(self):
        out=mod.summarize_state_controls([one(2) for _ in range(4)],bank_changes(),
                aim_visibly_moved=True,operator_same_session=True)
        self.assertTrue(out["record_member24_stable_across_all_four_no_shot_phases"])
        self.assertEqual(out["record_member24_distinct_word_class_count"],1)
        self.assertTrue(out["null_control_source_ball_triplets_stable"])
        self.assertFalse(out["candidate_is_gameplay_phase_state_verified"])
        self.assertFalse(out["training_approved"])

    def test_change_during_aim_not_a_hit(self):
        out=mod.summarize_state_controls([one(1),one(1),one(3),one(1)],
                                          bank_changes(),aim_visibly_moved=True,
                                          operator_same_session=True)
        self.assertEqual([x["word_changed"] for x in out["record_member24_changes_by_transition"]],
                         [False,True,True])
        self.assertFalse(out["impact_or_landing_event_verified"])
        self.assertFalse(out["swing_power_verified"])

    def test_unknown_word_is_not_coerced_to_state_enum(self):
        out=mod.summarize_state_controls([one(9) for _ in range(4)],bank_changes())
        self.assertEqual(out["record_member24_in_known_code_literal_set_by_phase"],
                         [False]*4)

    def test_wrong_store_register_blocks(self):
        words,_=make()
        words[0x8029F138]=dform(36,0,30,0x24)
        self.assertFalse(mod.source_write_sites_match(reader(words)))
        with self.assertRaises(ValueError):
            mod.inspect_one(reader(words),b"RSPE01\x00\x01")

    def test_wrong_literal_or_receiver_blocks(self):
        words,_=make()
        words[0x8029F0C8]=dform(14,0,0,99)
        self.assertFalse(mod.source_write_sites_match(reader(words)))
        words,_=make()
        words[mod.RECEIVER_SITE]=mr(30,3)
        self.assertFalse(mod.source_write_sites_match(reader(words)))

    def test_wrong_disc_or_manager_selector_blocks(self):
        words,refs=make()
        with self.assertRaises(ValueError):
            mod.inspect_one(reader(words),b"RSPE01\x00\x00")
        words,refs=make()
        words[refs["pm"]+0x334]+=4
        with self.assertRaises(ValueError):
            mod.inspect_one(reader(words),b"RSPE01\x00\x01")

    def test_word_or_membership_corruption_rejected(self):
        samples=[one() for _ in range(4)]
        samples[2]["state_word"]="1"
        with self.assertRaises(ValueError):
            mod.summarize_state_controls(samples,bank_changes())
        samples=[one() for _ in range(4)]
        samples[2]["in_written_literal_set"]=False
        with self.assertRaises(ValueError):
            mod.summarize_state_controls(samples,bank_changes())

    def test_phase_count_and_bank_count_rejected(self):
        with self.assertRaises(ValueError):
            mod.summarize_state_controls([one() for _ in range(3)],bank_changes())
        with self.assertRaises(ValueError):
            mod.summarize_state_controls([one() for _ in range(4)],bank_changes()[:2])

    def test_output_redaction_and_false_semantics(self):
        out=mod.summarize_state_controls([one(0xDEAD1234) for _ in range(4)],
                                          bank_changes())
        body=json.dumps(out)
        for word in ("dead1234","DEAD1234","0x910","runtime_pointer",
                     '"state_word"', "mem1.raw","private-root"):
            self.assertNotIn(word,body)
        self.assertFalse(out["allowed_to_publish"])
        self.assertFalse(out["ball_world_xyz_verified"])

    def test_cli_missing_dir_redacted(self):
        err=StringIO()
        with redirect_stderr(err):
            self.assertEqual(mod.main(["--private-root","PRIVATE-SECRET-DIRECTORY"]),1)
        self.assertNotIn("PRIVATE-SECRET",err.getvalue())


if __name__=="__main__":
    unittest.main()
