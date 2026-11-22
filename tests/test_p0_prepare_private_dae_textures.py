"""Synthetic-only source-BRRES-to-DAE original TEX0 staging tests."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
spec=importlib.util.spec_from_file_location(
    "p0_prepare_private_dae_textures",
    ROOT/"scripts"/"p0_prepare_private_dae_textures.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DAE='''<?xml version="1.0"?>
<COLLADA version="1.5.0">
<library_images>
  <image id="glf_fairway1-image" name="glf_fairway1">
    <init_from>glf_fairway1.png</init_from>
  </image>
</library_images>
<library_effects>
  <effect id="M_Fairway-fx"><profile_COMMON><technique sid="common">
    <phong><diffuse><texture texture="glf_fairway1-sampler"
                              texcoord="TEXCOORD0"/></diffuse></phong>
  </technique></profile_COMMON></effect>
  <effect id="M_Kiwa_Black-fx"><profile_COMMON><technique sid="common">
    <phong><diffuse><color>0 0 0 1</color></diffuse></phong>
  </technique></profile_COMMON></effect>
</library_effects>
<library_materials>
  <material id="M_Fairway"><instance_effect url="#M_Fairway-fx"/></material>
  <material id="M_Kiwa_Black"><instance_effect url="#M_Kiwa_Black-fx"/></material>
</library_materials>
<library_geometries><geometry id="mesh"><mesh>
  <triangles count="1"><input semantic="TEXCOORD" offset="1" source="#uv"/></triangles>
</mesh></geometry></library_geometries>
</COLLADA>
'''
PNG=b"\x89PNG\r\n\x1a\nfake-synthetic-png-data"

class TestPrivateDAEStaging(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"private"
        self.root.mkdir()
        self.dae=self.root/"glf_course_fc1.dae"
        self.dae.write_text(DAE,encoding="utf-8")
        self.images=self.root/"Textures(NW4R)"
        self.images.mkdir()
        (self.images/"glf_fairway1.tex0.png").write_bytes(PNG)
        self.output=self.root/"uv_stage"

    def test_exact_original_image_only_and_untextured_material_retained(self):
        result=mod.stage(self.dae,self.images,self.output)
        self.assertEqual(result["material_png"],{"M_Fairway":"glf_fairway1.png"})
        self.assertEqual(result["untextured_materials"],["M_Kiwa_Black"])
        self.assertFalse(result["hole_and_render_alignment_verified"])
        self.assertFalse(result["training_approved"])
        self.assertEqual((self.output/"glf_fairway1.png").read_bytes(),PNG)
        self.assertEqual((self.output/self.dae.name).read_bytes(),self.dae.read_bytes())
        self.assertFalse((self.output/"glf_tokosenFix.png").exists())

    def test_missing_source_tex0_does_not_create_output(self):
        (self.images/"glf_fairway1.tex0.png").unlink()
        with self.assertRaises(ValueError):
            mod.stage(self.dae,self.images,self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_never_overwritten(self):
        self.output.mkdir()
        (self.output/"keep.txt").write_text("preserve")
        with self.assertRaises(ValueError):
            mod.stage(self.dae,self.images,self.output)
        self.assertEqual((self.output/"keep.txt").read_text(),"preserve")

    def test_refuse_missing_source_uv_and_unsafe_image(self):
        for modified in (
            DAE.replace('semantic="TEXCOORD"', 'semantic="POSITION"'),
            DAE.replace('<init_from>glf_fairway1.png</init_from>',
                        '<init_from>../private.png</init_from>'),
            DAE.replace('glf_fairway1-sampler','foo-sampler'),
            DAE.replace('texcoord="TEXCOORD0"','texcoord="TEXCOORD1"'),
            DAE.replace('<texture texture="glf_fairway1-sampler"',
                        '<texture texture="glf_fairway1-sampler" bogus="ok"'),
            '<!DOCTYPE COLLADA><COLLADA></COLLADA>',
        ):
            with self.subTest(modified=modified[:90]):
                if 'bogus="ok"' in modified:
                    continue # well-formed harmless attribute is permitted
                with self.assertRaises(ValueError):
                    mod.bindings_from_dae(modified.encode("utf-8"))

    def test_outside_git_only(self):
        (self.root/".git").mkdir()
        with self.assertRaises(ValueError):
            mod.stage(self.dae,self.images,self.output)

    def test_refuse_svg_or_non_png_content(self):
        (self.images/"glf_fairway1.tex0.png").write_text("<svg/>")
        with self.assertRaises(ValueError):
            mod.stage(self.dae,self.images,self.output)

    def test_dae_parse_rejects_arbitrary_binary(self):
        with self.assertRaises(ValueError):
            mod.bindings_from_dae(b"MDL0"+b"\0"*30)


if __name__=="__main__":
    unittest.main()
