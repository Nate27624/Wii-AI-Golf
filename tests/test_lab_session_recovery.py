"""Regression for crash-safe Windows/Unix Lab locking and in-app V1 workflow."""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab import core, gui
from wii_ai_golf.lab.locks import (
    session_lock, lock_busy, any_lab_job_busy,
)


class CrashSafeLabLockTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.data = Path(td.name)
        self.live = self.data / "live-session.lock"
        self.run = self.data / "run-session.lock"

    def test_legacy_dead_owner_is_recovered_without_manual_delete(self):
        self.live.write_text(json.dumps({"pid": 987654321,
                                         "utc": "2026-10-24T00:00:00Z"}))
        with patch("wii_ai_golf.lab.locks.pid_running", return_value=False):
            self.assertFalse(lock_busy(self.live))
            with core.live_session_lock(self.data):
                self.assertTrue(lock_busy(self.live))
        self.assertFalse(lock_busy(self.live))
        self.assertTrue(self.live.is_file())  # sentinel is harmless

    def test_active_legacy_owner_blocks_and_metadata_preserved(self):
        original = json.dumps({"pid": os.getpid(), "utc": "existing"})
        self.run.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "older Lab version"):
            with core.lab_run_lock(self.data):
                self.fail("Active legacy owner should never be bypassed")
        self.assertEqual(self.run.read_text(encoding="utf-8"), original)
        self.assertTrue(lock_busy(self.run))

    def test_active_process_lock_prevents_parallel_game(self):
        with core.lab_run_lock(self.data):
            self.assertTrue(any_lab_job_busy(self.data))
            with self.assertRaisesRegex(ValueError, "already active"):
                with core.lab_run_lock(self.data):
                    self.fail("second Lab run must not start")
        self.assertFalse(any_lab_job_busy(self.data))

    def test_crash_style_legacy_lock_on_general_job_is_recovered(self):
        self.run.write_text(json.dumps({"pid": 987654321}))
        with patch("wii_ai_golf.lab.locks.pid_running", return_value=False):
            with core.lab_run_lock(self.data):
                self.assertTrue(lock_busy(self.run))
        self.assertFalse(lock_busy(self.run))

    def test_unknown_old_lock_fails_closed(self):
        self.live.write_text("not a recognized PID record", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "older Lab"):
            with core.live_session_lock(self.data):
                self.fail("Unrecognized lock must not be silently ignored")
        self.assertTrue(lock_busy(self.live))
        self.assertIn("not a recognized", self.live.read_text(encoding="utf-8"))

    def test_no_lock_needed_for_completed_run_file_sentinel(self):
        with core.lab_run_lock(self.data):
            pass
        self.assertTrue(self.run.exists())
        self.assertFalse(lock_busy(self.run))
        with core.lab_run_lock(self.data):
            pass


class SingleV1WorkflowSourceTests(unittest.TestCase):
    def test_bridge_controls_are_inside_selected_show_pane_not_top_toolbar(self):
        source = inspect.getsource(gui.launch)
        game = source.index("game_panel = ttk.LabelFrame")
        right = source.index("left, right = ttk.Frame(panes), ttk.Frame(panes)")
        self.assertGreater(game, right)
        self.assertIn('ttk.LabelFrame(right, text="Historical V1 · game test"', source)
        self.assertNotIn('game_panel = ttk.LabelFrame(\n        outer', source)
        self.assertIn("game_panel.pack_forget()", source)
        self.assertIn('{"a-lead"}', source)
        self.assertIn('"Prepare and run one V1 shot"', source)

    def test_preparation_is_automatic_and_launch_remains_consented(self):
        source = inspect.getsource(gui.launch)
        controller = source.split("    def start_v1_workflow():", 1)[1].split(
            "    def request_sync", 1)[0]
        self.assertIn("refresh_bridge_status()", controller)
        self.assertIn("prepare_historical_v1(continue_to_live=True)", controller)
        self.assertIn("launch_v1_trial()", controller)
        self.assertIn("ui.after_idle(launch_v1_trial)", source)
        self.assertIn('messagebox.askyesno(\n                "Confirm ONE live swing"', source)
        self.assertIn("run_selected(True, verified_v1=True)", source)

    def test_ui_checks_real_job_state_not_leftover_file_existence(self):
        source = inspect.getsource(gui.launch)
        self.assertIn("any_lab_job_busy(lab_data)", source)
        self.assertNotIn('("live-session.lock", "run-session.lock")):', source)
        self.assertIn("Restart Lab (updated)", source)


if __name__ == "__main__":
    unittest.main()
