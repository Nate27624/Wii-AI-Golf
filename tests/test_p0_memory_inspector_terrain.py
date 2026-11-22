"""Synthetic private OBJ loader tests; no real game geometry."""
import tempfile
import unittest
import subprocess
from unittest.mock import patch
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector.terrain import TerrainError,load_private_obj,surface_style,NEUTRAL,TerrainMesh
GOOD='# synthetic terrain\nv 0 1 0\nv 20 1 0\nv 0 1 20\nf 1 2 3\n'

class TerrainTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'private.obj';self.path.write_text(GOOD,encoding='ascii')
    def test_original_golf_surface_groups_preserve_face_order(self):
        self.path.write_text(GOOD.replace('f 1 2 3',
            'g KCL_OGWS_0001\nf 1 2 3\ng KCL_OGWS_0006\nf 1 3 2\ng KCL_OGWS_0007\nf 1 2 3'))
        mesh=load_private_obj(self.path)
        self.assertEqual(mesh.face_materials,(1,6,7))
        self.assertEqual(mesh.material_counts(),{1:1,6:1,7:1})
        self.assertEqual([m for _,m in mesh.drawing_colored_faces(focused=False)], [1,6,7])
        self.assertEqual(surface_style(6)[0],'Green')
        self.assertNotEqual(surface_style(1)[1],surface_style(7)[1])

    def test_decimation_keeps_original_face_material_alignment(self):
        groups=''.join('g KCL_OGWS_%04X\nf 1 2 3\n' % (6 if i%2 else 2) for i in range(20))
        self.path.write_text(GOOD.split('f 1 2 3')[0]+groups)
        mesh=load_private_obj(self.path)
        self.assertEqual([m for _,m in mesh.drawing_colored_faces(limit=5,focused=False)], [2]*5)
        self.assertEqual(len(mesh.drawing_faces(limit=5,focused=False)),5)

    def test_legacy_obj_is_neutral_not_fairway_guess(self):
        mesh=load_private_obj(self.path)
        self.assertEqual(mesh.material_counts(),{None:1})
        self.assertEqual(mesh.drawing_colored_faces()[0][1],None)
        self.assertEqual(surface_style(None),NEUTRAL)

    def test_unknown_and_camera_lock_ids_remain_neutral(self):
        self.path.write_text(GOOD.replace('f 1 2 3','g KCL_OGWS_0005\nf 1 2 3\ng KCL_OGWS_1234\nf 1 2 3'))
        mesh=load_private_obj(self.path)
        self.assertEqual(mesh.face_materials,(5,0x1234))
        self.assertEqual(surface_style(5),NEUTRAL)
        self.assertEqual(surface_style(0x1234),NEUTRAL)

    def test_rejects_non_source_groups_and_material_injection(self):
        for directive in ('g fairway', 'g KCL_OGWS_6', 'g KCL_OGWS_0006\nusemtl x',
                          'g KCL_OGWS_0006 other', 'o terrain',
                          'g KCL_OGWS_zzzz', 'g KCL_OGWS_0006\nmtllib ./unsafe.mtl'):
            with self.subTest(directive=directive):
                self.path.write_text(GOOD+directive+'\n')
                with self.assertRaises(TerrainError):load_private_obj(self.path)

    def test_materials_do_not_override_file_integrity_or_path_safety(self):
        self.path.write_text(GOOD.replace('f 1 2 3','g KCL_OGWS_0003\nf 1 2 3'))
        baseline=load_private_obj(self.path)
        self.path.write_text(GOOD.replace('f 1 2 3','g KCL_OGWS_0007\nf 1 2 3'))
        changed=load_private_obj(self.path)
        self.assertNotEqual(baseline.sha256,changed.sha256)
        (self.path.parent/'.git').mkdir()
        with self.assertRaises(TerrainError):load_private_obj(self.path)

    def test_invalid_face_material_length_abstains(self):
        good=load_private_obj(self.path)
        bad=TerrainMesh(good.vertices,good.faces,good.sha256,good.source_name,(1,2))
        with self.assertRaises(TerrainError):bad.drawing_colored_faces()
        with self.assertRaises(TerrainError):bad.material_counts()

    def test_ogws_palette_distinguishes_major_regions(self):
        values=[1,2,3,4,6,7,9,12]
        self.assertEqual(len(set(surface_style(x)[1] for x in values)),len(values))
        self.assertEqual(surface_style(0xFFFE),NEUTRAL)

    def test_load(self):
        t=load_private_obj(self.path);self.assertEqual(len(t.faces),1);self.assertEqual(len(t.sha256),64)
        self.assertEqual(len(t.drawing_faces()),1)
    def test_focus(self):
        t=load_private_obj(self.path);self.assertEqual(len(t.drawing_faces(((2.,1.,2.),))),1)
        self.assertEqual(len(t.drawing_faces(((2000.,1.,2000.),))),0)
        self.assertEqual(len(t.drawing_faces(((2000.,1.,2000.),),focused=False)),1)
    def test_degenerate(self):
        self.path.write_text(GOOD.replace('v 0 1 20','v 20 1 0'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_nan(self):
        self.path.write_text(GOOD.replace('v 0 1 20','v NaN 1 20'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_index(self):
        self.path.write_text(GOOD.replace('f 1 2 3','f 1 2 44'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_face_quad(self):
        self.path.write_text(GOOD.replace('f 1 2 3','f 1 2 3 2'))
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_symlink(self):
        link = self.path.with_name('alias.obj')
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest('Host cannot create symbolic links')
        with self.assertRaises(TerrainError):
            load_private_obj(link)

    def test_symlink_validation_without_privilege(self):
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(TerrainError):
                load_private_obj(self.path)
    def test_git_inside_forbidden(self):
        (self.path.parent/'.git').mkdir()
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_untracked_ignored_project_private_colored_obj(self):
        with tempfile.TemporaryDirectory() as dirname:
            repo = Path(dirname)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            derived = repo / 'Wii-AI-Golf-Data' / 'derived'
            derived.mkdir(parents=True)
            (derived / '.gitignore').write_text('*.obj\n', encoding='ascii')
            local = derived / 'hole01-collision-colored-PRIVATE.obj'
            local.write_text(GOOD.replace('f 1 2 3',
                             'g KCL_OGWS_0006\nf 1 2 3'), encoding='ascii')
            mesh = load_private_obj(local)
            self.assertEqual(mesh.face_materials, (6,))

    def test_tracked_or_unignored_colored_obj_rejected(self):
        with tempfile.TemporaryDirectory() as dirname:
            repo = Path(dirname)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            derived = repo / 'Wii-AI-Golf-Data' / 'derived'
            derived.mkdir(parents=True)
            local = derived / 'hole01-collision-colored-PRIVATE.obj'
            local.write_text(GOOD, encoding='ascii')
            with self.assertRaises(TerrainError):
                load_private_obj(local)
            subprocess.run(['git', '-C', str(repo), 'add', '-f', '--', str(local)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (derived / '.gitignore').write_text('*.obj\n', encoding='ascii')
            with self.assertRaises(TerrainError):
                load_private_obj(local)

    def test_only_plain_obj(self):
        self.path.write_text(GOOD+'mtllib bad.mtl\n')
        with self.assertRaises(TerrainError):load_private_obj(self.path)
    def test_decimation_limit(self):
        self.path.write_text(GOOD+('f 1 2 3\n'*150))
        t=load_private_obj(self.path)
        self.assertLessEqual(len(t.drawing_faces(limit=7)),7)
        with self.assertRaises(TerrainError):t.drawing_faces(limit=100000)
if __name__=='__main__':unittest.main()
