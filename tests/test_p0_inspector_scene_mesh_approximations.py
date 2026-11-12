"""Synthetic-only approximate 3D inspector meshes (no Wii assets or RAM)."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wii_ai_golf.inspector.scene_mesh_approximations import (
    actor_mesh_faces, actor_mesh_size, tree_mesh_faces,
    draw_3d_approximations, MAX_SCENE_FACES)
from wii_ai_golf.inspector.scene_camera import VisualCamera
from wii_ai_golf.inspector.source_actor_overlay import (
    SourceActorSnapshot, draw_source_actors)
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
