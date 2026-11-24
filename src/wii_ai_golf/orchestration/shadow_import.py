"""Read-only, fail-closed V2 roster to V3 Work Queue shadow preview.

This module cannot acquire leases, publish state, inspect private data, or
authorize cutover. Inputs must be fetched and pinned by a trusted caller.
"""
from __future__ import annotations

import hashlib
import json
import re

from . import state as model

BEGIN = "<!-- V2_ASSIGNMENTS_JSON_BEGIN -->"
END = "<!-- V2_ASSIGNMENTS_JSON_END -->"
STATES = {"ASSIGNED", "CLAIMED", "BLOCKED", "PARKED", "COMPLETED"}
THREAD = re.compile(
    r"https://github[.]com/Nate27624/Wii-AI-Golf/(?:issues|pull)/([1-9][0-9]*)"
)
SHA = re.compile(r"[0-9a-f]{40}")
MAX_COMMENT = 256 * 1024


class ShadowError(ValueError):
    """Source was incomplete, stale, ambiguous, or incompatible."""


def require(ok, message):
    if not ok:
        raise ShadowError(message)


def exact_keys(obj, keys):
    require(type(obj) is dict and set(obj) == set(keys), "unexpected JSON fields")


def unique_pairs(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, "duplicate JSON member")
        d[k] = v
    return d


