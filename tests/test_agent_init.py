"""Synthetic, no-network smoke tests for agent initialization."""
import subprocess
import json
import tempfile
import os
import importlib.util
from unittest.mock import patch
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
        self.assertIn("FINAL STATUS=ROLE + AGENT_ID + CONTINUE | ACTION REQUIRED | DECISION REQUIRED", proc.stdout)

    def test_manager_can_bootstrap_first_roster_but_cleanup_cannot(self):
        manager = self.invoke("--mode", "continue", "--role", "S000",
                              "--instance", "S000-manager-recovery-20261029-a")
        self.assertEqual(manager.returncode, 0, manager.stderr)
        self.assertIn("ROLE=S000:", manager.stdout)
        self.assertIn("MANAGER_BOOTSTRAP=VERIFY_UNIQUE_EXISTING_MANAGER_CLAIM", manager.stdout)
        self.assertIn("MANAGER_BOOTSTRAP_NEXT=If verified, publish FIRST ASSIGNMENT ROSTER V2", manager.stdout)
        self.assertNotIn("ASSIGNMENT_TASK=", manager.stdout)
        cleanup = self.invoke("--mode", "continue", "--role", "S000",
                              "--instance", "S000-cleanup-recovery-20261029-a")
        self.assertEqual(cleanup.returncode, 0, cleanup.stderr)
        self.assertIn("ASSIGNMENT_STATE=UNVERIFIED", cleanup.stdout)
        self.assertIn("Ask S000 manager", cleanup.stdout)
        self.assertNotIn("MANAGER_BOOTSTRAP=", cleanup.stdout)

    def test_continue_reports_role_and_instance_at_unassigned_bootstrap(self):
        proc = self.invoke("--mode", "continue", "--role", "S005",
                           "--instance", "S005-heldout-audit-1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ROLE=S005: Evaluation / censoring", proc.stdout)
        self.assertIn("AGENT_ID=S005-heldout-audit-1", proc.stdout)
        self.assertIn("FINAL STATUS=ROLE + AGENT_ID", proc.stdout)

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
        self.assertIn("INIT_ACTION=Register or match manager-issued roster assignment", proc.stdout)
        self.assertIn("ASSIGNMENT_STATE=UNVERIFIED", proc.stdout)

    def test_continue_retains_same_id_and_claim(self):
        proc = self.invoke_with_board(self.board(), "--mode", "continue",
                                      "--role", "S002", "--instance", "S002-memory-a")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("AGENT_ID=S002-memory-a", proc.stdout)
        self.assertIn("CONTINUE_ACTION=Preserve existing ID and active claim", proc.stdout)
        self.assertIn("After HANDOFF, request next exclusive roster assignment", proc.stdout)

    def test_live_unavailable_fails_closed_without_spawning_or_network_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--mode", "continue",
                 "--role", "S003", "--instance", "S003-model-a", "--live"],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
                env={**os.environ, "PATH": temp},
            )
        # No gh exists on PATH: must fail closed, with no fake assignment.
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PRIORITY_SOURCE=UNAVAILABLE", proc.stdout)
        self.assertNotIn("TASK_CANDIDATE_1", proc.stdout)
        self.assertIn("ALWAYS: Inspect live parent issue CLAIM/HANDOFF", proc.stdout)
        self.assertIn("NO LIVE DOLPHIN", proc.stdout)


    def test_live_board_uses_latest_verified_owner_comment_and_main_sha(self):
        spec = importlib.util.spec_from_file_location("v2_agent_init", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        board = self.board()
        blob = (
            "[S000-manager] PRIORITY BOARD V2\n"
            + module.START + "\n" + json.dumps(board) + "\n" + module.END
        )
        link = ("https://github.com/Nate27624/Wii-AI-Golf/pull/320"
                "#issuecomment-6489140049")
        good = {"user": {"login": "Nate27624"}, "body": blob, "html_url": link}
        forged = {"user": {"login": "untrusted_user"}, "body": blob, "html_url": link}
        with patch.object(module, "github_json",
                          side_effect=[{"sha": "a"*40}, [good, forged]]):
            result, sha, url = module.read_live_board()
        self.assertEqual(sha, "a"*40)
        self.assertEqual(url, link)
        self.assertEqual(len(result["tasks"]), 4)
        self.assertEqual(module.choose_tasks(result, "S002")[0]["id"], "S002-D1-ARCHIVE")

    def test_live_board_untrusted_author_cannot_assign_agent(self):
        spec = importlib.util.spec_from_file_location("v2_agent_init", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        board = self.board()
        comment = {
            "user": {"login": "untrusted_user"},
            "body": "[S000-manager] PRIORITY BOARD V2\n" + module.START +
                    json.dumps(board) + module.END,
            "html_url": "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7",
        }
        with patch.object(module, "github_json",
                          side_effect=[{"sha": "a"*40}, [comment]]):
            with self.assertRaisesRegex(ValueError, "No S000-manager priority board"):
                module.read_live_board()

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


    def roster(self):
        return {
            "version": 1, "main_sha": "a" * 40,
            "manager_id": "S000-manager-recovery-20261029-a",
            "assignments": [
                {"instance": "S001-runtime-a", "role": "S001",
                 "task_id": "S001-STARTUP-ROOT", "state": "ASSIGNED",
                 "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/308",
                 "owned_paths": ["scripts/launch_golf.py", "tests/test_integration_launcher.py"],
                 "objective": "Reconcile one canonical runtime user root across launcher components.",
                 "acceptance": "No conflicting edits, full exact-head two-platform offline tests."},
                {"instance": "S002-memory-a", "role": "S002",
                 "task_id": "S002-D1-ARCHIVE", "state": "IN_PROGRESS",
                 "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/121",
                 "owned_paths": ["scripts/audit_p0_seven_source_trajectory_private.py"],
                 "objective": "Compare D1 global versus selected source candidate controls.",
                 "acceptance": "Sanitized categorical source evidence, no physical ball label."},
            ],
        }

    def invoke_with_roster(self, roster, *extra):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roster.json"
            path.write_text(json.dumps(roster), encoding="utf-8")
            return self.invoke(*extra, "--roster-file", str(path))

    def test_manager_roster_for_init_requires_named_assignment(self):
        ok = self.invoke_with_roster(self.roster(), "--mode", "init",
                                     "--role", "S001", "--instance", "S001-runtime-a")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("ASSIGNMENT_STATE=ASSIGNED", ok.stdout)
        self.assertIn("ASSIGNMENT_TASK=S001-STARTUP-ROOT", ok.stdout)
        self.assertIn("ASSIGNMENT_THREAD=https://github.com/", ok.stdout)
        self.assertIn("ASSIGNMENT_NEXT=Verify latest issue/PR overlaps", ok.stdout)
        unknown = self.invoke_with_roster(self.roster(), "--mode", "init",
                                          "--role", "S003", "--instance", "S003-new-a")
        self.assertEqual(unknown.returncode, 0, unknown.stderr)
        self.assertIn("ASSIGNMENT_STATE=NOT_ASSIGNED", unknown.stdout)
        self.assertNotIn("ASSIGNMENT_TASK=", unknown.stdout)
        self.assertIn("await S000 roster entry", unknown.stdout)

    def test_continue_retains_identity_and_manager_slot(self):
        result = self.invoke_with_roster(self.roster(), "--mode", "continue",
                                         "--role", "S002", "--instance", "S002-memory-a")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ROLE=S002:", result.stdout)
        self.assertIn("ASSIGNMENT_STATE=IN_PROGRESS", result.stdout)
        self.assertIn("ASSIGNMENT_NEXT=Finish existing CLAIM first", result.stdout)
        self.assertIn("FINAL STATUS=ROLE + AGENT_ID", result.stdout)

    def test_roster_duplicates_overlapping_paths_and_spoofing_rejected(self):
        spec = importlib.util.spec_from_file_location("v2_assign_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        roster = self.roster()
        module.validate_roster(roster)
        for changed in ("instance", "task_id"):
            clone = json.loads(json.dumps(roster))
            clone["assignments"][1][changed] = clone["assignments"][0][changed]
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                module.validate_roster(clone)
        clone = json.loads(json.dumps(roster))
        clone["assignments"][1]["owned_paths"] = ["scripts/launch_golf.py"]
        with self.assertRaisesRegex(ValueError, "path overlaps"):
            module.validate_roster(clone)
        for path in ("../outside", "/tmp/private", "scripts/../x", "scripts/*.py"):
            clone = json.loads(json.dumps(roster))
            clone["assignments"][1]["owned_paths"] = [path]
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.validate_roster(clone)
        clone = json.loads(json.dumps(roster))
        clone["assignments"][1]["owned_paths"] = [{"dict": "bad"}]
        with self.assertRaises(ValueError):
            module.validate_roster(clone)

    def test_live_assignment_roster_authentic_comment_and_author(self):
        spec = importlib.util.spec_from_file_location("v2_assign_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        roster = self.roster()
        prefix = "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: S000-manager-recovery-20261029-a\n"
        body = prefix + module.ASSIGN_START + json.dumps(roster) + module.ASSIGN_END
        url = "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-100"
        trusted = {"body": body, "user": {"login": "Nate27624"}, "html_url": url}
        spoofed = {"body": body, "user": {"login": "other_user"}, "html_url": url}
        with patch.object(module, "github_json", return_value=[trusted, spoofed]):
            found, link = module.read_live_roster()
        self.assertEqual(found["manager_id"], roster["manager_id"])
        self.assertEqual(link, url)
        with patch.object(module, "github_json", return_value=[spoofed]):
            with self.assertRaisesRegex(ValueError, "No manager assignment roster"):
                module.read_live_roster()
        forged = dict(trusted)
        forged["body"] = body.replace("manager_id: S000-manager-recovery-20261029-a", "manager_id: S000-unrelated-a")
        with patch.object(module, "github_json", return_value=[forged]):
            with self.assertRaisesRegex(ValueError, "manager ID"):
                module.read_live_roster()

    def test_parked_and_complete_assignments_are_not_work_grants(self):
        for state in ("BLOCKED", "COMPLETED", "PARKED"):
            with self.subTest(state=state):
                roster = self.roster()
                roster["assignments"][0]["state"] = state
                result = self.invoke_with_roster(roster, "--mode", "continue",
                                                 "--role", "S001", "--instance", "S001-runtime-a")
                self.assertIn(f"ASSIGNMENT_STATE={state}", result.stdout)
                self.assertIn("No new implementation", result.stdout)

    def test_init_requires_identity_but_suggest_does_not(self):
        self.assertNotEqual(self.invoke("--mode", "continue", "--role", "S002").returncode, 0)
        self.assertEqual(self.invoke("--mode", "suggest").returncode, 0)
        self.assertNotEqual(self.invoke("--mode", "suggest", "--instance", "S002-memory-a").returncode, 0)


    def test_live_board_paginates_past_one_hundred_to_latest_signed_board(self):
        spec = importlib.util.spec_from_file_location("v2_page_board", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = self.board()
        newer = json.loads(json.dumps(old))
        newer["tasks"][0]["id"] = "S001-NEW-PAGE-TWO"
        url = "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-102"
        def comment(board, author="AI-Bott", link=url):
            return {"user": {"login": author},
                    "body": "[S000-manager] PRIORITY BOARD V2\n"
                            + module.START + json.dumps(board) + module.END,
                    "html_url": link}
        first = [comment(old)] + [{} for _ in range(99)]
        second = [comment(newer), comment(old, author="forged-user")]
        with patch.object(module, "github_json",
                          side_effect=[{"sha": "a"*40}, first, second]) as api:
            board, sha, link = module.read_live_board()
        self.assertEqual((sha, link), ("a"*40, url))
        self.assertEqual(board["tasks"][0]["id"], "S001-NEW-PAGE-TWO")
        self.assertIn("page=2", api.call_args_list[2].args[0])
        self.assertEqual(api.call_count, 3)

    def test_live_roster_paginates_past_one_hundred_to_latest_signed_roster(self):
        spec = importlib.util.spec_from_file_location("v2_page_roster", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = self.roster()
        newer = json.loads(json.dumps(old))
        newer["assignments"][0]["task_id"] = "S001-NEW-PAGE-TWO"
        url = "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-103"
        def comment(roster, author="AI-Bott", link=url):
            return {"user": {"login": author},
                    "body": "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: "
                            + roster["manager_id"] + "\n" + module.ASSIGN_START
                            + json.dumps(roster) + module.ASSIGN_END,
                    "html_url": link}
        first = [comment(old)] + [{} for _ in range(99)]
        second = [comment(newer), comment(old, author="forged-user")]
        with patch.object(module, "github_json", side_effect=[first, second]) as api:
            roster, link = module.read_live_roster()
        self.assertEqual(link, url)
        self.assertEqual(roster["assignments"][0]["task_id"], "S001-NEW-PAGE-TWO")
        self.assertIn("page=2", api.call_args_list[1].args[0])
        self.assertEqual(api.call_count, 2)

    def test_latest_signed_manager_malformed_must_not_fall_back_to_page_one(self):
        spec = importlib.util.spec_from_file_location("v2_bad_new_page", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        link = "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-99"
        old_board = {"body": "[S000-manager] PRIORITY BOARD V2"
                              + module.START + json.dumps(self.board()) + module.END,
                     "user": {"login": "Nate27624"}, "html_url": link}
        newer_bad_board = {"body": "[S000-manager] PRIORITY BOARD V2\nmissing markers",
                           "user": {"login": "AI-Bott"}, "html_url": link}
        first = [old_board] + [{} for _ in range(99)]
        with patch.object(module, "github_json",
                          side_effect=[{"sha": "a"*40}, first, [newer_bad_board]]):
            with self.assertRaisesRegex(ValueError, "markers missing"):
                module.read_live_board()
        old_roster = {"body": "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: "
                              + self.roster()["manager_id"] + "\n" + module.ASSIGN_START
                              + json.dumps(self.roster()) + module.ASSIGN_END,
                      "user": {"login": "Nate27624"}, "html_url": link}
        newer_bad_roster = {"body": "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: "
                                    + self.roster()["manager_id"] + "\n"
                                    + module.ASSIGN_START + "{malformed"
                                    + module.ASSIGN_END,
                            "user": {"login": "AI-Bott"}, "html_url": link}
        with patch.object(module, "github_json",
                          side_effect=[[old_roster] + [{} for _ in range(99)],
                                       [newer_bad_roster]]):
            with self.assertRaisesRegex(ValueError, "JSON malformed"):
                module.read_live_roster()

    def test_broken_second_page_does_not_grant_stale_assignment(self):
        spec = importlib.util.spec_from_file_location("v2_fail_page", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = {"user": {"login": "AI-Bott"}, "html_url":
               "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-99",
               "body": "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: "
                       + self.roster()["manager_id"] + "\n" + module.ASSIGN_START
                       + json.dumps(self.roster()) + module.ASSIGN_END}
        for bad in ("bad-schema", ValueError("GitHub page two read unavailable")):
            with self.subTest(bad=str(bad)):
                with patch.object(module, "github_json",
                                  side_effect=[[old] + [{} for _ in range(99)], bad]):
                    with self.assertRaises(ValueError):
                        module.read_live_roster()

    def test_no_authorized_roster_after_pagination_stays_unassigned(self):
        spec = importlib.util.spec_from_file_location("v2_no_page_roster", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        forged = {"user": {"login": "forged-user"},
                  "body": "[S000-manager] ASSIGNMENT ROSTER V2\n"
                          + module.ASSIGN_START + json.dumps(self.roster())
                          + module.ASSIGN_END}
        with patch.object(module, "github_json",
                          side_effect=[[{} for _ in range(100)], [forged]]):
            with self.assertRaisesRegex(ValueError, "No manager assignment roster"):
                module.read_live_roster()

    def test_pagination_budget_exhaustion_fails_closed(self):
        spec = importlib.util.spec_from_file_location("v2_many_pages", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "github_json",
                          side_effect=[[{} for _ in range(100)] for _ in range(20)]) as api:
            with self.assertRaisesRegex(ValueError, "pagination limit exceeded"):
                module.read_live_roster()
        self.assertEqual(api.call_count, 20)

    def test_stale_live_roster_main_remains_unverified(self):
        import io
        from contextlib import redirect_stdout
        spec = importlib.util.spec_from_file_location("v2_page_stale_main", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stale = self.roster()
        stale["main_sha"] = "b"*40
        url = "https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-200"
        output = io.StringIO()
        with patch.object(module, "read_live_board",
                          return_value=(self.board(), "a"*40, url)), \
             patch.object(module, "read_live_roster", return_value=(stale, url)), \
             patch.object(module, "git", return_value="clean"), \
             patch.object(sys, "argv", ["agent_init.py", "--mode", "continue",
                                       "--role", "S002", "--instance",
                                       "S002-memory-a", "--live"]), \
             redirect_stdout(output):
            self.assertEqual(module.main(), 0)
        text = output.getvalue()
        self.assertIn("ROSTER_FRESHNESS=STALE_MAIN", text)
        self.assertIn("ASSIGNMENT_STATE=UNVERIFIED", text)
        self.assertNotIn("ASSIGNMENT_TASK=", text)


if __name__ == "__main__":
    unittest.main()
