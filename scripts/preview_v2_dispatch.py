"""Offline, fail-closed preview of completed-to-next V2 agent assignments.

This tool does not fetch GitHub, write a manager roster or grant ownership.
Feed verified current-main roster/backlog JSON via local files or stdin.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VALID_READY = {"ready", "READY", "ready_offline"}
COMPLETED = {"COMPLETED", "PARKED"}
ACTIVE = {"ASSIGNED", "CLAIMED", "IN_PROGRESS", "BLOCKED"}
REQUIRED_TASK = {"id", "role", "status", "owned_paths"}
REQUIRED_ROW = {"instance", "role", "state", "owned_paths"}


def preview(roster: dict, backlog: dict, *, verified_main: str,
            handoffs: list | None = None, reserves: dict | None = None) -> dict:
    """Produce advisory proposals only, abstaining on ambiguity or conflicts."""
    if not isinstance(verified_main, str) or len(verified_main) != 40 or any(c not in "0123456789abcdef" for c in verified_main):
        raise ValueError("verified main must be an exact 40-character SHA")
    if not isinstance(roster, dict) or not isinstance(backlog, dict):
        raise ValueError("expected JSON objects")
    if roster.get("main_sha") != verified_main or backlog.get("main_sha") != verified_main:
        raise ValueError("stale-main inputs")
    rows, tasks = roster.get("assignments"), backlog.get("tasks")
    if not isinstance(rows, list) or not isinstance(tasks, list):
        raise ValueError("missing roster assignments or backlog tasks")
    if not all(isinstance(row, dict) and REQUIRED_ROW <= row.keys() for row in rows):
        raise ValueError("malformed roster row")
    if not all(isinstance(task, dict) and REQUIRED_TASK <= task.keys() for task in tasks):
        raise ValueError("malformed task row")
    if len({row["instance"] for row in rows}) != len(rows):
        raise ValueError("duplicate instance")
    used = {}
    for row in rows:
        if row["state"] not in (COMPLETED | ACTIVE):
            raise ValueError("invalid lifecycle")
        paths = row["owned_paths"]
        if not isinstance(paths, list) or any(not isinstance(p, str) or not p for p in paths):
            raise ValueError("invalid roster paths")
        if row["state"] in ACTIVE:
            for p in paths:
                if p in used:
                    raise ValueError("existing ownership collision")
                used[p] = row["instance"]

    task_ids = [task["id"] for task in tasks]
    if any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
        raise ValueError("invalid task ID")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("duplicate backlog task ID")

    # A handoff is evidence only if its exact instance and assigned task match
    # the roster. It never releases the row or grants a new claim by itself.
    receipts = handoffs or []
    if not isinstance(receipts, list):
        raise ValueError("handoffs must be a list")
    verified_receipts = {}
    for receipt in receipts:
        if not isinstance(receipt, dict) or not all(k in receipt for k in ("instance", "task_id", "status", "url", "main_sha")):
            raise ValueError("malformed handoff receipt")
        if receipt["status"] != "COMPLETE_RELEASED" or receipt["main_sha"] != verified_main:
            continue
        if not isinstance(receipt["url"], str) or not receipt["url"].startswith("https://github.com/"):
            raise ValueError("handoff missing canonical url")
        matches = [r for r in rows if r["instance"] == receipt["instance"] and r.get("task_id") == receipt["task_id"]]
        if len(matches) == 1:
            verified_receipts[receipt["instance"]] = receipt

    if reserves is None:
        reserves = {}
    if not isinstance(reserves, dict):
        raise ValueError("reserves must map agent IDs to ordered task IDs")
    if any(not isinstance(v, list) or any(not isinstance(t, str) for t in v) for v in reserves.values()):
        raise ValueError("invalid reserves")

    eligible = {}
    for task in tasks:
        paths = task["owned_paths"]
        if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p for p in paths):
            raise ValueError("invalid task paths")
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate task path")
        if task["status"] not in VALID_READY:
            continue
        role = task["role"]
        eligible.setdefault(role, []).append(task)
    proposals, skipped = [], []
    reserved = set(used)
    # Never suggest a task named by ANY roster row, including completed history.\n    assigned_ids = {row.get("task_id") for row in rows}
    for row in rows:
        if row["role"] == "S000":
            continue
        receipt = verified_receipts.get(row["instance"])
        if row["state"] not in COMPLETED and receipt is None:
            continue
        options = [t for t in eligible.get(row["role"], []) if t["id"] not in assigned_ids]
        preferred = reserves.get(row["instance"], [])
        options.sort(key=lambda t: (preferred.index(t["id"]) if t["id"] in preferred else len(preferred), {"P0": 0, "P1": 1, "P2": 2}.get(t.get("priority"), 3), t["id"]))
        selected = None
        for task in options:
            if task["id"] == row.get("task_id") or any(p in reserved and used.get(p) != row["instance"] for p in task["owned_paths"]):
                continue
            if task.get("dependencies") not in (None, []):
                continue  # Dependency clearance requires separate manager evidence.
            selected = task
            break
        if selected is None:
            skipped.append({"instance": row["instance"], "reason": "no unblocked conflict-free ready task"})
            continue
        reserved.update(selected["owned_paths"])
        assigned_ids.add(selected["id"])
        proposals.append({"instance": row["instance"], "role": row["role"],
                          "requires_roster_reconciliation": row["state"] not in COMPLETED,
                          "handoff": receipt["url"] if receipt else None,
                          "task_id": selected["id"], "proposed_paths": selected["owned_paths"],
                          "status": "MANAGER_REVIEW_REQUIRED"})
    return {"main_sha": verified_main, "proposals": proposals, "skipped": skipped,
            "authorization": "ADVISORY_ONLY_NOT_A_CLAIM"}




ADVISORY_START = "<!-- V2_DISPATCH_ADVISORY_JSON_BEGIN -->"
ADVISORY_END = "<!-- V2_DISPATCH_ADVISORY_JSON_END -->"
CANONICAL_REPO = "Nate27624/Wii-AI-Golf"
TRUSTED_LOGINS = {"AI-Bott", "Nate27624"}


def _trusted_comment(comment: dict) -> bool:
    """Authenticate the GitHub account, not the claimed agent chat identity."""
    return (isinstance(comment, dict)
            and isinstance(comment.get("user"), dict)
            and comment["user"].get("login") in TRUSTED_LOGINS)


def parse_advisory(comments: list, *, verified_main: str,
                   roster_comment_id: int) -> dict:
    """Read latest GitHub-authored dispatcher snapshot; refuse stale context."""
    for comment in reversed(comments):
        if not _trusted_comment(comment):
            continue
        body = comment.get("body", "")
        if not isinstance(body, str) or not body.startswith("[S000-dispatcher-"):
            continue
        if ADVISORY_START not in body:
            continue
        if ADVISORY_END not in body:
            raise ValueError("Latest dispatcher advisory is truncated")
        raw = body.split(ADVISORY_START, 1)[1].split(ADVISORY_END, 1)[0].strip()
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise ValueError("Malformed dispatcher advisory JSON") from None
        if (data.get("schema") != "v2-dispatch-advisory-v1"
                or data.get("authority") != "ADVISORY_ONLY_NOT_A_CLAIM"
                or data.get("roster_comment_id") != roster_comment_id
                or data.get("main_sha") != verified_main):
            raise ValueError("Dispatcher advisory stale or untrusted")
        return data
    raise ValueError("No authenticated dispatcher advisory snapshot found")


def find_handoff(row: dict, issue_comments: list, *, verified_main: str,
                 roster_created_at: str) -> dict | None:
    """Identify a *candidate* source receipt for manager review, never a release.

    Account ownership and comment body are checked; agent identity is not
    cryptographically authenticated because multiple agents share a login.
    """
    latest = None
    for comment in issue_comments:
        if not _trusted_comment(comment):
            continue
        body = comment.get("body")
        created = comment.get("created_at", "")
        if not isinstance(body, str) or not isinstance(created, str):
            continue
        if created < roster_created_at:
            continue
        prefix = f"[{row['instance']}]"
        if not body.startswith(prefix):
            continue
        # Any newer explicit CLAIM negates an earlier handoff observation.
        if body[len(prefix):].lstrip().startswith("CLAIM"):
            latest = None
        if not body[len(prefix):].lstrip().startswith("HANDOFF"):
            continue
        lowered = body.lower()
        if (row["task_id"] not in body or verified_main not in body
                or "releas" not in lowered
                or re.search(r"\b(?:not|never)\s+releas(?:e|ed)\b", lowered)):
            continue
        url = comment.get("html_url", "")
        if (not isinstance(url, str) or not re.fullmatch(
                r"https://github\.com/Nate27624/Wii-AI-Golf/(issues|pull)/[1-9][0-9]*#issuecomment-[1-9][0-9]*", url)
                or not url.startswith(row["thread"] + "#issuecomment-")):
            continue
        latest = {"instance": row["instance"], "task_id": row["task_id"],
                  "status": "COMPLETE_RELEASED", "main_sha": verified_main,
                  "url": url}
    return latest


def load_live() -> tuple[dict, dict, str, list]:
    """Read-only gh API integration. Aborts on stale roster/advisory."""
    try:
        from scripts import agent_init
    except ImportError:
        import agent_init
    latest = agent_init.github_json(f"repos/{CANONICAL_REPO}/commits/main")
    sha = latest.get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Unverified live main")
    comments = agent_init.read_coordination_comments()
    roster, url = agent_init.read_live_roster()
    if roster["main_sha"] != sha:
        raise ValueError("Current roster stale relative to main")
    m = re.search(r"#issuecomment-([1-9][0-9]*)$", url)
    if not m:
        raise ValueError("Missing roster comment ID")
    roster_id = int(m.group(1))
    advisory = parse_advisory(comments, verified_main=sha,
                              roster_comment_id=roster_id)
    roster_comment = next((c for c in comments if c.get("id") == roster_id), None)
    if roster_comment is None or not _trusted_comment(roster_comment):
        raise ValueError("Cannot verify roster comment origin")
    handoffs = []
    for row in roster["assignments"]:
        if row["role"] == "S000" or row["state"] not in ACTIVE:
            continue
        issue = re.fullmatch(
            r"https://github\.com/Nate27624/Wii-AI-Golf/(?:issues|pull)/([1-9][0-9]*)",
            row["thread"])
        if issue is None:
            raise ValueError("Invalid owner issue")
        issue_no = issue.group(1)
        history = []
        for page in range(1, 11):
            chunk = agent_init.github_json(
                f"repos/{CANONICAL_REPO}/issues/{issue_no}/comments?per_page=100&page={page}"
            )
            if not isinstance(chunk, list) or len(chunk) > 100:
                raise ValueError("Invalid issue history")
            history.extend(chunk)
            if len(chunk) < 100:
                break
        else:
            raise ValueError("Issue history exceeds bounded fetch")
        receipt = find_handoff(row, history, verified_main=sha,
                               roster_created_at=roster_comment["created_at"])
        if receipt:
            handoffs.append(receipt)
    return roster, advisory, sha, handoffs

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path)
    parser.add_argument("--live", action="store_true", help="Read authenticated GitHub main, roster, backlog and handoff comments")
    parser.add_argument("--backlog", type=Path)
    parser.add_argument("--main-sha")
    parser.add_argument("--handoffs", type=Path)
    parser.add_argument("--reserves", type=Path)
    args = parser.parse_args()
    if args.live:
        if args.roster or args.backlog or args.handoffs:
            parser.error("--live cannot mix with unverified roster/backlog/handoff files")
        roster, backlog, sha, handoffs = load_live()
        if args.main_sha and args.main_sha != sha:
            raise ValueError("Live main differs from expected SHA")
    else:
        if not args.roster or not args.backlog or not args.main_sha:
            parser.error("Offline preview requires --roster, --backlog and --main-sha")
        roster = json.loads(args.roster.read_text(encoding="utf-8"))
        backlog = json.loads(args.backlog.read_text(encoding="utf-8"))
        sha = args.main_sha
        handoffs = json.loads(args.handoffs.read_text(encoding="utf-8")) if args.handoffs else None
    result = preview(roster, backlog, verified_main=sha, handoffs=handoffs,
                     reserves=json.loads(args.reserves.read_text(encoding="utf-8")) if args.reserves else None)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
