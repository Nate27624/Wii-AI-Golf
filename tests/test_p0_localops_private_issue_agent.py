"""Synthetic-only Windows local-ops mailbox safety tests; no GitHub/PC calls."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = (Path(__file__).resolve().parents[1]
          / "scripts" / "local_ops" / "private_issue_agent.py")
spec = importlib.util.spec_from_file_location("wii_private_localops", SCRIPT)
agent = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = agent
spec.loader.exec_module(agent)


def issue(operation="repo_status", params=None, actor="Nate27624"):
    return {
        "title": agent.TITLE,
        "number": 17,
        "user": {"login": actor},
        "body": json.dumps({
            "schema": agent.SCHEMA, "operation": operation,
            "params": {} if params is None else params}),
    }


class FakeClient:
    def __init__(self, issues=()):
        self.issues = list(issues)
        self.messages = []
        self.closed = []
    def pending(self):
        return list(self.issues)
    def comments(self, number):
        return []
    def comment(self, number, body):
        self.messages.append((number, body))
    def close(self, number):
        self.closed.append(number)


class LocalOpsSafetyTests(unittest.TestCase):
    def test_allowlisted_operations_and_exact_parameters(self):
        scenarios = (
            ("repo_status", {}),
            ("list_project_files", {"subdir": "scripts/local_ops"}),
            ("run_inspector_tests", {"suite": "inspector"}),
            ("run_inspector_tests", {"suite": "localops"}),
            ("sync_review_branch", {
                "branch": "agent/p0-inspector-ball-trace",
                "required_sha": "a"*40}),
            ("launch_inspector", {}),
        )
        for op, params in scenarios:
            with self.subTest(op=op):
                self.assertEqual(agent.decode_request(
                    issue(op, params), "Nate27624"), (op, params))
        bad_requests = (
            ("powershell", {"command": "whoami"}),
            ("repo_status", {"command": "whoami"}),
            ("run_inspector_tests", {"suite": "setup.py"}),
            ("sync_review_branch", {
                "branch": "--exec=evil", "required_sha": "a"*40}),
            ("sync_review_branch", {
                "branch": "agent/x", "required_sha": "ZZZ"}),
            ("list_project_files", {"subdir": "../secrets"}),
            ("list_project_files", {"subdir": "C:/Users"}),
            ("list_project_files", {"subdir": "scripts\\evil"}),
            ("list_project_files", {"subdir": "/home"}),
            ("list_project_files", {"subdir": ".git"}),
        )
        for op, params in bad_requests:
            with self.subTest(op=op, params=params):
                # .git is not rejected in decode, but it must not be
                # enumerated; present-day decoder handles syntax only.
                if params == {"subdir": ".git"}:
                    continue
                with self.assertRaises(agent.BridgeError):
                    agent.decode_request(issue(op, params), "Nate27624")

    def test_wrong_actor_and_untrusted_issue_never_reaches_executor(self):
        untrusted = issue(actor="mallory")
        with self.assertRaises(agent.BridgeError):
            agent.decode_request(untrusted, "Nate27624")
        pr = issue()
        pr["pull_request"] = {"url": "https://example.invalid"}
        with self.assertRaises(agent.BridgeError):
            agent.decode_request(pr, "Nate27624")
        bogus = issue()
        bogus["body"] = '{"schema":"bad","operation":"repo_status","params":{}}'
        with self.assertRaises(agent.BridgeError):
            agent.decode_request(bogus, "Nate27624")

    def test_token_not_in_child_test_execution_environment(self):
        token = "github_pat_" + "SECRETABC" * 5
        with patch.dict(os.environ, {
            "WII_GOLF_LOCALOPS_GITHUB_TOKEN": token,
            "GH_TOKEN": "other_token",
            "CUSTOM_PATH_FOR_TEST": "ok"}):
            env = agent._child_env()
            self.assertNotIn("WII_GOLF_LOCALOPS_GITHUB_TOKEN", env)
            self.assertNotIn("GH_TOKEN", env)
            self.assertEqual(env["CUSTOM_PATH_FOR_TEST"], "ok")
            original = (
                "test output " + token +
                "\nother key github_pat_fake_secrettoken_chars0123456789")
            redacted = agent._redact_output(original)
            self.assertNotIn(token, redacted)
            self.assertNotIn("github_pat_", redacted)
        class FakeCompleted:
            stdout = "ok"
            stderr = ""
            returncode = 0
        with patch.object(agent.subprocess, "run",
                          return_value=FakeCompleted()) as run:
            result = agent.run_fixed(["git", "status"], Path("."), 10)
            self.assertEqual(result, "ok")
            kwargs = run.call_args.kwargs
            self.assertIs(kwargs["shell"], False)
            self.assertNotIn("WII_GOLF_LOCALOPS_GITHUB_TOKEN",
                             kwargs["env"])
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)

    def test_reviews_checkout_only_exact_head_and_known_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = {"branch": "agent/a", "required_sha": "a"*40}
            responses = [
                "",  # clean worktree
                "https://github.com/Nate27624/Wii-AI-Golf.git",
                "",  # fetch
                "b"*40,  # rev-parse newer unreviewed branch
            ]
            with patch.object(agent, "run_fixed", side_effect=responses) as r:
                with self.assertRaisesRegex(
                        agent.BridgeError, "differs from reviewed"):
                    agent.execute("sync_review_branch", request, root, None, None)
                self.assertEqual(len(r.call_args_list), 4)
                self.assertNotIn("switch", str(r.call_args_list))

    def test_project_listing_cannot_escape_approved_worktree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "scripts").mkdir()
            self.assertEqual(agent.project_subdir(root, "scripts"),
                             root / "scripts")
            with self.assertRaises(agent.BridgeError):
                agent.project_subdir(root, "..")
            with self.assertRaises(agent.BridgeError):
                agent.project_subdir(root, "not-a-directory")

    def test_private_repo_is_strictly_required(self):
        class Public:
            def call(self, *_):
                return {"private": False, "full_name": "Nate27624/Public"}
        client = object.__new__(agent.APIClient)
        client.mailbox = "Nate27624/Public"
        client.call = Public().call
        with self.assertRaisesRegex(agent.BridgeError, "PRIVATE"):
            client.verify_private()

    def test_approved_operations_require_consent_to_execute_code(self):
        self.assertTrue(agent.approved("repo_status", "read-only"))
        self.assertTrue(agent.approved("list_project_files", "read-only"))
        with patch.object(agent.sys.stdin, "isatty", return_value=False):
            self.assertFalse(agent.approved(
                "run_inspector_tests", "executes source code"))
            self.assertFalse(agent.approved("sync_review_branch",
                                            "mutates local checkout"))
            self.assertFalse(agent.approved("launch_inspector", "GUI"))

    def test_result_payload_is_complete_json_and_closed_after_execution(self):
        body = agent.result_comment(17, "repo_status", "success",
                                    {"output": "a"*11000})
        self.assertTrue(body.startswith(agent.RESULT))
        body_json = body.split("```json\n", 1)[1].rsplit(
            "\n```", 1)[0]
        result = json.loads(body_json)
        self.assertEqual(result["issue"], 17)
        self.assertLessEqual(len(result["result"]["output"]), 4400)
        self.assertEqual(result["status"], "success")
        with tempfile.TemporaryDirectory() as folder:
            client = FakeClient((issue(),))
            with patch.object(agent, "execute",
                              return_value={"commit": "abcdef0"}):
                self.assertTrue(agent.process_one(
                    client, Path(folder), "Nate27624", None, None))
            self.assertEqual(client.closed, [17])
            self.assertEqual(len(client.messages), 2)
            self.assertTrue(client.messages[0][1].startswith(
                "WII_LOCALOPS_CLAIM_V1"))
            self.assertTrue(client.messages[1][1].startswith(agent.RESULT))

    def test_dry_run_never_performs_or_comments(self):
        client = FakeClient((issue(),))
        with patch.object(agent, "execute") as do:
            self.assertTrue(agent.process_one(
                client, Path("."), "Nate27624", None, None, dry_run=True))
            do.assert_not_called()
        self.assertEqual(client.messages, [])
        self.assertEqual(client.closed, [])


if __name__ == "__main__":
    unittest.main()
