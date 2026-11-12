"""Offline-only 3D observed ball-curve regression; no ROM, bridge or RAM."""
from __future__ import annotations

import inspect
import math
from pathlib import Path
import struct
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from wii_ai_golf.inspector.replay import Sample, Replay, BALL
from wii_ai_golf.inspector.source_ball_trace import (
    BallTrace, observed_ball_trace, MAX_TRACE_SAMPLES)
from wii_ai_golf.inspector.scene_mesh_approximations import draw_3d_ball_trace
from wii_ai_golf.inspector.scene_camera import VisualCamera
from wii_ai_golf.inspector.unified_source_view import ComparisonKCL
from wii_ai_golf.inspector.gui import Inspector
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow


def f32(x):
    return struct.unpack(">I", struct.pack(">f",x))[0]


def sample(index, point, *, digest="source-A", qualified=True,
           state="complete", time_ns=None, frame=None):
    if time_ns is None:
        time_ns = index*100_000_000
    return Sample(
        index, "LIVE", index, time_ns, time_ns+200_000,
        {BALL: tuple(f32(float(x)) for x in point)},
        digest, qualified, "", state,
        (index,index+1) if frame is None else frame)


def comparison():
    return ComparisonKCL(
        "synthetic-source-hash",
        ((0.,0.,0.), (100.,0.,0.), (0.,0.,100.)),
        ((0,1,2),), ("#529965",),
        1., (0.,0.,0.), (1.,1.), ((0,1),(1,2),(0,2)))


def camera():
    return VisualCamera(
        position=(43.,75.,240.), focus=(43.,0.,30.),
        yaw=0., pitch=.1, scale=200.)


