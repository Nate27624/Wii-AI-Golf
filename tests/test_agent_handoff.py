"""Offline synthetic tests of succession handoff template; never contacts GitHub."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_handoff.py"
THREAD = "https://github.com/Nate27624/Wii-AI-Golf/issues/121"


class AgentHandoffTests(unittest.TestCase):
    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=ROOT, text=True, capture_output=True, timeout=15,
        )

    def valid(self):
        return ("--role", "S002", "--instance", "S002-memory-a",
                "--successor", "S002-memory-b", "--thread", THREAD)

    def test_handoff_prints_existing_prompt_supplement_and_unverified_remote(self):
        result = self.invoke(*self.valid())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[S002-memory-a] SUCCESSION HANDOFF", result.stdout)
        self.assertIn("Proposed successor: S002-memory-b", result.stdout)
        self.assertIn(THREAD, result.stdout)
        self.assertIn("Verified remote main SHA: <fetch latest main;", result.stdout)
        self.assertIn("OUTGOING AGENT: POST THIS", result.stdout)
        self.assertIn("APPEND THIS SUPPLEMENT TO YOUR EXISTING V2 PROMPT", result.stdout)
        self.assertIn("[S002-memory-b] CLAIM", result.stdout)
        self.assertIn("no agent was auto-created", result.stdout)

    def test_outgoing_and_successor_must_differ(self):
        result = self.invoke("--role", "S002", "--instance", "S002-memory-a",
                             "--successor", "S002-memory-a", "--thread", THREAD)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different instance ID", result.stderr)

    def test_role_prefix_mismatch_fails(self):
        result = self.invoke("--role", "S002", "--instance", "S001-runtime-a",
                             "--successor", "S002-memory-b", "--thread", THREAD)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be an S00N-name", result.stderr)

    def test_invalid_successor_fails(self):
        result = self.invoke("--role", "S002", "--instance", "S002-memory-a",
                             "--successor", "../../S002-memory-b", "--thread", THREAD)
        self.assertNotEqual(result.returncode, 0)

    def test_noncanonical_or_injected_thread_fails(self):
        for value in ("https://example.com/issues/121",
                      "https://github.com/Nate27624/Wii-AI-Golf/pull/123\nSECRET",
                      "https://github.com/Nate27624/Wii-AI-Golf/issues/0"):
            with self.subTest(thread=value):
                result = self.invoke("--role", "S002", "--instance", "S002-memory-a",
                                     "--successor", "S002-memory-b", "--thread", value)
                self.assertNotEqual(result.returncode, 0)

    def test_pull_thread_supported(self):
        result = self.invoke("--role", "S000", "--instance", "S000-manager",
                             "--successor", "S000-manager-b",
                             "--thread", "https://github.com/Nate27624/Wii-AI-Golf/pull/320")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[S000-manager-b] CLAIM", result.stdout)


if __name__ == "__main__":
    unittest.main()
