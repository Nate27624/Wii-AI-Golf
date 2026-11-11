"""Fabricated-only identity and provenance controls for two in-flight archives."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "audit_p0_dual_airborne_archive_identity_private",
    ROOT / "scripts" / "audit_p0_dual_airborne_archive_identity_private.py")
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SMALL_BANKS = (
    ("MEM1", "mem1.raw", "FLIGHT-MEM1.bin", 40),
    ("MEM2", "mem2.raw", "FLIGHT-MEM2.bin", 64),
)


def create_example(root: Path, *, change: str | None = None) -> tuple:
    captures = root / "Wii-AI-Golf-Data" / "captures"
    captures.mkdir(parents=True)
    left = captures / m.HUMAN_ARCHIVE
    right = captures / "p0-airborne-case-PRIVATE"
    left.mkdir()
    right.mkdir()
    metadata = {
        "kind": "private-human-observed-in-flight-dolphin-dump",
        "banks_same_physics_frame_verified": False,
        "ball_xyz_verified": False,
        "training_approved": False,
        "files": [],
    }
    for label, left_name, right_name, n in SMALL_BANKS:
        data = bytes([31 if label == "MEM1" else 119]) * n
        (left / left_name).write_bytes(data)
        (right / right_name).write_bytes(
            (bytes([44]) * n) if change == label else data
        )
        metadata["files"].append({
            "file": left_name,
            "bytes": n,
            "copy_verified": True,
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    (left / m.LEFT_MANIFEST).write_text(json.dumps(metadata), encoding="utf8")
    (right / m.RIGHT_PROVENANCE).write_text(
        json.dumps({"kind": "different-operator-provenance", "safe": True}),
        encoding="utf8"
    )
    return captures, left, right


class ArchiveIdentityTests(unittest.TestCase):
    def test_identical_both_banks_only_proves_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            result = m.compare_archives(cap, a, b, banks=SMALL_BANKS)
            self.assertTrue(result["MEM1_equal"])
            self.assertTrue(result["MEM2_equal"])
            self.assertTrue(result["both_archives_same_bank_pair_bytes"])
            self.assertFalse(result["same_boot_verified"])
            self.assertFalse(result["both_banks_same_guest_frame_verified"])
            self.assertFalse(result["training_approved"])
            self.assertFalse(result["source_selected_ball_world_xyz_verified"])
            self.assertFalse(result["allowed_to_publish"])
            self.assertFalse(result["right_provenance_hash_schema_verified"])

    def test_mem1_only_difference(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root), change="MEM1")
            r = m.compare_archives(cap, a, b, banks=SMALL_BANKS)
            self.assertFalse(r["MEM1_equal"])
            self.assertTrue(r["MEM2_equal"])
            self.assertTrue(r["any_bank_different"])
            self.assertFalse(r["both_archives_same_bank_pair_bytes"])

    def test_mem2_only_difference(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root), change="MEM2")
            r = m.compare_archives(cap, a, b, banks=SMALL_BANKS)
            self.assertTrue(r["MEM1_equal"])
            self.assertFalse(r["MEM2_equal"])
            self.assertTrue(r["any_bank_different"])

    def test_corrupted_left_manifest_checksum_fails(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            manifest = a / m.LEFT_MANIFEST
            o = json.loads(manifest.read_text())
            o["files"][0]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(o))
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, b, banks=SMALL_BANKS)

    def test_manifest_false_verified_physics_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            manifest = a / m.LEFT_MANIFEST
            o = json.loads(manifest.read_text())
            o["banks_same_physics_frame_verified"] = True
            manifest.write_text(json.dumps(o))
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, b, banks=SMALL_BANKS)

    def test_missing_right_provenance_refused(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            (b / m.RIGHT_PROVENANCE).unlink()
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, b, banks=SMALL_BANKS)

    def test_missing_or_wrong_bank_size_refused(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            (b / "FLIGHT-MEM1.bin").write_bytes(b"x")
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, b, banks=SMALL_BANKS)

    def test_same_archive_and_external_path_refused(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, a, banks=SMALL_BANKS)
            external = cap.parent / "external"
            external.mkdir()
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, external, banks=SMALL_BANKS)

    def test_multiple_right_archives_fails_without_guessing(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            (cap / "p0-airborne-second-PRIVATE").mkdir()
            code = m.main(["--captures-root", str(cap), "--left-archive", str(a)])
            self.assertEqual(code, 2)

    def test_absolute_paths_and_hashes_not_serialized(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            result = m.compare_archives(cap, a, b, banks=SMALL_BANKS)
            output = json.dumps(result)
            self.assertNotIn(str(cap), output)
            self.assertNotIn("FLIGHT-MEM1.bin", output)
            self.assertNotIn(m.HUMAN_ARCHIVE, output)
            self.assertNotIn("p0-airborne-case-PRIVATE", output)
            self.assertNotIn(hashlib.sha256(bytes([31]) * 40).hexdigest(), output)

    def test_symlink_bank_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            src = b / "FLIGHT-MEM1.bin"
            new = b / "source"
            src.rename(new)
            try:
                src.symlink_to(new)
            except OSError:
                self.skipTest("OS does not permit symlink creation")
            with self.assertRaises(m.Abstain):
                m.compare_archives(cap, a, b, banks=SMALL_BANKS)

    def test_cli_prints_only_sanitized_json(self):
        with tempfile.TemporaryDirectory() as root:
            cap, a, b = create_example(Path(root))
            with mock.patch.object(m, "BANKS", SMALL_BANKS):
                with mock.patch("sys.stdout") as stdout:
                    code = m.main(["--captures-root", str(cap)])
            self.assertEqual(code, 0)
            blob = "".join(str(call.args[0]) for call in stdout.write.call_args_list)
            self.assertNotIn(str(cap), blob)
            self.assertNotIn("sha256", blob)
            self.assertIn("both_archives_same_bank_pair_bytes", blob)


if __name__ == "__main__":
    unittest.main()
