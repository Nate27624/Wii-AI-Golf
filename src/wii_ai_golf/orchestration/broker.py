"""Work Queue metadata admission, not a deployed service or artifact gateway.

The host owns the credential registry, clock, GitHub store and review callback.
Workers never receive those capabilities. All operations are explicit; no
background execution, source publication or operator approval is implied.
"""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import hmac
import re
import threading
import time
from dataclasses import dataclass

from . import state as model
from . import github_store as storage
from . import artifact_gateway as gateway


class AdmissionError(ValueError):
    pass


class CursorError(AdmissionError):
    pass


def require(ok, message):
    if not ok:
        raise AdmissionError(message)


def digest(value):
    return hashlib.sha256(storage.canonical(value)).hexdigest()


def token_digest(token):
    require(isinstance(token, str) and 32 <= len(token) <= 512 and
            token.isascii() and all(33 <= ord(c) <= 126 for c in token),
            "authentication failed")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Principal:
    identity: str
    roles: frozenset
    manager: bool = False
    maintenance: bool = False
    read_only: bool = False


class Credentials:
    """Host-created registry of hashes of high-entropy, per-worker credentials.

    The host must not reuse identities for unrelated workers, nor expose the
    registry, tokens or its GitHub credential. Hashes are not password KDFs.
    """
    def __init__(self, rows):
        self._rows = []
        identities = set()
        hashes = set()
        for hashed, principal in rows:
            require(isinstance(hashed, str) and len(hashed) == 64 and
                    all(c in "0123456789abcdef" for c in hashed), "credential hash")
            require(isinstance(principal, Principal), "principal")
            model.ident(principal.identity)
            require(type(principal.roles) is frozenset and
                    principal.roles <= model.ROLES and
                    type(principal.manager) is bool and type(principal.maintenance) is bool
                    and type(principal.read_only) is bool
                    and (not principal.manager or "S000" in principal.roles)
                    and (not principal.read_only or (not principal.roles and
                         not principal.manager and not principal.maintenance)),
                    "invalid principal roles")
            require(principal.identity not in identities and hashed not in hashes,
                    "duplicate credential or principal")
            identities.add(principal.identity)
            hashes.add(hashed)
            self._rows.append((hashed, principal))

    def authenticate(self, token):
        hashed = token_digest(token)
        found = None
        for candidate, principal in self._rows:
            if hmac.compare_digest(candidate, hashed):
                found = principal
        require(found is not None, "authentication failed")
        return found


def run_prefix(principal):
    return "run-" + digest(["principal", principal.identity])[:32] + "-"


def run_for(principal, request_id):
    return run_prefix(principal) + digest(["acquire", request_id])


def operation_for(principal, request_id, action, payload):
    # Full payload digest, with a separate durable key prefix for detecting
    # conflicting request-ID reuse. IDs fit the model's 128-character bound.
    prefix = "op-" + digest([principal.identity, request_id])[:32] + "-"
    return prefix, prefix + digest([action, payload])


def fields(payload, required, optional=()):
    require(type(payload) is dict and set(required) <= set(payload)
            and set(payload) <= set(required) | set(optional), "invalid request fields")


