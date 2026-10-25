"""S000 UI game-testing workflow: audit, safe preparation, live V1 gating.

These tests do not start Dolphin or create a generated bridge.
"""
from __future__ import annotations
from pathlib import Path
import json
import inspect
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab import core
from wii_ai_golf.shared.bridge_provenance import (
    ATOMIC, SWING_V1, NEUTRAL_V2, AUTOLOAD,
    audit_bridge_sources, inspect_bridge_file, prepare_isolated_legacy_bridge,
)


class LabGameTestingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "Wii-AI-Golf"
        self.root.mkdir()
        scripts = self.root / "scripts"
        scripts.mkdir()
        for file in ("audit_local_swing_bridge.py", "run_golf_experiment.py"):
            (scripts / file).write_text("# stub\n", encoding="utf-8")
        self.registry = core.load_catalog(core.CATALOG)
        self.current = self.root.parent / "tools" / "mcp_bridge_swing.py"
        self.backup = self.current.with_name(
            self.current.name + ".before-neutral-v2.bak")
        self.legacy = self.current.with_name("mcp_bridge_swing_legacy_eval.py")
        self.current.parent.mkdir()
        self.current.write_text(ATOMIC + "\n" + SWING_V1 + "\n" + NEUTRAL_V2)

    def p(self, name, **kw):
        return core.plan(name, root=self.root, python="python.exe",
                         catalog=self.registry, **kw)

    def test_all_three_steps_registered_in_correct_order(self):
        ids = [x["id"] for x in self.registry]
        sequence = ("integration.bridge-audit",
                    "integration.prepare-v1",
                    "integration.v1-diagnostic")
        self.assertEqual(ids[ids.index(sequence[0]):ids.index(sequence[0])+3],
                         list(sequence))
        self.assertEqual([core.get_experiment(x, catalog=self.registry)["mode"]
                          for x in sequence], ["offline", "offline", "live"])

    def test_audit_and_prepare_are_reviewed_offline_commands(self):
        audit = self.p("integration.bridge-audit")
        prepare = self.p("integration.prepare-v1")
        self.assertFalse(audit.live)
        self.assertFalse(prepare.live)
        self.assertEqual(Path(audit.command[1]).name,
                         "audit_local_swing_bridge.py")
        self.assertEqual(Path(prepare.command[1]).name,
                         "audit_local_swing_bridge.py")
        self.assertNotIn("--prepare-legacy-trial", audit.command)
        self.assertIn("--prepare-legacy-trial", prepare.command)
        self.assertNotIn("--send-live", prepare.command)
        self.assertNotIn("launch_golf.py", prepare.command)
        self.assertFalse(prepare.summary()["fresh_canonical_boot"])

    def test_three_steps_appear_in_desktop_ui_with_readiness_and_restart(self):
        # Tkinter needs Windows/display, but this verifies the UI actually
        # exposes the registered audit/prep/live flow rather than only CLI.
        from wii_ai_golf.lab.gui import launch
        source = inspect.getsource(launch)
        for label in ("Historical V1 · game test", "Prepare and run one V1 shot",
                      "Recheck environment", "Game tests", "Restart Lab (updated)") :
            with self.subTest(label=label):
                self.assertIn(label, source)
        for experiment in ("integration.bridge-audit",
                           "integration.prepare-v1", "integration.v1-diagnostic"):
            self.assertIn(experiment, source)

    def test_valid_backup_preparation_avoids_modifying_installed_bridge(self):
        source = ATOMIC + "\n" + SWING_V1 + "\n"
        self.backup.write_text(source)
        self.assertTrue(audit_bridge_sources(self.current)["v1_isolated_trial_possible"])
        original = self.current.read_bytes()
        copy = prepare_isolated_legacy_bridge(self.current)
        self.assertEqual(copy, self.legacy)
        self.assertEqual(copy.read_bytes(), self.backup.read_bytes())
        self.assertEqual(self.current.read_bytes(), original)
        self.assertEqual(inspect_bridge_file(copy)["revision"],
                         "V1-neutral-swing-calls")
        live = self.p("integration.v1-diagnostic")
        self.assertTrue(live.live)
        self.assertEqual(Path(live.command[1]).name, "run_golf_experiment.py")
        self.assertEqual(live.command[live.command.index("--bridge") + 1],
                         str(self.legacy.resolve()))
        self.assertEqual(live.command[live.command.index("--a-lead-frames") + 1],
                         "0")
        self.assertEqual(live.command[live.command.index("--a-prime-requests") + 1],
                         "0")

    def test_no_safe_backup_cannot_be_prepared_or_run(self):
        with self.assertRaisesRegex(ValueError, "backup missing/unknown"):
            prepare_isolated_legacy_bridge(self.current)
        with self.assertRaisesRegex(ValueError, "unavailable/invalid"):
            self.p("integration.v1-diagnostic")
        self.assertFalse(self.legacy.exists())

    def test_autoload_bridge_rejected_and_current_bridge_untouched(self):
        self.backup.write_text(ATOMIC + SWING_V1 + AUTOLOAD)
        before = self.current.read_bytes()
        with self.assertRaisesRegex(ValueError, "backup missing/unknown"):
            prepare_isolated_legacy_bridge(self.current)
        self.assertEqual(before, self.current.read_bytes())
        self.assertFalse(self.legacy.exists())

    def test_mismatched_destination_never_overwritten(self):
        self.backup.write_text(ATOMIC + SWING_V1)
        self.legacy.write_text("some unrelated file")
        with self.assertRaises(FileExistsError):
            prepare_isolated_legacy_bridge(self.current)
        self.assertEqual(self.legacy.read_text(), "some unrelated file")

    def test_offline_execution_never_receives_live_permission(self):
        plan = self.p("integration.bridge-audit")
        with patch.object(core, "_git_revision", return_value="sha"), \
             patch.object(core, "local_bridge_fingerprint", return_value={}):
            logdir = self.root.parent / "Wii-AI-Golf-Data" / "lab"
            record = core.execute(
                plan, root=self.root, data=logdir,
                run_command=lambda *_a, **_kw:
                SimpleNamespace(returncode=0, stdout="V1 available", stderr=""))
        self.assertEqual(record["execution_status"], "finished")
        self.assertEqual(record["game_outcome"], "not_observed_or_verified")
        self.assertIn("V1 available",
                      Path(record["offline_log"]).read_text(encoding="utf-8"))
        self.assertFalse(core.lock_busy(logdir / "live-session.lock"))


if __name__ == "__main__":
    unittest.main()
