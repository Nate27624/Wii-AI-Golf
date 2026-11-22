"""Synthetic-only full collision mesh and texture UI regression tests.

No original assets, no Dolphin, no private memory files, no guest actions.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from wii_ai_golf.inspector.gui import Inspector
from wii_ai_golf.inspector.terrain import TerrainMesh, TerrainError, MAX_DRAW_FACES
from wii_ai_golf.inspector.terrain_solid import back_to_front, shaded_hex

A=((0.0,0.0,0.0),(20.0,0.0,0.0),(0.0,0.0,20.0))


class Value:
    def __init__(self,v):self.v=v
    def get(self):return self.v
    def set(self,v):self.v=v


class FakeCanvas:
    def __init__(self):self.ops=[]
    def delete(self,*a,**kw):
        if "all" in a:self.ops=[]
    def winfo_width(self):return 800
    def winfo_height(self):return 520
    def __getattr__(self,name):
        if name not in ("create_polygon","create_text","create_line","create_oval"):
            raise AttributeError(name)
        def f(*args,**kw):
            self.ops.append((name,kw))
        return f


class TestFullTerrainDetail(unittest.TestCase):
    def view(self, count=2498):
        class Sample:
            words={}
            source_qualified=True
            source_digest="synthetic_source"
            def vec(self,channel):
                return {
                    "selected_ball_plus_0x30":(0.,0.,0.),
                    "selected_ball_cache_plus_0xcc":(0.,0.,0.),
                    "pin_candidate":(20.,0.,20.),
                    "tee_start_candidate":(0.,0.,0.),
                }.get(channel)
        c=FakeCanvas()
        v=SimpleNamespace(
            canvas=c, replay=SimpleNamespace(samples=(Sample(),)),
            index=Value(0), yaw=0.65, pitch=0.48,
            terrain_mesh=TerrainMesh(
                A,((0,1,2),)*count,"a"*64,"synthetic-private-OBJ",
                (6,)*count),
            terrain_visible=Value(True),terrain_focus=Value(False),
            terrain_full_detail=Value(True),terrain_solid=Value(True),
            terrain_edges=Value(False),terrain_colors=Value(True),
            terrain_point_labels=Value(False),
            terrain_status=Value(""),landmark_status=Value(""),
            aim_status=Value(""),baseline=None,aim_baseline_source=None,
            aim_baseline_mode="",live_worker=None,live_last=None,
            camera_zoom=1.,camera_pan=(0.,0.),
            a_status=Value("A RELEASED"),a_reason=Value("synthetic"))
        v.draw_a_overlay=lambda:Inspector.draw_a_overlay(v)
        return v

    def test_full_2498_faces_shaded_without_label_clutter(self):
        v=self.view()
        Inspector.draw_path(v)
        poly=[kw for method,kw in v.canvas.ops
              if method=="create_polygon" and "terrain_solid_face" in kw.get("tags",())]
        self.assertEqual(len(poly),2498)
        self.assertEqual(poly[0]["fill"],shaded_hex("#73e998",A))
        self.assertIn("2498/2498",v.terrain_status.get())
        self.assertIn("COMPLETE",v.terrain_status.get())
        self.assertFalse(any(kw.get("text")=="TEE (candidate)"
                             for _,kw in v.canvas.ops))
        self.assertTrue(any(kw.get("text")=="A RELEASED"
                            for _,kw in v.canvas.ops))

    def test_preview_explicit_downsamples(self):
        v=self.view()
        v.terrain_full_detail.set(False)
        Inspector.draw_path(v)
        poly=[kw for method,kw in v.canvas.ops
              if method=="create_polygon" and "terrain_solid_face" in kw.get("tags",())]
        self.assertEqual(len(poly),833)
        self.assertIn("PARTIAL",v.terrain_status.get())

    def test_edges_and_wireframe_toggles(self):
        v=self.view(count=3)
        v.terrain_solid.set(False)
        v.terrain_edges.set(True)
        Inspector.draw_path(v)
        lines=[kw for method,kw in v.canvas.ops
               if method=="create_line" and "terrain_wire_edge" in kw.get("tags",())]
        self.assertEqual(len(lines),3)
        v.terrain_solid.set(True)
        v.terrain_edges.set(True)
        v.canvas.ops.clear()
        Inspector.draw_path(v)
        poly=[kw for method,kw in v.canvas.ops
              if method=="create_polygon" and "terrain_solid_face" in kw.get("tags",())]
        self.assertEqual(len(poly),3)
        self.assertTrue(all(kw.get("outline") for kw in poly))

    def test_source_bounds_and_no_generated_triangles(self):
        self.assertGreaterEqual(MAX_DRAW_FACES,2498)
        mesh=TerrainMesh(A,((0,1,2),)*2498,"a"*64,"synthetic",(None,)*2498)
        faces=mesh.drawing_faces(focused=False,limit=MAX_DRAW_FACES)
        self.assertEqual(len(faces),2498)
        self.assertEqual(mesh.faces[0],(0,1,2))
        with self.assertRaises(TerrainError):
            mesh.drawing_faces(focused=False,limit=MAX_DRAW_FACES+1)

    def test_private_uv_preview_is_a_separate_reader(self):
        source=(ROOT/"src/wii_ai_golf/inspector/gui.py").read_text("utf-8")
        self.assertIn("Preview PRIVATE game textures",source)
        self.assertIn("load_private_visual_model(filename)",source)
        self.assertIn("TexturedPreviewWindow",source)
        self.assertIn("All triangles",source)
        self.assertIn("Solid terrain",source)
        self.assertNotIn('rpc.call("memory.write',source)

    def test_source_color_loader_requires_mesh(self):
        v=SimpleNamespace(terrain_mesh=None,
                          surface_label_status=Value(""),
                          draw_path=Mock())
        self.assertFalse(Inspector.load_terrain_labels_path(v,"anything-PRIVATE.json"))
        self.assertIn("load",v.surface_label_status.get())
        v.draw_path.assert_not_called()

    def test_invalid_camera_for_solid_sort_abstains(self):
        with self.assertRaises(ValueError):
            back_to_front(((A,None),),float("nan"),0.3)
        with self.assertRaises(ValueError):
            shaded_hex("bad",A)


if __name__=="__main__":
    unittest.main()
