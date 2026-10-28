"""Synthetic-only global source vs four roster and r31 input source tests."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_global_ball_roster_receiver_private as mod


def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)

def bl(pc,dest):
    return (18<<26)|((dest-pc)&0x03fffffc)|1

def fake_instruction_words():
    source={}
    for _name,pc,start in mod.prev.CALLS:
        for address in range(start,pc,4): source[address]=0x60000000
        source[start+8]=mr(31,3)
        source[pc-4]=mr(3,31)
        source[pc]=bl(pc,mod.prev.CACHE_WRITER_ENTRY)
    return source

def fake_roster(global_index=None):
    pm=0x90010000
    records=[pm+4+i*0xCC for i in range(4)]
    balls=[0x90020000+i*0x400 for i in range(4)]
    global_ptr=balls[global_index] if global_index is not None else 0x90030000
    memory={mod.roster.PLAYER_MANAGER_STATIC_CANDIDATE:pm}
    for rec,ball in zip(records,balls):
        memory[rec+0x88]=ball
        memory[ball+0x4C]=ball+0x30
    sample={"selected_index":0,"refs":{"ball":balls[0]}}
    return memory,sample,global_ptr,balls


class GlobalRosterAndR31(unittest.TestCase):
    def test_global_outside_four_source_players(self):
        memory,sample,global_ptr,balls=fake_roster()
        out=mod.roster_global_membership(memory.__getitem__,sample,global_ptr)
        self.assertTrue(out["global_matches_exactly_zero_player_slots"])
        self.assertFalse(out["global_matches_source_selected_slot"])
        self.assertFalse(out["global_matches_an_inactive_player_slot"])

    def test_global_equal_inactive_slot_classified(self):
        memory,sample,ptr,balls=fake_roster(global_index=2)
        out=mod.roster_global_membership(memory.__getitem__,sample,ptr)
        self.assertTrue(out["global_matches_an_inactive_player_slot"])
        self.assertFalse(out["global_matches_exactly_zero_player_slots"])

    def test_global_equal_selected_slot_classified(self):
        memory,sample,ptr,balls=fake_roster(global_index=0)
        out=mod.roster_global_membership(memory.__getitem__,sample,ptr)
        self.assertTrue(out["global_matches_source_selected_slot"])
        self.assertFalse(out["global_matches_an_inactive_player_slot"])

    def test_missing_fourth_roster_source_fails_closed(self):
        memory,sample,ptr,balls=fake_roster()
        del memory[0x90010004+3*0xCC+0x88]
        with self.assertRaises((KeyError,ValueError)):
            mod.roster_global_membership(memory.__getitem__,sample,ptr)

    def test_corrupt_source_ball_selfref_refuses(self):
        memory,sample,ptr,balls=fake_roster()
        memory[balls[1]+0x4C]=balls[1]+0x2C
        with self.assertRaises(ValueError):
            mod.roster_global_membership(memory.__getitem__,sample,ptr)

    def test_same_two_roster_pointers_refuses(self):
        memory,sample,ptr,balls=fake_roster()
        memory[0x90010004+2*0xCC+0x88]=balls[1]
        with self.assertRaises(ValueError):
            mod.roster_global_membership(memory.__getitem__,sample,ptr)

    def test_selected_pointer_mismatch_refuses(self):
        memory,sample,ptr,balls=fake_roster()
        sample["refs"]["ball"]=balls[1]
        with self.assertRaises(ValueError):
            mod.roster_global_membership(memory.__getitem__,sample,ptr)

    def test_receiver_r31_entry_r3_candidate_two_callers(self):
        memory=fake_instruction_words()
        out=mod.trace_r31_inputs(memory.__getitem__)
        self.assertEqual(len(out),2)
        self.assertTrue(all(x["r31_from_entry_r3_unambiguous_linear_candidate"] for x in out))
        self.assertTrue(all(x["first_observed_r31_assignment_class"]=="mr_r31_from_entry_r3_candidate" for x in out))
        self.assertTrue(all(not x["source_call_can_prove_runtime_receiver"] for x in out))

    def test_branch_before_first_r31_assignment_refuses_unambiguous(self):
        memory=fake_instruction_words()
        _,pc,start=mod.prev.CALLS[0]
        memory[start+4]=16<<26
        out=mod.trace_r31_inputs(memory.__getitem__)
        self.assertTrue(out[0]["first_assignment_after_branch_hazard"])
        self.assertFalse(out[0]["r31_from_entry_r3_unambiguous_linear_candidate"])

    def test_r31_second_write_not_unambiguous(self):
        memory=fake_instruction_words()
        _,pc,start=mod.prev.CALLS[1]
        memory[pc-8]=mr(31,5)
        out=mod.trace_r31_inputs(memory.__getitem__)
        self.assertGreater(out[1]["later_supported_r31_assignment_count"],0)
        self.assertFalse(out[1]["r31_from_entry_r3_unambiguous_linear_candidate"])

    def test_r31_unknown_function_not_promoted(self):
        memory=fake_instruction_words()
        _,pc,start=mod.prev.CALLS[0]
        memory[start+8]=0x60000000
        out=mod.trace_r31_inputs(memory.__getitem__)
        self.assertFalse(out[0]["r31_from_entry_r3_unambiguous_linear_candidate"])

    def test_invalid_callsite_refuses(self):
        memory=fake_instruction_words()
        _,pc,start=mod.prev.CALLS[0]
        memory[pc]=bl(pc,mod.prev.CACHE_WRITER_ENTRY+4)
        with self.assertRaises(ValueError):
            mod.trace_r31_inputs(memory.__getitem__)

    def test_shot_identity_mismatch_fails(self):
        samples={i:{"selected_index":0,"hole":1,
                  "refs":{"ball":1,"pin":2,"start":3,"scene_field":4}} for i in range(1,8)}
        samples[6]["refs"]["ball"]=6
        code={i:{"global_matches_exactly_zero_player_slots":True} for i in range(1,8)}
        with self.assertRaises(ValueError):
            mod.summarize(samples,code,[])

    def test_safe_output_no_private_roster_or_pointer(self):
        samples={i:{"selected_index":0,"hole":1,
                  "refs":{"ball":0x90000100,"pin":0x90000180,
                          "start":0x900001c0,"scene_field":0x90000200}} for i in range(1,8)}
        row={
            "four_player_slot_ball_pointers_source_validated":True,
            "global_matches_any_player_slot":False,
            "global_matches_source_selected_slot":False,
            "global_matches_an_inactive_player_slot":False,
            "global_matches_exactly_zero_player_slots":True,
        }
        code={i:dict(row) for i in range(1,8)}
        report=mod.summarize(samples,code,[])
        txt=json.dumps(report)
        self.assertTrue(report["wedge_source_global_outside_all_four_roster_balls"])
        self.assertFalse(report["r31_runtime_receiver_verified"])
        self.assertNotIn("0x90000100",txt)
        self.assertNotIn("90010000",txt)
        self.assertFalse(report["training_approved"])

    def test_isolated_cli_import(self):
        script=Path(mod.__file__)
        p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                         cwd=script.parents[2],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--dump-directory",p.stdout)


if __name__=="__main__":
    unittest.main()
