"""No Dolphin: synthetic calibration, heldout, fail-closed and classifier tests."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from wii_ai_golf.inspector.a_button import AButtonStudy, SEQUENCE, classify


def record(held:bool, *, noisy:False=False):
    return tuple((17 if held else 8) if i in (29,37,39,40,42,44,46,48) else 42 for i in range(51))


def train(*, failed=None, moved=None, noisy=None):
    s=AButtonStudy()
    for n,phase in enumerate(SEQUENCE):
        s.arm((n+1)*10000)
        for j in range(3):
            h=phase.startswith('H')
            if phase==failed: h=not h
            row=list(record(h))
            if phase==noisy and j==1: row[29]=123
            source='stable' if phase!=moved else 'changed'
            s.observe(tuple(row),source,(1,2,3),(7,),(n+1)*10000+j)
    return s


class AStateTests(unittest.TestCase):
    def test_passes_seven_stage_repeats_and_heldout(self):
        s=train()
        self.assertTrue(s.verified)
        self.assertEqual(len(s.model),8)
        self.assertFalse(s.failure)
        self.assertEqual(s.predict(record(True),'stable',(1,2,3),(7,)),'UNKNOWN')
        self.assertEqual(s.predict(record(True),'stable',(1,2,3),(7,)),'PRESSED')
        self.assertEqual(s.predict(record(False),'stable',(1,2,3),(7,)),'UNKNOWN')
        self.assertEqual(s.predict(record(False),'stable',(1,2,3),(7,)),'RELEASED')

    def test_wrong_heldout_abstains(self):
        self.assertFalse(train(failed='H2').verified)

    def test_persistent_latch_abstains(self):
        s=AButtonStudy()
        for n,phase in enumerate(SEQUENCE):
            s.arm((n+1)*1000)
            for j in range(3): s.observe(record(phase!='R0'),'owner',(1,2,3),(5,),(n+1)*1000+j)
        self.assertFalse(s.verified)

    def test_source_aim_or_ball_changed_abstains(self):
        for field in ('source','ball','aim'):
            s=AButtonStudy();s.arm(2000)
            s.observe(record(False),'owner',(1,2,3),(5,),2000)
            args={'source':'owner','ball':(1,2,3),'aim':(5,)}
            args[field]={'source':'other','ball':(1,2,4),'aim':(6,)}[field]
            s.observe(record(False),args['source'],args['ball'],args['aim'],2001)
            self.assertFalse(s.verified)
            self.assertTrue(s.failure)

    def test_no_premature_or_stale_sampling(self):
        s=AButtonStudy();s.arm(2000)
        self.assertIn('waiting',s.observe(record(False),'owner',(1,2,3),(5,),1999))
        self.assertEqual(s.windows['R0'],[])
        self.assertIn('waiting',s.observe(None,'owner',(1,2,3),(5,),2000))
        self.assertIn('1/3',s.observe(record(False),'owner',(1,2,3),(5,),2001))
        with self.assertRaises(ValueError):s.arm(2002)

    def test_invalid_or_discordant_records_unknown(self):
        s=train()
        self.assertEqual(classify(tuple([999]*51),s.model),'UNKNOWN')
        self.assertEqual(classify(None,s.model),'UNKNOWN')
        v=list(record(True));v[29]=8
        self.assertEqual(classify(tuple(v),s.model),'UNKNOWN')
        self.assertEqual(s.predict(record(True),'other',(1,2,3),(7,)),'UNKNOWN')
        self.assertEqual(s.predict(record(True),'stable',(1,2,3),(7,)),'UNKNOWN')

    def test_stale_reset_model_is_empty(self):
        s=train();s.invalidate('operator reset')
        self.assertEqual(s.predict(record(True),'stable',(1,2,3),(7,)),'UNKNOWN')
        self.assertFalse(s.verified)

if __name__=='__main__':unittest.main()
