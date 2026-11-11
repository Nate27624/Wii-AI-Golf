"""Synthetic Collada source tests; never use/copy actual game assets."""
import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.dae_visual import load_private_dae_visual_model
from wii_ai_golf.inspector.texture_render import prepare_textures, render_preview
from wii_ai_golf.inspector.visual_model import VisualAssetError

PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+UXZ0AAAAASUVORK5CYII=")

DAE = """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2008/03/COLLADASchema" version="1.5.0">
  <library_images><image id="glf_fairway1-image" name="glf_fairway1">
    <init_from>glf_fairway1.png</init_from></image></library_images>
  <library_effects>
    <effect id="M_Fairway-fx"><profile_COMMON><technique sid="common">
      <phong><diffuse><texture texture="glf_fairway1-sampler" texcoord="TEXCOORD0"/>
      </diffuse></phong></technique></profile_COMMON></effect>
    <effect id="M_Kiwa_Black-fx"><profile_COMMON><technique sid="common">
      <phong><diffuse><color>0.1 0.3 0.5 1</color></diffuse></phong>
      </technique></profile_COMMON></effect>
  </library_effects>
  <library_materials>
    <material id="M_Fairway"><instance_effect url="#M_Fairway-fx"/></material>
    <material id="M_Kiwa_Black"><instance_effect url="#M_Kiwa_Black-fx"/></material>
  </library_materials>
  <library_geometries><geometry id="grass"><mesh>
    <source id="grass-positions"><float_array id="grass-pos-data" count="9">
      0 0 0 8 0 0 0 8 0
    </float_array><technique_common><accessor source="#grass-pos-data" count="3" stride="3"/>
    </technique_common></source>
    <source id="grass-uvs"><float_array id="grass-uv-data" count="6">
      0 0 1 0 0 1
    </float_array><technique_common><accessor source="#grass-uv-data" count="3" stride="2"/>
    </technique_common></source>
    <vertices id="grass-verts"><input semantic="POSITION" source="#grass-positions"/>
    </vertices>
    <triangles count="1" material="fairway_symbol">
      <input semantic="VERTEX" source="#grass-verts" offset="0"/>
      <input semantic="TEXCOORD" source="#grass-uvs" offset="1" set="0"/>
      <p>0 0 1 1 2 2</p></triangles>
    <triangles count="1" material="M_Kiwa_Black">
      <input semantic="VERTEX" source="#grass-verts" offset="0"/>
      <p>0 1 2</p></triangles>
  </mesh></geometry></library_geometries>
  <library_visual_scenes><visual_scene id="testscene"><node id="grass-node">
    <instance_geometry url="#grass"><bind_material><technique_common>
      <instance_material symbol="fairway_symbol" target="#M_Fairway"/>
    </technique_common></bind_material></instance_geometry>
  </node></visual_scene></library_visual_scenes>
</COLLADA>"""


