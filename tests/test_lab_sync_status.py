"""Offline lock details: never infer a dead process or delete safety state."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab.sync_status import lock_blockers


class LabSyncStatusTests(unittest.TestCase):
    def test_no_locks_has_no_blockers(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(lock_blockers(Path(folder)), [])

    def test_explains_both_existing_locks_with_pid_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            payload = json.dumps({"pid": 3808, "utc": "2026-10-25T00:53:38Z"})
            for name in ("run-session.lock", "live-session.lock"):
                (data / name).write_text(payload)
            rows = lock_blockers(data)
            self.assertEqual(len(rows), 2)
            self.assertTrue(all("3808" in row for row in rows))
            self.assertTrue(all("2026-10-25" in row for row in rows))
            self.assertEqual((data / "run-session.lock").read_text(), payload)
            self.assertEqual((data / "live-session.lock").read_text(), payload)

    def test_invalid_lock_refuses_to_silently_assume_idle(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            (data / "run-session.lock").write_text("{not json")
            blockers = lock_blockers(data)
            self.assertEqual(len(blockers), 1)
            self.assertIn("manual inspection", blockers[0])
            self.assertTrue((data / "run-session.lock").exists())

    def test_invalid_pid_is_not_treated_as_safe_to_remove(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            (data / "live-session.lock").write_text('{"pid": null}')
            blockers = lock_blockers(data)
            self.assertEqual(len(blockers), 1)
            self.assertIn("invalid PID", blockers[0])


if __name__ == "__main__":
    unittest.main()
