#!/usr/bin/env python3
"""Pure data contract for requesting the separate PRIVATE LocalOps v2 agent.

This module NEVER opens network connections, runs commands, reads environment
variables, or accesses the operator's machine. Authorized ChatGPT agents can
produce the exact GitHub issue title/body through their GitHub connector and
parse the agent's result comments. Execution policies reside ONLY in the
private LocalOps agent's local Windows configuration.
"""
from __future__ import annotations

import json
import re

MAILBOX_REPOSITORY = "Nate27624/Wii-AI-Golf-LocalOps"
ISSUE_TITLE = "[LOCALOPS-v2]"
SCHEMA = "localops-v2"
PROJECT = "wii-golf"
RESULT_MARKER = "LOCALOPS_RESULT_V2"
APPROVAL_MARKER = "LOCALOPS_APPROVAL_REQUIRED_V2"
FEEDBACK_MARKER = "LOCALOPS_OPERATOR_FEEDBACK_V2"
NAME = re.compile(r"[a-z][a-z0-9_-]{0,49}\Z")
BRANCH = re.compile(r"agent/[A-Za-z0-9][A-Za-z0-9._/-]{0,90}\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
PATH_PART = re.compile(r"[A-Za-z0-9._-]+\Z")
DENIED_PARTS = frozenset({
    "", ".", "..", ".git", ".env", ".venv",
    ".ssh", ".config", "node_modules", "__pycache__", "secrets",
})
OPERATIONS = frozenset({
    "git_status", "list_files", "run_task", "checkout_reviewed",
    "run_research",
})
RESEARCH_ARG = re.compile(
    r"(?:--?[A-Za-z][A-Za-z0-9-]{0,31}(?:=[A-Za-z0-9_.:-]{1,64})?"
    r"|[A-Za-z0-9_.:][A-Za-z0-9_.:-]{0,63})\Z")


def request(operation: str, *, task: str | None = None,
            subdir: str | None = None, branch: str | None = None,
            sha: str | None = None, script: str | None = None,
            args: list[str] | None = None,
            intent: str | None = None,
            expected_output: str | None = None) -> tuple[str, str]:
    """Return title + JSON body for ONE request; never execute any task.

    run_task always chooses a locally pre-registered named task. The title
    and body must be submitted to MAILBOX_REPOSITORY, not Wii-AI-Golf.
    """
    if type(operation) is not str or operation not in OPERATIONS:
        raise ValueError("Unrecognized LocalOps operation")
    if operation == "git_status":
        if any(x is not None for x in (
                task, subdir, branch, sha, script, args)):
            raise ValueError("git_status does not accept parameters")
        params = {}
    elif operation == "run_task":
        if (type(task) is not str or not NAME.fullmatch(task)
                or any(x is not None for x in (
                    subdir, branch, sha, script, args))):
            raise ValueError("Only a registered task NAME is allowed")
        params = {"task": task}
    elif operation == "list_files":
        if (type(subdir) is not str or not 1 <= len(subdir) <= 130
                or subdir.startswith(("/", "\\"))
                or "\\" in subdir or ":" in subdir
                or any(not PATH_PART.fullmatch(part)
                       or part in DENIED_PARTS for part in subdir.split("/"))
                or any(x is not None for x in (
                    task, branch, sha, script, args))):
            raise ValueError("Invalid relative project subdirectory")
        params = {"subdir": subdir}
    elif operation == "run_research":
        if (type(script) is not str or not 1 <= len(script) <= 180
                or not script.endswith(".py")
                or script.startswith(("/", "\\"))
                or "\\" in script or ":" in script
                or any(not PATH_PART.fullmatch(part)
                       or part in DENIED_PARTS or part.startswith(".")
                       for part in script.split("/"))
                or "/" not in script
                or any(x is not None for x in (task, subdir, branch, sha))):
            raise ValueError("Invalid project-relative study script path")
        if args is None:
            args = []
        if (type(args) is not list or len(args) > 12
                or any(type(v) is not str
                       or not RESEARCH_ARG.fullmatch(v)
                       or ".." in v or "://" in v
                       or v.lower().startswith((
                           "-c", "--exec", "--eval", "--script",
                           "--file", "--path", "--config",
                           "--input", "--output", "--shell"))
                       for v in args)):
            raise ValueError("Research args must be bounded simple CLI tokens")
        params = {"script": script, "args": args}
    else:  # checkout_reviewed
        if (type(branch) is not str or not BRANCH.fullmatch(branch)
                or ".." in branch or "//" in branch
                or branch.endswith(("/", "."))
                or type(sha) is not str or not SHA40.fullmatch(sha)
                or any(x is not None for x in (task, subdir, script, args))):
            raise ValueError("An exact reviewed agent branch and SHA are required")
        params = {"branch": branch, "sha": sha}
    body = {"schema": SCHEMA, "project": PROJECT,
            "operation": operation, "params": params}
    for key, value in (("intent", intent), ("expected_output", expected_output)):
        if value is None:
            continue
        if (type(value) is not str or not 1 <= len(value) <= 180
                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError("Approval summary must be 1-180 printable characters")
        body[key] = value
    return ISSUE_TITLE, json.dumps(body, separators=(",", ":"), sort_keys=True)


def parse_result_comment(comment_body: str, *, issue_number: int,
                         operation: str) -> dict | None:
    """Parse a trusted author's structured LocalOps RESULT, or return None.

    The caller MUST verify the comment's GitHub repo/author and issue number
    through its authenticated connector. This parser itself is not an
    authentication mechanism. A CLAIM or pending-approval comment is NOT
    execution evidence.
    """
    if (type(comment_body) is not str or len(comment_body) > 20000
            or type(issue_number) is not int or issue_number < 1
            or operation not in OPERATIONS):
        return None
    start = RESULT_MARKER + "\n```json\n"
    if not comment_body.startswith(start) or not comment_body.endswith("\n```"):
        return None
    raw = comment_body[len(start):-4]
    try:
        result = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if (type(result) is not dict
            or set(result) != {"schema", "issue", "operation", "status", "result"}
            or result["schema"] != SCHEMA
            or type(result["issue"]) is not int or result["issue"] != issue_number
            or result["operation"] != operation
            or result["status"] not in ("success", "error", "declined")
            or not isinstance(result["result"], (dict, str))):
        return None
    return result


def parse_operator_feedback(comment_body: str, *, issue_number: int) -> dict | None:
    """Parse non-executable operator feedback after verifying issue/author."""
    if (type(comment_body) is not str or len(comment_body) > 1500
            or type(issue_number) is not int or issue_number < 1
            or not comment_body.startswith(FEEDBACK_MARKER + "\n")):
        return None
    try:
        item = json.loads(comment_body[len(FEEDBACK_MARKER) + 1:])
    except (ValueError, TypeError):
        return None
    if (type(item) is not dict
            or set(item) != {"issue", "decision", "feedback"}
            or type(item["issue"]) is not int or item["issue"] != issue_number
            or item["decision"] not in ("success", "error", "declined")
            or type(item["feedback"]) is not str
            or not 1 <= len(item["feedback"]) <= 1000):
        return None
    return item


def approval_pending(comment_body: str) -> bool:
    """This is a *request to ask the operator*, not proof of approval."""
    return (type(comment_body) is str
            and comment_body.startswith(APPROVAL_MARKER + ": "))


if __name__ == "__main__":
    # This module is a contract library, deliberately not a CLI that sends
    # private requests or executes local code.
    raise SystemExit("Use the GitHub connector to submit private LocalOps issues.")