class DirectDAETests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name) / "WiiGolfVisualPrivate"
        self.folder.mkdir()
        self.dae = self.folder / "glf_course_fc1.dae"
        self.dae.write_bytes(DAE.encode("utf-8"))
        self.textures = self.folder / "Textures(NW4R)"
        self.textures.mkdir()
        self.png = self.textures / "glf_fairway1.tex0.png"
        self.png.write_bytes(PIXEL)

    def test_source_uv_and_exact_raw_tex0_png(self):
        visual = load_private_dae_visual_model(self.dae)
        self.assertEqual(len(visual.faces), 2)
        self.assertEqual(visual.faces[0].material, "M_Fairway")
        self.assertEqual(visual.faces[1].material, "M_Kiwa_Black")
        self.assertEqual(visual.uvs[:3], ((0., 0.), (1., 0.), (0., 1.)))
        self.assertEqual(visual.textures["M_Fairway"].filename.name, self.png.name)
        self.assertEqual(visual.textures["M_Fairway"].sha256,
                         hashlib.sha256(self.png.read_bytes()).hexdigest())
        self.assertEqual(visual.solid_colors["M_Kiwa_Black"], (26, 76, 128))
        self.assertEqual(visual.obj_sha256, hashlib.sha256(self.dae.read_bytes()).hexdigest())

    def test_brawlcrate_sampler_surface_ref_to_image_name(self):
        # The real FC1 DAE has image ID glf_fairway1-image and image NAME
        # glf_fairway1. Collada newparams can refer to either.
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from>glf_fairway1</init_from></surface>'
            '</newparam><newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        patched = DAE.replace(
            '<effect id="M_Fairway-fx"><profile_COMMON>',
            '<effect id="M_Fairway-fx"><profile_COMMON>' + params)
        self.dae.write_bytes(patched.encode("utf-8"))
        model = load_private_dae_visual_model(self.dae)
        self.assertIn("M_Fairway", model.textures)
        self.assertEqual(model.textures["M_Fairway"].sha256,
                         hashlib.sha256(self.png.read_bytes()).hexdigest())

    def test_brawlcrate_collada15_nested_surface_init_from_ref(self):
        # Reproduces the real original Wii Golf M_Bunker-fx failure:
        # <init_from><ref>glf_sand01-image</ref></init_from> has no .text.
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from>'
            '<ref>glf_fairway1-image</ref>'
            '</init_from></surface></newparam>'
            '<newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        patched = DAE.replace(
            '<effect id="M_Fairway-fx"><profile_COMMON>',
            '<effect id="M_Fairway-fx"><profile_COMMON>' + params
        ).replace(
            '<init_from>glf_fairway1.png</init_from>',
            '<init_from><ref>glf_fairway1.png</ref></init_from>'
        )
        self.dae.write_bytes(patched.encode("utf-8"))
        model = load_private_dae_visual_model(self.dae)
        self.assertEqual(model.textures["M_Fairway"].sha256,
                         hashlib.sha256(self.png.read_bytes()).hexdigest())

    def test_brawlcrate_collada15_nested_surface_init_from_name(self):
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from>'
            '<ref>glf_fairway1</ref>'
            '</init_from></surface></newparam>'
            '<newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        self.dae.write_bytes(DAE.replace(
            '<effect id="M_Fairway-fx"><profile_COMMON>',
            '<effect id="M_Fairway-fx"><profile_COMMON>' + params
        ).encode("utf-8"))
        self.assertIn("M_Fairway", load_private_dae_visual_model(self.dae).textures)

    def test_brawlcrate_collada15_rejects_ambiguous_or_empty_ref(self):
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from><ref>ORIGINAL</ref></init_from></surface>'
            '</newparam>'
            '<newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        for source in ('', 'https://example.com/remote.png',
                       'glf_fairway1-image</ref><ref>other'):
            broken = DAE.replace(
                '<effect id="M_Fairway-fx"><profile_COMMON>',
                '<effect id="M_Fairway-fx"><profile_COMMON>' +
                params.replace('ORIGINAL', source))
            self.dae.write_bytes(broken.encode("utf-8"))
            with self.subTest(ref=source), self.assertRaises(VisualAssetError):
                load_private_dae_visual_model(self.dae)

    def test_brawlcrate_sampler_surface_ref_to_image_id(self):
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from>glf_fairway1-image</init_from></surface>'
            '</newparam><newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        patched = DAE.replace(
            '<effect id="M_Fairway-fx"><profile_COMMON>',
            '<effect id="M_Fairway-fx"><profile_COMMON>' + params)
        self.dae.write_bytes(patched.encode("utf-8"))
        self.assertIn("M_Fairway", load_private_dae_visual_model(self.dae).textures)

    def test_invalid_sampler_surface_cannot_guess_material(self):
        params = (
            '<newparam sid="glf_fairway1-surface">'
            '<surface type="2D"><init_from>other-image</init_from></surface>'
            '</newparam><newparam sid="glf_fairway1-sampler">'
            '<sampler2D><source>glf_fairway1-surface</source></sampler2D>'
            '</newparam>'
        )
        self.dae.write_bytes(DAE.replace(
            '<effect id="M_Fairway-fx"><profile_COMMON>',
            '<effect id="M_Fairway-fx"><profile_COMMON>' + params
        ).encode("utf-8"))
        with self.assertRaisesRegex(VisualAssetError, "sampler does not match image"):
            load_private_dae_visual_model(self.dae)

    def test_ambiguous_name_alias_rejected(self):
        duplicate = ('<image id="glf_fake-image" name="glf_fairway1">'
                     '<init_from>glf_fake.png</init_from></image>')
        self.dae.write_bytes(DAE.replace(
            '</library_images>', duplicate + '</library_images>'
        ).encode("utf-8"))
        with self.assertRaisesRegex(VisualAssetError, "Ambiguous Collada source image alias"):
            load_private_dae_visual_model(self.dae)

    def test_original_png_and_scene_render_no_blender(self):
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest("Optional small Pillow/NumPy renderer not installed")
        Image.new("RGBA", (4,4), (26,188,71,255)).save(self.png)
        visual = load_private_dae_visual_model(self.dae)
        textures = prepare_textures(visual)
        scene, drawn = render_preview(visual, 180, 180, yaw=0, pitch=0, textures=textures)
        self.assertGreaterEqual(drawn, 1)
        self.assertEqual(scene.size, (180, 180))

    def test_absent_png_never_fabricated(self):
        self.png.unlink()
        with self.assertRaisesRegex(VisualAssetError, "Missing or ambiguous"):
            load_private_dae_visual_model(self.dae)

    def test_missing_uv_fails_closed(self):
        self.dae.write_bytes(DAE.replace('semantic="TEXCOORD"','semantic="NORMAL"').encode())
        with self.assertRaises(VisualAssetError):
            load_private_dae_visual_model(self.dae)

    def test_bad_image_link_never_fetches(self):
        self.dae.write_bytes(DAE.replace("glf_fairway1.png", "../outside.png").encode())
        with self.assertRaises(VisualAssetError):
            load_private_dae_visual_model(self.dae)

    def test_xml_external_entity_never_loaded(self):
        self.dae.write_bytes(b'<!DOCTYPE a [ <!ENTITY x SYSTEM "file:///etc/passwd"> ]>' +
                             DAE.encode())
        with self.assertRaises(VisualAssetError):
            load_private_dae_visual_model(self.dae)

    def test_source_count_mismatch_abstains(self):
        self.dae.write_bytes(DAE.replace('count="9"', 'count="8"').encode())
        with self.assertRaises(VisualAssetError):
            load_private_dae_visual_model(self.dae)

    def test_material_without_original_diffuse_is_omitted_not_fabricated(self):
        self.dae.write_bytes(DAE.replace("<color>0.1 0.3 0.5 1</color>", "").encode())
        visual = load_private_dae_visual_model(self.dae)
        self.assertEqual(len(visual.faces), 1)
        self.assertEqual(visual.textured_face_count, 1)
        self.assertEqual(visual.faces[0].material, "M_Fairway")
        self.assertEqual(visual.skipped_source_faces, 1)
        self.assertNotIn("M_Kiwa_Black", visual.solid_colors)
        self.assertFalse(any(self.folder.glob("*.obj")))

    def test_bad_untextured_source_color_is_rejected_not_guessed(self):
        for bad in ("NaN 0 0 1", "2 0 0 1", "1 0", "0 0 0 0 0"):
            with self.subTest(value=bad):
                self.dae.write_bytes(
                    DAE.replace("<color>0.1 0.3 0.5 1</color>",
                                "<color>" + bad + "</color>").encode())
                with self.assertRaises(VisualAssetError):
                    load_private_dae_visual_model(self.dae)

    def test_missing_all_textured_source_faces_refuses_empty_preview(self):
        # Do not claim an authentic textured preview from color-only
        # source geometry, even if that untextured source color exists.
        self.dae.write_bytes(
            DAE.replace('material="fairway_symbol"',
                        'material="M_Kiwa_Black"').encode())
        with self.assertRaisesRegex(
                VisualAssetError, "source-textured Collada triangles"):
            load_private_dae_visual_model(self.dae)

    def test_symlink_or_git_boundary_rejected(self):
        (self.folder / ".git").mkdir()
        with self.assertRaises(VisualAssetError):
            load_private_dae_visual_model(self.dae)

    def test_existing_collision_obj_unaffected(self):
        original = self.dae.read_bytes()
        load_private_dae_visual_model(self.dae)
        self.assertEqual(self.dae.read_bytes(), original)
        self.assertFalse(any(self.folder.glob("*.obj")))

    def test_gui_selects_dae_path_no_blender(self):
        from wii_ai_golf.inspector.gui import Inspector
        inst = object.__new__(Inspector)
        inst.root = object()
        with patch('wii_ai_golf.inspector.gui.filedialog.askopenfilename',
                   return_value=str(self.dae)), \
             patch('wii_ai_golf.inspector.gui.load_private_dae_visual_model') as loader, \
             patch('wii_ai_golf.inspector.textured_preview.TexturedPreviewWindow') as window:
            Inspector.open_textured_model(inst)
        loader.assert_called_once_with(str(self.dae))
        window.assert_called_once_with(inst.root, loader.return_value)


if __name__ == "__main__":
    unittest.main()
