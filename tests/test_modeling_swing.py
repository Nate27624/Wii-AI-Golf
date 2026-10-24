import math
import unittest
from wii_ai_golf.modeling.swing import AXES,SwingProfile,swing_trace,trace_hash

class SwingTests(unittest.TestCase):
    def test_four_phases(self):
        t=swing_trace(SwingProfile())
        self.assertEqual(len(t),59)
        self.assertEqual(t[0],[True,0.,0.,0.,0.,0.,0.,0.])
        self.assertEqual(t[12][:4],[True,0.,-1.,0.])
        self.assertEqual(t[27][:4],[True,0.,1.,0.])
        self.assertEqual(t[-1],[False,0.,0.,0.,0.,0.,0.,0.])

    def test_all_axes_within_integrator_bounds(self):
        for axis in AXES:
            for s in swing_trace(SwingProfile(axis=axis)):
                self.assertIs(type(s[0]),bool)
                self.assertEqual(len(s),8)
                self.assertTrue(all(math.isfinite(x) for x in s[1:]))
                self.assertTrue(all(abs(x)<=1 for x in s[1:4]))
                self.assertTrue(0<=s[4]<=1.5 and 0<=s[5]<=8 and 0<=s[6]<=8)
                self.assertTrue(abs(s[7])<=math.pi)

    def test_trace_hash_stable_and_sensitive(self):
        p=SwingProfile()
        self.assertEqual(trace_hash(swing_trace(p)),trace_hash(swing_trace(p)))
        self.assertNotEqual(trace_hash(swing_trace(p)),trace_hash(swing_trace(p.with_changes(speed_m_s=2))))

    def test_rejects_invalid(self):
        for value in (dict(axis="q"),dict(speed_m_s=-1),dict(speed_m_s=9),
                      dict(travel_m=2),dict(angle_rad=float("nan")),
                      dict(angle_rad=4),dict(ready_frames=1.5),
                      dict(ready_frames=300,backswing_frames=300),
                      dict(downswing_frames=0),dict(speed_m_s=True)):
            with self.subTest(value=value),self.assertRaises(ValueError):
                SwingProfile(**value)

    def test_no_aliased_rows(self):
        t=swing_trace(SwingProfile());t[0][1]=99
        self.assertEqual(t[1][1],0.)
