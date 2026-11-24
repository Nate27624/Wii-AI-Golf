"""Fenced immutable artifact acceptance; no code ref writes or merges.

A trusted host inspects a proposed one-parent Git commit against an exact
base, reviews the complete manifest, then commits acceptance in the Work
Queue ledger. An accepted proposal is NOT a source-branch promotion.
"""
from __future__ import annotations

import copy
import hashlib
import re

from . import state as model
from . import github_store as storage

MAX_TREE_ENTRIES = 100_000
MAX_CHANGES = 256
_REGULAR = {"100644", "100755"}
_MODES = {"040000": "tree", "100644": "blob", "100755": "blob",
          "120000": "blob", "160000": "commit"}


class ArtifactError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ArtifactError(message)


def scope_path(path, owned):
    model.path(path)
    # Exact spelling is required for ownership; the queue's collision
    # detection is more conservative (case-insensitive).
    return any(path == root or path.startswith(root + "/") for root in owned)


def entry(value):
    if value is None:
        return
    model.fields(value, ("mode", "sha"))
    require(isinstance(value["mode"], str) and value["mode"] in _REGULAR,
            "only regular file changes permitted")
    storage.sha(value["sha"])


def validate_manifest(changes, owned):
    require(type(changes) is list and 0 < len(changes) <= MAX_CHANGES,
            "empty or oversized artifact")
    paths = []
    for change in changes:
        model.fields(change, ("path", "before", "after"))
        path = change["path"]
        require(scope_path(path, owned), "artifact outside assigned path scope")
        paths.append(model.path(path))
        before, after = change["before"], change["after"]
        entry(before)
        entry(after)
        require(before != after, "unchanged artifact entry")
    require(paths == sorted(paths) and len(paths) == len(set(paths)),
            "unordered or case-aliased manifest")
    return changes


def manifest_digest(base, head, changes):
    return hashlib.sha256(storage.canonical(
        {"base": storage.sha(base), "head": storage.sha(head), "changes": changes}
    )).hexdigest()


def make_record(current, task, run_id, fence, now, base, head, changes):
    model.active(current, task, run_id, fence)
    require(task != model.MANAGER, "manager metadata lease cannot accept source")
    require(now == current["clock"], "artifact admission time")
    validate_manifest(changes, current["tasks"][task]["paths"])
    return {"task": task, "run_id": run_id, "fence": fence, "admitted_at": now,
            "goal_sha": current["oversight"]["goal_sha"],
            "revision": current["revision"], "base": base, "head": head,
            "changes": copy.deepcopy(changes),
            "manifest_digest": manifest_digest(base, head, changes)}


def validate_record(record, current):
    model.fields(record, ("task", "run_id", "fence", "admitted_at", "goal_sha",
                          "revision", "base", "head", "changes", "manifest_digest"))
    task, run_id = model.ident(record["task"]), model.ident(record["run_id"])
    require(task in current["tasks"] and task != model.MANAGER and
            run_id in current["runs"], "artifact run missing")
    run = current["runs"][run_id]
    fence = model.integer(record["fence"], "artifact fence")
    require(run["task"] == task and run["fence"] == fence, "artifact run mismatch")
    now = model.integer(record["admitted_at"], "artifact admission time")
    require(run["acquired"] <= now <= run["heartbeat"] <= current["clock"],
            "artifact time outside run history")
    rev = model.integer(record["revision"], "artifact revision")
    require(0 < rev <= current["revision"], "artifact revision")
    storage.sha(record["goal_sha"])
    require(storage.sha(record["base"]) != storage.sha(record["head"]), "identical base/head")
    changes = validate_manifest(record["changes"], current["tasks"][task]["paths"])
    require(record["manifest_digest"] ==
            manifest_digest(record["base"], record["head"], changes),
            "artifact manifest digest mismatch")
    return record


class GitHubTreeInspector:
    """Read-only, fixed-repository Git object inspector owned by the host.

    Compare complete immutable recursive trees, not worker-supplied paths
    or a paginated/truncated compare endpoint. Unknown path spellings,
    symlink/gitlink changes and incomplete trees fail closed.
    """
    def __init__(self, transport, repository):
        require(isinstance(repository, str) and
                re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                and all(p not in (".", "..") for p in repository.split("/")),
                "invalid repository")
        self._transport = transport
        self._prefix = "/repos/" + repository + "/git/"

    def _get(self, endpoint):
        obj = self._transport("GET", self._prefix + endpoint, None)
        require(type(obj) is dict, "invalid immutable Git object")
        return obj

    def _commit(self, head):
        obj = self._get("commits/" + storage.sha(head))
        require(obj.get("sha") == head and type(obj.get("tree")) is dict,
                "commit identity mismatch")
        return obj, storage.sha(obj["tree"].get("sha"))

    def _tree(self, tree_sha):
        obj = self._get("trees/" + tree_sha + "?recursive=1")
        require(obj.get("sha") == tree_sha and obj.get("truncated") is False,
                "incomplete or wrong Git tree")
        rows = obj.get("tree")
        require(type(rows) is list and len(rows) <= MAX_TREE_ENTRIES, "tree size")
        all_entries = {}
        aliases = set()
        for row in rows:
            require(type(row) is dict, "invalid tree entry")
            path = row.get("path")
            normalized = model.path(path)
            require(normalized not in aliases, "case-aliased Git tree")
            aliases.add(normalized)
            mode, kind = row.get("mode"), row.get("type")
            require(isinstance(mode, str) and mode in _MODES and _MODES[mode] == kind,
                    "unknown Git entry type")
            all_entries[path] = {"mode": mode, "sha": storage.sha(row.get("sha"))}
        for path in all_entries:
            if "/" in path:
                parent = path.rsplit("/", 1)[0]
                require(parent in all_entries and all_entries[parent]["mode"] == "040000",
                        "missing parent tree")
        return {p: v for p, v in all_entries.items() if v["mode"] != "040000"}

    def inspect(self, base, head):
        require(storage.sha(base) != storage.sha(head), "identical base/head")
        _, before_tree = self._commit(base)
        proposed, after_tree = self._commit(head)
        parents = proposed.get("parents")
        require(type(parents) is list and len(parents) == 1
                and type(parents[0]) is dict and parents[0].get("sha") == base,
                "proposal must be a single direct child of its base")
        before, after = self._tree(before_tree), self._tree(after_tree)
        # Reject case-only renames and aliases across the two snapshots.
        aliases = {}
        for path in list(before) + list(after):
            key = model.path(path)
            require(key not in aliases or aliases[key] == path, "case-only path change")
            aliases[key] = path
        result = [{"path": p, "before": before.get(p), "after": after.get(p)}
                  for p in sorted(set(before) | set(after), key=model.path)
                  if before.get(p) != after.get(p)]
        require(0 < len(result) <= MAX_CHANGES, "empty or oversized artifact")
        for change in result:
            entry(change["before"])
            entry(change["after"])
        return result
