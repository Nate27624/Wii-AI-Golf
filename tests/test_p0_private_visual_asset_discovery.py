"""Synthetic-only local asset discovery. Never loads game or Nintendo data."""
import base64
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location(
    "p0_private_visual_asset_discovery",
    ROOT / "scripts" / "p0_private_visual_asset_discovery.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+UXZ0AAAAASUVORK5CYII=")
OBJ = (
    "mtllib course.mtl\n"
    "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
    "vt 0 0\nvt 1 0\nvt 0 1\n"
    "usemtl original_type\nf 1/1 2/2 3/3\n")
MTL = "newmtl original_type\nmap_Kd original.png\n"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "PrivateVisual"
        self.root.mkdir()

    def save(self, name, data):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def test_empty_scan_does_not_claim_model(self):
        result = mod.scan(self.root)
        self.assertEqual(result["stage"], "NO_COURSE_VISUAL_ASSETS_FOUND")
        self.assertFalse(result["source_hole_and_alignment_verified"])
        self.assertFalse(result["training_approved"])

    def test_archive_magic_remains_a_candidate(self):
        self.save("Stage/RPGolScene/course_foo.carc", b"Yaz0" + b"\x00"*20)
        found = mod.scan(self.root)
        self.assertEqual(found["stage"], "ARCHIVES_FOUND_NEEDS_FORMAT_VERIFIED_EXTRACTION")
        self.assertEqual(found["archive_headers"]["YAZ0_COMPRESSED"], 1)
        self.assertFalse(found["ready_uv_models"])

    def test_raw_brres_discovery_never_auto_claims_correct_hole(self):
        self.save("glf_course_random.brres", b"bres" + b"\x00"*20)
        found = mod.scan(self.root)
        self.assertEqual(found["stage"], "BRRES_FOUND_NEEDS_MDL0_TEX0_EXPORT")
        self.assertEqual(found["archive_headers"]["BRRES"], 1)
        self.assertFalse(found["source_hole_and_alignment_verified"])

    def test_dae_precedes_archive_for_model_export_guidance(self):
        self.save("course.dae", b"synthetic DAE")
        self.save("sample.carc", b"Yaz0" + b"\x00"*8)
        found = mod.scan(self.root)
        self.assertEqual(found["stage"], "DAE_FOUND_NEEDS_UV_OBJ_MTL_PNG_CONVERSION")

    def test_real_uv_mtl_png_set_is_preview_ready_not_hole_verified(self):
        obj = self.save("hole01/course.obj", OBJ.encode("ascii"))
        self.save("hole01/course.mtl", MTL.encode("ascii"))
        self.save("hole01/original.png", PNG)
        result = mod.scan(self.root)
        self.assertEqual(result["stage"], "UV_VISUAL_MODELS_READY_TO_PREVIEW_HOLE_UNVERIFIED")
        self.assertEqual(result["ready_uv_models"][0]["uv_faces"], 1)
        self.assertEqual(result["ready_uv_models"][0]["png_textures"], 1)
        self.assertFalse(result["ready_uv_models"][0]["hole_verified"])
        check = mod.check_model(obj)
        self.assertEqual(check["status"], "READY_PRIVATE_TEXTURE_PREVIEW")

    def test_collision_obj_without_uv_never_marked_ready(self):
        self.save("hole01-collision-PRIVATE.obj",
                  b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        self.assertEqual(mod.scan(self.root)["stage"], "NO_COURSE_VISUAL_ASSETS_FOUND")

    def test_never_follow_symlinked_dirs(self):
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside) / "other"
            other.mkdir()
            (other / "secret.brres").write_bytes(b"bres" + b"\x00"*10)
            link = self.root / "linked"
            try:
                link.symlink_to(other, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation privilege unavailable")
            self.assertEqual(mod.scan(self.root)["count_by_extension"], {})

    def test_git_nested_rejected_if_root_itself_is_git(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(ValueError):
            mod.scan(self.root)

    def test_filename_only_is_not_evidence(self):
        self.save("glf_course_hole1.brres", b"bogus")
        report = mod.scan(self.root)
        self.assertEqual(report["archive_headers"]["UNRECOGNIZED_HEADER"], 1)
        self.assertFalse(report["source_hole_and_alignment_verified"])


if __name__ == "__main__":
    unittest.main()
