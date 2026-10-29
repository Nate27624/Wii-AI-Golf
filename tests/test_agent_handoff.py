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

    def test_handoff_prints_complete_successor_prompt_and_unverified_remote(self):
        result = self.invoke(*self.valid())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[S002-memory-a] SUCCESSION HANDOFF", result.stdout)
        self.assertIn("Proposed successor: S002-memory-b", result.stdout)
        self.assertIn(THREAD, result.stdout)
        self.assertIn("Verified remote main SHA: <fetch latest main;", result.stdout)
        self.assertIn("OUTGOING AGENT: POST THIS", result.stdout)
        self.assertIn("NEW CHAT PROMPT — COPY FROM NEXT LINE THROUGH END MARKER", result.stdout)
        self.assertIn("=== END NEW CHAT PROMPT ===", result.stdout)
        self.assertIn("# Wii Sports Golf AI — V2 Successor Agent", result.stdout)
        self.assertIn("FIRST: Fetch current main. Read merging.md", result.stdout)
        self.assertIn("Self-merge only when every merging.md", result.stdout)
        self.assertIn("No live Dolphin experiment", result.stdout)
        self.assertIn("[S002-memory-b] CLAIM", result.stdout)
        self.assertIn("Do not claim to be working asynchronously or to auto-create another chat.", result.stdout)

    def test_successor_prompt_is_standalone_and_extractable(self):
        result = self.invoke(*self.valid())
        self.assertEqual(result.returncode, 0, result.stderr)
        _, _, prompt = result.stdout.partition(
            "=== NEW CHAT PROMPT — COPY FROM NEXT LINE THROUGH END MARKER ==="
        )
        self.assertTrue(prompt, "Missing standalone prompt section")
        prompt, separator, end = prompt.partition("=== END NEW CHAT PROMPT ===")
        self.assertTrue(separator)
        self.assertFalse(end.strip(), "No output should follow the copyable prompt")
        self.assertIn("You are S002-memory-b", prompt)
        self.assertIn("S002-memory-a", prompt)
        self.assertIn(THREAD, prompt)
        self.assertIn("docs/v2-agent-continuity.md", prompt)
        self.assertIn("docs/v2-universal-prompts.md", prompt)
        self.assertIn("PR #320", prompt)
        self.assertIn("--mode init --role S002", prompt)
        self.assertIn("ASSIGNMENT ROSTER V2", prompt)
        self.assertIn("manager roster entry matches you", prompt)
        self.assertIn("Role: S002", prompt)
        self.assertIn("Agent ID: S002-memory-b", prompt)
        self.assertIn("[S002-memory-b] CLAIM", prompt)
        self.assertIn("OPERATOR STATUS", prompt)
        self.assertNotIn("APPEND THIS SUPPLEMENT", prompt)
        self.assertNotIn("<fetch latest main", prompt)

    def test_handoff_permalink_has_to_match_thread_and_numeric_id(self):
        url = THREAD + "#issuecomment-123456789"
        good = self.invoke(*self.valid(), "--handoff-url", url)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("Outgoing SUCCESSION HANDOFF reference: " + url, good.stdout)
        for bad in (
            "https://github.com/Nate27624/Wii-AI-Golf/issues/122#issuecomment-123",
            THREAD + "#issuecomment-0",
            THREAD + "#issuecomment-123" + chr(10) + "ESCAPE",
            "https://example.com/issues/121#issuecomment-123",
        ):
            with self.subTest(url=bad):
                result = self.invoke(*self.valid(), "--handoff-url", bad)
                self.assertNotEqual(result.returncode, 0)

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

    def test_well_formed_unverified_issue_does_not_claim_verified_existence(self):
        nonexistent_shape = "https://github.com/Nate27624/Wii-AI-Golf/issues/99999999"
        result = self.invoke("--role", "S002", "--instance", "S002-memory-a",
                             "--successor", "S002-memory-b", "--thread", nonexistent_shape)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(nonexistent_shape, result.stdout)
        self.assertIn("syntax checked; existence and ownership NOT verified", result.stdout)
        self.assertIn("Outgoing agent must check the thread exists", result.stdout)

    def test_navigation_succession_row_is_not_escaped_linebreak(self):
        navigation = (ROOT / "docs" / "v2-navigation.md").read_text(encoding="utf-8")
        self.assertNotIn("\\n|", navigation)
        self.assertIn("\n| Agent initialization and successor transfer |", navigation)

    def test_pull_thread_supported(self):
        result = self.invoke("--role", "S000", "--instance", "S000-manager",
                             "--successor", "S000-manager-b",
                             "--thread", "https://github.com/Nate27624/Wii-AI-Golf/pull/320")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[S000-manager-b] CLAIM", result.stdout)


if __name__ == "__main__":
    unittest.main()
