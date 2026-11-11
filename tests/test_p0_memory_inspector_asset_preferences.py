"""Synthetic saved private asset-path persistence; no Dolphin or original files."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.inspector.asset_preferences import (
    AssetSelections, SavedAssetError, discover_private_tree, load_asset_selections,
    remember_asset, save_asset_selections, local_settings_path,
)
from wii_ai_golf.inspector.tree_positions import EXPECTED_NAME
from test_p0_memory_inspector_tree_positions import payload


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.settings = self.base / "config" / "inspector-assets-v1.json"
        self.data = self.base / "Wii-AI-Golf-Data" / "derived"
        self.data.mkdir(parents=True)
        self.tree = self.data / EXPECTED_NAME
        self.tree.write_text(json.dumps(payload()), encoding="utf-8")
        self.obj = self.base / "terrain-PRIVATE.obj"
        self.obj.write_text("v 0 0 0\nv 1 0 0\nv 0 0 1\nf 1 2 3\n", encoding="ascii")

    def test_absent_settings_first_run_enables_auto_discovery(self):
        found = load_asset_selections(self.settings)
        self.assertIsNone(found.tree_json)
        self.assertTrue(found.auto_find_trees)
        self.assertIsNone(found.terrain_obj)

    def test_round_trip_only_paths_and_disabled_flags(self):
        state = AssetSelections()
        state = remember_asset(state, "tree_json", self.tree)
        state = remember_asset(state, "terrain_obj", self.obj)
        self.assertTrue(state.auto_find_trees)
        save_asset_selections(state, self.settings)
        reopened = load_asset_selections(self.settings)
        self.assertEqual(state, reopened)
        raw = self.settings.read_text("utf-8")
        self.assertEqual(json.loads(raw)["tree_json"], str(self.tree.resolve()))
        self.assertEqual(json.loads(raw)["terrain_obj"], str(self.obj.resolve()))
        self.assertNotIn("tree_positions", raw)
        self.assertNotIn("training_approved", raw)
        self.assertNotIn("170.0", raw)
        self.assertFalse(list(self.settings.parent.glob("*.tmp")))

    def test_tree_clear_prevents_auto_rediscovery(self):
        saved = remember_asset(AssetSelections(), "tree_json", self.tree)
        cleared = remember_asset(saved, "tree_json", None)
        self.assertIsNone(cleared.tree_json)
        self.assertFalse(cleared.auto_find_trees)
        save_asset_selections(cleared, self.settings)
        reopened = load_asset_selections(self.settings)
        self.assertFalse(reopened.auto_find_trees)
        self.assertIsNone(reopened.tree_json)

    def test_terrain_clear_preserves_tree_file(self):
        state = remember_asset(AssetSelections(), "tree_json", self.tree)
        state = remember_asset(state, "terrain_obj", self.obj)
        cleared = remember_asset(state, "terrain_obj", None)
        self.assertIsNone(cleared.terrain_obj)
        self.assertEqual(cleared.tree_json, str(self.tree.resolve()))

    def test_autodiscover_only_expected_source_file(self):
        checkout = self.base / "Wii-Golf-Tree-PR432"
        checkout.mkdir()
        self.assertEqual(discover_private_tree(checkout).resolve(), self.tree.resolve())
        self.tree.unlink()
        self.assertIsNone(discover_private_tree(checkout))
        self.tree.write_text(json.dumps({"some_other_source": "not original"}))
        self.assertIsNone(discover_private_tree(checkout))

    def test_discover_refuses_git_private_data_and_symlinks(self):
        checkout = self.base / "Wii-Golf-Tree-PR432"
        checkout.mkdir(exist_ok=True)
        (self.base / ".git").mkdir()
        self.assertIsNone(discover_private_tree(checkout))
        (self.base / ".git").rmdir()
        self.tree.unlink()
        external = self.base / "outside.json"
        external.write_text(json.dumps(payload()))
        try:
            self.tree.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not available on this Windows runner")
        self.assertIsNone(discover_private_tree(checkout))

    def test_missing_saved_asset_path_is_not_replaced_with_guess(self):
        state = remember_asset(AssetSelections(), "tree_json", self.tree)
        self.tree.unlink()
        save_asset_selections(state, self.settings)
        restored = load_asset_selections(self.settings)
        self.assertEqual(restored.tree_json, str(self.tree.resolve()))
        self.assertFalse(self.tree.exists())

    def test_refuse_malformed_settings_and_extra_fields(self):
        self.settings.parent.mkdir(parents=True)
        for text in ('{', json.dumps({"version": 1}), json.dumps({
                "version": 1, "terrain_obj": None, "tree_json": None,
                "auto_find_trees": True, "unexpected": True,
                }), json.dumps({
                "version": True, "terrain_obj": None, "tree_json": None,
                "auto_find_trees": True,
                })):
            with self.subTest(text=text):
                self.settings.write_text(text)
                with self.assertRaises(SavedAssetError):
                    load_asset_selections(self.settings)

    def test_refuse_relative_or_unsafe_paths(self):
        for bad in ("relative/file.obj", "\n", "", 1, False):
            with self.subTest(path=bad):
                with self.assertRaises(SavedAssetError):
                    save_asset_selections(AssetSelections(terrain_obj=bad), self.settings)
        with self.assertRaises(SavedAssetError):
            remember_asset(AssetSelections(), "evil", self.obj)

    def test_refuse_oversized_settings(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_bytes(b"x" * 8193)
        with self.assertRaises(SavedAssetError):
            load_asset_selections(self.settings)

    def test_settings_file_symlink_is_refused(self):
        self.settings.parent.mkdir(parents=True)
        other = self.base / "other.json"
        other.write_text("{}")
        try:
            self.settings.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink privileges unavailable")
        with self.assertRaises(SavedAssetError):
            load_asset_selections(self.settings)
        with self.assertRaises(SavedAssetError):
            save_asset_selections(AssetSelections(), self.settings)

    def test_settings_path_is_outside_checkout(self):
        import os
        with patch.dict("os.environ", {
            "XDG_CONFIG_HOME": str(self.base / "xdg"),
            "LOCALAPPDATA": str(self.base / "local"),
        }, clear=False):
            path = local_settings_path()
        if os.name == "nt":
            self.assertEqual(path, self.base / "local" / "WiiAIGolf" / "inspector-assets-v1.json")
        else:
            self.assertEqual(path, self.base / "xdg" / "wii-ai-golf" / "inspector-assets-v1.json")
        self.assertNotIn("Wii-Golf-Tree-PR432", str(path))


class FakeStatus:
    def __init__(self, value=""):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class GuiRestorationTests(SelectionTests):
    def fake_inspector(self):
        from wii_ai_golf.inspector.gui import Inspector
        inspector = Inspector.__new__(Inspector)
        inspector.saved_assets = AssetSelections()
        inspector.terrain_status = FakeStatus()
        inspector.tree_status = FakeStatus()
        inspector.asset_settings_status = FakeStatus()
        inspector.tree_visible = FakeStatus(False)
        inspector.terrain_visible = FakeStatus(False)
        inspector.terrain_mesh = None
        inspector.tree_positions = None
        inspector.draw_path = lambda: None
        return inspector

    def test_reopen_reloads_both_with_no_dialog(self):
        from wii_ai_golf.inspector.gui import Inspector
        state = remember_asset(AssetSelections(), "terrain_obj", self.obj)
        state = remember_asset(state, "tree_json", self.tree)
        inspector = self.fake_inspector()
        with patch("wii_ai_golf.inspector.gui.load_asset_selections", return_value=state), patch(
                "wii_ai_golf.inspector.gui.discover_private_tree") as discover:
            Inspector.restore_private_assets(inspector)
            discover.assert_not_called()
        self.assertIsNotNone(inspector.tree_positions)
        self.assertEqual(len(inspector.tree_positions.positions), 94)
        self.assertIsNotNone(inspector.terrain_mesh)
        self.assertTrue(inspector.tree_visible.get())
        self.assertTrue(inspector.terrain_visible.get())

    def test_cleared_trees_not_auto_discovered(self):
        from wii_ai_golf.inspector.gui import Inspector
        inspector = self.fake_inspector()
        cleared = AssetSelections(auto_find_trees=False)
        with patch("wii_ai_golf.inspector.gui.load_asset_selections", return_value=cleared), patch(
                "wii_ai_golf.inspector.gui.discover_private_tree") as discover:
            Inspector.restore_private_assets(inspector)
            discover.assert_not_called()
        self.assertIsNone(inspector.tree_positions)

    def test_invalid_saved_tree_does_not_discover_others(self):
        from wii_ai_golf.inspector.gui import Inspector
        inspector = self.fake_inspector()
        saved = remember_asset(AssetSelections(), "tree_json", self.tree)
        self.tree.unlink()
        with patch("wii_ai_golf.inspector.gui.load_asset_selections", return_value=saved), patch(
                "wii_ai_golf.inspector.gui.discover_private_tree") as discover:
            Inspector.restore_private_assets(inspector)
            discover.assert_not_called()
        self.assertIsNone(inspector.tree_positions)
        self.assertIn("not loaded", inspector.tree_status.get())

    def test_first_start_detects_safe_original_private_tree(self):
        from wii_ai_golf.inspector.gui import Inspector
        inspector = self.fake_inspector()
        with patch("wii_ai_golf.inspector.gui.load_asset_selections", return_value=AssetSelections()), patch(
                "wii_ai_golf.inspector.gui.discover_private_tree", return_value=self.tree), patch(
                "wii_ai_golf.inspector.gui.save_asset_selections") as write:
            Inspector.restore_private_assets(inspector)
            write.assert_called_once()
        self.assertEqual(len(inspector.tree_positions.positions), 94)


if __name__ == "__main__":
    unittest.main()
