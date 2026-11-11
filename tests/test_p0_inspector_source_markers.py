"""Synthetic source-only marker layer; no Nintendo art/ROM/coordinates committed."""
from __future__ import annotations
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from wii_ai_golf.inspector.replay import Sample, BALL, CACHE
from wii_ai_golf.inspector.scene_camera import VisualCamera
from wii_ai_golf.inspector.source_markers import (
    marker_snapshot, display_transform, draw_source_markers,
    source_marker_status)
from wii_ai_golf.inspector.tree_positions import TreePositions
from wii_ai_golf.inspector.unified_source_view import ComparisonKCL


def fbits(v):
    return int.from_bytes(struct.pack(">f",v),"big")


def sample(*, qualified=True, digest="source-epoch-1"):
    words={
        BALL:tuple(fbits(x) for x in (0.,0.,0.)),
        CACHE:tuple(fbits(x) for x in (8.,0.,1.)),
        "tee_start_candidate":tuple(fbits(x) for x in (10.,0.,5.)),
        "pin_candidate":tuple(fbits(x) for x in (-10.,0.,-5.)),
    }
    return Sample(0,"test",0,100,200,words,digest,qualified,"","complete",None)


def tree_source():
    return TreePositions(
        positions=tuple((float(i%12)*7-40.,0.,float(i//12)*7-23.)
                        for i in range(94)),
        sha256="0"*64,source_name="synthetic-original-tree-94-private.json")


def comparison():
    return ComparisonKCL(
        "0"*64, ((0.,0.,0.),(20.,0.,0.),(0.,0.,20.)),
        ((0,1,2),),("#50aa50",),1.,(0.,0.,0.),
        (1.,1.),((0,1),(1,2),(2,0)))


def camera():
    return VisualCamera(
        # Set eye on the camera's own +toward basis so the synthetic
        # actor XYZ=0 is inside the current viewport, not below its edge.
        position=(0.,-24.,118.),focus=(0.,0.,0.),
        yaw=0.,pitch=.2,scale=80.)


class SourceMarkerTests(unittest.TestCase):
    def test_only_qualified_same_packet_ball_tee_pin_cache(self):
        snap=marker_snapshot(sample(),selected_player_index=2)
        self.assertEqual(snap.ball,(0.,0.,0.))
        self.assertEqual(snap.cache,(8.,0.,1.))
        self.assertEqual(snap.tee,(10.,0.,5.))
        self.assertEqual(snap.pin,(-10.,0.,-5.))
        self.assertEqual(snap.selected_player_index,2)
        self.assertTrue(snap.source_qualified)
        self.assertEqual(snap.source_digest,"source-epoch-1")
        for packet in (sample(qualified=False),sample(digest=None),None):
            hidden=marker_snapshot(packet,selected_player_index=1)
            self.assertFalse(hidden.source_qualified)
            self.assertIsNone(hidden.ball)
            self.assertIsNone(hidden.pin)
            self.assertIsNone(hidden.tee)
            self.assertIsNone(hidden.cache)
            # Unqualified source packet MUST NOT carry live player ID.
            self.assertIsNone(hidden.selected_player_index)

    def test_unverified_display_only_transform_exact(self):
        comp=comparison()
        self.assertEqual(display_transform(comp,(7.,4.,-3.)),(7.,4.,-3.))
        comp2=ComparisonKCL(
            comp.source_sha256,comp.vertices,comp.faces,comp.colors,3.,
            (10.,7.,-4.),comp.span_ratio_xz,comp.edge_faces)
        self.assertEqual(display_transform(comp2,(2.,3.,5.)),(16.,16.,11.))
        with self.assertRaises(ValueError):
            display_transform(comp2,(float("nan"),0.,0.))

    def test_94_exact_source_bases_and_optional_non_native_tree_icons(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional visual dependency unavailable")
        image=Image.new("RGB",(700,460),(19,32,46))
        original=image.tobytes()
        untouched, counts=draw_source_markers(
            image.copy(),camera(),None,tree_source(),marker_snapshot(sample()),
            show_trees=True,show_tree_crowns=True,
            show_ball=True,show_tee_pin=True,show_cache=True)
        self.assertEqual(untouched.tobytes(),original)
        self.assertEqual(counts["trees"],0)
        image2, counts2=draw_source_markers(
            image.copy(),camera(),comparison(),tree_source(),
            marker_snapshot(sample()),show_trees=True,show_tree_crowns=False,
            show_ball=False,show_tee_pin=False,show_cache=False)
        # All 94 source bases are retained; only projected bases inside the
        # current camera frustum are counted as visible pixels.
        self.assertEqual(len(tree_source().positions),94)
        self.assertGreater(counts2["trees"],0)
        self.assertLessEqual(counts2["trees"],94)
        self.assertNotEqual(image2.tobytes(),original)
        self.assertEqual(counts2["ball"],0)
        image3, counts3=draw_source_markers(
            image.copy(),camera(),comparison(),tree_source(),
            marker_snapshot(sample()),show_trees=True,show_tree_crowns=True,
            show_ball=True,show_tee_pin=True,show_cache=True)
        self.assertEqual(counts3["trees"],counts2["trees"])
        self.assertEqual(counts3["ball"],1)
        self.assertEqual(counts3["tee"],1)
        self.assertEqual(counts3["pin"],1)
        self.assertEqual(counts3["cache"],1)
        self.assertNotEqual(image2.tobytes(),image3.tobytes())

    def test_unqualified_sample_never_appears_as_original_game_actor(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional visual dependency unavailable")
        orig=Image.new("RGB",(600,400),(19,32,46))
        hidden, counts=draw_source_markers(
            orig.copy(),camera(),comparison(),None,
            marker_snapshot(sample(qualified=False)),
            show_trees=False,show_tree_crowns=False,
            show_ball=True,show_tee_pin=True,show_cache=True)
        self.assertEqual(hidden.tobytes(),orig.tobytes())
        self.assertEqual(counts["ball"],0)
        self.assertEqual(counts["tee"],0)
        self.assertEqual(counts["pin"],0)

    def test_player_toggle_exposes_metadata_only_never_fake_3d_body(self):
        msg=source_marker_status(
            marker_snapshot(sample(),selected_player_index=1),
            tree_source(),comparison(),show_player=True)
        self.assertIn("selected player 1",msg)
        self.assertIn("NOT verified",msg)
        self.assertIn("94 exact tree bases",msg)
        self.assertIn("UNVERIFIED",msg)
        other=source_marker_status(
            marker_snapshot(sample(),selected_player_index=1),
            tree_source(),comparison(),show_player=False)
        self.assertIn("player hidden",other)
        self.assertNotIn("selected player 1",other)

    def test_gui_synchronizes_only_source_qualified_current_replay_sample(self):
        from wii_ai_golf.inspector.gui import Inspector
        inst=object.__new__(Inspector)
        inst.visual_preview=Mock()
        inst.index=Mock()
        inst.index.get.return_value=0
        inst.replay=SimpleNamespace(samples=(sample(),))
        inst.selected_player_index=0
        Inspector._sync_actor_markers(inst)
        snap=inst.visual_preview.set_actor_snapshot.call_args.args[0]
        self.assertEqual(snap.ball,(0.,0.,0.))
        self.assertEqual(snap.selected_player_index,0)
        inst.visual_preview.reset_mock()
        inst.replay=None
        Inspector._sync_actor_markers(inst)
        inst.visual_preview.set_actor_snapshot.assert_called_once_with(None)

    def test_top_viewer_exposes_all_optional_controls(self):
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        for name in ("show_trees","show_tree_crowns","show_ball",
                     "show_tee_pin","show_cache","show_player",
                     "choose_private_trees","set_source_trees",
                     "set_actor_snapshot"):
            self.assertTrue(
                name in TexturedPreviewWindow.__dict__
                or name in TexturedPreviewWindow.__init__.__code__.co_names,
                msg=name)


if __name__=="__main__":
    unittest.main()
