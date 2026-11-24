"""Pure offline V3 lease transitions. No GitHub, clock, IO or credentials.

The trusted broker supplies integer UTC seconds and serializes each transition.
A returned state is a proposal, not an authoritative lease until committed.
"""
from __future__ import annotations

import copy
import re

LEASE_SECONDS = 120
MANAGER = "S000-MANAGER"
MANAGER_RESOURCE = "work-queue-metadata"
REVIEW_SECONDS = 300
ROLES = {"S000", "S001", "S002", "S003", "S004", "S005"}
STATES = {"OPEN", "IN_PROGRESS", "BLOCKED", "PARKED", "CLOSED"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
_SHA = re.compile(r"[0-9a-f]{40}")
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
             *(f"lpt{i}" for i in range(1, 10))}


class LeaseError(ValueError):
    """Invalid state or unauthorized transition; input is never mutated."""


def require(condition, message):
    if not condition:
        raise LeaseError(message)


def integer(value, name):
    require(type(value) is int and 0 <= value <= 2**53-1, name)
    return value


def ident(value):
    require(isinstance(value, str) and _ID.fullmatch(value), "invalid identifier")
    return value


def fields(value, expected):
    require(type(value) is dict and set(value) == set(expected), "invalid fields")


def path(value):
    require(isinstance(value, str) and len(value) <= 512 and _PATH.fullmatch(value),
            "invalid repository-relative path")
    for part in value.split("/"):
        require(part not in {".", ".."} and not part.endswith(".")
                and part.lower().split(".")[0] not in _RESERVED
                and part.lower() != ".git", "ambiguous path")
    return value.lower()


def overlap(a, b):
    a, b = path(a), path(b)
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def unique_list(values, validator):
    require(type(values) is list, "expected list")
    normalized = [validator(v) for v in values]
    require(len(set(normalized)) == len(normalized), "duplicate value")
    return normalized


def text(value, limit=400):
    # Structural bounds only. Broker must review public-data privacy.
    require(isinstance(value, str) and 0 < len(value) <= limit
            and all(ord(c) >= 32 and ord(c) != 127 for c in value), "invalid text")


def checkpoint(value):
    fields(value, ("head", "next", "summary", "evidence"))
    require(value["head"] is None or
            isinstance(value["head"], str) and _SHA.fullmatch(value["head"]),
            "invalid checkpoint head")
    text(value["next"])
    text(value["summary"], 1000)
    # References are identifiers, not arbitrary paths, URLs, or private logs.
    unique_list(value["evidence"], ident)
    require(len(value["evidence"]) <= 64, "too many evidence references")


def resources_conflict(a, b):
    return (bool({r.lower() for r in a["resources"]} & {r.lower() for r in b["resources"]}) or
            any(overlap(p, q) for p in a["paths"] for q in b["paths"]))


def scope(value):
    unique_list(value["paths"], path)
    unique_list(value["resources"], lambda v: ident(v).lower())
    require(value["paths"] or value["resources"], "empty scope")


def new_task(role, priority, paths, resources, dependencies, thread, objective,
             acceptance, initial_checkpoint):
    return {"role": role, "priority": priority, "paths": list(paths),
            "resources": list(resources), "dependencies": list(dependencies),
            "thread": thread, "objective": objective, "acceptance": acceptance,
            "status": "OPEN", "fence": 0, "run": None,
            "checkpoint": copy.deepcopy(initial_checkpoint)}