class Broker:
    """Host-side, synchronous metadata broker with a private store capability.

    Explicit hot mode supports only disposable metadata transitions; artifact,
    publication and the legacy read wire remain disabled in that mode.
    A request does at most one store publication. Conflicts require the
    caller to reread/retry; uncertain writes require receipt reconciliation.
    The host must serialize this broker with any future external effects.
    """
    def __init__(self, store, credentials, *, clock=None, reviewer=None, inspector=None,
                 publication_observer=None, hot=False, history_cursor_key=None):
        require(type(hot) is bool, "invalid store mode")
        require(history_cursor_key is None or (type(history_cursor_key) is bytes
                and 32 <= len(history_cursor_key) <= 128), "invalid cursor key")
        self._history_cursor_key = history_cursor_key
        self._hot = hot
        self._store = store
        self._credentials = credentials
        self._clock = clock if clock is not None else lambda: int(time.time())
        self._reviewer = reviewer
        self._inspector = inspector
        self._publication_observer = publication_observer
        self._lock = threading.RLock()

    def _read(self):
        return self._store.read_hot() if self._hot else self._store.read()

    def _lookup(self, snapshot, kind, key):
        return self._store.hot_lookup_at(snapshot, kind, key)

    def _now(self, snapshot):
        now = model.integer(self._clock(), "trusted broker clock")
        require(now >= snapshot.state["clock"], "broker clock rollback")
        return now

    def _roles(self, principal):
        return sorted(principal.roles)

    def _candidates(self, current, principal, now):
        if principal.read_only:
            return []
        return [k for k in model.dispatch_candidates(current, self._roles(principal), now)
                if k != model.MANAGER or principal.manager]

    def status(self, token):
        principal = self._credentials.authenticate(token)
        # A read pins an immutable commit and never grants a lease.
        # Do not serialize potentially slow GitHub reads with worker heartbeats.
        snap = self._read()
        now = self._now(snap)
        effective = model.sweep(snap.state, now)
        pending = None if self._hot else storage.pending_publication(snap.envelope)
        return {"head": snap.head, "durable_revision": snap.state["revision"],
                "effective_at": now, "state": effective,
                "eligible": [] if pending else self._candidates(effective, principal, now),
                "task_order": sorted(effective["tasks"], key=lambda k: (
                    k != model.MANAGER, effective["tasks"][k]["priority"], k)),
                "publication_pending": pending,
                "publications": {} if self._hot else copy.deepcopy(snap.envelope["publications"]),
                "manager_authorized": principal.manager,
                "accepted_artifacts": {} if self._hot else copy.deepcopy(snap.envelope["artifacts"])}

    def capacity(self, token):
        """Authenticated read-only capacity view; separate from status schema."""
        self._credentials.authenticate(token)
        require(not self._hot, "hot capacity wire unavailable")
        return storage.capacity_report(self._store.read())

    def task_history(self, token, task, *, limit=20, cursor=None):
        """Authenticated read-only view for the single LocalOps interface."""
        self._credentials.authenticate(token)
        # History pins its own tip; concurrent appends cannot change its ancestors.
        require(not self._hot, "permanent hot history unavailable")
        return self._store.task_history(task, limit=limit, cursor=cursor)

    def hot_history(self, token, project, task, *, limit=20, cursor=None):
        """Read permanent task history using an authenticated immutable pin.

        Only a trusted project-bound endpoint supplies project. A host-owned
        key is distinct from worker credentials and must persist across restarts
        if outstanding cursors are to survive them.
        """
        principal = self._credentials.authenticate(token)
        require(principal.read_only and self._hot, "hot operator history unavailable")
        require(self._history_cursor_key is not None, "history cursor key unavailable")
        require(type(project) is str and _READ_PROJECT.fullmatch(project),
                "invalid history project")
        model.ident(task)
        require(type(limit) is int and 1 <= limit <= 50, "history page limit")
        binding = {"project": project, "repository": self._store.prefix,
                   "branch": self._store.branch, "task": task}
        now = model.integer(self._clock(), "trusted broker clock")
        if cursor is None:
            snap = self._store.read_hot()
            now = self._now(snap)
            position = None
            expires = now + 3600
            model.integer(expires, "cursor expiry")
        else:
            row = decode_cursor(cursor, self._history_cursor_key)
            if (set(row) != set(binding) | {"head", "position", "expires", "count"}
                    or any(row.get(k) != v for k, v in binding.items())
                    or type(row["expires"]) is not int or not now < row["expires"]
                    or type(row["position"]) is not int or type(row["count"]) is not int
                    or not 1 <= row["position"] <= row["count"]):
                raise CursorError("invalid or expired history cursor")
            # No arbitrary user SHA traversal: signature and binding verified
            # before reading the exact snapshot originally issued by this host.
            snap = self._store._hot_at(storage.sha(row["head"]))
            self._now(snap)
            if snap.manifest["event_counts"].get(task) != row["count"]:
                raise CursorError("invalid history snapshot")
            position, expires = row["position"], row["expires"]
        page = self._store.hot_task_history(snap, task, limit=limit, position=position)
        next_position = page.pop("next_position")
        page["next_cursor"] = None if next_position is None else encode_cursor(
            {**binding, "head": snap.head, "count": page["event_count"],
             "position": next_position, "expires": expires}, self._history_cursor_key)
        return page

    def _owned(self, current, principal, payload):
        task, run_id, fence = (payload[k] for k in ("task", "run_id", "fence"))
        model.ident(task)
        model.ident(run_id)
        model.integer(fence, "fence")
        require(run_id.startswith(run_prefix(principal)), "not your execution run")
        require(task in current["tasks"], "unknown task")
        require(current["tasks"][task]["role"] in principal.roles,
                "role not authorized")
        require(task != model.MANAGER or principal.manager, "manager not authorized")
        return task, run_id, fence

    def _review(self, principal, action, payload, snapshot):
        # Structural validation is not semantic privacy or provenance review.
        # Deployment must provide a trusted, fail-closed verifier. Never let a
        # worker supply or bypass it. Review receives copies, not credentials.
        require(self._reviewer is not None, "checkpoint review unavailable")
        require(self._reviewer(principal, action, copy.deepcopy(payload),
                               snapshot.state) is True, "checkpoint review denied")

    def _response(self, snapshot, principal, request_id, action, op, replayed, now):
        row = (self._lookup(snapshot, "receipt", op) if self._hot
               else snapshot.envelope["receipts"][op])
        require(row is not None, "receipt unavailable")
        result = {"operation": op, "revision": row["revision"], "head": snapshot.head,
                  "replayed": replayed}
        if action == "acquire":
            run_id = run_for(principal, request_id)
            effective = model.sweep(snapshot.state, now)
            run = effective["runs"].get(run_id)
            if run is None and self._hot:
                run = self._lookup(snapshot, "run", run_id)
                require(run is not None and run["status"] == "CLOSED",
                        "archived acquisition missing terminal run")
            require(run is not None, "acquisition receipt missing run")
            role_allowed = effective["tasks"][run["task"]]["role"] in principal.roles
            manager_allowed = run["task"] != model.MANAGER or principal.manager
            result["lease"] = {"task": run["task"], "run_id": run_id,
                               "fence": run["fence"], "expires": run["expires"],
                               "active": run["status"] == "IN_PROGRESS" and role_allowed and manager_allowed}
        if action == "accept_artifact":
            require(op in snapshot.envelope["artifacts"], "artifact acceptance missing")
            result["artifact"] = copy.deepcopy(snapshot.envelope["artifacts"][op])
            result["source_promoted"] = False
        if action == "prepare_publication":
            result["publication"] = copy.deepcopy(snapshot.envelope["publications"][op])
            result["source_promoted"] = False
        return result

    def request(self, token, request_id, action, payload):
        """Authenticate, validate, transition and persist metadata; never source IO."""
        principal = self._credentials.authenticate(token)
        require(not principal.read_only, "read-only principal cannot mutate")
        model.ident(request_id)
        require(action in ("acquire", "renew", "finish", "manager_pass", "sweep", "accept_artifact",
                           "prepare_publication", "resolve_publication"),
                "unknown operation")
        require(not self._hot or action not in ("accept_artifact", "prepare_publication",
                                                 "resolve_publication"),
                "hot artifact/publication integration unavailable")
        require(type(payload) is dict, "invalid request")
        # Snapshot input prevents callback or caller mutation during admission.
        payload = copy.deepcopy(payload)
        prefix, op = operation_for(principal, request_id, action, payload)
        with self._lock:
            snap = self._read()
            current = snap.state
            now = self._now(snap)
            if self._hot:
                prior = self._lookup(snap, "request", prefix)
                matches = [] if prior is None else [prior["operation"]]
                if matches == [op]:
                    row = self._lookup(snap, "receipt", op)
                    require(row is not None and row["digest"] ==
                            digest([principal.identity, request_id, action, payload]),
                            "hot request receipt mismatch")
            else:
                matches = [key for key in snap.envelope["receipts"] if key.startswith(prefix)]
            if matches:
                require(matches == [op], "request ID reused with different payload")
                # A receipt is historical, not a fresh grant. Authentication
                # still applies; replay does not renew an expired lease.
                return self._response(snap, principal, request_id, action, op, True, now)
            pending = None if self._hot else storage.pending_publication(snap.envelope)
            require(pending is None or action == "resolve_publication",
                    "unresolved publication; queue frozen")
            artifact = None
            publication = None
            changes = None
            if action == "prepare_publication":
                fields(payload, ("task", "run_id", "fence", "artifact", "target"))
                task, run_id, fence = self._owned(current, principal, payload)
                model.active(model.sweep(current, now), task, run_id, fence)
                key = payload["artifact"]
                require(isinstance(key, str) and key in snap.envelope["artifacts"],
                        "accepted artifact required")
                record = snap.envelope["artifacts"][key]
                require((record["task"], record["run_id"], record["fence"]) ==
                        (task, run_id, fence), "artifact belongs to another lease")
                require(isinstance(payload["target"], str) and
                        storage._PUBLICATION_REF.fullmatch(payload["target"]),
                        "disposable publication target required")
                self._review(principal, action,
                             {**payload, "record": copy.deepcopy(record)}, snap)
                after = self._now(snap)
                require(after >= now, "broker clock rollback during publication review")
                now = after
                proposed = model.sweep(current, now)
                model.active(proposed, task, run_id, fence)
                publication = {"artifact": key, "target": payload["target"]}
            elif action == "resolve_publication":
                fields(payload, ("intent",))
                require(principal.maintenance and pending is not None and
                        payload["intent"] == pending, "publication reconciliation not authorized")
                require(self._publication_observer is not None, "settled observation unavailable")
                row = snap.envelope["publications"][pending]
                record = snap.envelope["artifacts"][row["artifact"]]
                # The trusted host, not the worker, must establish that no
                # request remains in flight and observe the exact target ref.
                observed = self._publication_observer(copy.deepcopy(row),
                                                       copy.deepcopy(record))
                require(isinstance(observed, str) and
                        observed in (record["base"], record["head"]),
                        "ambiguous publication outcome")
                after = self._now(snap)
                require(after >= now, "broker clock rollback during reconciliation")
                now = after
                proposed = model.sweep(current, now)
                publication = {"intent": pending, "observed_head": observed}
            elif action == "acquire":
                fields(payload, ())
                effective = model.sweep(current, now)
                require(not any(rid.startswith(run_prefix(principal)) and
                                run["status"] == "IN_PROGRESS"
                                for rid, run in effective["runs"].items()),
                        "worker already holds a lease")
                candidates = self._candidates(effective, principal, now)
                if not candidates:
                    return {"idle": True, "head": snap.head,
                            "durable_revision": current["revision"]}
                task = candidates[0]
                proposed, _ = model.acquire(current, task, run_for(principal, request_id),
                                             current["tasks"][task]["role"], now,
                                             cold_run_exists=(lambda key:
                                                 self._lookup(snap, "run", key) is not None)
                                             if self._hot else None)
            elif action == "sweep":
                fields(payload, ())
                require(principal.maintenance, "maintenance not authorized")
                proposed = model.sweep(current, now)
            else:
                if action == "renew":
                    fields(payload, ("task", "run_id", "fence"), ("progress",))
                elif action == "finish":
                    fields(payload, ("task", "run_id", "fence", "outcome", "progress"))
                elif action == "accept_artifact":
                    fields(payload, ("task", "run_id", "fence", "base", "head", "progress"))
                else:
                    fields(payload, ("task", "run_id", "fence", "observed_revision",
                                     "progress"), ("priorities", "additions", "retire"))
                task, run_id, fence = self._owned(current, principal, payload)
                model.active(model.sweep(current, now), task, run_id, fence)
                if action == "manager_pass":
                    require(principal.manager and task == model.MANAGER,
                            "manager not authorized")
                review_payload = payload
                if action == "accept_artifact":
                    require(task != model.MANAGER and self._inspector is not None,
                            "artifact inspection unavailable or unauthorized")
                    storage.sha(payload["base"])
                    storage.sha(payload["head"])
                    model.checkpoint(payload["progress"])
                    require(payload["progress"]["head"] == payload["head"],
                            "checkpoint must pin proposed artifact")
                    # The host, never the worker, provides the complete manifest.
                    changes = copy.deepcopy(self._inspector.inspect(payload["base"], payload["head"]))
                    gateway.validate_manifest(changes, current["tasks"][task]["paths"])
                    after_inspection = self._now(snap)
                    require(after_inspection >= now, "broker clock rollback during inspection")
                    now = after_inspection
                    model.active(model.sweep(current, now), task, run_id, fence)
                    review_payload = {**payload, "changes": changes,
                                      "manifest_digest": gateway.manifest_digest(
                                          payload["base"], payload["head"], changes),
                                      "goal_sha": current["oversight"]["goal_sha"]}
                if "progress" in payload:
                    model.checkpoint(payload["progress"])
                    self._review(principal, action, review_payload, snap)
                    # Recheck trusted time after potentially slow review.
                    after_review = self._now(snap)
                    require(after_review >= now, "broker clock rollback during review")
                    now = after_review
                if action in ("renew", "accept_artifact"):
                    proposed = model.renew(current, task, run_id, fence, now,
                                           payload.get("progress"))
                elif action == "finish":
                    proposed = model.finish(current, task, run_id, fence, now,
                                            payload["outcome"], payload["progress"])
                else:
                    proposed = model.manager_pass(
                        current, run_id, fence, now, payload["observed_revision"],
                        payload["progress"], priorities=payload.get("priorities"),
                        additions=payload.get("additions"), retire=payload.get("retire"))
            # A same-second heartbeat/sweep may be a model no-op. Persist one
            # operation receipt anyway so retries remain unambiguous.
            if proposed == current:
                proposed["revision"] += 1
            model.validate(proposed)
            if action == "accept_artifact":
                artifact = gateway.make_record(proposed, task, run_id, fence, now,
                                               payload["base"], payload["head"], changes)
            if self._hot:
                # The authorized proposal is pinned to snap; publish_hot checks
                # equality of that root and uses a non-forced ref CAS.
                receipt = self._store.publish_hot(
                    snap, op, digest([principal.identity, request_id, action, payload]),
                    lambda state, cold_exists: proposed)
            else:
                receipt = self._store.publish(snap, proposed, op, artifact=artifact,
                                              publication=publication)
            try:
                observed = self._read()
                row = (self._lookup(observed, "receipt", op) if self._hot
                       else observed.envelope["receipts"].get(op))
                require(row is not None and row.get("digest") == receipt.digest,
                        "published receipt missing; reconcile before retry")
                return self._response(observed, principal, request_id, action, op,
                                      receipt.replayed, self._now(observed))
            except (storage.StoreError, model.LeaseError, AdmissionError):
                raise storage.UncertainWrite("published response unavailable; reconcile receipt") from None


