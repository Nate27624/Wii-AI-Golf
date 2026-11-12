#!/usr/bin/env python3
"""Private GitHub Issues mailbox -> locally approved, FIXED Windows project tasks.

This deliberately does NOT run commands, scripts or PowerShell supplied by
issues, comments or pull requests. All operation commands are coded here,
arguments are strict JSON data, and every code-executing operation requires
confirmation on the local console. The mailbox MUST be a separate PRIVATE
GitHub repository. No GitHub Actions self-hosted runner is installed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api.github.com"
SCHEMA = "wii-golf-localops-v1"
TITLE = "[WII-LOCALOPS-v1]"
RESULT = "WII_LOCALOPS_RESULT_V1"
MAX_ISSUES = 30
MAX_BODY = 1500
MAX_OUTPUT = 4800
POLL_SECONDS = 12
ALLOWED = frozenset({
    "repo_status", "list_project_files", "run_inspector_tests",
    "sync_review_branch", "launch_inspector",
})
BRANCH = re.compile(r"^agent/[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


class BridgeError(Exception):
    """Controlled, display-safe bridge validation error."""


class APIClient:
    def __init__(self, token: str, mailbox: str):
        if not token or len(token) < 16:
            raise BridgeError("Missing restricted GitHub Issues token")
        if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", mailbox):
            raise BridgeError("Invalid mailbox repository name")
        self.token, self.mailbox = token, mailbox

    def call(self, method: str, path: str, payload: dict | None = None):
        if not path.startswith("/") or ".." in path or "://" in path:
            raise BridgeError("Invalid GitHub API path")
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            API + path, data=data, method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "WiiGolfPrivateLocalOps/1",
                **({"Content-Type": "application/json"} if data else {}),
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(150_000)
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            raise BridgeError(
                f"GitHub API HTTP {exc.code}; check private repo and token scopes"
            ) from None
        except (URLError, TimeoutError):
            raise BridgeError("Cannot reach GitHub API") from None

    def verify_private(self) -> None:
        info = self.call("GET", "/repos/" + self.mailbox)
        if info.get("private") is not True or info.get("full_name") != self.mailbox:
            raise BridgeError("REFUSING: command mailbox must be a PRIVATE repository")

    def pending(self) -> list[dict]:
        items = self.call(
            "GET", "/repos/" + self.mailbox
            + "/issues?state=open&per_page=" + str(MAX_ISSUES)
            + "&sort=created&direction=asc")
        if not isinstance(items, list):
            raise BridgeError("Malformed GitHub issue listing")
        return [i for i in items if (
            isinstance(i, dict) and i.get("title") == TITLE
            and "pull_request" not in i)]

    def comments(self, number: int) -> list[dict]:
        result = self.call("GET", f"/repos/{self.mailbox}/issues/{number}/comments"
                           "?per_page=100")
        return result if isinstance(result, list) else []

    def comment(self, number: int, text: str):
        self.call("POST", f"/repos/{self.mailbox}/issues/{number}/comments",
                  {"body": text})

    def close(self, number: int):
        self.call("PATCH", f"/repos/{self.mailbox}/issues/{number}",
                  {"state": "closed"})


def decode_request(issue: dict, trusted_actor: str) -> tuple[str, dict]:
    """Strict transport shape, no shell/PowerShell, no arbitrary path/command."""
    author = issue.get("user")
    if (issue.get("title") != TITLE
            or not isinstance(author, dict)
            or not isinstance(author.get("login"), str)
            or author["login"].lower() != trusted_actor.lower()
            or "pull_request" in issue):
        raise BridgeError("Issue author/type is not trusted")
    raw = issue.get("body")
    if not isinstance(raw, str) or len(raw) > MAX_BODY:
        raise BridgeError("Invalid issue request body length")
    try:
        body = json.loads(raw)
    except (ValueError, TypeError):
        raise BridgeError("Issue body must be strict JSON") from None
    if (not isinstance(body, dict)
            or set(body) != {"schema", "operation", "params"}
            or body.get("schema") != SCHEMA
            or type(body.get("operation")) is not str
            or body["operation"] not in ALLOWED
            or not isinstance(body.get("params"), dict)):
        raise BridgeError("Unrecognized request schema/operation")
    op, params = body["operation"], body["params"]
    keys = {
        "repo_status": set(),
        "list_project_files": {"subdir"},
        "run_inspector_tests": {"suite"},
        "sync_review_branch": {"branch", "required_sha"},
        "launch_inspector": set(),
    }[op]
    if set(params) != keys:
        raise BridgeError("Unexpected or missing operation parameters")
    if op == "list_project_files":
        part = params["subdir"]
        if (not isinstance(part, str) or len(part) > 120
                or part.startswith(("/", "\\"))
                or ":" in part or "\\" in part
                or any(c in ("", ".", "..", ".git", ".env", ".venv",
                             "node_modules", "__pycache__")
                       for c in part.split("/"))
                or not re.fullmatch(r"[A-Za-z0-9_./-]+", part)):
            raise BridgeError("Invalid relative project directory")
    if op == "run_inspector_tests" and params["suite"] not in (
            "inspector", "localops"):
        raise BridgeError("Only fixed test suites are supported")
    if op == "sync_review_branch":
        branch, sha = params["branch"], params["required_sha"]
        if (not isinstance(branch, str) or not BRANCH.fullmatch(branch)
                or ".." in branch or "//" in branch or branch.endswith(("/", "."))
                or not isinstance(sha, str) or not SHA.fullmatch(sha)):
            raise BridgeError("Invalid reviewed source branch/commit")
    return op, params


def project_subdir(root: Path, relative: str) -> Path:
    try:
        # Windows can return canonical casing/long-path aliases when
        # resolving a child. Normalize the *base* before checking containment.
        root = root.resolve(strict=True)
        target = (root / relative).resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError, OSError):
        raise BridgeError("Requested project directory does not exist") from None
    if not target.is_relative_to(root) or not target.is_dir():
        raise BridgeError("Directory is outside the approved project checkout")
    return target


def describe(op: str, params: dict) -> str:
    if op == "sync_review_branch":
        return f"git fetch + DETACHED checkout {params['branch']} at verified SHA"
    if op == "run_inspector_tests":
        return f"Run fixed Python {params['suite']} tests (executes repository code)"
    if op == "launch_inspector":
        return "Start local inspector GUI using configured, fixed private paths"
    if op == "list_project_files":
        return "List names under repo/" + params["subdir"]
    return "Read-only local Git status and active commit"


def approved(op: str, description: str) -> bool:
    if op in ("repo_status", "list_project_files"):
        return True
    # No blanket prompt bypass. Even a trusted GitHub account can be
    # compromised; fetching/testing code is RCE on the local machine.
    if not sys.stdin.isatty():
        print("Declined: execution needs an interactive local console.")
        return False
    try:
        response = input(f"Approve LOCAL operation: {description}? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        return False
    return response.strip().lower() == "y"


def _child_env() -> dict[str, str]:
    """Do not expose the mailbox GitHub credential to project code/tests."""
    forbidden = {"WII_GOLF_LOCALOPS_GITHUB_TOKEN",
                 "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"}
    return {k: v for k, v in os.environ.items() if k not in forbidden}


def _redact_output(value: str) -> str:
    secret = os.environ.get("WII_GOLF_LOCALOPS_GITHUB_TOKEN", "")
    if secret:
        value = value.replace(secret, "[REDACTED GITHUB CREDENTIAL]")
    value = re.sub(r"(?i)(?:ghp_|github_pat_|ghu_|ghs_)[A-Za-z0-9_]{15,}",
                   "[REDACTED GITHUB CREDENTIAL]", value)
    return value[:MAX_OUTPUT]


def run_fixed(cmd: list[str], root: Path, timeout: int = 25) -> str:
    """No shell, user-provided command/path/executable or unbounded output."""
    try:
        result = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True,
            errors="replace", timeout=timeout, shell=False,
            stdin=subprocess.DEVNULL, check=False, env=_child_env())
    except subprocess.TimeoutExpired:
        raise BridgeError("Fixed operation timed out") from None
    except OSError:
        raise BridgeError("Required local tool unavailable") from None
    combined = _redact_output((result.stdout + "\n" + result.stderr).strip())
    if result.returncode != 0:
        raise BridgeError(
            f"Fixed command failed (exit {result.returncode}): "
            + combined[:500])
    return combined


def execute(op: str, params: dict, root: Path, terrain: Path | None,
            labels: Path | None) -> dict:
    if op == "repo_status":
        head = run_fixed(["git", "rev-parse", "--short", "HEAD"], root)
        status = run_fixed(
            ["git", "status", "--short", "--untracked-files=no"], root)
        return {"commit": head, "tracked_changes": status or "(clean)"}
    if op == "list_project_files":
        target = project_subdir(root, params["subdir"])
        entries = sorted(p.name for p in target.iterdir()
                         if not p.is_symlink() and p.name not in
                         (".git", ".env", ".venv", "__pycache__"))
        return {"subdir": params["subdir"], "names": entries[:80],
                "truncated": len(entries) > 80}
    if op == "run_inspector_tests":
        suite = params["suite"]
        patterns = (
            ("test_p0_inspector*.py", "test_p0_memory_inspector*.py")
            if suite == "inspector" else ("test_p0_localops*.py",))
        outputs = []
        for pattern in patterns:
            text = run_fixed(
                [sys.executable, "-I", "-m", "unittest", "discover",
                 "-s", "tests", "-p", pattern, "-v"], root, timeout=180)
            outputs.append(pattern + ":\n" + text[:1900])
        return {"suite": suite, "output": "\n".join(outputs)[:MAX_OUTPUT]}
    if op == "sync_review_branch":
        status = run_fixed(["git", "status", "--porcelain=v1"], root)
        if status:
            raise BridgeError("Checkout has uncommitted/untracked changes")
        branch = params["branch"]
        sha = params["required_sha"]
        remote = run_fixed(["git", "remote", "get-url", "origin"], root)
        if remote.strip().rstrip("/") not in (
            "https://github.com/Nate27624/Wii-AI-Golf.git",
            "https://github.com/Nate27624/Wii-AI-Golf",
            "git@github.com:Nate27624/Wii-AI-Golf.git"):
            raise BridgeError("Origin remote is not the approved Wii Golf repo")
        ref = "refs/remotes/origin/" + branch
        run_fixed(["git", "fetch", "--no-tags", "origin",
                   "+refs/heads/" + branch + ":" + ref], root, timeout=90)
        # EXACT reviewed commit only, never a newer unreviewed descendant.
        actual = run_fixed(["git", "rev-parse", ref], root).strip()
        if actual != sha:
            raise BridgeError("Remote branch head differs from reviewed SHA")
        run_fixed(["git", "switch", "--detach", ref], root)
        head = run_fixed(["git", "rev-parse", "HEAD"], root)
        return {"checkout": branch, "commit": head}
    if op == "launch_inspector":
        if (terrain is None or labels is None
                or not terrain.is_file() or not labels.is_file()):
            raise BridgeError("Configure existing private terrain OBJ and labels")
        script = root / "scripts" / "p0_memory_inspector.py"
        if not script.is_file():
            raise BridgeError("Inspector script missing in checkout")
        # The launched program's own code can touch local files. Explicit
        # console approval is mandatory even though arguments are fixed.
        subprocess.Popen(
            [sys.executable, "-I", str(script), "--terrain-obj",
             str(terrain), "--terrain-labels", str(labels),
             "--visual-course", "3"], cwd=str(root),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, shell=False, env=_child_env(),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        return {"status": "Inspector launch requested locally"}
    raise BridgeError("Unsupported fixed local operation")


def result_comment(number: int, op: str, state: str, payload) -> str:
    # Results go exclusively to verified PRIVATE issue. Never include
    # environment variables, auth headers or local private course content.
    # Truncate long output BEFORE serializing. JSON remains valid and
    # parseable by the ChatGPT GitHub connector after completion.
    if isinstance(payload, str):
        payload = _redact_output(payload)[:MAX_OUTPUT - 600]
    if isinstance(payload, dict):
        payload = {k: (_redact_output(str(v))[:MAX_OUTPUT - 600]
                       if isinstance(v, str) else v)
                   for k, v in payload.items()}
    text = json.dumps(
        {"schema": SCHEMA, "issue": number, "operation": op,
         "status": state, "result": payload},
        indent=2, ensure_ascii=True)
    return RESULT + "\n\x60\x60\x60json\n" + text + "\n\x60\x60\x60"


def process_one(client: APIClient, root: Path, trusted_actor: str,
                terrain: Path | None, labels: Path | None,
                dry_run: bool = False) -> bool:
    for issue in client.pending():
        number = issue.get("number")
        if type(number) is not int or number < 1:
            continue
        # Never run a request whose result/claim exists, even after a crash.
        comments = client.comments(number)
        if any(isinstance(c.get("body"), str)
               and c["body"].startswith(("WII_LOCALOPS_CLAIM_V1", RESULT))
               for c in comments):
            continue
        try:
            operation, params = decode_request(issue, trusted_actor)
        except BridgeError:
            # Ignore all untrusted/invalid requests. No remote error body
            # indicates which filter might be bypassed.
            continue
        description = describe(operation, params)
        print(f"Private issue #{number}: {description}")
        if dry_run:
            return True
        if not approved(operation, description):
            # Record a definitive local rejection, preventing repeat
            # prompts every 12 seconds while watching a pending issue.
            client.comment(number, result_comment(
                number, operation, "declined", "Local operator did not approve"))
            client.close(number)
            print("Declined; request closed without execution.")
            return True
        client.comment(number, "WII_LOCALOPS_CLAIM_V1: locally approved for "
                              + operation)
        try:
            output = execute(operation, params, root, terrain, labels)
            status = "success"
        except BridgeError as exc:
            output, status = str(exc), "error"
        except Exception:
            output, status = "Local operation failed (redacted)", "error"
        client.comment(number, result_comment(number, operation, status, output))
        client.close(number)
        print(f"Private issue #{number}: {status}")
        return True
    return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox", required=True,
                        help="Private GitHub repo, e.g. owner/Wii-AI-Golf-LocalOps")
    parser.add_argument("--worktree", required=True, type=Path)
    parser.add_argument("--trusted-actor", default="Nate27624")
    parser.add_argument("--terrain-obj", type=Path)
    parser.add_argument("--terrain-labels", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true",
                      help="Poll private issues until Ctrl+C")
    mode.add_argument("--once", action="store_true",
                      help="Process at most one request (default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print pending operation; NEVER acknowledge/execute")
    args = parser.parse_args(argv)
    root = args.worktree.resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        print("Worktree must exist and be a local Git checkout", file=sys.stderr)
        return 2
    if args.mailbox.lower() == "nate27624/wii-ai-golf":
        print("REFUSING public source repository as a command mailbox",
              file=sys.stderr)
        return 2
    token = os.environ.get("WII_GOLF_LOCALOPS_GITHUB_TOKEN", "")
    try:
        client = APIClient(token, args.mailbox)
        client.verify_private()
        while True:
            process_one(client, root, args.trusted_actor,
                        args.terrain_obj, args.terrain_labels, args.dry_run)
            if args.dry_run or not args.watch:
                return 0
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("Stopped local bridge.")
        return 0
    except BridgeError as exc:
        print(f"Local bridge stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