def validate(state):
    require(type(state) is dict and type(state.get("version")) is int
            and state["version"] in (2, 3), "version")
    hot = state["version"] == 3
    base_fields = ("version", "revision", "clock", "tasks", "runs", "holds", "oversight")
    fields(state, base_fields + (("archived_fences",) if hot else ()))
    integer(state["revision"], "revision")
    integer(state["clock"], "clock")
    tasks, runs, holds = state["tasks"], state["runs"], state["holds"]
    require(all(type(x) is dict for x in (tasks, runs, holds)), "invalid maps")
    floors = state["archived_fences"] if hot else {key: 0 for key in tasks}
    require(type(floors) is dict and set(floors) == set(tasks), "archive fence coverage")
    for floor in floors.values():
        integer(floor, "archived fence floor")
    o = state["oversight"]
    fields(o, ("goal_sha", "epoch", "reviewed_epoch", "reviewed_at"))
    require(isinstance(o["goal_sha"], str) and _SHA.fullmatch(o["goal_sha"]),
            "immutable operator goal SHA required")
    integer(o["epoch"], "review epoch")
    require(o["reviewed_epoch"] is None or
            integer(o["reviewed_epoch"], "reviewed epoch") <= o["epoch"],
            "reviewed epoch")
    require((o["reviewed_at"] is None) == (o["reviewed_epoch"] is None),
            "incomplete review")
    if o["reviewed_at"] is not None:
        require(integer(o["reviewed_at"], "review time") <= state["clock"], "future review")
    require(MANAGER in tasks, "permanent manager missing")
    active = []
    for key, t in tasks.items():
        ident(key)
        fields(t, ("role", "priority", "paths", "resources", "dependencies",
                   "thread", "objective", "acceptance", "status", "fence", "run",
                   "checkpoint"))
        require(isinstance(t["role"], str) and t["role"] in ROLES, "role")
        integer(t["priority"], "priority")
        integer(t["fence"], "fence")
        scope(t)
        unique_list(t["dependencies"], ident)
        require(all(d in tasks and d != key for d in t["dependencies"]),
                "unknown or self dependency")
        integer(t["thread"], "canonical issue number")
        require(t["thread"] > 0, "canonical issue number")
        text(t["objective"])
        text(t["acceptance"])
        checkpoint(t["checkpoint"])
        if key == MANAGER:
            require(t["role"] == "S000" and t["priority"] == 0 and
                    t["paths"] == [] and t["resources"] == [MANAGER_RESOURCE] and
                    t["dependencies"] == [] and t["status"] in
                    ("OPEN", "IN_PROGRESS", "BLOCKED"), "invalid permanent manager")
        else:
            require(MANAGER not in t["dependencies"] and
                    MANAGER_RESOURCE not in {r.lower() for r in t["resources"]},
                    "reserved manager scope/dependency")
        require(isinstance(t["status"], str) and t["status"] in STATES, "status")
        if t["status"] == "IN_PROGRESS":
            ident(t["run"])
            require(t["run"] in runs, "missing active run")
            active.append((key, t))
        else:
            require(t["run"] is None, "inactive task has run")
    # Iterative topological check, avoiding recursion on malformed input.
    remaining = set(tasks)
    while remaining:
        ready = {k for k in remaining if not (set(tasks[k]["dependencies"]) & remaining)}
        require(ready, "dependency cycle")
        remaining -= ready
    fences = {k: set() for k in tasks}
    for key, run in runs.items():
        ident(key)
        fields(run, ("task", "fence", "acquired", "heartbeat", "expires",
                     "status", "outcome", "receipt"))
        ident(run["task"])
        require(run["task"] in tasks, "unknown run task")
        t = tasks[run["task"]]
        f = integer(run["fence"], "run fence")
        require(floors[run["task"]] < f <= t["fence"]
                and f not in fences[run["task"]], "run fence")
        fences[run["task"]].add(f)
        for name in ("acquired", "heartbeat", "expires"):
            integer(run[name], name)
        require(run["acquired"] <= run["heartbeat"] <= state["clock"]
                and run["expires"] == run["heartbeat"] + LEASE_SECONDS,
                "invalid lease times")
        if run["status"] == "IN_PROGRESS":
            require(t["status"] == "IN_PROGRESS" and t["run"] == key
                    and f == t["fence"] and run["outcome"] is None
                    and run["receipt"] is None, "invalid active lease")
        else:
            require(run["status"] == "CLOSED" and t["run"] != key, "invalid closed run")
            require(isinstance(run["outcome"], str) and
                    run["outcome"] in {"EXPIRED", "OPEN", "BLOCKED", "PARKED", "CLOSED"},
                    "invalid outcome")
            if run["task"] == MANAGER:
                require(run["outcome"] in ("EXPIRED", "OPEN", "BLOCKED"),
                        "invalid manager outcome")
            if run["outcome"] == "EXPIRED":
                require(run["receipt"] is None and run["expires"] <= state["clock"],
                        "invalid expiration")
            else:
                checkpoint(run["receipt"])
    for k, t in tasks.items():
        require(floors[k] <= t["fence"]
                and len(fences[k]) == t["fence"] - floors[k], "missing run history")
        if t["status"] == "IN_PROGRESS":
            require(runs[t["run"]]["status"] == "IN_PROGRESS", "closed active run")
            require(all(tasks[d]["status"] == "CLOSED" for d in t["dependencies"]),
                    "active dependency")
    for key, hold in holds.items():
        ident(key)
        fields(hold, ("paths", "resources"))
        scope(hold)
        require(MANAGER_RESOURCE not in {r.lower() for r in hold["resources"]},
                "legacy hold cannot reserve manager metadata")
    for i, (_, t) in enumerate(active):
        require(not any(resources_conflict(t, h) for h in holds.values()), "legacy hold")
        require(not any(resources_conflict(t, u) for _, u in active[:i]), "active overlap")
    return state


