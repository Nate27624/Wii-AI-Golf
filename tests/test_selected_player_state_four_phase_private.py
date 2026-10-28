"""Fabricated source/PPC and four-phase selected-player state tests."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

import audit_selected_player_state_four_phase_private as study
import audit_golf_two_bank_roster_private as roster
from test_selected_ball_start_link_private import fixture
from test_golf_two_bank_roster_private import dform, mr


def synthetic_reader(words):
    def read(addr):
        if (roster.PLAYER_MANAGER_CODE[0] <= addr < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= addr < 0x802A2210
                or 0x80290B44 <= addr < 0x80294184):
            return words.get(addr, 0)
        if addr not in words:
            raise ValueError("Undefined synthetic source word")
        return words[addr]
    return read


def fake(stage_value=1):
    words,refs=fixture()
    words[0x8029F0C0]=mr(29,3)
    for load, store, literal, reg in study.WRITES:
        words[load]=dform(14,0,0,literal)
        words[store]=dform(36,0,reg,0x24)
    selected=refs["pm"]+4
    words[selected+0x24]=stage_value
    return study._one(synthetic_reader(words),b"RSPE01\x00\x01"),words,refs


def four(*values):
    values=values or (1,1,1,1)
    return [fake(v)[0] for v in values]


def changed():
    return [{"MEM1":True,"MEM2":True} for _ in range(3)]


class SelectedPlayerStateStudyTests(unittest.TestCase):
    def test_static_source_gate_and_idle_state(self):
        x=fake()[0]
        self.assertTrue(x[0]["source_five_literal_write_patterns_match_rev1"])
        self.assertTrue(x[0]["raw_state_in_source_written_literal_set"])
        self.assertEqual(x[1]["value"],1)
        result=study.summarize_four(four(),changed(),
                                    visible_aim=True,same_session=True)
        self.assertTrue(result["selected_player_state_word_stable_in_no_shot"])
        self.assertTrue(result[
            "source_current_start_and_ball_candidate_stable_in_no_shot"])
        self.assertTrue(result["all_three_transitions_have_distinct_both_banks"])
        self.assertFalse(result["state_word_semantics_verified"])
        self.assertFalse(result["training_allowed"])

    def test_source_state_changes_during_aim_only_is_not_labeled_aim_enum(self):
        result=study.summarize_four(four(1,1,2,2),changed(),
                                    visible_aim=True,same_session=True)
        self.assertTrue(result["selected_player_state_word_changed_during_aim"])
        self.assertFalse(result["selected_player_state_word_stable_in_no_shot"])
        self.assertTrue(result["source_current_start_and_ball_candidate_stable_in_no_shot"])
        self.assertFalse(result["state_word_semantics_verified"])
        self.assertFalse(result["shot_or_ball_motion_recorded"])

    def test_unknown_numeric_state_is_reported_without_clamping(self):
        result=study.summarize_four(four(99,99,99,99),changed())
        self.assertEqual(result["observed_value_in_source_literal_set"],
                         [False]*4)
        self.assertTrue(result["selected_player_state_word_stable_in_no_shot"])
        self.assertFalse(result["state_word_runtime_writer_PC_observed"])

    def test_pinned_source_rejects_corrupted_literal_load(self):
        (_,words,refs)=fake()
        words[0x8029F1BC]=dform(14,0,0,8)
        read = synthetic_reader(words)
        with self.assertRaises(ValueError):
            study._one(read,b"RSPE01\x00\x01")

    def test_pinned_source_rejects_corrupted_register_or_offset(self):
        for pc, alt in [
            (0x8029F0C0,mr(28,3)),
            (0x8029F0CC,dform(36,0,29,0x24)),
            (0x8029F1C0,dform(36,0,29,0x28))
        ]:
            (pair,words,refs)=fake()
            words[pc]=alt
            read = synthetic_reader(words)
            with self.subTest(pc=pc),self.assertRaises(ValueError):
                study._one(read,b"RSPE01\x00\x01")

    def test_non_rev1_scene_fails_source_gate(self):
        pair,words,refs=fake()
        read = synthetic_reader(words)
        with self.assertRaises(ValueError):
            study._one(read,b"RSPE01\x00\x00")
        words[refs["config"]+0x94]=3
        with self.assertRaises(ValueError):
            study._one(read,b"RSPE01\x00\x01")

    def test_selected_record_switch_does_not_masquerade_as_state_change(self):
        records=four()
        altered=(dict(records[3][0]),dict(records[3][1]))
        altered[1]["selected_index"]=1
        records[3]=altered
        with self.assertRaises(ValueError):
            study.summarize_four(records,changed())

    def test_hole_switch_is_rejected(self):
        records=four()
        altered=(dict(records[1][0]),dict(records[1][1]))
        altered[1]["hole"]=3
        records[1]=altered
        with self.assertRaises(ValueError):
            study.summarize_four(records,changed())

    def test_unverified_bool_bank_provenance_is_rejected(self):
        changes=changed()
        changes[0]["MEM2"]="True"
        with self.assertRaises(ValueError):
            study.summarize_four(four(),changes)

    def test_incomplete_pair_count_rejected(self):
        with self.assertRaises(ValueError):
            study.summarize_four(four()[:3],changed())
        with self.assertRaises(ValueError):
            study.summarize_four(four(),changed()[:2])

    def test_no_raw_values_pointers_paths_or_writes_in_summary(self):
        output=json.dumps(study.summarize_four(four(99,99,3,3),changed()),
                          sort_keys=True)
        for forbidden in ('"value":', '"ball":', '"record":', '"start":',
                          "0x91000000", "raw_hex", "Dolphin Emulator",
                          "mem2.raw", "mem1.raw", "raw_state_value"):
            self.assertNotIn(forbidden,output)
        self.assertFalse(json.loads(output)["allowed_to_publish"])

    def test_false_aim_or_session_provenance_never_promotes_training(self):
        for aim,session in [(False,False),(True,False),(False,True)]:
            report=study.summarize_four(four(),changed(),
                                        visible_aim=aim,same_session=session)
            self.assertFalse(report["training_allowed"])
            self.assertFalse(report["phase_labels_independently_verified"])

    def test_non_differing_memory_banks_do_not_become_confirmed_clock(self):
        changes=changed()
        changes[2]={"MEM1":False,"MEM2":False}
        report=study.summarize_four(four(),changes(),
                                    visible_aim=True,same_session=True)
        self.assertFalse(report["all_three_transitions_have_distinct_both_banks"])

if __name__=="__main__":
    unittest.main()
