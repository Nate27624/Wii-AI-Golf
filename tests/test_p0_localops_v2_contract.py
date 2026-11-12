"""Synthetic-only public LocalOps v2 consumer contract for Wii Golf agents."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts" / "local_ops" / "contract_v2.py"
spec = importlib.util.spec_from_file_location("wii_golf_localops_contract", FILE)
contract = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contract
spec.loader.exec_module(contract)


class PublicContractTests(unittest.TestCase):
    def assert_request(self, op, params, **kwargs):
        title, raw = contract.request(op, **kwargs)
        self.assertEqual(title, "[LOCALOPS-v2]")
        obj = json.loads(raw)
        self.assertEqual(obj, {
            "schema": "localops-v2",
            "project": "wii-golf",
            "operation": op,
            "params": params})
        # Never submit to public source repo.
        self.assertEqual(
            contract.MAILBOX_REPOSITORY,
            "Nate27624/Wii-AI-Golf-LocalOps")
        self.assertNotEqual(
            contract.MAILBOX_REPOSITORY, "Nate27624/Wii-AI-Golf")

    def test_readonly_status_and_bounded_list(self):
        self.assert_request("git_status", {})
        self.assert_request("list_files", {"subdir": "scripts/local_ops"},
                            subdir="scripts/local_ops")
        self.assert_request("list_files", {"subdir": "tests"}, subdir="tests")

    def test_named_local_tasks_no_remote_command_argv_or_shell(self):
        for name in ("python_version", "inspector_tests",
                     "viewer_tests", "launch_inspector"):
            with self.subTest(name=name):
                self.assert_request("run_task", {"task": name}, task=name)
        source = FILE.read_text("utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("Popen(", source)

    def test_exact_sha_only_for_checkout(self):
        sha = "b8cd643b93386d22d22ccc05169156ff2c59fe06"
        self.assert_request("checkout_reviewed", {
            "branch": "agent/p0-inspector-3d-ball-trace-20261111",
            "sha": sha}, branch="agent/p0-inspector-3d-ball-trace-20261111",
            sha=sha)

    def test_fail_closed_on_injected_or_malformed_request(self):
        invalid = [
            ("powershell", {}),
            ("run_task", {"task": "cmd /c whoami"}),
            ("run_task", {"task": "../secrets"}),
            ("run_task", {"task": True}),
            ("run_task", {"task": "inspector_tests", "subdir": "src"}),
            ("run_task", {}),
            ("git_status", {"task": "python_version"}),
            ("list_files", {"subdir": "../secrets"}),
            ("list_files", {"subdir": ".git"}),
            ("list_files", {"subdir": "src/.env"}),
            ("list_files", {"subdir": "C:/Users/Nate"}),
            ("list_files", {"subdir": "a\\b"}),
            ("list_files", {"subdir": "/etc"}),
            ("list_files", {"subdir": ""}),
            ("checkout_reviewed", {
                "branch": "agent/../x", "sha": "a"*40}),
            ("checkout_reviewed", {
                "branch": "main", "sha": "a"*40}),
            ("checkout_reviewed", {
                "branch": "agent/valid", "sha": "not-a-sha"}),
            ("checkout_reviewed", {
                "branch": "agent/valid", "sha": True}),
        ]
        for op, args in invalid:
            with self.subTest(op=op, args=args), self.assertRaises(ValueError):
                contract.request(op, **args)

    def test_result_requires_exact_envelope_and_matching_issue(self):
        sample = {
            "schema": "localops-v2",
            "issue": 3,
            "operation": "git_status",
            "status": "success",
            "result": {"head": "b8cd643b", "tracked_changes": "(clean)"},
        }
        text = ("LOCALOPS_RESULT_V2\n```json\n"
                + json.dumps(sample, indent=2) + "\n```")
        self.assertEqual(contract.parse_result_comment(
            text, issue_number=3, operation="git_status"), sample)
        self.assertIsNone(contract.parse_result_comment(
            text, issue_number=4, operation="git_status"))
        self.assertIsNone(contract.parse_result_comment(
            text, issue_number=3, operation="run_task"))
        self.assertIsNone(contract.parse_result_comment(
            "LOCALOPS_CLAIM_V2: wii-golf/git_status",
            issue_number=3, operation="git_status"))
        self.assertIsNone(contract.parse_result_comment(
            "LOCALOPS_APPROVAL_REQUIRED_V2: wii-golf/run_task",
            issue_number=3, operation="git_status"))
        self.assertTrue(contract.approval_pending(
            "LOCALOPS_APPROVAL_REQUIRED_V2: wii-golf/run_task"))
        self.assertFalse(contract.approval_pending(text))

    def test_result_rejects_extra_fields_malformed_json_and_bool_id(self):
        item = {"schema": "localops-v2", "issue": 3,
                "operation": "run_task", "status": "success",
                "result": {"output": "ok"}}
        def comment(data):
            return ("LOCALOPS_RESULT_V2\n```json\n"
                    + json.dumps(data) + "\n```")
        for bad in (
            {**item, "shell": "pwsh"},
            {**item, "issue": True},
            {**item, "status": "pending"},
            {**item, "schema": "wii-golf-localops-v1"},
            {**item, "result": ["/sensitive/paths"]},
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(contract.parse_result_comment(
                    comment(bad), issue_number=3, operation="run_task"))
        self.assertIsNone(contract.parse_result_comment(
            "LOCALOPS_RESULT_V2\n```json\n{BROKEN}\n```",
            issue_number=3, operation="run_task"))

    def test_agent_onboarding_points_to_remote_contract(self):
        agents = (ROOT / "AGENTS.md").read_text("utf-8")
        readme = (ROOT / "README.md").read_text("utf-8")
        guide = (ROOT / "docs" / "v2-localops-agent-guide.md").read_text("utf-8")
        self.assertIn("docs/v2-localops-agent-guide.md", agents)
        self.assertIn("docs/v2-localops-agent-guide.md", readme)
        for necessary in (
            "[LOCALOPS-v2]", "LOCALOPS_RESULT_V2",
            "LOCALOPS_APPROVAL_REQUIRED_V2", "wii-golf",
            "Nate27624/Wii-AI-Golf-LocalOps",
            "git_status", "list_files", "run_task",
            "checkout_reviewed", "source", "approval",
        ):
            with self.subTest(necessary=necessary):
                self.assertIn(necessary, guide)
        self.assertIn("No game input", guide)
        self.assertIn("not equivalent to permission", guide)


if __name__ == "__main__":
    unittest.main()
