"""Synthetic source-independent scene camera tests (no Dolphin or private OBJ)."""
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector.navigation import (
    MIN_ZOOM, MAX_ZOOM, wheel_steps, zoom_at_cursor, pan_by)

class CameraMathTests(unittest.TestCase):
    def test_cursor_stays_fixed_during_zoom(self):
        for cursor in ((20,10),(450,220),(800,420)):
            zoom,pan=zoom_at_cursor(1.5,(63.,-44.),cursor,(900,470),3.)
            before=((cursor[0]-450-63)/1.5,(cursor[1]-235+44)/1.5)
            after=((cursor[0]-450-pan[0])/zoom,(cursor[1]-235-pan[1])/zoom)
            self.assertAlmostEqual(before[0],after[0],places=10)
            self.assertAlmostEqual(before[1],after[1],places=10)

    def test_wheel_normalized_on_windows_and_x11(self):
        self.assertEqual(wheel_steps(120),1)
        self.assertEqual(wheel_steps(-240),-2)
        self.assertEqual(wheel_steps(button=4),1)
        self.assertEqual(wheel_steps(button=5),-1)
        self.assertEqual(wheel_steps(float('nan')),0)
        self.assertEqual(wheel_steps('120'),0)
        self.assertEqual(wheel_steps(True),0)

    def test_zoom_bounds_both_directions(self):
        zoom,pan=1.,(0.,0.)
        for _ in range(200):zoom,pan=zoom_at_cursor(zoom,pan,(310.,203.),(900,470),8)
        self.assertEqual(zoom,MAX_ZOOM)
        self.assertTrue(all(math.isfinite(x) for x in pan))
        for _ in range(200):zoom,pan=zoom_at_cursor(zoom,pan,(310.,203.),(900,470),-8)
        self.assertEqual(zoom,MIN_ZOOM)
        self.assertTrue(all(math.isfinite(x) for x in pan))

    def test_pan_changes_only_translation(self):
        self.assertEqual(pan_by((4.,-5.),10.,-2.),(14.,-7.))
        with self.assertRaises(ValueError): pan_by((0.,0.),float('inf'),0.)

    def test_invalid_camera_does_not_change_state(self):
        for args in ((0,(0.,0.),(0.,0.),(900,470),1),
                     (1.,(0.,0.),(0.,0.),(0,470),1),
                     (1.,(float('nan'),0.),(0.,0.),(900,470),1)):
            with self.subTest(args=args), self.assertRaises(ValueError):zoom_at_cursor(*args)

    def test_gui_wheel_middle_pan_and_focus_preserve_orbit(self):
        from wii_ai_golf.inspector.gui import Inspector
        class Canvas:
            def winfo_width(self):return 900
            def winfo_height(self):return 470
            def focus_set(self):pass
        obj=object.__new__(Inspector)
        obj.canvas=Canvas();obj.yaw=0.65;obj.pitch=0.48;obj.drag_origin=None;obj.drag_button=None
        obj.camera_zoom=1.;obj.camera_pan=(0.,0.)
        draws=[];obj.draw_path=lambda:draws.append((obj.camera_zoom,obj.camera_pan,obj.yaw,obj.pitch))
        obj.scene_wheel(SimpleNamespace(x=500,y=200,delta=120,num=None))
        self.assertGreater(obj.camera_zoom,1)
        self.assertNotEqual(obj.camera_pan,(0,0))
        obj.drag_start(SimpleNamespace(x=200,y=150,num=2))
        obj.drag_move(SimpleNamespace(x=220,y=180))
        self.assertEqual(obj.drag_button,2)
        self.assertEqual((obj.yaw,obj.pitch),(.65,.48))
        oldpan=obj.camera_pan
        obj.drag_end(SimpleNamespace(x=220,y=180,num=2))
        self.assertIsNone(obj.drag_origin)
        self.assertNotEqual(oldpan,(0.,0.))
        obj.drag_start(SimpleNamespace(x=0,y=0,num=3))
        obj.drag_move(SimpleNamespace(x=20,y=10))
        self.assertNotEqual(obj.yaw,.65)
        oldyaw=obj.yaw
        obj.frame_view()
        self.assertEqual(obj.camera_zoom,1.)
        self.assertEqual(obj.camera_pan,(0.,0.))
        self.assertEqual(obj.yaw,oldyaw)
        self.assertGreaterEqual(len(draws),4)

    def test_replay_projection_preserves_orthographic_camera(self):
        from wii_ai_golf.inspector.gui import project
        p=(2.,3.,4.)
        self.assertEqual(project(p,.65,.48),project(p,.65,.48))

if __name__=='__main__':unittest.main()
