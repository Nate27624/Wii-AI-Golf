"""Source-local public lab command parser and safe invocation regression."""
from __future__ import annotations
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf import cli
from wii_ai_golf.lab import core
from wii_ai_golf.lab.github_sync import SyncReport


class LabCliTests(unittest.TestCase):
    def test_registry_lists_all_agent_roles_without_running_code(self):
        output = io.StringIO()
        with patch.object(cli, "_run") as spawn, redirect_stdout(output):
            self.assertEqual(cli.main(["lab", "list"]), 0)
            spawn.assert_not_called()
        self.assertIn("integration.swing", output.getvalue())
        self.assertIn("evaluation.capture", output.getvalue())
        self.assertIn("generalization.holdout", output.getvalue())
        self.assertIn("planned", output.getvalue())

    def test_v1_diagnostic_listed_in_shared_cli_registry(self):
        entries = core.load_catalog(core.CATALOG)
        diagnostic = next(e for e in entries if e["id"] == "integration.v1-diagnostic")
        self.assertEqual(diagnostic["mode"], "live")
        self.assertEqual(diagnostic["kind"], "v1_capture")
        self.assertIn("initial", diagnostic["description"].lower())
        self.assertIn("club pose", diagnostic["description"].lower())
        self.assertIn("no automatic score", diagnostic["description"].lower())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["lab", "list"]), 0)
        self.assertIn("integration.v1-diagnostic", out.getvalue())

    def test_live_plan_does_not_execute_or_create_files(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(cli, "DATA_ROOT", Path(d)), \
                 patch.object(core, "execute") as run, \
                 redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(["lab", "plan", "evaluation.capture"]), 0)
                run.assert_not_called()
            text = out.getvalue()
            self.assertIn("run_golf_experiment.py", text)
            self.assertIn("collect_outcome_transition.py", text)
            self.assertIn('"fresh_canonical_boot": true', text)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_live_requires_explicit_flag_and_never_submits_experiment(self):
        with patch.object(core, "_git_revision") as git, \
             patch.object(core, "local_bridge_fingerprint") as bridge, \
             patch.object(cli, "_run") as run, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["lab", "run", "evaluation.capture"]), 2)
            git.assert_not_called()
            bridge.assert_not_called()
            run.assert_not_called()

    def test_planned_study_rejected_and_no_process_started(self):
        with patch.object(cli, "_run") as run:
            self.assertEqual(cli.main(["lab", "plan", "modeling.sweep"]), 2)
            run.assert_not_called()

    def test_github_sync_cli_shows_updated_tests_but_does_not_run_them(self):
        updated = SyncReport("updated", "before", "after",
                             ("tests/test_outcome_more.py",),
                             "Fast-forwarded approved main.")
        with patch("wii_ai_golf.lab.github_sync.sync_merged_main",
                   return_value=updated) as sync, \
             patch.object(core, "execute") as execute, \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["lab", "sync"]), 0)
            sync.assert_called_once_with(cli.ROOT, lab_data=cli.DATA_ROOT / "lab")
            execute.assert_not_called()
        self.assertIn("tests/test_outcome_more.py", out.getvalue())
        self.assertIn("Run 'py scripts/golf.py lab list'", out.getvalue())

    def test_github_sync_refuses_an_untrusted_or_dirty_checkout(self):
        blocked = SyncReport("blocked", note="Working tree has local changes.")
        with patch("wii_ai_golf.lab.github_sync.sync_merged_main",
                   return_value=blocked), \
             patch.object(cli, "_run") as run, \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["lab", "sync"]), 1)
            run.assert_not_called()
        self.assertIn("blocked", out.getvalue())

    def test_synthetic_learning_plan_is_not_real_game(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["lab", "plan", "learning.demo"]), 0)
        rendered = out.getvalue()
        self.assertIn('"fresh_canonical_boot": false', rendered)
        self.assertIn("wii_ai_golf.demo", rendered)


if __name__ == "__main__":
    unittest.main()