def hot_projection(state):
    """Separate model-v3 projection of a fully validated model-v2 state.

    The returned cold records MUST be durably archived atomically with the
    hot state before use. A bare floor is not evidence of archive integrity.
    This function performs no persistence or authorization.
    """
    validate(state)
    require(state["version"] == 2, "full history required for initial projection")
    projected = copy.deepcopy(state)
    projected["version"] = 3
    projected["archived_fences"] = {key: 0 for key in projected["tasks"]}
    return compact_hot(projected)


def compact_hot(state):
    """Return hot state and exact newly closed-run delta, without a new revision.

    Only a contiguous terminal prefix of each task's run history can move.
    The active run and monotonic task fence are never removed. The storage
    layer must bind the delta, prior archive root and new floors atomically.
    """
    validate(state)
    require(state["version"] == 3, "hot model required")
    hot = copy.deepcopy(state)
    delta = {}
    for key, run in sorted(hot["runs"].items(), key=lambda item:
                           (item[1]["task"], item[1]["fence"])):
        if run["status"] != "CLOSED":
            continue
        task = run["task"]
        require(run["fence"] == hot["archived_fences"][task] + 1,
                "noncontiguous archive delta")
        delta[key] = copy.deepcopy(run)
        hot["archived_fences"][task] = run["fence"]
        del hot["runs"][key]
    return validate(hot), delta


def restore_hot(state, cold_runs):
    """Offline equivalence oracle; verify complete historical fences/records.

    The caller must separately authenticate the cold records against their
    immutable root. This is not a scalable operational read path.
    """
    validate(state)
    require(state["version"] == 3 and type(cold_runs) is dict, "hot restore input")
    full = copy.deepcopy(state)
    floors = full.pop("archived_fences")
    full["version"] = 2
    require(not set(full["runs"]) & set(cold_runs), "duplicate cold run")
    for run in cold_runs.values():
        require(type(run) is dict and run.get("task") in floors
                and run.get("status") == "CLOSED", "invalid cold run")
        require(integer(run.get("fence"), "cold fence") <= floors[run["task"]],
                "cold fence above archive floor")
    full["runs"].update(copy.deepcopy(cold_runs))
    return validate(full)


def initial(tasks, holds=None, now=0, *, goal_sha):
    """Bootstrap requires an explicit permanent manager and operator goal pin."""
    state = {"version": 2, "revision": 0, "clock": now,
             "tasks": copy.deepcopy(tasks), "runs": {},
             "holds": copy.deepcopy({} if holds is None else holds),
             "oversight": {"goal_sha": goal_sha, "epoch": 0,
                           "reviewed_epoch": None, "reviewed_at": None}}
    return validate(state)


