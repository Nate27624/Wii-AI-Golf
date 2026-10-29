#!/usr/bin/env python3
"""Read-only V2 initialization, workload suggestion and same-agent continuation.

For live priorities, read the latest S000-manager board from canonical GitHub
coordination PR #320 using an already-authenticated GitHub CLI. If unavailable,
print a fail-closed instruction to check live GitHub in ChatGPT. No writes.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO = "Nate27624/Wii-AI-Golf"
BOARD_ISSUE = 320
START = "<!-- V2_PRIORITY_BOARD_JSON_BEGIN -->"
END = "<!-- V2_PRIORITY_BOARD_JSON_END -->"
ASSIGN_START = "<!-- V2_ASSIGNMENTS_JSON_BEGIN -->"
ASSIGN_END = "<!-- V2_ASSIGNMENTS_JSON_END -->"
ASSIGN_STATES = ("ASSIGNED", "CLAIMED", "IN_PROGRESS", "BLOCKED", "COMPLETED", "PARKED")
ROLES = {
    "S000": "Integration / coordination",
    "S001": "Dolphin runtime / input",
    "S002": "Capture / source provenance",
    "S003": "Control modeling",
    "S004": "Training / optimization",
    "S005": "Evaluation / censoring",
}
INSTANCE_PATTERN = re.compile(r"S00[0-5]-[a-z0-9][a-z0-9-]{1,39}")
THREAD_PATTERN = re.compile(
    r"https://github\.com/Nate27624/Wii-AI-Golf/(?:issues|pull)/[1-9][0-9]*"
)
PRIORITIES = ("P0", "P1", "P2")
STATUSES = ("ready_offline", "blocked", "review_only")


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True, stderr=subprocess.DEVNULL, timeout=8
        ).strip() or "unavailable"
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def github_json(endpoint: str) -> Any:
    """Read only. No shell, logins, state changes, token printing or writes."""
    try:
        process = subprocess.run(
            ["gh", "api", endpoint, "--method", "GET"],
            text=True, capture_output=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("GitHub CLI unavailable or timed out") from None
    if process.returncode:
        raise ValueError("GitHub API read unavailable (authentication/rate limit/network)")
    try:
        return json.loads(process.stdout)
    except (ValueError, TypeError):
        raise ValueError("GitHub API supplied invalid JSON") from None


def read_live_board() -> tuple[dict, str, str]:
    latest = github_json(f"repos/{REPO}/commits/main")
    main_sha = latest.get("sha")
    if not isinstance(main_sha, str) or not re.fullmatch("[0-9a-f]{40}", main_sha):
        raise ValueError("Could not authenticate remote main SHA")
    comments = github_json(f"repos/{REPO}/issues/{BOARD_ISSUE}/comments?per_page=100")
    if not isinstance(comments, list):
        raise ValueError("Unexpected coordination comments API schema")
    for comment in reversed(comments):
        if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
            continue
        # The prefix is untrusted text. Require GitHub-authenticated author identity.
        author = comment.get("user")
        if not isinstance(author, dict) or author.get("login") not in ("Nate27624", "AI-Bott"):
            continue
        body = comment["body"]
        if not body.startswith("[S000-manager] PRIORITY BOARD V2"):
            continue
        if START not in body or END not in body:
            continue
        raw = body.split(START, 1)[1].split(END, 1)[0].strip()
        try:
            board = json.loads(raw)
        except ValueError:
            raise ValueError("Latest manager priority board malformed") from None
        validate_board(board)
        url = comment.get("html_url", "")
        if not isinstance(url, str) or not url.startswith(
            f"https://github.com/{REPO}/pull/{BOARD_ISSUE}#issuecomment-"
        ):
            raise ValueError("Missing authenticated canonical priority board comment URL")
        return board, main_sha, url
    raise ValueError("No S000-manager priority board found in latest coordination comments")



def validate_roster(roster: Any) -> None:
    """Validate manager's advisory work allocations; never claim an atomic lock."""
    if not isinstance(roster, dict) or roster.get("version") != 1:
        raise ValueError("Assignment roster must have version=1")
    if not isinstance(roster.get("main_sha"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", roster["main_sha"]
    ):
        raise ValueError("Assignment roster needs verified main SHA")
    manager = roster.get("manager_id")
    if not isinstance(manager, str) or not INSTANCE_PATTERN.fullmatch(manager):
        raise ValueError("Assignment roster manager ID malformed")
    if not manager.startswith("S000-"):
        raise ValueError("Assignment roster manager must be S000")
    assignments = roster.get("assignments")
    if not isinstance(assignments, list) or not 1 <= len(assignments) <= 20:
        raise ValueError("Assignment roster requires 1-20 entries")
    ids: set[str] = set()
    task_ids: set[str] = set()
    paths: dict[str, str] = {}
    for row in assignments:
        if not isinstance(row, dict):
            raise ValueError("Assignment entry must be an object")
        instance = row.get("instance")
        role = row.get("role")
        task = row.get("task_id")
        state = row.get("state")
        objective = row.get("objective")
        thread = row.get("thread")
        owned_paths = row.get("owned_paths")
        acceptance = row.get("acceptance")
        if (not isinstance(instance, str) or
            not INSTANCE_PATTERN.fullmatch(instance) or
            not isinstance(role, str) or role not in ROLES or
            not instance.startswith(role + "-")):
            raise ValueError("Assignment has invalid agent ID/role")
        if instance in ids:
            raise ValueError("Assignment roster has duplicate instance")
        ids.add(instance)
        if not isinstance(task, str) or not re.fullmatch(r"[A-Z0-9-]{4,60}", task):
            raise ValueError("Assignment has invalid task ID")
        if state not in ASSIGN_STATES:
            raise ValueError("Assignment has invalid lifecycle state")
        if not isinstance(thread, str) or not THREAD_PATTERN.fullmatch(thread):
            raise ValueError("Assignment requires canonical owner issue/PR")
        if (not isinstance(objective, str) or
            not 8 <= len(objective) <= 220 or
            any(c in objective for c in "\r\n<>")):
            raise ValueError("Assignment objective invalid")
        if (not isinstance(acceptance, str) or
            not 8 <= len(acceptance) <= 220 or
            any(c in acceptance for c in "\r\n<>")):
            raise ValueError("Assignment acceptance invalid")
        if (not isinstance(owned_paths, list) or
            not 1 <= len(owned_paths) <= 15 or
            not all(isinstance(p, str) for p in owned_paths) or
            len(owned_paths) != len(set(owned_paths))):
            raise ValueError("Assignment needs distinct bounded paths")
        for p in owned_paths:
            if (not isinstance(p, str) or not 1 <= len(p) <= 180 or
                p.startswith("/") or "\\" in p or
                any(part in ("..", "") for part in p.split("/")) or
                any(c in p for c in "\r\n<>*?{}")):
                raise ValueError("Assignment has unsafe/unbounded path")
            # Only active code-write owners are exclusive. Read-only audits
            # must name non-overlapping evidence/issue paths or PARK.
            if state in ("ASSIGNED", "CLAIMED", "IN_PROGRESS"):
                for other_path, other_id in paths.items():
                    if (p == other_path or p.startswith(other_path + "/") or
                        other_path.startswith(p + "/")):
                        raise ValueError(
                            f"Assignment path overlaps between {other_id} and {instance}"
                        )
                paths[p] = instance
        if state in ("ASSIGNED", "CLAIMED", "IN_PROGRESS"):
            if task in task_ids:
                raise ValueError("Assignment task has multiple active owners")
            task_ids.add(task)


def read_live_roster() -> tuple[dict, str]:
    """GET-only. Match authorized GitHub author and manager identity explicitly."""
    comments = github_json(f"repos/{REPO}/issues/{BOARD_ISSUE}/comments?per_page=100")
    if not isinstance(comments, list):
        raise ValueError("Unexpected assignment comments API schema")
    for comment in reversed(comments):
        if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
            continue
        author = comment.get("user")
        if not isinstance(author, dict) or author.get("login") not in ("Nate27624", "AI-Bott"):
            continue
        body = comment["body"]
        if not body.startswith("[S000-manager] ASSIGNMENT ROSTER V2"):
            continue
        if ASSIGN_START not in body or ASSIGN_END not in body:
            raise ValueError("Latest manager assignment roster markers missing")
        try:
            roster = json.loads(body.split(ASSIGN_START, 1)[1].split(ASSIGN_END, 1)[0])
        except (ValueError, TypeError):
            raise ValueError("Latest manager assignment roster JSON malformed") from None
        validate_roster(roster)
        if roster["manager_id"] not in body.split(ASSIGN_START, 1)[0]:
            raise ValueError("Assignment roster manager ID not identified in heading")
        url = comment.get("html_url", "")
        if not isinstance(url, str) or not re.fullmatch(
            rf"https://github\.com/{re.escape(REPO)}/pull/{BOARD_ISSUE}#issuecomment-[1-9][0-9]*",
            url,
        ):
            raise ValueError("Missing canonical manager assignment permalink")
        return roster, url
    raise ValueError("No manager assignment roster published; request allocation on #320")


def print_assignment(roster: dict | None, instance: str | None, mode: str,
                     role: str | None = None) -> None:
    if roster is None:
        print("ASSIGNMENT_STATE=UNVERIFIED; do not self-assign new files")
        if (role == "S000" and isinstance(instance, str) and
                (instance.startswith("S000-manager-") or instance == "S000-manager")):
            # This is bootstrap guidance, not a grant of S000 authority.
            # Verify the UNIQUE, operator-authorized manager CLAIM on GitHub.
            print("MANAGER_BOOTSTRAP=VERIFY_UNIQUE_EXISTING_MANAGER_CLAIM")
            print("MANAGER_BOOTSTRAP_NEXT=If verified, publish FIRST ASSIGNMENT ROSTER V2 on #320")
            print("MANAGER_BOOTSTRAP_NOTE=Manager does not require its own roster entry before publishing first roster")
        else:
            print("ASSIGNMENT_NEXT=Ask S000 manager on #320 for a named exclusive assignment")
        return
    if mode == "suggest" or not instance:
        print("ASSIGNMENT_STATE=MANAGER_OWNED; new agents must request a slot from S000")
        for row in roster["assignments"]:
            print(f"ROSTER_SLOT={row['instance']} [{row['role']}] {row['state']} {row['task_id']}")
        return
    match = next((a for a in roster["assignments"] if a["instance"] == instance), None)
    if match is None:
        print("ASSIGNMENT_STATE=NOT_ASSIGNED; no automatic role or task selection")
        print("ASSIGNMENT_NEXT=Post [INSTANCE] ASSIGNMENT REQUEST on #320; await S000 roster entry")
        return
    print(f"ASSIGNMENT_STATE={match['state']}")
    print(f"ASSIGNMENT_TASK={match['task_id']}")
    print(f"ASSIGNMENT_ROLE={match['role']}")
    print(f"ASSIGNMENT_THREAD={match['thread']}")
    print(f"ASSIGNMENT_PATHS={','.join(match['owned_paths'])}")
    print(f"ASSIGNMENT_OBJECTIVE={match['objective']}")
    print(f"ASSIGNMENT_ACCEPTANCE={match['acceptance']}")
    if match["state"] in ("BLOCKED", "COMPLETED", "PARKED"):
        print("ASSIGNMENT_NEXT=No new implementation; report status or ask manager for reallocation")
    elif mode == "init":
        print("ASSIGNMENT_NEXT=Verify latest issue/PR overlaps, then post [INSTANCE] CLAIM referencing roster permalink")
    else:
        print("ASSIGNMENT_NEXT=Finish existing CLAIM first; verify unchanged assignment and overlap before edits")


def validate_board(board: Any) -> None:
    if not isinstance(board, dict) or board.get("version") != 1:
        raise ValueError("Priority board must have version=1")
    if not isinstance(board.get("main_sha"), str) or not re.fullmatch(
        "[0-9a-f]{40}", board["main_sha"]
    ):
        raise ValueError("Priority board must pin a 40-digit main SHA")
    tasks = board.get("tasks")
    if not isinstance(tasks, list) or not tasks or len(tasks) > 30:
        raise ValueError("Priority board must contain 1-30 tasks")
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Priority task must be an object")
        task_id = task.get("id")
        role = task.get("role")
        priority = task.get("priority")
        status = task.get("status")
        issue = task.get("thread")
        summary = task.get("objective")
        if not isinstance(task_id, str) or not re.fullmatch("[A-Z0-9-]{4,60}", task_id):
            raise ValueError("Invalid task ID")
        if task_id in seen:
            raise ValueError("Duplicate priority task ID")
        seen.add(task_id)
        if role not in ROLES or priority not in PRIORITIES or status not in STATUSES:
            raise ValueError("Invalid task role/priority/status")
        if not isinstance(issue, str) or not THREAD_PATTERN.fullmatch(issue):
            raise ValueError("Task thread must be a canonical repository issue or PR")
        if not isinstance(summary, str) or not 8 <= len(summary) <= 220:
            raise ValueError("Task objective length invalid")
        if any(char in summary for char in "\r\n<>"):
            raise ValueError("Task objective contains unsafe markup/control characters")


def choose_tasks(board: dict, role: str | None) -> list[dict]:
    tasks = [t for t in board["tasks"] if role is None or t["role"] == role]
    tasks.sort(key=lambda t: (PRIORITIES.index(t["priority"]),
                              STATUSES.index(t["status"]), t["id"]))
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("init", "continue", "suggest"), default="init")
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--instance", help="Same stable S00N-name on CONTINUE; distinct on new INIT")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--live", action="store_true",
                        help="Read authenticated current main + S000 priority board via gh api")
    parser.add_argument("--roster-file", type=Path,
                        help="Offline fixture; assignments NOT live/authorized")
    choice.add_argument("--board-file", type=Path,
                        help="Offline fixture/manual board; never claims live GitHub verification")
    args = parser.parse_args()
    if args.mode != "suggest":
        if not args.role or not args.instance:
            parser.error("init/continue require --role and --instance")
        if not INSTANCE_PATTERN.fullmatch(args.instance):
            parser.error("Instance must be S00N-name, lowercase letters/digits/hyphens")
        if not args.instance.startswith(args.role + "-"):
            parser.error("Instance prefix must match selected role")
    elif args.instance:
        parser.error("suggest mode does not reserve/accept an instance ID")

    root = Path(__file__).resolve().parents[1]
    charter = root / "docs" / "v2-agent-charter.md"
    if not charter.exists():
        parser.error("Missing docs/v2-agent-charter.md: sync a valid V2 checkout")
    print(f"MODE={args.mode.upper()}")
    if args.instance:
        print(f"AGENT_ID={args.instance}")
        print(f"ROLE={args.role}: {ROLES[args.role]}")
    print(f"BRANCH={git(root, 'branch', '--show-current')}")
    print(f"HEAD={git(root, 'rev-parse', 'HEAD')}")
    worktree = git(root, "status", "--porcelain")
    print(f"WORKTREE_STATUS={worktree if worktree == 'unavailable' else (worktree or 'clean')}")
    print(f"CHARTER={charter.relative_to(root)}")
    if args.role == "S000":
        manager = root / "docs" / "S000-manager-playbook.md"
        if not manager.is_file():
            parser.error("Missing S000 manager playbook")
        print(f"MANAGER_PLAYBOOK={manager.relative_to(root).as_posix()}")
        print("MANAGER_DUTY=Collect agent questions; resolve from evidence; escalate operator-only decisions.")
        print("MANAGER_DUTY=Keep roles focused, prevent duplicate implementations, and route answers back.")

    board = None
    live_sha = None
    try:
        if args.live:
            board, live_sha, permalink = read_live_board()
            print("PRIORITY_SOURCE=GITHUB_LIVE_READ")
            print(f"LIVE_MAIN_SHA={live_sha}")
            print(f"PRIORITY_BOARD_URL={permalink}")
            if board["main_sha"] != live_sha:
                print("PRIORITY_FRESHNESS=BOARD_BEHIND_MAIN; independently recheck all proposed tasks")
            else:
                print("PRIORITY_FRESHNESS=MAIN_SHA_MATCH; still check live CLAIMs and PR overlap")
        elif args.board_file:
            if not args.board_file.is_file() or args.board_file.stat().st_size > 100_000:
                raise ValueError("Offline priority file unavailable or oversized")
            board = json.loads(args.board_file.read_text(encoding="utf-8"))
            validate_board(board)
            print("PRIORITY_SOURCE=OFFLINE_UNVERIFIED")
            print("PRIORITY_FRESHNESS=UNKNOWN; no assignment is reserved or confirmed")
        else:
            print("PRIORITY_SOURCE=NOT_FETCHED")
            print("PRIORITY_FRESHNESS=UNKNOWN; use --live or GitHub connector and read S000 board")
    except (OSError, ValueError) as exc:
        print(f"PRIORITY_SOURCE=UNAVAILABLE; {exc}")
        print("PRIORITY_FRESHNESS=UNKNOWN; no task assignment inferred")
        board = None

    if board is not None:
        recommendations = choose_tasks(board, args.role)
        if not recommendations:
            print("TASK_CANDIDATES=NONE_FOR_ROLE; ask S000 on canonical issue, do not invent a task")
        for idx, task in enumerate(recommendations[:6], 1):
            print(f"TASK_CANDIDATE_{idx}={task['priority']} {task['status']} "
                  f"{task['id']} [{task['role']}] {task['thread']}")
            print(f"TASK_OBJECTIVE_{idx}={task['objective']}")
        print("TASK_CANDIDATES_ARE_S000_SUGGESTIONS_NOT_OWNERSHIP_OR_MERGE_APPROVAL")
    roster = None
    try:
        if args.live:
            roster, roster_url = read_live_roster()
            print("ROSTER_SOURCE=GITHUB_LIVE_READ")
            print(f"ROSTER_URL={roster_url}")
            if roster["main_sha"] != live_sha:
                print("ROSTER_FRESHNESS=STALE_MAIN; do not take new assignments until manager refreshes")
                roster = None
            else:
                print("ROSTER_FRESHNESS=MAIN_SHA_MATCH; still verify issue claims/PR overlaps")
        elif args.roster_file:
            if not args.roster_file.is_file() or args.roster_file.stat().st_size > 100_000:
                raise ValueError("Offline roster unavailable or oversized")
            roster = json.loads(args.roster_file.read_text(encoding="utf-8"))
            validate_roster(roster)
            print("ROSTER_SOURCE=OFFLINE_UNVERIFIED; never proof of exclusive ownership")
        else:
            print("ROSTER_SOURCE=NOT_FETCHED; use --live or connected GitHub")
    except (OSError, ValueError) as exc:
        print(f"ROSTER_SOURCE=UNAVAILABLE; {exc}")
        roster = None
    print_assignment(roster, args.instance, args.mode, args.role)
    print(f"CANONICAL_COORDINATION=https://github.com/{REPO}/pull/{BOARD_ISSUE}")
    print("ALWAYS: Read current main, root merging.md, v2-navigation, charter, continuity and latest S000 board.")
    print("ALWAYS: Inspect live parent issue CLAIM/HANDOFF, open PRs and changed-file overlaps.")
    if args.mode == "init":
        print("INIT_ACTION=Register or match manager-issued roster assignment; do not independently choose a task.")
        print("INIT_ACTION=Post [AGENT_ID] CLAIM with exact paths, evidence, tests and owner issue before edits.")
    elif args.mode == "continue":
        print("CONTINUE_ACTION=Preserve existing ID and active claim; finish/reconcile it before switching.")
        print("CONTINUE_ACTION=After HANDOFF, request next exclusive roster assignment from S000 before changing scope.")
        print("CONTINUE_ACTION=If work merged/closed, post HANDOFF; then PARK until the manager assigns new scope.")
    else:
        print("SUGGEST_ACTION=Request an available manager-issued identity/task from #320.")
        print("SUGGEST_ACTION=Do not start a duplicate agent on paths already under active CLAIM.")
    print("POST: [AGENT_ID] HANDOFF | branch/head | tests | evidence | blockers | next owner")
    print("POST: [AGENT_ID] QUESTION | blocker | evidence | options | suggested resolution")
    print("FINAL STATUS=ROLE + AGENT_ID + CONTINUE | ACTION REQUIRED | DECISION REQUIRED")
    print("USER CONTINUATION=CONTINUE V2; always show role and instance; preserve same claim")
    print("CONTEXT LIMIT=HANDOFF V2; use scripts/agent_handoff.py and a distinct successor ID")
    print("NO LIVE DOLPHIN; NO RAW CAPTURE OR PRIVATE EVIDENCE PUBLICATION.")
    print("SELF-MERGE=Allowed only when all merging.md gates PASS; GitHub protections apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
