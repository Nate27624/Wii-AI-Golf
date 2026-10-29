"""Unified golf lab: safe registry and one-shot execution contract."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab import core


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Wii-AI-Golf"
        self.root.mkdir()
        for file in ("scripts/launch_golf.py", "scripts/run_golf_experiment.py",
                     "scripts/golf.py", "scripts/audit_motion_candidates.py",
                     "scripts/compare_outcome_runs.py", "scripts/recover_outcome_capture.py"):
            path = self.root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# stub", encoding="utf-8")
        self.experiments = core.load_catalog(core.CATALOG)
        path = self.root / "research" / "experiments.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"schema_version": 1,
                                   "experiments": self.experiments}), encoding="utf-8")
        self.data = self.root.parent / "Wii-AI-Golf-Data" / "lab"

    def plan(self, name, **kw):
        return core.plan(name, root=self.root, python="python.exe", **kw)

    def test_catalog_includes_each_agent_and_planned_entries(self):
        self.assertEqual({e["owner"] for e in self.experiments},
                         {"S000", "S001", "S002", "S003", "S004", "S005"})
        self.assertIn("integration.swing", {e["id"] for e in self.experiments})
        self.assertEqual(self.plan("evaluation.capture").live, True)
        for blocked in ("modeling.sweep", "generalization.holdout"):
            with self.assertRaisesRegex(ValueError, "planned, NOT runnable"):
                self.plan(blocked)

    def test_registry_rejects_arbitrary_script_and_invalid_modes(self):
        evil = dict(self.experiments[0], kind="../../scripts/exploit.py")
        with self.assertRaisesRegex(ValueError, "Unrecognized owner/kind/mode"):
            core.load_catalog(self._catalog([evil]))
        bad = dict(self.experiments[0], id="a/../../game.py")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            core.load_catalog(self._catalog([bad]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            core.load_catalog(self._catalog([self.experiments[0],
                                             self.experiments[0]]))

    def _catalog(self, items):
        p = self.root / "research" / "experiments.json"
        p.write_text(json.dumps({"schema_version": 1, "experiments": items}),
                     encoding="utf-8")
        return p

    def test_live_capture_uses_canonical_one_boot_and_NO_separate_A_prime(self):
        shot = self.plan("evaluation.capture")
        command = list(shot.command)
        self.assertEqual(Path(command[1]).name, "run_golf_experiment.py")
        self.assertEqual(command[command.index("--script") + 1],
                         "collect_outcome_transition.py")
        self.assertEqual(command[command.index("--a-prime-requests") + 1], "0")
        self.assertEqual(command[command.index("--pre-samples") + 1], "3")
        self.assertEqual(command[command.index("--post-samples") + 1], "2")
        self.assertEqual(command[command.index("--interval") + 1], "0.0")
        self.assertIn("--send-live", command)
        self.assertNotIn("--attach-running", command)
        self.assertNotIn("savestate_session.py", command)
        self.assertTrue(shot.live)
        self.assertTrue(shot.summary()["fresh_canonical_boot"])
        self.assertEqual(shot.summary()["game_outcome"], "not_observed_or_verified")

    def test_ui_registered_v1_diagnostic_is_explicit_and_full_boot_only(self):
        from wii_ai_golf.shared.bridge_provenance import ATOMIC, SWING_V1
        bridge = self.root.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
        bridge.parent.mkdir(parents=True)
        bridge.write_text(ATOMIC + "\\n" + SWING_V1 + "\\n", encoding="utf-8")
        p = self.plan("integration.v1-diagnostic", a_lead=0)
        cmd = list(p.command)
        self.assertEqual(Path(cmd[1]).name, "run_golf_experiment.py")
        self.assertIn("--send-live", cmd)
        self.assertEqual(cmd[cmd.index("--bridge")+1], str(bridge.resolve()))
        self.assertEqual(cmd[cmd.index("--a-lead-frames")+1], "0")
        self.assertEqual(cmd[cmd.index("--a-prime-requests")+1], "0")
        self.assertEqual(cmd[cmd.index("--script")+1], "collect_outcome_transition.py")
        self.assertIn("--observe-start-pose", cmd)
        self.assertNotIn("--attach-running", cmd)
        self.assertTrue(p.live)
        p12 = self.plan("integration.v1-diagnostic", a_lead=12)
        self.assertEqual(list(p12.command)[list(p12.command).index("--a-lead-frames")+1], "12")
        p45 = self.plan("integration.v1-diagnostic", a_lead=45)
        self.assertEqual(list(p45.command)[list(p45.command).index("--a-lead-frames")+1], "45")
        for invalid in (-1, 91, 180, 1.5, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.plan("integration.v1-diagnostic", a_lead=invalid)
        with self.assertRaisesRegex(ValueError, "does not accept --a-prime"):
            self.plan("integration.v1-diagnostic", a_prime=60)
        with self.assertRaisesRegex(ValueError, "only supported"):
            self.plan("evaluation.capture", a_lead=12)

    def test_v1_diagnostic_rejects_missing_wrong_or_autoloaded_bridge(self):
        from wii_ai_golf.shared.bridge_provenance import ATOMIC, SWING_V1, NEUTRAL_V2, AUTOLOAD
        bridge = self.root.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
        with self.assertRaisesRegex(ValueError, "unavailable/invalid"):
            self.plan("integration.v1-diagnostic")
        bridge.parent.mkdir(parents=True, exist_ok=True)
        for source in ("anything else", ATOMIC + SWING_V1 + NEUTRAL_V2,
                       ATOMIC + SWING_V1 + AUTOLOAD):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "unavailable/invalid"):
                bridge.write_text(source)
                self.plan("integration.v1-diagnostic")

    def test_live_swing_is_distinct_diagnostic_not_s002_collector(self):
        p = self.plan("integration.swing", a_prime=60, follow_through=90)
        cmd = list(p.command)
        self.assertEqual(Path(cmd[1]).name, "launch_golf.py")
        self.assertIn("--swing", cmd)
        self.assertIn("--profile", cmd)
        self.assertEqual(cmd[cmd.index("--a-prime-frames")+1], "60")
        self.assertEqual(cmd[cmd.index("--follow-through-frames")+1], "90")

    def test_live_never_runs_without_explicit_opt_in(self):
        p = self.plan("evaluation.capture")
        with patch.object(core, "_git_revision", return_value="abc"), \
             patch.object(core, "local_bridge_fingerprint", return_value={}) as fingerprint:
            was_called = []
            with self.assertRaisesRegex(ValueError, "requires explicit --live"):
                core.execute(p, root=self.root, data=self.data,
                             run_command=lambda *_args, **_kwargs: was_called.append("ran"))
            self.assertFalse(was_called)
            fingerprint.assert_not_called()
        self.assertFalse((self.data / "runs").exists())

    def test_one_live_run_writes_metadata_but_never_fake_score(self):
        p = self.plan("evaluation.capture")
        calls = []
        def runner(argv, **kw):
            calls.append((argv, kw))
            return SimpleNamespace(returncode=0)
        with patch.object(core, "_git_revision", return_value="safesha"), \
             patch.object(core, "local_bridge_fingerprint",
                          return_value={"sha256": "bridgehash"}):
            record = core.execute(p, root=self.root, data=self.data,
                                  allow_live=True, run_command=runner)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["cwd"], self.root)
        self.assertFalse(core.lock_busy(self.data / "live-session.lock"))
        self.assertEqual(record["revision"], "safesha")
        self.assertEqual(record["bridge_on_disk"]["sha256"], "bridgehash")
        self.assertEqual(record["execution_status"], "finished")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["game_outcome"], "not_observed_or_verified")
        self.assertNotIn("game_score", record)
        observed = core.history(self.data)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["run_id"], record["run_id"])

    def test_live_lock_blocks_duplicate_session_and_retains_first(self):
        p = self.plan("integration.swing")
        with core.live_session_lock(self.data):
            with self.assertRaisesRegex(ValueError, r"(?:is already active|may be active)"):
                core.execute(p, root=self.root, data=self.data, allow_live=True,
                             run_command=lambda *_a, **_k: self.fail("No second process"))
            self.assertTrue((self.data / "live-session.lock").is_file())
        self.assertFalse(core.lock_busy(self.data / "live-session.lock"))

    def test_offline_runs_require_no_live_approval(self):
        p = self.plan("core.tests")
        self.assertFalse(p.live)
        self.assertEqual(p.command[1:4], ("-m", "unittest", "discover"))
        with patch.object(core, "_git_revision", return_value=None):
            result = core.execute(p, root=self.root, data=self.data,
                                  run_command=lambda *_a, **_k: SimpleNamespace(returncode=3))
        self.assertEqual(result["execution_status"], "failed")
        self.assertEqual(result["exit_code"], 3)
        self.assertFalse(core.lock_busy(self.data / "live-session.lock"))
        with self.assertRaisesRegex(ValueError, "--live is only"):
            core.execute(p, root=self.root, data=self.data, allow_live=True)

    def test_evaluation_offline_reports_require_input_files(self):
        with self.assertRaisesRegex(ValueError, "--input"):
            self.plan("evaluation.compare")
        a = self.plan("evaluation.compare", input_path="a.json",
                      second_input="b.json", output_path="comparison.json")
        self.assertIn("a.json", a.command)
        self.assertIn("b.json", a.command)
        self.assertIn("comparison.json", a.command)
        with self.assertRaisesRegex(ValueError, "requires --contact and --green"):
            self.plan("evaluation.recover", input_path="private.jsonl")
        b = self.plan("evaluation.recover", input_path="private.jsonl",
                      contact="yes", green="no", distance="100ft")
        self.assertEqual(Path(b.command[1]).name, "recover_outcome_capture.py")
        self.assertIn("--raw", b.command)
        self.assertIn("100ft", b.command)

    def test_bad_options_do_not_start_game(self):
        for name, kw in (
            ("integration.swing", {"a_prime": 181}),
            ("integration.swing", {"follow_through": -1}),
            ("evaluation.capture", {"follow_through": 90}),
            ("core.tests", {"input_path": "secret"}),
        ):
            with self.subTest(name=name, kw=kw), self.assertRaises(ValueError):
                self.plan(name, **kw)

    def test_schema_status_execution_is_not_outcome(self):
        p = self.plan("integration.swing")
        with patch.object(core, "_git_revision", return_value=None):
            result = core.execute(p, root=self.root, data=self.data,
                                  allow_live=True,
                                  run_command=lambda *_a, **_k: SimpleNamespace(returncode=0))
        self.assertEqual(result["execution_status"], "finished")
        self.assertEqual(result["game_outcome"], "not_observed_or_verified")
        self.assertNotIn("hit", result)
        self.assertNotIn("on_green", result)


if __name__ == "__main__":
    unittest.main()