def prepare(state, now):
    validate(state)
    integer(now, "broker clock")
    require(now >= state["clock"], "clock rollback")
    s = copy.deepcopy(state)
    s["clock"] = now
    for t in s["tasks"].values():
        if t["run"] is not None:
            run = s["runs"][t["run"]]
            if now >= run["expires"]:
                run["status"] = "CLOSED"
                run["outcome"] = "EXPIRED"
                t["run"] = None
                t["status"] = "OPEN"
                s["oversight"]["epoch"] += 1
    return s


def commit(before, after):
    if before != after:
        after["revision"] = before["revision"] + 1
    return validate(after)


def sweep(state, now):
    """Reconcile expired runs, including at the exact 120s boundary."""
    return commit(state, prepare(state, now))


def eligible(s, key, role):
    t = s["tasks"][key]
    return (t["role"] == role and t["status"] == "OPEN"
            and all(s["tasks"][d]["status"] == "CLOSED" for d in t["dependencies"])
            and not any(resources_conflict(t, h) for h in s["holds"].values())
            and not any(u["status"] == "IN_PROGRESS" and resources_conflict(t, u)
                        for u in s["tasks"].values()))


def manager_due(s):
    o = s["oversight"]
    return (o["reviewed_epoch"] != o["epoch"] or o["reviewed_at"] is None
            or s["clock"] - o["reviewed_at"] >= REVIEW_SECONDS)


def dispatch_candidates(state, roles, now):
    """All eligible roles, manager first when due; no loop on unchanged review."""
    roles = unique_list(roles, ident)
    require(all(r in ROLES for r in roles), "role")
    s = prepare(state, now)
    keys = [k for k, t in s["tasks"].items() if t["role"] in roles
            and eligible(s, k, t["role"]) and (k != MANAGER or manager_due(s))]
    return sorted(keys, key=lambda k: (k != MANAGER, s["tasks"][k]["priority"], k))


def candidates(state, role, now):
    require(isinstance(role, str) and role in ROLES, "role")
    return dispatch_candidates(state, [role], now)


def acquire(state, task, run_id, role, now, *, cold_run_exists=None):
    ident(task)
    ident(run_id)
    require(isinstance(role, str) and role in ROLES, "role")
    s = prepare(state, now)
    require(task in s["tasks"], "unknown task")
    t = s["tasks"][task]
    if run_id in s["runs"]:
        old = s["runs"][run_id]
        require(old["task"] == task and t["role"] == role
                and t["run"] == run_id and old["status"] == "IN_PROGRESS",
                "run ID already consumed")
        return commit(state, s), old["fence"]
    if s["version"] == 3:
        # The caller must consult the exact, trusted archive index. A
        # missing or ambiguous lookup is never proof of nonmembership.
        require(callable(cold_run_exists), "cold run lookup required")
        require(cold_run_exists(run_id) is False, "archived run ID or uncertain lookup")
    require(eligible(s, task, role), "task unavailable")
    if task == MANAGER:
        require(manager_due(s), "manager review not due")
    t["fence"] += 1
    t["run"] = run_id
    t["status"] = "IN_PROGRESS"
    s["runs"][run_id] = {"task": task, "fence": t["fence"], "acquired": now,
                         "heartbeat": now, "expires": now + LEASE_SECONDS,
                         "status": "IN_PROGRESS", "outcome": None, "receipt": None}
    return commit(state, s), t["fence"]


def active(s, task, run_id, fence):
    ident(task)
    ident(run_id)
    integer(fence, "fence")
    require(task in s["tasks"] and run_id in s["runs"], "unknown lease")
    t, run = s["tasks"][task], s["runs"][run_id]
    require(t["run"] == run_id and t["fence"] == fence
            and run["task"] == task and run["fence"] == fence
            and run["status"] == "IN_PROGRESS", "stale lease")
    return t, run


def renew(state, task, run_id, fence, now, progress=None):
    """Heartbeat alone is enough; optional checkpoint is durable in same transition."""
    s = prepare(state, now)
    t, run = active(s, task, run_id, fence)
    if progress is not None:
        checkpoint(progress)
        t["checkpoint"] = copy.deepcopy(progress)
    run["heartbeat"] = now
    run["expires"] = now + LEASE_SECONDS
    return commit(state, s)


