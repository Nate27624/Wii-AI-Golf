"""Fabricated-only native-free P0 authenticated receiver-chain integration tests."""
from __future__ import annotations
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_authenticated_receiver_chain_private as runner
import review_p0_outer_receiver_argument_source as outer


def lwz(rt,ra,disp):
    return (32 << 26) | (rt << 21) | (ra << 16) | (disp & 65535)


def row(label, offset="+0x020", distance=1):
    return {
        "outer_source_function_entry_label":label,
        "exact_direct_calls_found_within_window":1,
        "candidate_callsite_source_entry_offset":offset,
        "nearest_r3_definition_distance_words":distance,
        "nearest_supported_r3_definition_class":"gpr_load_r3_from_r13",
        "status":"SYNTAX_ONLY_NEEDS_CFG_AND_RUNTIME",
    }


def samples():
    return ([row(a[0]) for a in outer.SOURCES],
            [{
                "published_source_function":name,
                "status":"STATIC_ENTRY_R3_MUST_FLOW",
                "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3":True,
            } for name in ("fn_80299ACC","fn_80299C20")])


class ReceiverIntegrationTests(unittest.TestCase):
    def test_global_source_slot_requires_three_exact_rev1_ppc_forms(self):
        disp = -128
        addr = {
            runner.FIRST_SOURCE_PC:lwz(3,13,runner.FIELD_SDA_DISPLACEMENT),
            runner.GLOBAL_LOAD_PC:lwz(3,13,disp),
            runner.TRANSLATION_PC:lwz(3,3,0x4C),
        }
        base=0x80400000
        roster=SimpleNamespace(GOLF_FIELD_STATIC=base,
                               _bank=lambda p, size:"MEM1")
        got, imm = runner._source_global_slot(lambda pc:addr[pc],roster)
        self.assertEqual((got,imm),
                         (base-runner.FIELD_SDA_DISPLACEMENT+disp,disp))
        for pc in addr:
            original=addr[pc]
            addr[pc]=0
            with self.subTest(pc=pc):
                with self.assertRaises(ValueError):
                    runner._source_global_slot(lambda x:addr[x],roster)
            addr[pc]=original

    def test_mem1_static_global_slot_bounds_fail_closed(self):
        addr={
            runner.FIRST_SOURCE_PC:lwz(3,13,runner.FIELD_SDA_DISPLACEMENT),
            runner.GLOBAL_LOAD_PC:lwz(3,13,-16),
            runner.TRANSLATION_PC:lwz(3,3,0x4C),
        }
        roster=SimpleNamespace(GOLF_FIELD_STATIC=0x80400000,
                               _bank=lambda p,size:"MEM2")
        with self.assertRaises(ValueError):
            runner._source_global_slot(lambda pc:addr[pc],roster)

    def test_direct_global_r13_syntactic_candidate(self):
        outer_rows,inner_rows=samples()
        disp=-120
        entry=outer.SOURCES[0][1]
        read=lambda pc: lwz(3,13,disp) if pc==entry+0x1C else 0
        kind=runner._classification(outer_rows[0],read,disp,inner_rows[0])
        self.assertEqual(kind,"DIRECT_GLOBAL_R13_LOAD_SYNTAX_CANDIDATE")

    def test_roster_like_88_load_not_assigned_owner(self):
        outer_rows, inner_rows = samples()
        entry=outer.SOURCES[0][1]
        read=lambda pc: lwz(3,31,0x88) if pc==entry+0x1C else 0
        kind=runner._classification(outer_rows[0],read,-120,inner_rows[0])
        self.assertEqual(kind,"BALL_CHILD_OFFSET_0x88_UNOWNED_BASE_CANDIDATE")

    def test_wrong_disp_or_unknown_source_never_promoted(self):
        a,b=samples()
        entry=outer.SOURCES[0][1]
        read=lambda pc: lwz(3,13,-119) if pc==entry+0x1C else 0
        self.assertEqual(runner._classification(a[0],read,-120,b[0]),
                         "OTHER_OR_UNRESOLVED_GPR_R3_SOURCE")
        a[0]["nearest_r3_definition_distance_words"]=None
        self.assertEqual(runner._classification(a[0],read,-120,b[0]),
                         "UNRESOLVED_R3_INPUT")
        a[0]["exact_direct_calls_found_within_window"]=0
        self.assertEqual(runner._classification(a[0],read,-120,b[0]),
                         "UNRESOLVED_OUTER_CALLSITE")

    def test_all_native_roster_balls_distinct_from_global_pointer(self):
        pm=0x90001000
        stride=204
        recs=[pm+4+i*stride for i in range(4)]
        balls=[0x90002000+i*0x400 for i in range(4)]
        global_ball=0x90005000
        field_base=0x80400000
        slot=0x80400010
        mem={field_base:pm, pm+0x334:recs[0],slot:global_ball}
        for rec, ball in zip(recs,balls):
            mem[rec+0x88]=ball
            mem[ball+0x4C]=ball+0x30
        mem[global_ball+0x4C]=global_ball+0x30
        rd=SimpleNamespace(u32=lambda x:mem[x])
        roster=SimpleNamespace(ROSTER_STRIDE=stride,
                               PLAYER_MANAGER_STATIC_CANDIDATE=field_base,
                               _bank=lambda p,size:"MEM2")
        seven=SimpleNamespace(roster=roster,
                              _get=lambda rd:{"selected_index":0})
        r=runner._native_roster_global_gate(rd,seven,slot)
        self.assertTrue(r["source_global_ball_is_outside_four_roster_balls"])
        self.assertFalse(r["source_global_ball_equals_source_selected_ball"])
        mem[slot]=balls[1]
        r=runner._native_roster_global_gate(rd,seven,slot)
        self.assertFalse(r["source_global_ball_is_outside_four_roster_balls"])
        mem[slot]=balls[0]
        r=runner._native_roster_global_gate(rd,seven,slot)
        self.assertTrue(r["source_global_ball_equals_source_selected_ball"])

    def test_cloned_roster_ball_rejected(self):
        pm=0x90001000
        stride=204
        balls=[0x90002000,0x90002000,0x90003000,0x90004000]
        slot=0x80400010
        mem={0x80400000:pm,pm+0x334:pm+4,slot:0x90005000}
        for i, ball in enumerate(balls):
            mem[pm+4+i*stride+0x88]=ball
            mem[ball+0x4C]=ball+0x30
        mem[0x9000504C]=0x90005030
        rd=SimpleNamespace(u32=lambda p:mem[p])
        roster=SimpleNamespace(ROSTER_STRIDE=stride,
                               PLAYER_MANAGER_STATIC_CANDIDATE=0x80400000,
                               _bank=lambda p,size:"MEM2")
        with self.assertRaises(ValueError):
            runner._native_roster_global_gate(
                rd,SimpleNamespace(roster=roster,
                    _get=lambda x:{"selected_index":0}),slot)

    def test_synthesis_preserves_no_runtime_claim_even_when_static_both_succeed(self):
        a,b=samples()
        outer_r={"outer_call_windows":a}
        inner_r={"sources":b,"both_static_proofs_succeeded":True}
        code={}
        for i,(_,entry,*_) in enumerate(outer.SOURCES):
            code[entry+0x1C]=lwz(3,13,-120)
        out=runner.synthesize(outer_r,inner_r,
                             [{"all_four_source_roster_balls_valid_and_distinct":True,
                               "source_global_ball_is_outside_four_roster_balls":True} for _ in range(7)],
                             lambda pc:code[pc],-120)
        self.assertTrue(out["any_static_source_global_load_candidate"])
        self.assertTrue(out["both_inner_static_cfg_must_flow"])
        self.assertTrue(out["source_global_outside_four_roster_in_all_captures"])
        for key in ("selected_player_ball_as_runtime_receiver_verified",
                    "global_ball_as_runtime_receiver_verified",
                    "cache_writer_executed_in_captured_frame_verified",
                    "real_rendered_ball_xyz_or_velocity_verified",
                    "power_contact_score_outcome_verified",
                    "training_approved","allowed_to_publish"):
            self.assertFalse(out[key])
        payload=json.dumps(out)
        for word in ("0x90005000","0x80400010","-120","0x8029"):
            self.assertNotIn(word,payload)

    def test_incomplete_samples_abstain(self):
        a,b=samples()
        for native in ([],[{}],[{"all_four_source_roster_balls_valid_and_distinct":False}]*7):
            with self.assertRaises((ValueError,KeyError)):
                runner.synthesize({"outer_call_windows":a},
                                  {"sources":b},native,lambda pc:0,-120)

    def test_source_digest_rejects_invalid_word(self):
        regions=((0x80000000,0x80000008),)
        ok=runner._digest_code(lambda pc:0x60000000,regions)
        self.assertEqual(len(ok),32)
        for value in (-1,2**32,True,None):
            with self.assertRaises(ValueError):
                runner._digest_code(lambda pc:value,regions)

    def test_snapshot_runner_rechecks_canonical_before_and_after(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for n in runner.CAPTURES:
                for bank in (1,2):
                    (folder/f"{n}.{bank}.raw").write_bytes(b"mock")
            folders={n:folder for n in runner.CAPTURES}
            src=SimpleNamespace(_file=lambda folder,name,size:folder/name)
            rd=SimpleNamespace(u32=lambda pc:0x60000000)
            seven=SimpleNamespace(
                SIZE=(4,4),
                src=src,roster=SimpleNamespace(TwoBankReader=lambda *args:rd),
                _check_archive=lambda a:folders)
            cfg=SimpleNamespace(CALLERS=(("a",0x80299ACC,0x80299B64),
                                               ("b",0x80299C20,0x80299C58)),
                                inspect_known_callers=lambda read:{
                                   "sources":[]})
            with ExitStack() as stack:
                stack.enter_context(patch.object(runner,"_native_roster_global_gate",
                    return_value={"all_four_source_roster_balls_valid_and_distinct":True,
                                  "source_global_ball_is_outside_four_roster_balls":True}))
                stack.enter_context(patch.object(runner,"_source_global_slot",
                    return_value=(0x80400020,-120)))
                stack.enter_context(patch.object(runner,"_digest_code",
                    return_value=b"synthetic_digest"))
                stack.enter_context(patch.object(runner,"synthesize",
                    return_value={"kind":"SYNTHETIC_ONLY"}))
                with patch.object(seven,"_check_archive",side_effect=[folders,folders]) as check:
                    self.assertEqual(runner.analyze(folder,seven,cfg),
                                     {"kind":"SYNTHETIC_ONLY"})
                    self.assertEqual(check.call_count,2)
                with patch.object(seven,"_check_archive",
                                  side_effect=[folders,ValueError("tampered")]) as check:
                    with self.assertRaises(ValueError):
                        runner.analyze(folder,seven,cfg)
                    self.assertEqual(check.call_count,2)

if __name__=="__main__":
    unittest.main()
