"""Synthetic-only passive A detection: no operator windows, controller or Dolphin."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector.a_live import LiveAIndicator, PUBLISHED_OFFSETS


def record(held=False, partial=False):
    words=[3]*51
    for i,o in enumerate(PUBLISHED_OFFSETS):
        words[o//4]=100+i+(100 if held and (not partial or i%2==0) else 0)
    return tuple(words)


class AutoAReadTests(unittest.TestCase):
    def test_auto_init_and_observe_held_released(self):
        detector=LiveAIndicator()
        kwargs={'source':'owner1','ball':(1,2,3),'aim':(5,)}
        self.assertEqual(detector.observe(record(),**kwargs),'UNKNOWN')
        self.assertEqual(detector.observe(record(),**kwargs),'RELEASED')
        self.assertEqual(detector.observe(record(True),**kwargs),'UNKNOWN')
        self.assertEqual(detector.observe(record(True),**kwargs),'PRESSED')
        self.assertEqual(detector.observe(record(),**kwargs),'UNKNOWN')
        self.assertEqual(detector.observe(record(),**kwargs),'RELEASED')

    def test_partial_changes_fail_closed(self):
        detector=LiveAIndicator();ctx={'source':'owner','ball':(1,2,3),'aim':(5,)}
        detector.observe(record(),**ctx);detector.observe(record(),**ctx)
        self.assertEqual(detector.observe(record(True,partial=True),**ctx),'UNKNOWN')
        self.assertEqual(detector.observe(record(True,partial=True),**ctx),'UNKNOWN')
        self.assertIn('partial',detector.mode)

    def test_actor_swap_and_aim_movement_resets_baseline(self):
        d=LiveAIndicator();ctx={'source':'owner','ball':(1,2,3),'aim':(5,)}
        d.observe(record(),**ctx);d.observe(record(),**ctx)
        d.observe(record(True),**ctx)
        self.assertEqual(d.observe(record(True),**{**ctx,'source':'other'}),'UNKNOWN')
        self.assertTrue(d.blocked)
        self.assertEqual(d.observe(record(True),**{**ctx,'aim':(6,)}),'UNKNOWN')

    def test_invalid_reading_never_produces_press(self):
        d=LiveAIndicator()
        self.assertEqual(d.observe(None,'x',(1,2,3),(4,)),'UNKNOWN')
        self.assertEqual(d.observe(tuple([False]*51),'x',(1,2,3),(4,)),'UNKNOWN')
        self.assertEqual(d.observe(record(),None,(1,2,3),(4,)),'UNKNOWN')

    def test_no_buttons_or_hardcoded_private_words(self):
        source=(ROOT/'src/wii_ai_golf/inspector/a_live.py').read_text()
        self.assertIn('PUBLISHED_OFFSETS',source)
        self.assertNotIn('rpc.call(',source)
        self.assertNotIn('controller.',source)

if __name__=='__main__':unittest.main()
