"""Synthetic regression: S001 legacy V1 Lab plan never falls back to old Felk.

Planning must remain pure: tests do not launch game, write Dolphin User, or
perform real RPC. Native files are intentionally absent to test preview safety.
"""
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.lab import core
from wii_ai_golf.shared.bridge_provenance import ATOMIC, SWING_V1, NEUTRAL_V2

class V1CleanBootPlanningTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "Wii-AI-Golf"
        (self.repo / "scripts").mkdir(parents=True)
        (self.repo / "scripts" / "run_golf_experiment.py").write_text("# mock")
        tools = self.repo.parent / "tools"
        tools.mkdir()
        self.bridge = tools / "mcp_bridge_swing_legacy_eval.py"
        self.bridge.write_text(ATOMIC + "\n" + SWING_V1 + "\n", encoding="utf-8")
        self.catalog = core.load_catalog(core.CATALOG)

    def plan(self, a_lead=0):
        return core.plan("integration.v1-diagnostic", catalog=self.catalog,
                         root=self.repo, python="python.exe", a_lead=a_lead)

    def test_v1_explicit_clean_dolphin_and_isolated_user(self):
        cmd = list(self.plan().command)
        def arg(name):
            return Path(cmd[cmd.index(name) + 1])
        clean = self.repo.parent / "tools" / "FelkDolphin-Clean"
        self.assertEqual(arg("--dolphin"), clean / "Dolphin.exe")
        self.assertEqual(arg("--dolphin-user"), clean / "User")
        self.assertEqual(arg("--bridge"), self.bridge.resolve())
        self.assertEqual(arg("--config"), self.repo / "research" / "launch.local.json")
        self.assertEqual(arg("--catalog"), self.repo / "research" / "savestates.local.json")
        self.assertNotIn(str(self.repo.parent / "tools" / "FelkDolphin" / "Dolphin.exe"), cmd)
        self.assertEqual(cmd.count("--send-live"), 1)
        self.assertEqual(cmd.count("--send-live-swing"), 1)
        self.assertEqual(cmd[cmd.index("--script")+1], "collect_outcome_transition.py")
        self.assertEqual(cmd[cmd.index("--a-prime-requests")+1], "0")
        self.assertEqual(cmd[cmd.index("--a-lead-frames")+1], "0")
        self.assertTrue(self.plan().live)

    def test_plan_does_not_require_creating_or_starting_clean_dolphin(self):
        clean = self.repo.parent / "tools" / "FelkDolphin-Clean"
        self.assertFalse(clean.exists())
        self.assertEqual(self.plan().summary()["game_outcome"],
                         "not_observed_or_verified")
        self.assertFalse(clean.exists())

    def test_a_lead_changes_only_owned_input_knob(self):
        x = list(self.plan().command)
        y = list(self.plan(a_lead=12).command)
        i = x.index("--a-lead-frames") + 1
        self.assertEqual(y.index("--a-lead-frames") + 1, i)
        self.assertEqual(x[:i] + x[i+1:], y[:i] + y[i+1:])
        self.assertEqual(y[i], "12")
        self.assertEqual(x[i], "0")

    def test_invalid_legacy_bridge_rejected_before_live_plan(self):
        self.bridge.write_text(ATOMIC + "\n" + SWING_V1 + "\n" + NEUTRAL_V2)
        with self.assertRaises(ValueError):
            self.plan()

if __name__ == "__main__":
    unittest.main()
