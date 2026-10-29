"""Offline, fail-closed preview of completed-to-next V2 agent assignments.

This tool does not fetch GitHub, write a manager roster or grant ownership.
Feed verified current-main roster/backlog JSON via local files or stdin.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

VALID_READY = {"ready", "READY", "ready_offline"}
COMPLETED = {"COMPLETED", "PARKED"}
ACTIVE = {"ASSIGNED", "CLAIMED", "IN_PROGRESS", "BLOCKED"}
REQUIRED_TASK = {"id", "role", "status", "owned_paths"}
REQUIRED_ROW = {"instance", "role", "state", "owned_paths"}


def preview(roster: dict, backlog: dict, *, verified_main: str) -> dict:
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
    assigned_ids = {row.get("task_id") for row in rows if row["state"] in ACTIVE}
    for row in rows:
        if row["state"] not in COMPLETED or row["role"] == "S000":
            continue
        options = [t for t in eligible.get(row["role"], []) if t["id"] not in assigned_ids]
        options.sort(key=lambda t: ({"P0": 0, "P1": 1, "P2": 2}.get(t.get("priority"), 3), t["id"]))
        selected = None
        for task in options:
            if any(p in reserved for p in task["owned_paths"]):
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
                          "task_id": selected["id"], "proposed_paths": selected["owned_paths"],
                          "status": "MANAGER_REVIEW_REQUIRED"})
    return {"main_sha": verified_main, "proposals": proposals, "skipped": skipped,
            "authorization": "ADVISORY_ONLY_NOT_A_CLAIM"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--backlog", required=True, type=Path)
    parser.add_argument("--main-sha", required=True)
    args = parser.parse_args()
    result = preview(json.loads(args.roster.read_text(encoding="utf-8")),
                     json.loads(args.backlog.read_text(encoding="utf-8")),
                     verified_main=args.main_sha)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
