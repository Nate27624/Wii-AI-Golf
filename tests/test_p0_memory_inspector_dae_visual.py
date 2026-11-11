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
from wii_ai_golf.inspector.collada_scene_graph import UnsupportedSceneFeature
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

    def test_source_dae_scene_matrix_180yaw_and_translation_now_applied(self):
        original = self.dae.read_bytes()
        scene_matrix = '<matrix>-1 0 0 0 0 1 0 0 0 0 -1 0 10 0 20 1</matrix>'
        self.dae.write_text(DAE.replace(
            '<node id="grass-node">',
            '<node id="grass-node">' + scene_matrix), encoding="utf-8")
        model = load_private_dae_visual_model(self.dae)
        self.assertEqual(model.vertices[:3],
                         ((10., 0., 20.), (2., 0., 20.), (10., 8., 20.)))
        self.assertEqual(model.faces[0].material, "M_Fairway")
        self.assertEqual(model.uvs[:3], ((0.,0.), (1.,0.), (0.,1.)))
        self.assertNotEqual(original, self.dae.read_bytes())
        self.assertEqual(model.obj_sha256,
                         hashlib.sha256(self.dae.read_bytes()).hexdigest())

    def test_nested_source_translate_rotate_are_combined(self):
        transformed = DAE.replace(
            '<node id="grass-node">',
            '<node id="root"><translate>10 0 20</translate>'
            '<node id="grass-node"><rotate>0 1 0 180</rotate>').replace(
            '</node></visual_scene>', '</node></node></visual_scene>')
        self.dae.write_text(transformed, encoding="utf-8")
        result = load_private_dae_visual_model(self.dae)
        self.assertAlmostEqual(result.vertices[0][0], 10.)
        self.assertAlmostEqual(result.vertices[0][2], 20.)
        self.assertAlmostEqual(result.vertices[1][0], 2.)
        self.assertAlmostEqual(result.vertices[1][2], 20.)

    def test_duplicate_source_geometry_instances_render_all_original_faces(self):
        self.dae.write_text(DAE.replace(
            '</node></visual_scene>',
            '<node id="second"><translate>10 0 20</translate>'
            '<instance_geometry url="#grass"/></node>'
            '</node></visual_scene>'),
            encoding="utf-8")
        visual = load_private_dae_visual_model(self.dae)
        self.assertEqual(len(visual.faces), 4)
        self.assertEqual(len(visual.vertices), 12)
        # First instance retains original vertices, second receives authored
        # local translation; source UV/materials preserved for every face.
        self.assertEqual(visual.vertices[:3],
                         ((0., 0., 0.), (8., 0., 0.), (0., 8., 0.)))
        self.assertEqual(visual.vertices[6:9],
                         ((10., 0., 20.), (18., 0., 20.), (10., 8., 20.)))

    def test_unsupported_source_scene_controller_fails_closed(self):
        self.dae.write_text(DAE.replace(
            '<node id="grass-node">',
            '<node id="grass-node"><instance_controller url="#unknown"/>'),
            encoding="utf-8")
        with self.assertRaisesRegex(VisualAssetError, "Unsupported original scene"):
            load_private_dae_visual_model(self.dae)

    def test_original_scene_instance_node_resolves_source_matrix(self):
        # Common Collada 1.5 source DAG reuse; no unproven flattening or
        # invented 180-degree world rotation. Parent @ referenced child.
        import re
        data=DAE.replace(
            '<library_visual_scenes>',
            '<library_nodes><node id="shared-ground">'
            '<translate>10 0 20</translate>'
            '<instance_geometry url="#grass"/>'
            '</node></library_nodes><library_visual_scenes>'
        )
        data,n=re.subn(
            r'<instance_geometry url="#grass">.*?</instance_geometry>',
            '<instance_node url="#shared-ground"/>',
            data, count=1, flags=re.S)
        self.assertEqual(n,1)
        self.dae.write_text(data,encoding="utf-8")
        model=load_private_dae_visual_model(self.dae)
        self.assertEqual(model.vertices[:3],
                         ((10.,0.,20.),(18.,0.,20.),(10.,8.,20.)))
        self.assertIsNone(model.source_scene_warning)
        self.assertIn("M_Fairway",model.textures)

    def test_original_scene_controller_compatibility_loads_real_png_with_warning(self):
        # Exact failure category seen in original course can be safely shown
        # as UNALIGNED geometry-library preview, NOT native scene/collision.
        modified=DAE.replace(
            '<node id="grass-node">',
            '<node id="grass-node"><instance_controller url="#golf-skin"/>')
        self.dae.write_text(modified,encoding="utf-8")
        with self.assertRaisesRegex(
                UnsupportedSceneFeature, "instance_controller"):
            load_private_dae_visual_model(self.dae)
        result=load_private_dae_visual_model(
            self.dae,allow_geometry_only_for_unsupported_scene=True)
        self.assertEqual(len(result.faces),2)
        self.assertEqual(result.textures["M_Fairway"].sha256,
                         hashlib.sha256(self.png.read_bytes()).hexdigest())
        self.assertEqual(result.obj_sha256,
                         hashlib.sha256(self.dae.read_bytes()).hexdigest())
        self.assertIn("GEOMETRY-ONLY",result.source_scene_warning)
        self.assertIn("instance_controller",result.source_scene_warning)
        self.assertIn("NOT APPLIED",result.source_scene_warning)

    def test_unsupported_source_lookat_skew_report_specific_feature(self):
        for element in (
            '<lookat>0 0 0 0 0 -1 0 1 0</lookat>',
            '<skew>45 1 0 0 0 1 0</skew>',
        ):
            self.dae.write_text(DAE.replace(
                '<node id="grass-node">','<node id="grass-node">'+element),
                encoding="utf-8")
            with self.subTest(element=element),self.assertRaisesRegex(
                    UnsupportedSceneFeature, element[1:].split(">")[0]):
                load_private_dae_visual_model(self.dae)

    def test_instance_node_cycle_and_external_ref_still_fail_closed(self):
        template=DAE.replace(
            '<node id="grass-node">',
            '<node id="grass-node"><instance_node url="DEST"/>')
        for target in ("#grass-node","https://evil.invalid/remote.dae#tree",
                       "#unknown-source"):
            self.dae.write_text(template.replace("DEST",target),encoding="utf-8")
            with self.subTest(target=target),self.assertRaises(VisualAssetError):
                load_private_dae_visual_model(
                    self.dae,allow_geometry_only_for_unsupported_scene=True)

    def test_external_controller_and_malformed_lookat_never_use_fallback(self):
        for record in (
            '<instance_controller url="https://invalid.example/evil.dae#skin"/>',
            '<lookat>0 0 0</lookat>',
            '<skew>nan 1 0 0 0 1 0</skew>',
        ):
            self.dae.write_text(
                DAE.replace('<node id="grass-node">',
                            '<node id="grass-node">'+record),
                encoding="utf-8")
            with self.subTest(record=record),self.assertRaises(VisualAssetError):
                load_private_dae_visual_model(
                    self.dae,allow_geometry_only_for_unsupported_scene=True)

    def test_gui_auto_compatibility_marks_geometry_only_unverified(self):
        from wii_ai_golf.inspector.gui import Inspector
        import types
        inst=object.__new__(Inspector)
        inst.root=Mock()
        inst.visual_tab=Mock()
        inst._legacy_terrain_tab=Mock()
        inst.visual_preview=None
        inst.visual_status=Mock()
        inst.terrain_mesh=None
        model=types.SimpleNamespace(
            source_name=self.dae.name,faces=[object(),object()],
            textures={"M_Fairway":object()},
            source_scene_warning=(
                "GEOMETRY-ONLY ORIGINAL-TEXTURE PREVIEW: unsupported controller"))
        with patch("wii_ai_golf.inspector.gui.load_private_dae_visual_model",
                   side_effect=[
                       UnsupportedSceneFeature(
                           "Unsupported original scene graph <instance_controller>"),
                       model]) as loader,patch(
                           "wii_ai_golf.inspector.textured_preview.TexturedPreviewWindow") as preview:
            self.assertTrue(Inspector.load_visual_path(inst,str(self.dae)))
        self.assertEqual(loader.call_count,2)
        self.assertTrue(loader.call_args_list[1].kwargs.get(
            "allow_geometry_only_for_unsupported_scene"))
        self.assertIn("GEOMETRY-ONLY",inst.visual_status.set.call_args.args[0])
        self.assertIs(inst.visual_preview,preview.return_value)

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

    def test_gui_embeds_dae_in_main_inspector_without_blender(self):
        from wii_ai_golf.inspector.gui import Inspector
        inst = object.__new__(Inspector)
        inst.root = object()
        inst.visual_tab = object()
        inst.visual_preview = None
        inst.visual_status = Mock()
        inst._legacy_terrain_tab = Mock()
        inst.visual_tab = Mock()
        with patch('wii_ai_golf.inspector.gui.load_private_dae_visual_model') as loader, \
             patch('wii_ai_golf.inspector.textured_preview.TexturedPreviewWindow') as window:
            loader.return_value.source_name = self.dae.name
            loader.return_value.faces = [object()]
            loader.return_value.textures = {"M_Fairway": object()}
            self.assertTrue(Inspector.load_visual_path(inst, str(self.dae)))
        loader.assert_called_once_with(str(self.dae))
        window.assert_called_once_with(inst.visual_tab, loader.return_value,
                                       embedded=True)
        inst._legacy_terrain_tab.pack_forget.assert_called_once()
        inst.visual_tab.pack.assert_called_once_with(fill="both", expand=True)
        self.assertIs(inst.visual_preview, window.return_value)

    def test_visual_path_stays_private_and_auto_discovered_only_beside_terrain(self):
        from wii_ai_golf.inspector.gui import _known_private_visual_candidate
        terrain = self.folder / "hole01-collision-candidate-PRIVATE.obj"
        terrain.write_text("dummy outside Git private collision source")
        target = self.folder / "WiiGolfVisualPrivate" / "visual_exports" / "glf_course_fc1"
        target.mkdir(parents=True)
        candidate = target / "glf_course_fc1.dae"
        candidate.write_text("synthetic original-source stand-in")
        self.assertEqual(_known_private_visual_candidate(str(terrain)), candidate)
        self.assertIsNone(_known_private_visual_candidate(""))
        candidate.unlink()
        self.assertIsNone(_known_private_visual_candidate(str(terrain)))


if __name__ == "__main__":
    unittest.main()
