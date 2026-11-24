"""GitHub-backed Work Queue persistence, isolated integration phase.

Not an authorization broker. Only explicitly named disposable test refs may
be mutated until cutover review. All timestamps and transition authorization
must come from the future broker, never from this transport.
"""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import state as model

MAX_LEDGER = 2 * 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
LEDGER = "ledger.json"
STATE_REF = "orchestration/v3-state"
_TEST_REF = re.compile(r"orchestration/v3-test-[a-z0-9][a-z0-9-]{0,63}")
_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class StoreError(RuntimeError):
    pass


class Conflict(StoreError):
    """Observed state changed; caller must reread and recompute."""


class UncertainWrite(StoreError):
    """Cannot establish whether a ref update committed; reconcile, do not replay."""


class HttpFailure(StoreError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"GitHub HTTP {status}")


def check(condition, message):
    if not condition:
        raise StoreError(message)


def sha(value):
    check(isinstance(value, str) and _SHA.fullmatch(value), "invalid Git object SHA")
    return value


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise StoreError("not canonical JSON") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    try:
        check(len(raw) <= MAX_RESPONSE, "oversized JSON")
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              StoreError("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise StoreError("invalid JSON") from exc


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubRest:
    """Small stdlib transport, fixed origin, bounded response, no redirects/retries."""
    def __init__(self, token, timeout=15):
        check(isinstance(token, str) and token and not any(c.isspace() for c in token),
              "missing or invalid broker credential")
        self._token = token
        self._timeout = timeout
        self._opener = build_opener(NoRedirect())

    def __call__(self, method, path, payload=None):
        check(method in ("GET", "POST", "PATCH") and path.startswith("/repos/")
              and not path.startswith("//"), "invalid GitHub request")
        req = Request("https://api.github.com" + path, method=method,
                      data=None if payload is None else canonical(payload),
                      headers={"Authorization": "Bearer " + self._token,
                               "Accept": "application/vnd.github+json",
                               "Content-Type": "application/json",
                               "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "wii-ai-golf-work-queue"})
        try:
            with self._opener.open(req, timeout=self._timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
        except HTTPError as exc:
            # Never surface remote response text or credentials.
            raise HttpFailure(exc.code) from None
        except (URLError, TimeoutError, OSError):
            raise StoreError("GitHub transport unavailable") from None
        return decode(raw)


@dataclass(frozen=True)
class Snapshot:
    head: str
    envelope: dict

    @property
    def state(self):
        return copy.deepcopy(self.envelope["state"])


@dataclass(frozen=True)
class Receipt:
    operation: str
    revision: int
    digest: str
    observed_head: str
    replayed: bool


def validate_envelope(value):
    check(type(value) is dict and set(value) == {"schema", "state", "receipts"},
          "invalid ledger envelope")
    check(type(value["schema"]) is int and value["schema"] == 1, "ledger schema")
    model.validate(value["state"])
    receipts = value["receipts"]
    check(type(receipts) is dict, "receipt map")
    revisions = set()
    for key, row in receipts.items():
        model.ident(key)
        check(type(row) is dict and set(row) == {"digest", "revision"}, "receipt")
        check(isinstance(row["digest"], str) and _DIGEST.fullmatch(row["digest"]),
              "receipt digest")
        rev = model.integer(row["revision"], "receipt revision")
        check(rev not in revisions and rev <= value["state"]["revision"],
              "receipt history")
        revisions.add(rev)
    check(len(revisions) == value["state"]["revision"] + 1, "missing receipt history")
    check(len(canonical(value)) <= MAX_LEDGER, "ledger capacity; stop for reviewed compaction")
    return value


def fingerprint(base, next_state):
    return hashlib.sha256(canonical({"parent": sha(base), "state": next_state})).hexdigest()


class GitHubStore:
    """Read a pinned ref and propose a single-parent, non-forced transition.

    Production state is read-only at this phase. The callable transport can
    be GitHubRest or a fixture. A caller holding direct write credentials
    can bypass the model; this class must not be distributed to workers
    with broker credentials.
    """
    def __init__(self, transport, repository, branch):
        check(isinstance(repository, str) and _REPO.fullmatch(repository)
              and all(p not in (".", "..") for p in repository.split("/")), "repository")
        check(isinstance(branch, str) and
              (branch == STATE_REF or _TEST_REF.fullmatch(branch)), "state ref")
        self.call = transport
        self.prefix = "/repos/" + repository + "/git/"
        self.branch = branch

    def _api(self, method, endpoint, payload=None):
        result = self.call(method, self.prefix + endpoint, payload)
        check(type(result) is dict, "invalid GitHub object response")
        return result

    def _ref(self):
        obj = self._api("GET", "ref/heads/" + quote(self.branch, safe="/"))
        check(obj.get("ref") == "refs/heads/" + self.branch, "unexpected ref")
        target = obj.get("object")
        check(type(target) is dict and target.get("type") == "commit", "ref target")
        return sha(target.get("sha"))

    def _at(self, head):
        commit = self._api("GET", "commits/" + sha(head))
        check(commit.get("sha") == head, "commit identity")
        tree = commit.get("tree")
        check(type(tree) is dict, "commit tree")
        tree_sha = sha(tree.get("sha"))
        tree = self._api("GET", "trees/" + tree_sha)
        check(tree.get("sha") == tree_sha and tree.get("truncated") is False,
              "tree identity/truncation")
        entries = tree.get("tree")
        check(type(entries) is list and len(entries) == 1, "not an initialized ledger tree")
        entry = entries[0]
        check(type(entry) is dict and entry.get("path") == LEDGER
              and entry.get("mode") == "100644" and entry.get("type") == "blob",
              "invalid ledger tree")
        blob_sha = sha(entry.get("sha"))
        blob = self._api("GET", "blobs/" + blob_sha)
        check(blob.get("sha") == blob_sha and blob.get("encoding") == "base64",
              "blob identity/encoding")
        size = blob.get("size")
        check(type(size) is int and 0 <= size <= MAX_LEDGER, "blob size")
        encoded = blob.get("content")
        check(isinstance(encoded, str) and len(encoded) <= 4 * MAX_LEDGER,
              "blob content")
        try:
            raw = base64.b64decode(encoded.replace("\n", ""), validate=True)
        except (ValueError, binascii.Error):
            raise StoreError("invalid blob base64") from None
        check(len(raw) == size and len(raw) <= MAX_LEDGER, "blob size mismatch")
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        check(git_blob == blob_sha, "blob hash mismatch")
        value = decode(raw)
        check(raw == canonical(value), "noncanonical ledger")
        return Snapshot(head, validate_envelope(value))

    def read(self):
        return self._at(self._ref())

    def _writable(self):
        check(_TEST_REF.fullmatch(self.branch), "production writes disabled")

    def _record(self, snap, operation, digest, replayed):
        row = snap.envelope["receipts"].get(operation)
        if row is None:
            return None
        check(row["digest"] == digest, "operation ID reused with different payload")
        return Receipt(operation, row["revision"], digest, snap.head, replayed)

    def _candidate(self, parent, envelope):
        raw = canonical(validate_envelope(envelope))
        blob = sha(self._api("POST", "blobs", {
            "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"
        }).get("sha"))
        expected = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        check(blob == expected, "created blob hash mismatch")
        tree = sha(self._api("POST", "trees", {"tree": [
            {"path": LEDGER, "mode": "100644", "type": "blob", "sha": blob}
        ]}).get("sha"))
        obj = self._api("POST", "commits", {"message": "V3 Work Queue transition",
                                            "tree": tree, "parents": [parent]})
        candidate = sha(obj.get("sha"))
        check(obj.get("parents") == [{"sha": parent}] or
              (isinstance(obj.get("parents"), list) and len(obj["parents"]) == 1
               and isinstance(obj["parents"][0], dict)
               and obj["parents"][0].get("sha") == parent), "not a single-parent commit")
        check(isinstance(obj.get("tree"), dict) and obj["tree"].get("sha") == tree,
              "created commit tree mismatch")
        return candidate

    def _advance(self, parent, candidate, operation, digest):
        error = None
        try:
            obj = self._api("PATCH", "refs/heads/" + quote(self.branch, safe="/"),
                            {"sha": candidate, "force": False})
            check(obj.get("ref") == "refs/heads/" + self.branch and
                  isinstance(obj.get("object"), dict) and
                  obj["object"].get("sha") == candidate, "unexpected update response")
        except StoreError as exc:
            error = exc
        # Even a successful response is checked against the durable receipt.
        # Never issue a second PATCH here.
        try:
            observed_head = self._ref()
            if observed_head == parent and isinstance(error, HttpFailure) and error.status in (
                    401, 403, 404, 409, 422):
                raise error
            observed = self._at(observed_head)
        except HttpFailure as exc:
            if exc is error:
                raise
            raise UncertainWrite("cannot reconcile ref update") from None
        except StoreError:
            raise UncertainWrite("cannot reconcile ref update") from None
        receipt = self._record(observed, operation, digest, error is not None)
        if receipt is not None:
            return receipt
        if isinstance(error, HttpFailure) and error.status in (409, 422) and observed.head != parent:
            raise Conflict("non-fast-forward; reread and recompute")
        if isinstance(error, HttpFailure) and error.status in (401, 403, 404):
            raise error
        raise UncertainWrite("operation receipt not observed; do not replay")

    def bootstrap_test(self, expected_head, initial_state, operation):
        """Explicit one-time initialization of a disposable ref only.

        The test ref may start at a normal source commit; the new root tree
        contains only the ledger. Never use this for main or a live queue.
        """
        self._writable()
        sha(expected_head)
        model.ident(operation)
        model.validate(initial_state)
        check(initial_state["revision"] == 0, "bootstrap revision")
        digest = fingerprint(expected_head, initial_state)
        current = self._ref()
        if current != expected_head:
            snap = self._at(current)
            receipt = self._record(snap, operation, digest, True)
            if receipt is not None:
                return receipt
            raise Conflict("bootstrap ref moved")
        # Ref must not already contain a ledger, even with a different
        # operation or a supplied current head. Inspect its immutable tree.
        commit = self._api("GET", "commits/" + current)
        check(commit.get("sha") == current and type(commit.get("tree")) is dict,
              "bootstrap commit")
        tree_sha = sha(commit["tree"].get("sha"))
        tree = self._api("GET", "trees/" + tree_sha)
        check(tree.get("sha") == tree_sha and tree.get("truncated") is False
              and type(tree.get("tree")) is list, "bootstrap tree")
        check(not any(isinstance(e, dict) and e.get("path") == LEDGER
                      for e in tree["tree"]), "already initialized")
        envelope = {"schema": 1, "state": copy.deepcopy(initial_state),
                    "receipts": {operation: {"digest": digest, "revision": 0}}}
        return self._advance(current, self._candidate(current, envelope), operation, digest)

    def publish(self, expected, next_state, operation):
        """Persist one authorized model transition; the broker must validate it.

        Repeating the exact operation against its original snapshot returns
        the durable receipt even after newer commits. Conflicting operation
        ID reuse, stale snapshots and non-incrementing revisions fail closed.
        """
        self._writable()
        check(isinstance(expected, Snapshot), "snapshot required")
        sha(expected.head)
        validate_envelope(expected.envelope)
        model.ident(operation)
        model.validate(next_state)
        check(next_state["revision"] == expected.envelope["state"]["revision"] + 1,
              "expected one revision increment")
        digest = fingerprint(expected.head, next_state)
        current = self.read()
        prior = self._record(current, operation, digest, True)
        if prior is not None:
            return prior
        if current.head != expected.head:
            raise Conflict("stale snapshot; reread and recompute")
        check(current.envelope == expected.envelope, "snapshot payload mismatch")
        envelope = copy.deepcopy(current.envelope)
        envelope["state"] = copy.deepcopy(next_state)
        envelope["receipts"][operation] = {"digest": digest,
                                             "revision": next_state["revision"]}
        candidate = self._candidate(current.head, envelope)
        return self._advance(current.head, candidate, operation, digest)
