"""Synthetic-only approximate 3D inspector meshes (no Wii assets or RAM)."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wii_ai_golf.inspector.scene_mesh_approximations import (
    actor_mesh_faces, actor_mesh_size, tree_mesh_faces,
    direction_arrow_faces,
    draw_3d_approximations, MAX_SCENE_FACES)
from wii_ai_golf.inspector.scene_camera import VisualCamera
from wii_ai_golf.inspector.source_actor_overlay import (
    SourceActorSnapshot, draw_source_actors, from_sample)
from wii_ai_golf.inspector.replay import Sample, AIM
from wii_ai_golf.inspector.unified_source_view import (
    ComparisonKCL, source_to_visual_display)


def source_trees():
    return tuple((float(i % 12)*8., 0., float(i//12)*12.)
                 for i in range(94))


def comp():
    return ComparisonKCL(
        "a"*64,
        ((0.,0.,0.), (100.,0.,0.), (0.,0.,100.)),
        ((0,1,2),),
        ("#529965",),
        1.0, (0.,0.,0.), (1.,1.), ((0,1),(1,2),(0,2)))


def cam(position=(43.,75.,240.)):
    return VisualCamera(
        position=position, focus=(43.,0.,30.), yaw=0., pitch=.1, scale=200.)


class Approximate3DSceneTests(unittest.TestCase):
    def test_94_trees_are_true_world_meshes_not_screen_sprites(self):
        positions = source_trees()
        faces = tree_mesh_faces(positions)
        self.assertEqual(len(faces), 94*24)
        self.assertLessEqual(len(faces), MAX_SCENE_FACES)
        self.assertEqual({face.kind for face in faces}, {"tree"})
        # Each actual 3D tree has trunk and crown polygons in source XYZ.
        self.assertTrue(any(
            len({v[1] for v in face.vertices}) > 1
            for face in faces))
        self.assertTrue(any(
            len({v[0] for v in face.vertices}) > 1 and
            len({v[2] for v in face.vertices}) > 1
            for face in faces))
        self.assertEqual(source_trees(), positions)

    def test_player_flag_and_ball_have_bounded_volume_in_three_dimensions(self):
        comp_data = comp()
        snapshot = SourceActorSnapshot(
            ball=(20.,1.,18.), flag=(52.,1.,64.),
            tee_proxy=(20.,0.,18.), source_qualified=True)
        objects = actor_mesh_faces(comp_data, snapshot)
        self.assertGreater(len(objects), 100)
        self.assertLess(len(objects), 500)
        self.assertEqual({face.kind for face in objects},
                         {"flag", "ball", "player"})
        for kind in ("flag", "ball", "player"):
            vertices = [v for face in objects if face.kind == kind
                        for v in face.vertices]
            for axis in range(3):
                self.assertGreater(max(v[axis] for v in vertices) -
                                   min(v[axis] for v in vertices), 0.,
                                   (kind,axis))
            self.assertTrue(all(math.isfinite(x) for p in vertices for x in p))
        self.assertGreater(actor_mesh_size(comp_data), 0.)
        self.assertEqual(snapshot.flag, (52.,1.,64.))
        self.assertEqual(snapshot.ball, (20.,1.,18.))
        self.assertEqual(snapshot.tee_proxy, (20.,0.,18.))

    def test_missing_unqualified_sample_does_not_invent_actor_mesh(self):
        self.assertEqual(actor_mesh_faces(comp(), SourceActorSnapshot()), ())
        self.assertEqual(actor_mesh_faces(comp(), None), ())
        self.assertEqual(len(actor_mesh_faces(
            comp(), SourceActorSnapshot(
                ball=(20.,2.,20.),source_qualified=True),
            show_flag=False, show_player=False)) > 0, True)
        with self.assertRaises(ValueError):
            actor_mesh_faces(comp(), SourceActorSnapshot(
                ball=(20.,2.,20.),source_qualified=True),
                show_ball="yes")

    def test_tree_mesh_requires_exact_94_finite_source_points(self):
        with self.assertRaises(ValueError):
            tree_mesh_faces(source_trees()[:93])
        bad = source_trees()[:-1]+((float("nan"),0.,0.),)
        with self.assertRaises(ValueError):
            tree_mesh_faces(bad)

    def test_3d_visibility_modes_and_single_camera_projection(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        original = Image.new("RGB", (680,440), (20,36,53))
        baseline = original.tobytes()
        comparison = comp()
        tree_only = draw_3d_approximations(
            original.copy(), comparison, cam(), source_tree_positions=source_trees(),
            show_flag=False,show_ball=False,show_player=False,labels=False)
        self.assertNotEqual(tree_only.tobytes(), baseline)
        hidden = draw_3d_approximations(
            original.copy(), comparison, cam(), source_tree_positions=source_trees(),
            show_trees=False,show_flag=False,show_ball=False,show_player=False,
            labels=False)
        self.assertEqual(hidden.tobytes(),baseline)
        self.assertEqual(original.tobytes(),baseline)
        self.assertEqual(draw_3d_approximations(
            original.copy(), None, cam(), source_tree_positions=source_trees()
        ).tobytes(),baseline)
        self.assertNotEqual(draw_3d_approximations(
            original.copy(),comparison,cam(position=(10.,50.,160.)),
            source_tree_positions=source_trees(), labels=False).tobytes(),
            tree_only.tobytes())

    def test_actor_3d_wrapper_and_tree_toggle_independent(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        original = Image.new("RGB",(680,440),(19,32,46))
        state = SourceActorSnapshot(
            ball=(20.,0.,20.), flag=(50.,0.,55.),
            tee_proxy=(20.,0.,20.), source_qualified=True)
        render = draw_source_actors(original.copy(), comp(), cam(), state,
                                   labels=False)
        self.assertNotEqual(render.tobytes(),original.tobytes())
        tree_and_actor = draw_3d_approximations(
            original.copy(),comp(),cam(),snapshot=state,
            source_tree_positions=source_trees(),labels=False)
        self.assertNotEqual(tree_and_actor.tobytes(),render.tobytes())
        self.assertEqual(draw_3d_approximations(
            original.copy(),comp(),cam(),
            snapshot=SourceActorSnapshot(),show_trees=False).tobytes(),
            original.tobytes())

    def test_tree_and_actor_position_transform_keeps_native_source_intact(self):
        source=(13.,5.,17.)
        mapped = source_to_visual_display(source,comp())
        self.assertEqual(mapped,source)
        snap = SourceActorSnapshot(ball=source,flag=source,
                                   tee_proxy=source,source_qualified=True)
        actor_mesh_faces(comp(),snap)
        tree_mesh_faces(source_trees())
        self.assertEqual(snap.ball,source)

    def test_operator_screenshot_scale_reduced_at_both_green_and_tee(self):
        # At 100 source units wide the figure must be under 1 source unit
        # instead of the old 3.5 source-unit silhouette. No source geometry
        # or physical scale is modified.
        h = actor_mesh_size(comp())
        self.assertAlmostEqual(h, .8)
        actors = SourceActorSnapshot(
            ball=(20., 0., 20.), flag=(52., 0., 52.),
            tee_proxy=(20., 0., 20.), source_qualified=True)
        faces = actor_mesh_faces(comp(), actors)
        for kind in ("player", "flag"):
            positions = [p for face in faces if face.kind == kind
                         for p in face.vertices]
            height = max(p[1] for p in positions) - min(p[1] for p in positions)
            self.assertLess(height, 1.2)
            self.assertGreater(height, .3)
        self.assertLess(h, 100*.01)

    def test_degree_delta_requires_qualified_matching_source_baseline(self):
        import struct
        angle = lambda v: struct.unpack(">I", struct.pack(">f", v))[0]
        packet = Sample(
            0, "aim", 0, 0, 1,
            {AIM: (angle(math.radians(35.)),),
             "pin_candidate": tuple(angle(v) for v in (80., 1., 20.)),
             "tee_start_candidate": tuple(angle(v) for v in (20., 1., 20.))},
            "qualified-hash", True, "", "complete", None)
        measured = from_sample(
            packet, baseline=math.radians(10.),
            baseline_source="qualified-hash",
            baseline_mode="OPERATOR set pointed-at-flag reference")
        self.assertAlmostEqual(measured.aim_raw_degrees, 35., places=4)
        self.assertAlmostEqual(measured.aim_delta_degrees, 25., places=4)
        self.assertEqual(measured.aim_reference, "operator")
        wrong_epoch = from_sample(
            packet, baseline=math.radians(10.),
            baseline_source="different-source-epoch")
        self.assertIsNone(wrong_epoch.aim_delta_degrees)
        self.assertIsNotNone(wrong_epoch.aim_raw_degrees)
        self.assertEqual(direction_arrow_faces(comp(), wrong_epoch), ())
        absent = Sample(1, "aim", 1, 0, 1, packet.words,
                        None, False, "", "complete", None)
        self.assertEqual(from_sample(absent), SourceActorSnapshot())
        self.assertEqual(direction_arrow_faces(comp(),from_sample(absent)), ())

    def test_direction_arrow_is_3d_and_rotates_with_relative_degrees(self):
        source=SourceActorSnapshot(
            tee_proxy=(20., 1., 20.), flag=(70., 1., 20.),
            aim_delta_degrees=0., source_qualified=True,
            aim_reference="assumed")
        arrow = direction_arrow_faces(comp(), source)
        self.assertEqual({v.kind for v in arrow}, {"direction"})
        self.assertGreaterEqual(len(arrow), 9)
        self.assertLess(len(arrow), 20)
        vertices={v for face in arrow for v in face.vertices}
        self.assertGreater(max(v[0] for v in vertices)-min(v[0] for v in vertices), 6.)
        self.assertGreater(max(v[1] for v in vertices)-min(v[1] for v in vertices), 0.)
        rotated=SourceActorSnapshot(
            tee_proxy=source.tee_proxy, flag=source.flag,
            aim_delta_degrees=90., source_qualified=True,
            aim_reference="assumed")
        sideways={v for face in direction_arrow_faces(comp(),rotated)
                  for v in face.vertices}
        # +90 degrees rotates from tee -> +X to tee -> +Z.
        self.assertGreater(max(v[2] for v in sideways) -
                           min(v[2] for v in sideways), 6.)
        self.assertLess(max(v[0] for v in sideways) -
                        min(v[0] for v in sideways), 4.)
        self.assertEqual(source.tee_proxy, (20.,1.,20.))
        self.assertEqual(source.flag, (70.,1.,20.))

    def test_arrow_toggle_changes_pixels_without_game_writes(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional")
        original=Image.new("RGB",(900,580),(19,33,48))
        state=SourceActorSnapshot(
            tee_proxy=(20.,0.,20.), flag=(80.,0.,20.),
            aim_delta_degrees=18., source_qualified=True,
            aim_reference="operator")
        no_arrow=draw_3d_approximations(
            original.copy(),comp(),cam(),snapshot=state,
            show_trees=False,show_flag=False,show_ball=False,
            show_player=False,show_direction=False,labels=False)
        yes_arrow=draw_3d_approximations(
            original.copy(),comp(),cam(),snapshot=state,
            show_trees=False,show_flag=False,show_ball=False,
            show_player=False,show_direction=True,labels=False)
        self.assertEqual(no_arrow.tobytes(),original.tobytes())
        self.assertNotEqual(yes_arrow.tobytes(),original.tobytes())
        self.assertEqual(original.getpixel((0,0)),(19,33,48))

    def test_ui_degrees_provenance_and_direction_toggle(self):
        import inspect
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        visual=inspect.getsource(TexturedPreviewWindow.__init__)
        self.assertIn('self.show_direction = tk.BooleanVar(value=True)',visual)
        self.assertIn('("Swing direction arrow (aim hypothesis)", self.show_direction)',visual)
        self.assertIn("textvariable=self.direction_status",visual)
        sample=SourceActorSnapshot(
            tee_proxy=(20.,0.,20.), flag=(80.,0.,20.),
            aim_delta_degrees=12.5, aim_reference="operator",
            source_qualified=True)
        info=TexturedPreviewWindow.direction_readout(sample)
        self.assertIn("+12.5°",info)
        self.assertIn("operator-set",info)
        self.assertIn("HYPOTHESIS",info)
        illustration=SourceActorSnapshot(
            tee_proxy=(20.,0.,20.), flag=(80.,0.,20.),
            aim_delta_degrees=0., illustrative_only=True,
            aim_reference="illustrative")
        self.assertIn("ILLUSTRATIVE",
                      TexturedPreviewWindow.direction_readout(illustration))
        raw=SourceActorSnapshot(
            tee_proxy=(20.,0.,20.), flag=(80.,0.,20.),
            aim_raw_degrees=143.,source_qualified=True)
        self.assertIn("arrow hidden",TexturedPreviewWindow.direction_readout(raw))

    def test_controls_place_trees_in_same_3d_toolbar_not_legacy_section(self):
        import inspect
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        from wii_ai_golf.inspector.gui import Inspector
        preview_code=inspect.getsource(TexturedPreviewWindow.__init__)
        gui_code=inspect.getsource(Inspector._draw_controls)
        self.assertIn('"Trees (3D)", self.show_trees',preview_code)
        self.assertIn('"Flag", self.show_flag',preview_code)
        self.assertIn('"Ball", self.show_ball',preview_code)
        self.assertIn('"Player (tee proxy)", self.show_player',preview_code)
        self.assertNotIn('text="Show trees"',gui_code)
        self.assertNotIn('text="Illustrative crowns',gui_code)
        self.assertNotIn('text="Tree IDs"',gui_code)


if __name__=="__main__":
    unittest.main()
