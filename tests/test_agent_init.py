"""Synthetic, no-network smoke tests for agent initialization."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_init.py"

class AgentInitTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, timeout=15)

    def test_valid_identity(self):
        proc = self.invoke("--role", "S002", "--instance", "S002-memory-a")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENT_ID=S002-memory-a", proc.stdout)
        self.assertIn("NO LIVE DOLPHIN", proc.stdout)

    def test_manager_playbook_link(self):
        proc = self.invoke("--role", "S000", "--instance", "S000-manager")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MANAGER_PLAYBOOK=docs/S000-manager-playbook.md", proc.stdout)
        self.assertIn("MANAGER_DUTY=Collect agent questions", proc.stdout)
        self.assertIn("MANAGER_DUTY=Keep roles focused", proc.stdout)

    def test_v2_navigation_targets_exist(self):
        for path in ('docs/v2-navigation.md', 'docs/v2-evidence-gates.md', 'docs/v2-pr-triage.md', 'docs/S000-manager-playbook.md', 'merging.md'):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_wrong_role_prefix_rejected(self):
        proc = self.invoke("--role", "S002", "--instance", "S001-memory-a")
        self.assertNotEqual(proc.returncode, 0)

    def test_bad_instance_rejected(self):
        proc = self.invoke("--role", "S002", "--instance", "../bad")
        self.assertNotEqual(proc.returncode, 0)

    def test_missing_role_rejected(self):
        proc = self.invoke("--instance", "S002-memory-a")
        self.assertNotEqual(proc.returncode, 0)

if __name__ == "__main__":
    unittest.main()
