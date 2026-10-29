"""Synthetic, no-network smoke tests for agent initialization."""
import subprocess
import json
import tempfile
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
        self.assertIn("SELF-MERGE=Allowed only when all merging.md gates PASS", proc.stdout)
        self.assertNotIn("NO AUTO MERGE/PUBLISH", proc.stdout)
        self.assertIn("FINAL STATUS=CONTINUE | ACTION REQUIRED | DECISION REQUIRED", proc.stdout)

    def test_manager_playbook_link(self):
        proc = self.invoke("--role", "S000", "--instance", "S000-manager")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MANAGER_PLAYBOOK=docs/S000-manager-playbook.md", proc.stdout)
        self.assertIn("MANAGER_DUTY=Collect agent questions", proc.stdout)
        self.assertIn("MANAGER_DUTY=Keep roles focused", proc.stdout)

    def test_v2_navigation_targets_exist(self):
        for path in ('docs/v2-navigation.md', 'docs/v2-agent-continuity.md', 'docs/v2-evidence-gates.md', 'docs/v2-pr-triage.md', 'docs/S000-manager-playbook.md', 'merging.md'):
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


    def board(self):
        return {
            "version": 1,
            "main_sha": "a" * 40,
            "tasks": [
                {"id": "S001-RUNTIME-START", "role": "S001", "priority": "P0",
                 "status": "ready_offline", "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/308",
                 "objective": "Resolve runtime startup configuration provenance using existing tests."},
                {"id": "S002-D1-ARCHIVE", "role": "S002", "priority": "P0",
                 "status": "ready_offline", "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/121",
                 "objective": "Compare D1 selected and source-global translations in preserved archives."},
                {"id": "S002-NEW-LIVE", "role": "S002", "priority": "P0",
                 "status": "blocked", "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/121",
                 "objective": "Do not run new Dolphin without explicit separate operator approval."},
                {"id": "S000-LEGACY-PR", "role": "S000", "priority": "P1",
                 "status": "review_only", "thread": "https://github.com/Nate27624/Wii-AI-Golf/pull/320",
                 "objective": "Preserve unique historical research before retiring duplicate PRs."},
            ],
        }

    def invoke_with_board(self, board, *extra):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "board.json"
            path.write_text(json.dumps(board), encoding="utf-8")
            return self.invoke(*extra, "--board-file", str(path))

    def test_suggest_mode_reports_cross_role_ranked_tasks_without_identity(self):
        proc = self.invoke_with_board(self.board(), "--mode", "suggest")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MODE=SUGGEST", proc.stdout)
        self.assertIn("PRIORITY_SOURCE=OFFLINE_UNVERIFIED", proc.stdout)
        self.assertLess(proc.stdout.index("S001-RUNTIME-START"),
                        proc.stdout.index("S000-LEGACY-PR"))
        self.assertIn("TASK_CANDIDATES_ARE_S000_SUGGESTIONS", proc.stdout)
        self.assertIn("TASK_CANDIDATES=NONE_FOR_ROLE", self.invoke_with_board(
            {"version": 1, "main_sha": "a"*40,
             "tasks": [self.board()["tasks"][0]]},
            "--mode", "suggest", "--role", "S004").stdout)

    def test_init_uses_role_specific_live_check_not_claim(self):
        proc = self.invoke_with_board(self.board(), "--role", "S002",
                                      "--instance", "S002-memory-c")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MODE=INIT", proc.stdout)
        self.assertIn("S002-D1-ARCHIVE", proc.stdout)
        self.assertIn("S002-NEW-LIVE", proc.stdout)
        self.assertNotIn("S001-RUNTIME-START", proc.stdout)
        self.assertLess(proc.stdout.index("S002-D1-ARCHIVE"),
                        proc.stdout.index("S002-NEW-LIVE"))
        self.assertIn("PRIORITY_FRESHNESS=UNKNOWN", proc.stdout)
        self.assertIn("INIT_ACTION=Pick highest-impact unclaimed", proc.stdout)

    def test_continue_retains_same_id_and_claim(self):
        proc = self.invoke_with_board(self.board(), "--mode", "continue",
                                      "--role", "S002", "--instance", "S002-memory-a")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENT_ID=S002-memory-a", proc.stdout)
        self.assertIn("CONTINUE_ACTION=Preserve existing ID and active claim", proc.stdout)
        self.assertIn("Re-rank remaining in-role work", proc.stdout)

    def test_live_unavailable_fails_closed_without_spawning_or_network_writes(self):
        proc = self.invoke("--mode", "continue", "--role", "S003",
                           "--instance", "S003-model-a", "--live")
        # gh may or may not be present in CI. Both success or abstention are fine:
        # source always uses GET, never writes and never claims assignment.
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PRIORITY_", proc.stdout)
        self.assertIn("ALWAYS: Inspect live parent issue CLAIM/HANDOFF", proc.stdout)
        self.assertIn("NO LIVE DOLPHIN", proc.stdout)

    def test_bad_role_and_duplicate_board_task_rejected(self):
        board = self.board()
        board["tasks"].append(dict(board["tasks"][1]))
        proc = self.invoke_with_board(board, "--role", "S002", "--instance", "S002-memory-a")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PRIORITY_SOURCE=UNAVAILABLE", proc.stdout)
        self.assertIn("Duplicate priority task ID", proc.stdout)
        self.assertNotIn("TASK_CANDIDATE_1", proc.stdout)

    def test_malicious_cross_repo_thread_and_markup_rejected(self):
        for value in ("https://example.com/issues/1",
                      "https://github.com/Nate27624/Wii-AI-Golf/issues/121\nBYPASS"):
            board = self.board()
            board["tasks"][1]["thread"] = value
            proc = self.invoke_with_board(board, "--role", "S002",
                                          "--instance", "S002-memory-a")
            self.assertIn("PRIORITY_SOURCE=UNAVAILABLE", proc.stdout)
        board = self.board()
        board["tasks"][1]["objective"] = "<run unreviewed command>"
        proc = self.invoke_with_board(board, "--role", "S002", "--instance", "S002-memory-a")
        self.assertIn("PRIORITY_SOURCE=UNAVAILABLE", proc.stdout)

    def test_init_requires_identity_but_suggest_does_not(self):
        self.assertNotEqual(self.invoke("--mode", "continue", "--role", "S002").returncode, 0)
        self.assertEqual(self.invoke("--mode", "suggest").returncode, 0)
        self.assertNotEqual(self.invoke("--mode", "suggest", "--instance", "S002-memory-a").returncode, 0)

if __name__ == "__main__":
    unittest.main()