def parse_roster(comment, *, revision, main_sha, manager_id, comment_id):
    """Parse one *independently authenticated* exact GitHub roster comment.

    Expected revision, main head, manager and GitHub comment ID must come from
    the trusted caller, never be inferred from this untrusted comment body.
    """
    require(type(comment) is str and len(comment) <= MAX_COMMENT, "comment size")
    require(comment.lstrip().startswith("[S000-manager] ASSIGNMENT ROSTER V2"),
            "not a manager roster")
    require(comment.count(BEGIN) == 1 and comment.count(END) == 1,
            "missing or repeated V2 roster boundary")
    i, j = comment.index(BEGIN), comment.index(END)
    require(i < j and j > i + len(BEGIN), "roster boundary order")
    require(type(revision) is int and revision > 0, "expected revision")
    require(type(comment_id) is int and comment_id > 0, "source comment ID")
    require(isinstance(main_sha, str) and SHA.fullmatch(main_sha),
            "expected main SHA")
    model.ident(manager_id)
    try:
        value = json.loads(comment[i + len(BEGIN):j],
                           object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               ShadowError("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ShadowError("malformed V2 roster JSON") from exc
    exact_keys(value, ("version", "revision", "main_sha", "manager_id",
                       "assignments"))
    require(type(value["version"]) is int and value["version"] == 1,
            "V2 schema mismatch")
    require(type(value["revision"]) is int and value["revision"] == revision,
            "stale or mismatched revision")
    require(value["main_sha"] == main_sha and value["manager_id"] == manager_id,
            "unverified main or manager")
    rows = value["assignments"]
    require(type(rows) is list and 1 <= len(rows) <= 20,
            "invalid V2 roster count")
    instances, task_ids, paths = set(), set(), []
    manager_rows = 0
    for row in rows:
        exact_keys(row, ("instance", "role", "task_id", "state", "thread",
                         "owned_paths", "objective", "acceptance"))
        model.ident(row["instance"])
        model.ident(row["task_id"])
        require(row["instance"] not in instances and row["task_id"] not in task_ids,
                "duplicate V2 assignment")
        instances.add(row["instance"])
        task_ids.add(row["task_id"])
        require(row["task_id"] != model.MANAGER, "reserved V3 manager task")
        require(row["role"] in model.ROLES and row["state"] in STATES,
                "unknown role or state")
        if row["instance"] == manager_id:
            require(row["role"] == "S000", "manager role mismatch")
            manager_rows += 1
        require(type(row["thread"]) is str and THREAD.fullmatch(row["thread"]),
                "noncanonical owner issue/PR thread")
        model.text(row["objective"])
        model.text(row["acceptance"])
        owned = row["owned_paths"]
        require(type(owned) is list and 1 <= len(owned) <= 15,
                "missing or excessive path reservation")
        seen = set()
        for p in owned:
            normalized = model.path(p)
            require(normalized not in seen, "duplicate local path")
            seen.add(normalized)
            require(not any(model.overlap(p, other) for other in paths),
                    "overlapping V2 owners")
            paths.append(p)
    require(manager_rows == 1, "not exactly one V2 manager")
    # Digest identifies the submitted roster JSON, not an authenticated GitHub
    # source, verified goal revision, or green CI receipt.
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True).encode("ascii")
    return {"value": value, "sha256": hashlib.sha256(canonical).hexdigest(),
            "comment_id": comment_id,
            "comment_url": ("https://github.com/Nate27624/Wii-AI-Golf/"
                            "pull/320#issuecomment-" + str(comment_id)),
            "reservation_count": len(paths)}


def preview(roster, *, goal_sha):
    """Construct an inert V3 snapshot, NEVER write or dispatch this snapshot.

    All V2 reservations are retained as holds, including completed history.
    Unknown dependencies, PR heads, priority, approvals and CI are NOT inferred.
    """
    require(type(roster) is dict and set(roster) ==
            {"value", "sha256", "comment_id", "comment_url", "reservation_count"},
            "invalid parsed roster")
    value = roster["value"]
    # Parsing returns a mutable dict; never accept a source rewritten between
    # validation and preview merely because it still carries the old digest.
    try:
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ShadowError("invalid parsed roster") from exc
    require(hashlib.sha256(canonical).hexdigest() == roster["sha256"],
            "roster modified after source validation")
    source_id = roster["comment_id"]
    require(type(source_id) is int and source_id > 0 and
            roster["comment_url"] == (
                "https://github.com/Nate27624/Wii-AI-Golf/"
                "pull/320#issuecomment-" + str(source_id)),
            "roster source metadata modified")
    require(type(roster["reservation_count"]) is int and
            roster["reservation_count"] ==
            sum(len(row["owned_paths"]) for row in value["assignments"]),
            "roster reservation count modified")
    require(type(goal_sha) is str and SHA.fullmatch(goal_sha),
            "verified operator goal commit required")
    require(type(roster["sha256"]) is str and
            re.fullmatch(r"[0-9a-f]{64}", roster["sha256"]), "roster digest")
    manager = model.new_task(
        "S000", 0, [], [model.MANAGER_RESOURCE], [], 485,
        "Maintain the Work Queue aligned with approved project goals.",
        "Fenced, authenticated, scoped manager review without private approvals.",
        {"head": None, "next": "Verify goal revision and V2 ownership before cutover.",
         "summary": "Permanent manager blocked during read-only V2 shadow.",
         "evidence": []})
    manager["status"] = "BLOCKED"  # Even the manager cannot dispatch in shadow.
    tasks = {model.MANAGER: manager}
    holds = {}
    states = {}
    for row in value["assignments"]:
        task_id = row["task_id"]
        states[task_id] = row["state"]
        thread = int(THREAD.fullmatch(row["thread"]).group(1))
        progress = {
            "head": None,
            "next": "Verify V2 claims, dependencies, PR head, CI and consent.",
            "summary": "SHADOW ONLY: original V2 state " + row["state"] +
                       "; priority and dependency gates unverified.",
            "evidence": []}
        t = model.new_task(row["role"], 100, row["owned_paths"], [], [], thread,
                           row["objective"], row["acceptance"], progress)
        # No OPEN or IN_PROGRESS V3 specialist task until a reviewed cutover.
        t["status"] = ("CLOSED" if row["state"] == "COMPLETED" else
                       "PARKED" if row["state"] == "PARKED" else "BLOCKED")
        tasks[task_id] = t
        holds["V2-" + task_id] = {"paths": list(row["owned_paths"]),
                                  "resources": []}
    state = model.initial(tasks, holds, now=0, goal_sha=goal_sha)
    require(sum(len(h["paths"]) for h in state["holds"].values()) ==
            roster["reservation_count"], "lost V2 path reservation")
    require(all(t["status"] != "OPEN" for t in state["tasks"].values()),
            "shadow issued runnable ownership")
    return {
        "mode": "SHADOW_READ_ONLY",
        "cutover_eligible": False,
        "source": {"comment_id": roster["comment_id"],
                   "comment_url": roster["comment_url"],
                   "revision": value["revision"],
                   "main_sha": value["main_sha"],
                   "manager_id": value["manager_id"],
                   "roster_digest": roster["sha256"]},
        "original_v2_states": states,
        "reservation_count": roster["reservation_count"],
        "verification_gaps": [
            "GitHub source authenticity and latest-roster check are caller-owned",
            "Operator goal SHA must be independently approved",
            "Live claim and PR head/CI reconciliation required",
            "Priority, dependencies and private approvals are unknown",
            "No V3 lease, publishing, production state or cutover"],
        "state": state,
    }