class ObservedBallTraceTests(unittest.TestCase):
    def test_valid_three_source_samples_make_observed_polyline(self):
        data=(
            sample(0,(10,0,10)),
            sample(1,(13,2,15)),
            sample(2,(16,6,20)))
        trail=observed_ball_trace(data)
        self.assertTrue(trail.source_qualified)
        self.assertEqual(trail.segments,(((10.,0.,10.),
                                          (13.,2.,15.),
                                          (16.,6.,20.)),))
        self.assertEqual(trail.sample_count,3)
        self.assertEqual(observed_ball_trace(data,1).segments,
                         (((10.,0.,10.),(13.,2.,15.)),))
        self.assertEqual(observed_ball_trace(data,0).segments,())
        self.assertEqual(data[2].vec(BALL),(16.,6.,20.))

    def test_owner_switch_excludes_previous_shot_entirely(self):
        data=(
            sample(0,(10,0,10)),
            sample(1,(13,4,15)),
            sample(2,(80,0,70),digest="source-B"),
            sample(3,(82,2,73),digest="source-B"),
            sample(4,(84,4,77),digest="source-A"),
            sample(5,(85,3,78),digest="source-A"))
        self.assertEqual(observed_ball_trace(data,3).segments,
                         (((80.,0.,70.), (82.,2.,73.)),))
        # Returning to A is a NEW suffix; never join with samples 0/1.
        self.assertEqual(observed_ball_trace(data,5).segments,
                         (((84.,4.,77.), (85.,3.,78.)),))

    def test_invalid_capture_gap_not_connected_to_valid_history(self):
        data=(
            sample(0,(10,0,10)),
            sample(1,(11,2,13)),
            sample(2,(25,4,28),qualified=False),
            sample(3,(31,5,31)),
            sample(4,(32,4,34)))
        self.assertEqual(observed_ball_trace(data).segments,
                         (((10.,0.,10.), (11.,2.,13.)),
                          ((31.,5.,31.), (32.,4.,34.))))
        self.assertEqual(observed_ball_trace(data,2), BallTrace())
        invalid = sample(2,(25,4,28),state="quarantined")
        self.assertEqual(observed_ball_trace(data[:2]+(invalid,)),
                         BallTrace())
        self.assertEqual(observed_ball_trace(
            data[:2]+(sample(2,(25,4,28),digest=None),)), BallTrace())

    def test_large_sample_gap_and_timestamp_reversal_break_line(self):
        a=sample(0,(10,0,10))
        b=sample(1,(12,0,12),time_ns=3_000_000_000)
        c=sample(2,(14,0,14),time_ns=3_200_000_000)
        self.assertEqual(observed_ball_trace((a,b,c)).segments,
                         (((12.,0.,12.),(14.,0.,14.)),))
        reversed_time=sample(3,(18,0,18),time_ns=100_000)
        self.assertEqual(observed_ball_trace((a,b,c,reversed_time)).segments,
                         (((12.,0.,12.),(14.,0.,14.)),))

    def test_duplicate_stationary_samples_do_not_draw_fake_motion(self):
        data=tuple(sample(i,(15,0,15)) for i in range(30))
        trail=observed_ball_trace(data)
        self.assertEqual(trail.segments,())
        self.assertEqual(trail.sample_count,1)
        self.assertTrue(trail.source_qualified)

    def test_trace_limited_to_recent_samples_and_selection_prefix(self):
        data=tuple(sample(i,(10+i*.03, i*.02,15))
                   for i in range(240))
        trace=observed_ball_trace(data)
        self.assertEqual(trace.sample_count, MAX_TRACE_SAMPLES)
        self.assertEqual(trace.segments[0][0],data[60].vec(BALL))
        self.assertEqual(trace.segments[-1][-1],data[-1].vec(BALL))
        self.assertEqual(observed_ball_trace(data,20).sample_count,21)
        for bad in (-1,True,240,"20"):
            self.assertEqual(observed_ball_trace(data,bad),BallTrace())

    def test_render_3d_camera_projection_and_visibility_toggle(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        original=Image.new("RGB",(680,440),(19,32,46))
        pixels=original.tobytes()
        trace=observed_ball_trace((
            sample(0,(20,0,20)),
            sample(1,(22,5,23)),
            sample(2,(25,10,26))))
        on=draw_3d_ball_trace(original.copy(),comparison(),camera(),trace)
        self.assertNotEqual(on.tobytes(),pixels)
        self.assertEqual(original.tobytes(),pixels)
        self.assertEqual(draw_3d_ball_trace(
            original.copy(),comparison(),camera(),trace,visible=False).tobytes(),pixels)
        self.assertEqual(draw_3d_ball_trace(
            original.copy(),None,camera(),trace).tobytes(),pixels)
        self.assertEqual(draw_3d_ball_trace(
            original.copy(),comparison(),camera(),BallTrace()).tobytes(),pixels)

    def test_prevent_large_teleport_line_in_displayed_map(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        original=Image.new("RGB",(680,440),(19,32,46))
        trace=observed_ball_trace((
            sample(0,(10,0,10)),sample(1,(95,0,95))))
        self.assertTrue(trace.source_qualified)
        self.assertEqual(draw_3d_ball_trace(
            original.copy(),comparison(),camera(),trace).tobytes(),
            original.tobytes())

    def test_reject_unbounded_or_untyped_render_request(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        image=Image.new("RGB",(680,440))
        for payload in (None, {}, "trajectory"):
            with self.assertRaises(ValueError):
                draw_3d_ball_trace(image,comparison(),camera(),payload)
        too_many=BallTrace(
            segments=(tuple((float(i),0.,0.) for i in range(181)),),
            source_qualified=True)
        with self.assertRaises(ValueError):
            draw_3d_ball_trace(image,comparison(),camera(),too_many)

    def test_viewer_switch_and_current_source_replay_path(self):
        preview=object.__new__(TexturedPreviewWindow)
        TexturedPreviewWindow.set_ball_trace(preview,BallTrace())
        self.assertEqual(preview.ball_trace,BallTrace())
        with self.assertRaises(ValueError):
            TexturedPreviewWindow.set_ball_trace(preview,None)
        controller=object.__new__(Inspector)
        controller.visual_preview=Mock()
        controller.index=SimpleNamespace(get=lambda:2)
        data=(sample(0,(20,0,20)),sample(1,(23,6,23)),
              sample(2,(26,3,29)))
        controller.replay=Replay(Path("synthetic"),"qualified",data,(),"live")
        controller.baseline=None
        controller.aim_baseline_source=None
        Inspector._sync_visual_actors(controller)
        sent=controller.visual_preview.set_ball_trace.call_args.args[0]
        self.assertEqual(sent.segments[0][-1],(26.,3.,29.))
        controller.replay=None
        Inspector._sync_visual_actors(controller)
        controller.visual_preview.set_ball_trace.assert_called_with(BallTrace())

    def test_3d_control_uses_observed_label_and_snapshot_pipeline(self):
        init=inspect.getsource(TexturedPreviewWindow.__init__)
        render=inspect.getsource(TexturedPreviewWindow._render_frame)
        gui=inspect.getsource(Inspector._sync_visual_actors)
        self.assertIn('"Observed ball trail", self.show_ball_trace',init)
        self.assertIn('draw_3d_ball_trace(',render)
        self.assertIn("observed_ball_trace(replay.samples, i)",gui)
        self.assertIn('trace_setter(BallTrace())',gui)
        self.assertIn('trace_state=(BallTrace(), True)',render)


if __name__=="__main__":
    unittest.main()