# Staged LocalOps read wire v1. Storage versions are not wire versions.
# This adapter is a synchronous request/response seam, NOT an HTTP listener.
_READ_PROJECT = re.compile(r"[a-z][a-z0-9_-]{0,49}")
_READ_TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_READ_INTEGER = re.compile(r"0|[1-9][0-9]{0,15}")
_READ_LIMIT = 8 * 1024 * 1024


_CURSOR = re.compile(r"[A-Za-z0-9_-]{1,1536}\.[0-9a-f]{64}")


def encode_cursor(row, key):
    raw = storage.canonical(row)
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(key, b"v3-task-history-2\x00" + encoded.encode("ascii"),
                         hashlib.sha256).hexdigest()
    cursor = encoded + "." + signature
    require(_CURSOR.fullmatch(cursor), "history cursor too large")
    return cursor


def decode_cursor(cursor, key):
    if type(cursor) is not str or not _CURSOR.fullmatch(cursor):
        raise CursorError("invalid history cursor")
    encoded, signature = cursor.split(".")
    expected = hmac.new(key, b"v3-task-history-2\x00" + encoded.encode("ascii"),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise CursorError("invalid history cursor")
    try:
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4),
                               altchars=b"-_", validate=True)
        row = storage.decode(raw)
        if (type(row) is not dict or storage.canonical(row) != raw
                or encode_cursor(row, key) != cursor):
            raise CursorError("invalid history cursor")
        return row
    except (ValueError, binascii.Error, storage.StoreError):
        raise CursorError("invalid history cursor") from None


