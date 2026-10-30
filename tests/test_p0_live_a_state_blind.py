"""Synthetic-only no-Dolphin tests for blind live A-state study."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

# Use the real source-gated reader imports; never poison sys.modules in full CI.
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import p0_live_a_state_blind as module

class FakeRPC:
    def __init__(self,words):
        self.words = words
        self.calls = []
    def call(self,method,params):
        self.calls.append((method,params))
        assert method=='memory.read_u32'
        return self.words[(params[0]-0x90010000)//4]

def phase(phase,flag):
    return [dict(phase=phase, record=tuple(1 if i==7 and flag else
                                         0 if i==7 else 0x40000000 if i==37 else
                                         0x100 if i==38 else 0 for i in range(51)))
            for _ in range(3)]

def learned(*,latch=False, withheld_fail=False):
    w={}
    for key,held in module.CALIBRATION:
        flag=held
        if latch and key!='R0': flag=True
        if withheld_fail and key=='H2': flag=False
        w[key]=phase(key,flag)
    return w

class StudyTests(unittest.TestCase):
    def test_positive_repeated_withheld_live_classification(self):
        w=learned();model,rep=module.choose_model(w)
        self.assertTrue(rep['inference_enabled'])
        self.assertIn('+0x1C',rep['candidate_offsets_hex'])
        self.assertEqual(module.predict(phase('B',True),model),'PRESSED')
        self.assertEqual(module.predict(phase('B',False),model),'RELEASED')
    def test_latched_through_release_must_abstain(self):
        model,rep=module.choose_model(learned(latch=True))
        self.assertEqual(model,[])
        self.assertFalse(rep['inference_enabled'])
        self.assertEqual(module.predict(phase('B',True),model),'UNKNOWN')
    def test_withheld_failure_disables_all_predictions(self):
        model,rep=module.choose_model(learned(withheld_fail=True))
        self.assertEqual(model,[])
        self.assertEqual(rep['heldout']['H2']['prediction'],'RELEASED')
        self.assertFalse(rep['heldout_pass'])
    def test_within_phase_jitter_disqualifies_offset(self):
        w=learned()
        rows=list(w['H0']);rows[2]=dict(rows[2],record=tuple(
            17 if i==7 else v for i,v in enumerate(rows[2]['record'])))
        w['H0']=rows
        model,rep=module.choose_model(w)
        self.assertFalse(rep['inference_enabled'])
    def test_ambiguous_observed_word_abstains(self):
        model,_=module.choose_model(learned())
        rows=phase('B',False)
        rows=[dict(r,record=tuple(123 if i==7 else v for i,v in enumerate(r['record']))) for r in rows]
        self.assertEqual(module.predict(rows,model),'UNKNOWN')
    def test_record_read_is_readonly_bounded(self):
        rpc=FakeRPC(tuple(range(51)))
        got=module.hex_record(rpc,0x90010000)
        self.assertEqual(got,tuple(range(51)))
        self.assertEqual(len(rpc.calls),51)
        self.assertTrue(all(m=='memory.read_u32' for m,_ in rpc.calls))
    def test_source_scene_and_ball_changes_abstain(self):
        fake_event={'identity':tuple(range(14)),
                    'words':{'selected_ball_plus_0x30':(4,5,6),
                            'aim_candidate_plus_0x3c':(7,)},
                    'start_ns':1,'frame_bracket':(1,2)}
        with patch.object(module.source,'packet',return_value=fake_event):
            with self.assertRaisesRegex(module.Abstain,'SOURCE_IDENTITY_CHANGED'):
                module.capture(FakeRPC(tuple(range(51))),'B',0,tuple(range(13)),None,None)
            with self.assertRaisesRegex(module.Abstain,'BALL_MOVED'):
                module.capture(FakeRPC(tuple(range(51))),'B',0,tuple(range(14)),(1,2,3),None)
            with self.assertRaisesRegex(module.Abstain,'AIM_MOVED'):
                module.capture(FakeRPC(tuple(range(51))),'B',0,tuple(range(14)),None,(99,))
if __name__=='__main__':unittest.main()
