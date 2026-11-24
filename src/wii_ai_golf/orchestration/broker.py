"""Work Queue metadata admission, not a deployed service or artifact gateway.

The host owns the credential registry, clock, GitHub store and review callback.
Workers never receive those capabilities. All operations are explicit; no
background execution, source publication or operator approval is implied.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import threading
import time
from dataclasses import dataclass

from . import state as model
from . import github_store as storage
from . import artifact_gateway as gateway


class AdmissionError(ValueError):
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
                    and (not principal.manager or "S000" in principal.roles),
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

    A request does at most one store publication. Conflicts require the
    caller to reread/retry; uncertain writes require receipt reconciliation.
    The host must serialize this broker with any future external effects.
    """
    def __init__(self, store, credentials, *, clock=None, reviewer=None, inspector=None,
                 publication_observer=None):
        self._store = store
        self._credentials = credentials
        self._clock = clock if clock is not None else lambda: int(time.time())
        self._reviewer = reviewer
        self._inspector = inspector
        self._publication_observer = publication_observer
        self._lock = threading.RLock()

    def _now(self, snapshot):
        now = model.integer(self._clock(), "trusted broker clock")
        require(now >= snapshot.state["clock"], "broker clock rollback")
        return now

    def _roles(self, principal):
        return sorted(principal.roles)

    def _candidates(self, current, principal, now):
        return [k for k in model.dispatch_candidates(current, self._roles(principal), now)
                if k != model.MANAGER or principal.manager]

    def status(self, token):
        principal = self._credentials.authenticate(token)
        with self._lock:
            snap = self._store.read()
            now = self._now(snap)
            effective = model.sweep(snap.state, now)
            pending = storage.pending_publication(snap.envelope)
            return {"head": snap.head, "durable_revision": snap.state["revision"],
                    "effective_at": now, "state": effective,
                    "eligible": [] if pending else self._candidates(effective, principal, now),
                    "publication_pending": pending,
                    "publications": copy.deepcopy(snap.envelope["publications"]),
                    "manager_authorized": principal.manager,
                    "accepted_artifacts": copy.deepcopy(snap.envelope["artifacts"])}

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
        row = snapshot.envelope["receipts"][op]
        result = {"operation": op, "revision": row["revision"], "head": snapshot.head,
                  "replayed": replayed}
        if action == "acquire":
            run_id = run_for(principal, request_id)
            effective = model.sweep(snapshot.state, now)
            run = effective["runs"].get(run_id)
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
        model.ident(request_id)
        require(action in ("acquire", "renew", "finish", "manager_pass", "sweep", "accept_artifact",
                           "prepare_publication", "resolve_publication"),
                "unknown operation")
        require(type(payload) is dict, "invalid request")
        # Snapshot input prevents callback or caller mutation during admission.
        payload = copy.deepcopy(payload)
        prefix, op = operation_for(principal, request_id, action, payload)
        with self._lock:
            snap = self._store.read()
            current = snap.state
            now = self._now(snap)
            matches = [key for key in snap.envelope["receipts"] if key.startswith(prefix)]
            if matches:
                require(matches == [op], "request ID reused with different payload")
                # A receipt is historical, not a fresh grant. Authentication
                # still applies; replay does not renew an expired lease.
                return self._response(snap, principal, request_id, action, op, True, now)
            pending = storage.pending_publication(snap.envelope)
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
                                             current["tasks"][task]["role"], now)
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
            receipt = self._store.publish(snap, proposed, op, artifact=artifact,
                                          publication=publication)
            try:
                observed = self._store.read()
                require(observed.envelope["receipts"].get(op, {}).get("digest") == receipt.digest,
                        "published receipt missing; reconcile before retry")
                return self._response(observed, principal, request_id, action, op,
                                      receipt.replayed, self._now(observed))
            except (storage.StoreError, model.LeaseError, AdmissionError):
                raise storage.UncertainWrite("published response unavailable; reconcile receipt") from None
