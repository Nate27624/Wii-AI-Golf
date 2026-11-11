"""Synthetic UV/texture preview falsification tests; NEVER use original game assets."""
from __future__ import annotations
import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector.visual_model import (VisualAssetError, load_private_visual_model)
from wii_ai_golf.inspector.texture_render import render_preview, prepare_textures

# Tiny public-domain test PNG bytes (not Wii content), generated from a 1x1
# synthetic pixel. For rendering tests generate a 4x4 checker with Pillow.
PIXEL = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+UXZ0AAAAASUVORK5CYII=')
OBJ='''# synthetic UV geometry, not Wii data
mtllib field.mtl
o terrain
v 0 0 0
v 10 0 0
v 0 10 0
vt 0 0
vt 1 0
vt 0 1
usemtl grass
f 1/1 2/2 3/3
'''
MTL='''# synthetic material
newmtl grass
Kd 1 1 1
map_Kd grass.png
'''

class VisualAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.obj=self.root/'field.obj'
        self.mtl=self.root/'field.mtl'
        self.png=self.root/'grass.png'
        self.obj.write_text(OBJ,encoding='utf-8')
        self.mtl.write_text(MTL,encoding='utf-8')
        self.png.write_bytes(PIXEL)

    def test_uv_material_file_binding(self):
        model=load_private_visual_model(self.obj)
        self.assertEqual(model.vertices[1],(10.,0.,0.))
        self.assertEqual(model.uvs[2],(0.,1.))
        self.assertEqual(model.textured_face_count,1)
        self.assertEqual(model.faces[0].uvs,(0,1,2))
        self.assertEqual(model.textures['grass'].size,(1,1))
        self.assertEqual(model.obj_sha256,hashlib.sha256(self.obj.read_bytes()).hexdigest())

    def test_quad_triangulation_preserves_uv(self):
        self.obj.write_text(OBJ.replace('v 0 10 0','v 0 10 0\nv 10 10 0').replace('vt 0 1','vt 0 1\nvt 1 1').replace('f 1/1 2/2 3/3','f 1/1 2/2 4/4 3/3'))
        model=load_private_visual_model(self.obj)
        self.assertEqual(len(model.faces),2)
        self.assertEqual(model.faces[0].vertices,(0,1,3))
        self.assertEqual(model.faces[1].vertices,(0,3,2))
        self.assertEqual(model.faces[1].uvs,(0,3,2))

    def test_missing_uv_and_material_rejected(self):
        for contents in (OBJ.replace('f 1/1 2/2 3/3','f 1 2 3'),
                         OBJ.replace('usemtl grass\n',''),
                         OBJ.replace('vt 0 1\n',''),
                         OBJ.replace('mtllib field.mtl\n','')):
            with self.subTest(contents=contents[-60:]):
                self.obj.write_text(contents)
                with self.assertRaises(VisualAssetError):load_private_visual_model(self.obj)

    def test_outside_git_only(self):
        (self.root/'.git').mkdir()
        with self.assertRaisesRegex(VisualAssetError,'outside Git'):
            load_private_visual_model(self.obj)

    def test_mtl_parent_traversal_and_url_rejected(self):
        for mtl in ('map_Kd ../foo.png','map_Kd https://elsewhere.com/a.png','map_Kd /tmp/foo.png','map_Kd ..\\secret.png','map_Kd -s 1 1 1 grass.png'):
            self.mtl.write_text('newmtl grass\n'+mtl+'\n')
            with self.subTest(mtl=mtl),self.assertRaises(VisualAssetError):load_private_visual_model(self.obj)

    def test_symlink_and_unmatched_texture_rejected(self):
        link=self.root/'other.obj'
        try:link.symlink_to(self.obj)
        except (OSError,NotImplementedError):pass
        else:
            with self.assertRaises(VisualAssetError):load_private_visual_model(link)
        self.mtl.write_text(MTL.replace('grass.png','missing.png'))
        with self.assertRaises(VisualAssetError):load_private_visual_model(self.obj)

    def test_png_header_size_bounds(self):
        # Mutating only width in header violates safe 4K dimension bound,
        # even when image decoder has not been imported.
        damaged=bytearray(PIXEL)
        damaged[16:20]=(8192).to_bytes(4,'big')
        self.png.write_bytes(damaged)
        with self.assertRaises(VisualAssetError):load_private_visual_model(self.obj)

    def test_refuses_unsafe_obj_external_instructions(self):
        for addition in ('mtllib another.mtl','call ../evil','usemtl https://evil','f -3/-3 2/2 3/3',
                         'v NaN 0 0','usemtl other\nf 1/1 2/2 3/3'):
            self.obj.write_text(OBJ+'\n'+addition+'\n')
            with self.subTest(addition=addition),self.assertRaises(VisualAssetError):load_private_visual_model(self.obj)

    def test_texture_changes_block_renderer_reuse(self):
        model=load_private_visual_model(self.obj)
        self.png.write_bytes(PIXEL+b'junk')
        try:
            import PIL,numpy
        except ImportError:
            self.skipTest('Optional Pillow/NumPy unavailable')
        with self.assertRaisesRegex(VisualAssetError,'changed'):
            prepare_textures(model)

    def test_synthetic_uv_textured_triangle_renders(self):
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest('Optional Pillow/NumPy unavailable')
        Image.new('RGBA',(4,4),(13,188,91,255)).save(self.png)
        model=load_private_visual_model(self.obj)
        textures=prepare_textures(model)
        preview,n=render_preview(model,180,180,yaw=0.,pitch=0.,textures=textures)
        # Pitch 0 collapses geometry in XY? points x/y triangle -> works.
        self.assertEqual(n,1)
        arr=np.asarray(preview)
        self.assertTrue(((arr[:,:,0]==13)&(arr[:,:,1]==188)&(arr[:,:,2]==91)).any())
        with self.assertRaises(VisualAssetError):
            render_preview(model,10000,10000,textures=textures)


    def test_untextured_dae_material_uses_only_explicit_original_kd(self):
        # A real DAE has 12 materials, but only 11 texture slots. Never
        # fabricate a PNG for untextured M_Kiwa_Black. Use exported MTL Kd.
        self.obj.write_text(OBJ.replace('usemtl grass', 'usemtl M_Kiwa_Black'))
        self.mtl.write_text(MTL + 'newmtl M_Kiwa_Black\nKd 0.2 0.4 0.6\n')
        model = load_private_visual_model(self.obj)
        self.assertEqual(model.solid_colors['M_Kiwa_Black'], (51, 102, 153))
        self.assertNotIn('M_Kiwa_Black', model.textures)
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest('Optional Pillow/NumPy unavailable')
        preview, drawn = render_preview(model, 180, 180, yaw=0., pitch=0.)
        self.assertEqual(drawn, 1)
        arr = np.asarray(preview)
        self.assertTrue(((arr[:, :, 0] == 51) &
                         (arr[:, :, 1] == 102) &
                         (arr[:, :, 2] == 153)).any())

    def test_untextured_material_cannot_invent_or_accept_invalid_kd(self):
        self.obj.write_text(OBJ.replace('usemtl grass', 'usemtl M_Kiwa_Black'))
        for material in ('newmtl M_Kiwa_Black\n',
                         'newmtl M_Kiwa_Black\nKd NaN 0 0\n',
                         'newmtl M_Kiwa_Black\nKd 1.2 0 0\n',
                         'newmtl M_Kiwa_Black\nKd 0 0\n'):
            with self.subTest(material=material):
                self.mtl.write_text(MTL + material)
                with self.assertRaises(VisualAssetError):
                    load_private_visual_model(self.obj)

    def test_inspector_texture_button_is_explicit_and_does_not_touch_dolphin(self):
        try:
            from wii_ai_golf.inspector.gui import Inspector
        except ImportError:
            self.skipTest('Original inspector GUI not in isolated local stage')
        from unittest.mock import patch
        inspector = object.__new__(Inspector)
        inspector.root = object()
        with patch('wii_ai_golf.inspector.gui.filedialog.askopenfilename', return_value=str(self.obj)) as picker, \
             patch('wii_ai_golf.inspector.gui.load_private_visual_model') as load, \
             patch('wii_ai_golf.inspector.textured_preview.TexturedPreviewWindow') as preview:
            Inspector.open_textured_model(inspector)
            picker.assert_called_once()
            load.assert_called_once_with(str(self.obj))
            preview.assert_called_once_with(inspector.root, load.return_value)
        with patch('wii_ai_golf.inspector.gui.filedialog.askopenfilename', return_value='') as picker, \
             patch('wii_ai_golf.inspector.gui.load_private_visual_model') as load:
            Inspector.open_textured_model(inspector)
            load.assert_not_called()

if __name__=='__main__':unittest.main()