def _read_subset(row, keys):
    return {key: row[key] for key in keys}


def _operator_status(view, *, hot=False):
    """Explicit allowlist matching the corresponding LocalOps wire."""
    state = view["state"]
    require(state["version"] == (3 if hot else 2), "unsupported read wire source version")
    require(view["manager_authorized"] is False and view["eligible"] == [],
            "operator-only projection required")
    tasks = {}
    runs = {}
    for key, task in state["tasks"].items():
        row = _read_subset(task, ("role", "status", "priority", "thread",
                                  "dependencies", "run", "fence"))
        row["checkpoint"] = _read_subset(task["checkpoint"], ("head", "evidence"))
        tasks[key] = row
        if task["run"] is not None:
            run = state["runs"][task["run"]]
            runs[task["run"]] = _read_subset(
                run, ("task", "status", "fence", "heartbeat", "expires"))
    result = _read_subset(view, ("head", "durable_revision", "effective_at",
                                "eligible", "task_order", "publication_pending",
                                "manager_authorized"))
    result["state"] = {**_read_subset(state, ("version", "revision", "clock", "oversight")),
                       "tasks": tasks, "runs": runs}
    pending = view["publication_pending"]
    result["publications"] = {} if pending is None else {
        pending: {"resolution": view["publications"][pending]["resolution"]}}
    if hot:
        result["wire_version"] = 2
        result["publication_supported"] = False
        # No false healthy empty publication status on an incomplete backend.
        del result["publications"]
        del result["publication_pending"]
    return result