def finish(state, task, run_id, fence, now, outcome, progress):
    require(task != MANAGER or outcome == "BLOCKED",
            "manager must finish via manager_pass or explicitly block")
    """Atomic terminal receipt and release. Exact terminal retries are no-ops."""
    require(isinstance(outcome, str) and outcome in {"OPEN", "BLOCKED", "PARKED", "CLOSED"},
            "invalid finish outcome")
    checkpoint(progress)
    ident(task)
    ident(run_id)
    integer(fence, "fence")
    validate(state)
    integer(now, "broker clock")
    require(now >= state["clock"], "clock rollback")
    old = state["runs"].get(run_id)
    if old is not None and old["status"] == "CLOSED":
        require(old["task"] == task and old["fence"] == fence
                and old["outcome"] == outcome and old["receipt"] == progress,
                "conflicting or expired terminal retry")
        return copy.deepcopy(state)
    s = prepare(state, now)
    t, run = active(s, task, run_id, fence)
    t["checkpoint"] = copy.deepcopy(progress)
    t["run"] = None
    t["status"] = outcome
    run["status"] = "CLOSED"
    run["outcome"] = outcome
    run["receipt"] = copy.deepcopy(progress)
    s["oversight"]["epoch"] += 1
    return commit(state, s)


def manager_pass(state, run_id, fence, now, observed_revision, progress,
                 *, priorities=None, additions=None, retire=None):
    """Fenced atomic review + bounded queue mutations + release.

    Broker authenticates manager and supplies trusted time. The review must
    use the exact observed revision; concurrent changes require rereading.
    Goal changes and operator approval are intentionally not worker actions.
    """
    integer(observed_revision, "observed revision")
    checkpoint(progress)
    validate(state)
    integer(now, "broker clock")
    require(now >= state["clock"], "clock rollback")
    priorities = {} if priorities is None else priorities
    additions = {} if additions is None else additions
    retire = [] if retire is None else retire
    require(type(priorities) is dict and type(additions) is dict, "queue mutation maps")
    retire = unique_list(retire, ident)
    # A retry cannot silently repeat manager mutations. Broker reconciles the
    # committed review receipt after uncertain delivery; retry against latest
    # state is rejected rather than applying a second pass.
    require(observed_revision == state["revision"], "review snapshot changed")
    s = prepare(state, now)
    require(s["oversight"]["epoch"] == state["oversight"]["epoch"],
            "expired runs changed review snapshot; reconcile first")
    t, run = active(s, MANAGER, run_id, fence)
    for key, value in priorities.items():
        ident(key)
        require(key != MANAGER and key in s["tasks"] and
                s["tasks"][key]["status"] == "OPEN", "priority target not open")
        s["tasks"][key]["priority"] = integer(value, "priority")
    for key, value in additions.items():
        ident(key)
        require(key not in s["tasks"] and key != MANAGER, "task already exists")
        require(type(value) is dict and value.get("status") == "OPEN"
                and value.get("run") is None and type(value.get("fence")) is int
                and value["fence"] == 0, "new task must be open and unused")
        s["tasks"][key] = copy.deepcopy(value)
        if s["version"] == 3:
            s["archived_fences"][key] = 0
    for key in retire:
        require(key != MANAGER and key in s["tasks"] and
                s["tasks"][key]["status"] == "OPEN", "retire only open specialist task")
        # PARKED is not DONE; dependent tasks cannot be released by retirement.
        s["tasks"][key]["status"] = "PARKED"
    t["checkpoint"] = copy.deepcopy(progress)
    t["run"] = None
    t["status"] = "OPEN"
    run["status"] = "CLOSED"
    run["outcome"] = "OPEN"
    run["receipt"] = copy.deepcopy(progress)
    s["oversight"]["reviewed_epoch"] = s["oversight"]["epoch"]
    s["oversight"]["reviewed_at"] = now
    return commit(state, s)

