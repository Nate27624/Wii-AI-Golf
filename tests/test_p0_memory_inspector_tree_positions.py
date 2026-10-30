"""Offline synthetic safety/shape tests for private 94-tree inspector overlay data."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "src" / "wii_ai_golf" / "inspector" / "tree_positions.py"
# Import through package, like the real UI.
import sys
sys.path.insert(0, str(MODULE.parents[2]))
from wii_ai_golf.inspector.tree_positions import (
    EXPECTED_NAME, TreePositionsError, load_private_tree_positions,
)


def payload():
    return {
        "kind": "wii_sports_golf_private_tree_positions_v1",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "source_captures": [1, 5, 7],
        "source_count": 94,
        "source_element_stride_bytes": 84,
        "source_translation_offset_bytes": 48,
        "position_frame": "original_source_components_no_transform",
        "tree_positions": [[i * 10.0, float(i % 7), i * 15.0] for i in range(94)],
        "source_positions_bitwise_identical_across_captures": True,
        "world_visual_alignment_verified": False,
        "original_tree_meshes_verified": False,
        "collision_hitboxes_verified": False,
        "training_approved": False,
    }


class PrivateTreeOverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "Wii-AI-Golf-Data"
        self.folder = self.data / "derived"
        self.folder.mkdir(parents=True)
        self.path = self.folder / EXPECTED_NAME

    def put(self, obj=None):
        self.path.write_text(json.dumps(payload() if obj is None else obj), "utf-8")

    def test_valid_exact_source_contract(self):
        self.put()
        obj = load_private_tree_positions(self.path)
        self.assertEqual(len(obj.positions),94)
        self.assertEqual(obj.positions[17],(170.0,3.0,255.0))
        self.assertEqual(obj.drawing_positions(),obj.positions)
        self.assertEqual(len(obj.sha256),64)
        self.assertFalse(obj.visual_alignment_verified)
        self.assertFalse(obj.tree_models_verified)
        self.assertFalse(obj.collision_hitboxes_verified)
        self.assertFalse(obj.training_approved)

    def test_reject_mismatched_count(self):
        d = payload()
        d["source_count"] = 93
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_missing_position(self):
        d = payload()
        d["tree_positions"].pop()
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_duplicate_position(self):
        d = payload()
        d["tree_positions"][93] = d["tree_positions"][0]
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_nonfinite_coordinate(self):
        d = payload()
        d["tree_positions"][3][1] = float("nan")
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_infinite_coordinate(self):
        d = payload()
        d["tree_positions"][3][1] = float("inf")
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_boolean_as_numeric(self):
        d = payload()
        d["tree_positions"][3][1] = True
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_out_of_bound_coordinate(self):
        d = payload()
        d["tree_positions"][3][1] = 1e10
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_extra_json_key(self):
        d = payload()
        d["covert_remote_url"] = "https://example.com"
        self.put(d)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_modified_source_provenance(self):
        for field, wrong in (
            ("source_element_stride_bytes", 80),
            ("source_translation_offset_bytes", 64),
            ("game_id", "WRONG"),
            ("source_captures", [1, 2, 7]),
            ("source_positions_bitwise_identical_across_captures", False),
            ("training_approved", True),
            ("world_visual_alignment_verified", True),
            ("collision_hitboxes_verified", True),
        ):
            with self.subTest(field=field):
                d=payload()
                d[field]=wrong
                self.put(d)
                with self.assertRaises(TreePositionsError):
                    load_private_tree_positions(self.path)

    def test_reject_duplicate_json_key(self):
        d = json.dumps(payload())
        # Duplicate top-level kind should be caught even when equal.
        self.path.write_text(d[:-1]+',"kind":"wii_sports_golf_private_tree_positions_v1"}', "utf-8")
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_private_file_in_git_folder(self):
        (self.data / ".git").mkdir()
        self.put()
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)

    def test_reject_wrong_private_filename(self):
        self.put()
        renamed=self.folder/"not-tree-positions.json"
        self.path.rename(renamed)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(renamed)

    def test_reject_wrong_private_data_root(self):
        self.put()
        other=Path(self.tmp.name)/"OtherProject"/"derived"
        other.mkdir(parents=True)
        target=other/EXPECTED_NAME
        self.path.rename(target)
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(target)

    def test_reject_symlink_to_private_file(self):
        self.put()
        alias=self.folder/"tree-alias.json"
        try:
            alias.symlink_to(self.path)
        except (OSError,NotImplementedError):
            self.skipTest("Host cannot create symlink")
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(alias)

    def test_reject_symlink_data_directory(self):
        self.put()
        other=Path(self.tmp.name)/"OtherProject"/"derived"
        other.mkdir(parents=True)
        alias=other/EXPECTED_NAME
        try:
            alias.symlink_to(self.path)
        except (OSError,NotImplementedError):
            self.skipTest("Host cannot create symlink")
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(alias)

    def test_reject_oversized_file(self):
        self.path.write_bytes(b"x"*(65536+1))
        with self.assertRaises(TreePositionsError):
            load_private_tree_positions(self.path)


if __name__ == "__main__":
    unittest.main()
