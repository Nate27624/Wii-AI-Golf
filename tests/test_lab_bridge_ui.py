"""The Game Testing view must show truthful bridge findings IN the Lab window.

No Dolphin, RPC, GUI display, or GitHub connection is required.
"""
from __future__ import annotations
import inspect
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.lab.bridge_ui import inspect_game_bridges
from wii_ai_golf.lab import gui
from wii_ai_golf.shared.bridge_provenance import (
    ATOMIC, SWING_V1, NEUTRAL_V2, AUTOLOAD,
    prepare_isolated_legacy_bridge,
)


class BridgeScreenTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name) / "Wii-AI-Golf"
        self.root.mkdir()
        folder = self.root.parent / "tools"
        folder.mkdir()
        self.active = folder / "mcp_bridge_swing.py"
        self.backup = folder / "mcp_bridge_swing.py.before-neutral-v2.bak"
        self.test_copy = folder / "mcp_bridge_swing_legacy_eval.py"
        self.v2 = ATOMIC + "\n" + SWING_V1 + "\n" + NEUTRAL_V2 + "\n"
        self.v1 = ATOMIC + "\n" + SWING_V1 + "\n"
        self.active.write_text(self.v2, encoding="utf-8")

    def test_no_backup_shows_explicit_blocker_without_live_pretence(self):
        view = inspect_game_bridges(self.root)
        self.assertEqual(view.state, "blocked")
        self.assertFalse(view.can_prepare)
        self.assertFalse(view.can_test)
        self.assertIn("unavailable", view.title.lower())
        self.assertIn("installed bridge: V2", view.as_text())
        self.assertIn("do not verify", view.as_text().lower())

    def test_backup_found_enables_only_prepare_and_describes_next_action(self):
        self.backup.write_text(self.v1, encoding="utf-8")
        view = inspect_game_bridges(self.root)
        self.assertEqual(view.state, "needs_preparation")
        self.assertTrue(view.can_prepare)
        self.assertFalse(view.can_test)
        self.assertIn("Step 2", view.as_text())
        self.assertIn("Saved historical backup:", view.as_text())

    def test_prepared_identical_backup_enables_single_game_trial(self):
        self.backup.write_text(self.v1, encoding="utf-8")
        before = self.active.read_bytes()
        prepare_isolated_legacy_bridge(self.active)
        self.assertEqual(before, self.active.read_bytes())
        view = inspect_game_bridges(self.root)
        self.assertEqual(view.state, "ready")
        self.assertFalse(view.can_prepare)
        self.assertTrue(view.can_test)
        self.assertEqual(view.backup_sha, view.prepared_sha)
        self.assertIn("A prime at 0", view.as_text())
        self.assertIn("ball contact", view.as_text())

    def test_autoload_or_modified_copy_never_enables_live(self):
        for data in (self.v1 + AUTOLOAD, "unrecognized"):
            self.backup.write_text(data, encoding="utf-8")
            view = inspect_game_bridges(self.root)
            self.assertEqual(view.state, "blocked")
            self.assertFalse(view.can_test)
        self.backup.write_text(self.v1, encoding="utf-8")
        self.test_copy.write_text(self.v1 + "\n# modified", encoding="utf-8")
        view = inspect_game_bridges(self.root)
        self.assertEqual(view.state, "blocked")
        self.assertFalse(view.can_prepare)
        self.assertFalse(view.can_test)
        self.assertIn("does not match", view.title.lower())

    def test_unrecognized_installed_bridge_never_enables_trial(self):
        self.active.write_text(self.v1, encoding="utf-8")
        self.backup.write_text(self.v1, encoding="utf-8")
        view = inspect_game_bridges(self.root)
        self.assertEqual(view.state, "blocked")
        self.assertIn("not identified as V2", view.detail)
        self.assertFalse(view.can_test)

    def test_gui_inspect_is_inline_not_new_console_or_popup(self):
        source = inspect.getsource(gui.launch)
        inspect_code = source.split("    def inspect_bridges():", 1)[1].split(
            "    def navigate_study(", 1)[0]
        self.assertIn("refresh_bridge_status()", inspect_code)
        self.assertNotIn("subprocess", inspect_code)
        self.assertNotIn("show_last_offline_log", inspect_code)
        self.assertNotIn("messagebox", inspect_code)
        self.assertIn("game_details = tk.Text", source)
        self.assertIn("show_game_details(view.as_text())", source)
        self.assertIn("check_game_job()", source)
        self.assertNotIn('messagebox.showinfo("No offline run log yet"', source)

    def test_gui_prepare_is_background_and_reported_inline(self):
        source = inspect.getsource(gui.launch)
        prep = source.split("    def prepare_historical_v1(*, continue_to_live: bool = False):", 1)[1].split(
            "    def check_game_job():", 1)[0]
        self.assertIn('plan("integration.prepare-v1"', prep)
        self.assertIn("execute(trial", prep)
        self.assertIn("threading.Thread", prep)
        self.assertNotIn("CREATE_NEW_CONSOLE", prep)
        self.assertIn("can_prepare", prep)


if __name__ == "__main__":
    unittest.main()
