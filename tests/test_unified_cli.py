"""Unified CLI contract and no-stale-install regression tests.

No Dolphin binary or game is required; real-game subcommands are mocked at
the delegation layer and must preserve the canonical single-launch path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)

from wii_ai_golf import cli
from wii_ai_golf.research_catalog import evidence_summary, study_summary


class UnifiedGolfCliTests(unittest.TestCase):
    def run_mock(self, argv):
        with patch.object(cli, "_run", return_value=0) as run:
            code = cli.main(argv)
            self.assertEqual(code, 0)
            run.assert_called_once()
            return run.call_args.args[0], run.call_args.kwargs

    def test_play_uses_canonical_launcher_only(self):
        command, kwargs = self.run_mock(["play", "--slot", "2"])
        self.assertEqual(Path(command[1]).name, "launch_golf.py")
        self.assertEqual(command[command.index("--slot")+1], "2")
        self.assertNotIn("--swing", command)
        self.assertFalse(kwargs["dry_run"])

    def test_swing_is_one_canonical_fresh_launch_not_bare_bridge(self):
        command, kwargs = self.run_mock([
            "swing", "--slot", "2", "--preset", "forward",
            "--follow-through-frames", "30", "--a-setup-frames", "60"
        ])
        self.assertEqual(Path(command[1]).name, "launch_golf.py")
        self.assertIn("--swing", command)
        self.assertEqual(command[command.index("--slot")+1], "2")
        self.assertEqual(command[command.index("--follow-through-frames")+1], "30")
        self.assertEqual(command[command.index("--a-setup-frames")+1], "60")
        self.assertNotIn("--attach-running", command)
        self.assertNotIn("probe_swing.py", command)
        self.assertFalse(kwargs["dry_run"])

    def test_dry_run_never_launches_emulator(self):
        command, kwargs = self.run_mock(["swing", "--slot", "2", "--dry-run"])
        self.assertTrue(kwargs["dry_run"])
        self.assertEqual(Path(command[1]).name, "launch_golf.py")

    def test_default_precharge_is_explicit_and_dry_run_is_safe(self):
        command, kwargs = self.run_mock(["swing", "--slot", "2", "--dry-run"])
        self.assertEqual(command[command.index("--a-setup-frames") + 1], "45")
        self.assertTrue(kwargs["dry_run"])

    def test_invalid_a_setup_fails_without_spawning(self):
        with patch.object(cli, "_run") as run:
            self.assertEqual(cli.main(["swing", "--a-setup-frames", "0"]), 2)
            run.assert_not_called()

    def test_invalid_followthrough_fails_without_spawning(self):
        with patch.object(cli, "_run") as run:
            self.assertEqual(cli.main(["swing", "--follow-through-frames", "181"]), 2)
            run.assert_not_called()

    def test_experiment_is_coordinator_fresh_boot_not_standalone_probe(self):
        command, kwargs = self.run_mock([
            "experiment", "--send-live", "--script", "probe_swing.py",
            "--", "--preset", "forward", "--send-live-swing"
        ])
        self.assertEqual(Path(command[1]).name, "run_golf_experiment.py")
        self.assertIn("--send-live", command)
        self.assertEqual(command[command.index("--script")+1], "probe_swing.py")
        self.assertIn("--preset", command)
        self.assertIn("--", command)
        self.assertNotIn("--attach-running", command)

    def test_experiment_no_live_flag_defaults_to_dry_run_inside_coordinator(self):
        command, kwargs = self.run_mock([
            "experiment", "--script", "probe_swing.py",
            "--", "--preset", "forward"
        ])
        self.assertNotIn("--send-live", command)

    def test_state_and_scenarios_delegate_without_duplicating_implementations(self):
        state, _ = self.run_mock(["state", "list"])
        self.assertEqual(Path(state[1]).name, "savestate_session.py")
        self.assertEqual(state[-1], "list")
        scenario, _ = self.run_mock(["scenarios", "plan", "--rounds", "3", "--out", "foo.json"])
        self.assertEqual(Path(scenario[1]).name, "plan_scenarios.py")
        self.assertEqual(scenario[2:], ["plan", "--rounds", "3", "--out", "foo.json"])

    def test_bridge_patch_and_audit_remain_adapters(self):
        command, _ = self.run_mock([
            "bridge", "patch", "--source", "source.py", "--output", "patched.py", "--enable-swing"
        ])
        self.assertEqual(Path(command[1]).name, "patch_felk_bridge.py")
        self.assertIn("--enable-swing", command)
        audit, _ = self.run_mock(["research", "audit-motion", "--input", "report.json"])
        self.assertEqual(Path(audit[1]).name, "audit_motion_candidates.py")

    def test_test_and_synthetic_stay_local(self):
        command, _ = self.run_mock(["test", "--pattern", "test_integration_*.py"])
        self.assertEqual(command[1:4], ["-m", "unittest", "discover"])
        self.assertIn("test_integration_*.py", command)
        demo, _ = self.run_mock(["demo"])
        self.assertEqual(demo[1:], ["-m", "wii_ai_golf.demo"])

    def test_research_studies_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "queue.jsonl"
            row = {"study_id": "S001", "title": "Swing", "role": "integrator"}
            p.write_text(json.dumps(row)+"\n", encoding="utf-8")
            self.assertEqual(study_summary(p)["studies"][0]["study_id"], "S001")
            p.write_text((json.dumps(row)+"\n")*2, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                study_summary(p)

    def test_evidence_counts_human_contact_without_inventing_scores(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "swing-probes.jsonl"
            p.write_text(
                json.dumps({
                    "dispatch": {"state": "complete"}, "human_ball_moved": "yes",
                    "human_on_green": "no", "game_score": None,
                    "human_visual_power_gauge_estimate_pct": 75
                })+"\nBAD LINE\n",
                encoding="utf-8"
            )
            result = evidence_summary(p)
            self.assertEqual(result["trials"], 1)
            self.assertEqual(result["dispatch_complete"], 1)
            self.assertEqual(result["ball_moved_yes"], 1)
            self.assertEqual(result["on_green_yes"], 0)
            self.assertEqual(result["verified_scores"], 0)
            self.assertEqual(result["invalid_lines"], 1)

    def test_source_local_cli_needs_no_pip_install_and_ignores_stale_pkg(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "wii_ai_golf"
            bad.mkdir()
            (bad / "__init__.py").write_text("# stale editable\n", encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONPATH"] = d
            entry = ROOT / "scripts" / "golf.py"
            for command in ([sys.executable, str(entry), "--help"],
                            [sys.executable, "-I", str(entry), "research", "studies"]):
                with self.subTest(command=command):
                    result = subprocess.run(command, env=env, cwd=d, text=True,
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_module_entrypoint_works_with_checked_out_source(self):
        env = cli._environment()
        result = subprocess.run([sys.executable, "-m", "wii_ai_golf", "--help"],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wii AI Golf", result.stdout)


if __name__ == "__main__":
    unittest.main()