def _operator_history(page, *, hot=False):
    """Preserve the committed event identity, omit unrelated record contents."""
    rows = []
    for event in page["events"]:
        keys = ("task", "kind", "revision", "operation", "clock")
        row = _read_subset(event, keys + (("sequence", "source_commit") if hot else ("commit",)))
        data = event["data"]
        kind = row["kind"]
        if kind == "created":
            safe = _read_subset(data, ("status",))
        elif kind == "task_changed":
            safe = {key: _read_subset(data[key], ("status",))
                    for key in ("before", "after")}
        elif kind in ("claimed", "renewed", "expired", "released"):
            safe = {"run_id": data["run_id"], "run": _read_subset(
                data["run"], ("task", "fence", "status", "outcome", "expires"))}
        elif kind == "artifact_accepted":
            safe = _read_subset(data, ("task", "head"))
        elif kind == "publication_intent":
            safe = {"resolution": None}
            require(data["resolution"] is None, "unexpected publication resolution")
        elif kind == "publication_resolved":
            safe = {"resolution": _read_subset(data["resolution"], ("observed_head",))}
        elif kind == "oversight_changed":
            safe = _read_subset(data, ("epoch",))
        else:
            raise AdmissionError("unsupported read history event")
        row["data"] = safe
        rows.append(row)
    result = {**_read_subset(page, ("task", "head", "next_cursor")), "events": rows}
    if hot:
        result["wire_version"] = 2
        result["event_count"] = page["event_count"]
    return result


class OperatorReadEndpoint:
    """One configured project and its own trusted broker/credential registry.

    Host must bind the broker to that project's repository/ref, provision a
    distinct read-only credential registry per project, terminate verified TLS,
    enforce header/body limits and reject duplicate Authorization headers.
    No URL supplied by the caller selects a repository, store or credentials.
    This adapter cannot deploy a server or grant mutation authority.
    """

    def __init__(self, project, broker):
        require(type(project) is str and _READ_PROJECT.fullmatch(project),
                "invalid read endpoint project")
        require(isinstance(broker, Broker), "trusted broker required")
        self._project = project
        self._prefix = "/v3/projects/" + project
        self._broker = broker

    @staticmethod
    def _reply(status, payload):
        raw = storage.canonical(payload)
        if len(raw) > _READ_LIMIT:
            status, raw = 503, b'{"error":"response unavailable"}'
        return status, {"Content-Type": "application/json",
                        "Cache-Control": "no-store",
                        "Content-Length": str(len(raw))}, raw

    def handle(self, method, target, authorization):
        """Return (status, headers, JSON bytes); no request body or mutation route.

        The staging cursor counts revisions; persistent pinned task-event
        cursors require a coordinated replacement wire contract.
        """
        error = lambda status, message: self._reply(status, {"error": message})
        if method != "GET":
            return error(405, "method not allowed")
        if (type(authorization) is not str or len(authorization) > 519
                or not authorization.startswith("Bearer ")):
            return error(401, "authentication required")
        token = authorization[7:]
        try:
            principal = self._broker._credentials.authenticate(token)
        except AdmissionError:
            return error(401, "authentication required")
        if not principal.read_only:
            return error(403, "read-only principal required")
        if (type(target) is not str or len(target) > 2048
                or not target.isascii() or any(ord(c) <= 32 or ord(c) >= 127 for c in target)):
            return error(400, "invalid request")
        if not target.startswith(self._prefix + "/"):
            return error(404, "not found")
        route = target[len(self._prefix):]
        try:
            if route.startswith("/read-v2/"):
                return self._hot_route(route[len("/read-v2"):], token)
            if len(target) > 512:
                return error(400, "invalid request")
            if route == "/status":
                return self._reply(200, _operator_status(self._broker.status(token)))
            if route == "/capacity":
                return self._reply(200, self._broker.capacity(token))
            path, mark, query = route.partition("?")
            parts = path.split("/")
            if (len(parts) != 4 or parts[:2] != ["", "tasks"]
                    or parts[3] != "history" or not _READ_TASK.fullmatch(parts[2])):
                return error(404, "not found")
            values = {}
            if mark:
                for item in query.split("&"):
                    key, equal, value = item.partition("=")
                    if (not equal or key not in {"limit", "cursor"} or key in values
                            or not _READ_INTEGER.fullmatch(value)):
                        return error(400, "invalid query")
                    values[key] = int(value)
            limit, cursor = values.get("limit", 20), values.get("cursor")
            if not 1 <= limit <= 50 or (cursor is not None and cursor > 2**53 - 1):
                return error(400, "invalid query")
            page = self._broker.task_history(token, parts[2], limit=limit, cursor=cursor)
            return self._reply(200, _operator_history(page))
        except CursorError:
            return error(409, "refresh history")
        except storage.StoreError as exc:
            # No store diagnostics, paths, raw body or credential in the response.
            if str(exc) == "unknown task":
                return error(404, "not found")
            if str(exc) == "history cursor outside window":
                return error(409, "refresh history")
            return error(503, "response unavailable")
        except Exception:
            return error(503, "response unavailable")

    def _hot_route(self, route, token):
        error = lambda status, message: self._reply(status, {"error": message})
        if not self._broker._hot:
            return error(503, "response unavailable")
        if route == "/status":
            return self._reply(200, _operator_status(self._broker.status(token), hot=True))
        if route == "/capacity":
            return error(503, "capacity unavailable")
        path, mark, query = route.partition("?")
        parts = path.split("/")
        if (len(parts) != 4 or parts[:2] != ["", "tasks"]
                or parts[3] != "history" or not _READ_TASK.fullmatch(parts[2])):
            return error(404, "not found")
        values = {}
        if mark:
            for item in query.split("&"):
                name, equal, value = item.partition("=")
                if (not equal or name not in {"limit", "cursor"} or name in values
                        or (name == "limit" and not _READ_INTEGER.fullmatch(value))
                        or (name == "cursor" and not _CURSOR.fullmatch(value))):
                    return error(400, "invalid query")
                values[name] = value
        limit = int(values.get("limit", "20"))
        if not 1 <= limit <= 50:
            return error(400, "invalid query")
        page = self._broker.hot_history(token, self._project, parts[2],
                                        limit=limit, cursor=values.get("cursor"))
        return self._reply(200, _operator_history(page, hot=True))
