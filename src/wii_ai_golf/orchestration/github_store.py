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
# A settlement adds one receipt and one resolution to the intent. With
# 128-character IDs, 64-character digests, 40-character SHAs and bounded
# 16-digit counters, 1024 bytes conservatively covers this expansion.
# Expiring an active run cannot enlarge its task/run strings in schema 3.
SETTLEMENT_RESERVE = 1024
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


def capacity_report(snapshot):
    """Size of a validated, pinned schema-3 snapshot; never writes."""
    check(isinstance(snapshot, Snapshot), "snapshot required")
    validate_envelope(snapshot.envelope)
    used = len(canonical(snapshot.envelope))
    remaining = MAX_LEDGER - used
    level = ("critical" if used * 100 >= MAX_LEDGER * 90 or
             remaining < SETTLEMENT_RESERVE else
             "warning" if used * 100 >= MAX_LEDGER * 75 else "normal")
    return {"head": snapshot.head, "revision": snapshot.state["revision"],
            "used_bytes": used, "limit_bytes": MAX_LEDGER,
            "remaining_bytes": remaining, "level": level,
            "receipt_count": len(snapshot.envelope["receipts"]),
            "run_count": len(snapshot.state["runs"]),
            "settlement_reserve_bytes": SETTLEMENT_RESERVE,
            "publication_pending": pending_publication(snapshot.envelope) is not None}


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
    check(type(value) is dict and set(value) == {"schema", "state", "receipts", "artifacts", "publications"},
          "invalid ledger envelope")
    check(type(value["schema"]) is int and value["schema"] == 3, "ledger schema")
    model.validate(value["state"])
    check(value["state"]["version"] == 2, "schema 3 requires full-history model")
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
    # Lazy import avoids a dependency cycle; artifact records are part of
    # the same immutable ledger, not mutable worker checkpoint text.
    from . import artifact_gateway as gateway
    artifacts = value["artifacts"]
    check(type(artifacts) is dict, "artifact journal")
    for operation, record in artifacts.items():
        check(operation in receipts, "artifact receipt missing")
        try:
            gateway.validate_record(record, value["state"])
        except (ValueError, StoreError) as exc:
            raise StoreError("invalid artifact journal record") from exc
        check(record["revision"] == receipts[operation]["revision"],
              "artifact receipt revision")
    validate_publications(value)
    check(len(canonical(value)) <= MAX_LEDGER, "ledger capacity; stop for reviewed compaction")
    return value


# Offline archive conversion oracle. This is not an accepted ledger schema;
# GitHubStore deliberately continues to read/write schema 3 only.
ARCHIVE_PAGE_RECORDS = 64


def archive_digest(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_snapshot(snapshot, *, recent_receipts=64):
    """Partition a validated snapshot without changing its history or authority.

    The returned manifest must be pinned by a trusted future state commit.
    Pages contain immutable canonical JSON, not references to mutable files.
    """
    check(isinstance(snapshot, Snapshot), "snapshot required")
    sha(snapshot.head)
    validate_envelope(snapshot.envelope)
    check(type(recent_receipts) is int and 1 <= recent_receipts <= 1024,
          "recent receipt count")
    check(pending_publication(snapshot.envelope) is None,
          "cannot archive unresolved publication")
    hot = copy.deepcopy(snapshot.envelope)
    cutoff = max(0, hot["state"]["revision"] + 1 - recent_receipts)
    old_receipts = {k: v for k, v in hot["receipts"].items()
                    if v["revision"] < cutoff}
    old_runs = {k: v for k, v in hot["state"]["runs"].items()
                if v["status"] == "CLOSED"}
    for key in old_receipts:
        del hot["receipts"][key]
    for key in old_runs:
        del hot["state"]["runs"][key]
    pages, blobs = [], {}
    for kind, records in (("receipts", old_receipts), ("runs", old_runs)):
        keys = sorted(records)
        for offset in range(0, len(keys), ARCHIVE_PAGE_RECORDS):
            chunk = {k: records[k] for k in keys[offset:offset + ARCHIVE_PAGE_RECORDS]}
            raw = canonical({"kind": kind, "records": chunk})
            check(len(raw) <= MAX_LEDGER, "archive page too large")
            digest = archive_digest(raw)
            check(digest not in blobs, "duplicate archive page")
            blobs[digest] = raw
            pages.append({"kind": kind, "digest": digest, "count": len(chunk),
                          "first": next(iter(chunk)), "last": next(reversed(chunk))})
    manifest = {"format": "v3-archive-prototype-1", "source_head": snapshot.head,
                "source_digest": archive_digest(canonical(snapshot.envelope)),
                "recent_receipts": recent_receipts, "hot": hot, "pages": pages}
    return manifest, blobs


def restore_archive(manifest, blobs, *, expected_digest, expected_head):
    """Verify and rehydrate the original schema-3 envelope, or fail closed.

    expected_digest and expected_head must come from independent trusted
    metadata, not the supplied manifest. No partial state is returned.
    """
    check(type(manifest) is dict and set(manifest) == {
        "format", "source_head", "source_digest", "recent_receipts", "hot", "pages"},
          "archive manifest fields")
    check(isinstance(expected_digest, str) and _DIGEST.fullmatch(expected_digest)
          and archive_digest(canonical(manifest)) == expected_digest,
          "archive manifest digest mismatch")
    check(manifest["format"] == "v3-archive-prototype-1" and
          manifest["source_head"] == sha(expected_head), "archive source mismatch")
    check(type(blobs) is dict and type(manifest["pages"]) is list,
          "archive pages")
    envelope = copy.deepcopy(manifest["hot"])
    check(type(envelope) is dict and type(envelope.get("state")) is dict
          and type(envelope.get("receipts")) is dict
          and type(envelope["state"].get("runs")) is dict, "archive hot state")
    seen = set()
    for row in manifest["pages"]:
        check(type(row) is dict and set(row) == {"kind", "digest", "count", "first", "last"},
              "archive page descriptor")
        kind, digest = row["kind"], row["digest"]
        check(kind in ("receipts", "runs") and isinstance(digest, str)
              and _DIGEST.fullmatch(digest) and digest not in seen,
              "archive page identity")
        seen.add(digest)
        raw = blobs.get(digest)
        check(type(raw) is bytes and len(raw) <= MAX_LEDGER
              and archive_digest(raw) == digest, "missing or corrupt archive page")
        page = decode(raw)
        check(type(page) is dict and set(page) == {"kind", "records"}
              and page["kind"] == kind and raw == canonical(page),
              "invalid archive page")
        records = page["records"]
        check(type(records) is dict and type(row["count"]) is int
              and 1 <= len(records) == row["count"] <= ARCHIVE_PAGE_RECORDS,
              "archive page count")
        keys = sorted(records)
        check(keys[0] == row["first"] and keys[-1] == row["last"],
              "archive page bounds")
        dest = envelope["receipts"] if kind == "receipts" else envelope["state"]["runs"]
        check(not (set(dest) & set(records)), "duplicate archive record")
        dest.update(records)
    check(set(blobs) == seen, "unexpected archive pages")
    validate_envelope(envelope)
    check(archive_digest(canonical(envelope)) == manifest["source_digest"],
          "archive source digest mismatch")
    snapshot = Snapshot(expected_head, envelope)
    # Enforce canonical partition, including correct hot/cold boundaries.
    rebuilt, rebuilt_blobs = archive_snapshot(
        snapshot, recent_receipts=manifest["recent_receipts"])
    check(rebuilt == manifest and rebuilt_blobs == blobs,
          "noncanonical archive partition")
    return snapshot


class ArchiveIndex:
    """Read-only lookup against an independently trusted archive manifest.

    The pin must identify a manifest previously verified against the complete
    source snapshot. A hash of an arbitrary caller-supplied manifest is not
    sufficient authority. This index does not authorize state transitions.
    """
    def __init__(self, manifest, read_page, *, expected_digest, expected_head):
        check(type(manifest) is dict and set(manifest) == {
            "format", "source_head", "source_digest", "recent_receipts", "hot", "pages"},
              "archive manifest fields")
        check(isinstance(expected_digest, str) and _DIGEST.fullmatch(expected_digest)
              and archive_digest(canonical(manifest)) == expected_digest,
              "archive manifest digest mismatch")
        check(manifest["format"] == "v3-archive-prototype-1"
              and manifest["source_head"] == sha(expected_head), "archive source mismatch")
        check(callable(read_page) and type(manifest["pages"]) is list, "archive index")
        self._hot = copy.deepcopy(manifest["hot"])
        self._read_page = read_page
        self._pages = {"receipts": [], "runs": []}
        seen = set()
        for row in manifest["pages"]:
            check(type(row) is dict and set(row) == {"kind", "digest", "count", "first", "last"},
                  "archive page descriptor")
            kind, digest = row["kind"], row["digest"]
            check(kind in self._pages and isinstance(digest, str)
                  and _DIGEST.fullmatch(digest) and digest not in seen, "archive page identity")
            seen.add(digest)
            check(type(row["count"]) is int and 1 <= row["count"] <= ARCHIVE_PAGE_RECORDS,
                  "archive page count")
            model.ident(row["first"])
            model.ident(row["last"])
            check(row["first"] <= row["last"], "archive page range")
            prior = self._pages[kind]
            check(not prior or prior[-1]["last"] < row["first"], "archive ranges overlap")
            prior.append(copy.deepcopy(row))

    def _hot_records(self, kind):
        return self._hot["receipts"] if kind == "receipts" else self._hot["state"]["runs"]

    def _load(self, row):
        raw = self._read_page(row["digest"])
        check(type(raw) is bytes and len(raw) <= MAX_LEDGER
              and archive_digest(raw) == row["digest"], "missing or corrupt archive page")
        page = decode(raw)
        check(type(page) is dict and set(page) == {"kind", "records"}
              and page["kind"] == row["kind"] and raw == canonical(page), "invalid archive page")
        records = page["records"]
        check(type(records) is dict and len(records) == row["count"], "archive page count")
        keys = sorted(records)
        check(keys[0] == row["first"] and keys[-1] == row["last"], "archive page bounds")
        check(not set(keys) & set(self._hot_records(row["kind"])), "duplicate archive record")
        return records

    def lookup(self, kind, key):
        check(kind in self._pages, "archive lookup kind")
        model.ident(key)
        hot = self._hot_records(kind)
        if key in hot:
            return copy.deepcopy(hot[key])
        # Binary search the disjoint sorted page ranges. At most one cold
        # page read is needed, including a negative lookup inside a range.
        pages = self._pages[kind]
        lo, hi = 0, len(pages)
        while lo < hi:
            mid = (lo + hi) // 2
            if pages[mid]["last"] < key:
                lo = mid + 1
            else:
                hi = mid
        if lo == len(pages) or key < pages[lo]["first"]:
            return None
        return copy.deepcopy(self._load(pages[lo]).get(key))

    def receipt_prefix(self, prefix, *, max_pages=4):
        """Find all operation IDs with this prefix, or fail closed on budget.

        IDs use the model's ASCII alphabet; '~' sorts beyond every legal
        suffix. A missing candidate page is never interpreted as absence.
        """
        model.ident(prefix)
        check(type(max_pages) is int and 1 <= max_pages <= 64, "archive lookup budget")
        candidates = [row for row in self._pages["receipts"]
                      if row["last"] >= prefix and row["first"] <= prefix + "~"]
        check(len(candidates) <= max_pages, "archive prefix lookup budget exceeded")
        matches = {k: v for k, v in self._hot_records("receipts").items()
                   if k.startswith(prefix)}
        for row in candidates:
            matches.update({k: v for k, v in self._load(row).items() if k.startswith(prefix)})
        return copy.deepcopy(matches)


# Immutable path-copy radix index prototype. Root digest must be independently
# trusted; an arbitrary self-authenticated root cannot prove nonmembership.
_INDEX_KINDS = ("receipt", "request", "run", "event")
_REQUEST_OP = re.compile(r"(op-[0-9a-f]{32}-)[0-9a-f]{64}")


class IncrementalIndex:
    """Append-only content-addressed index, with bounded per-key object IO.

    The host supplies immutable blob read/write capabilities. put returns a
    new root; it never mutates the old root or publishes a state ref. Missing
    referenced objects are errors, not evidence that a key is absent.
    """
    def __init__(self, read_node, write_node):
        check(callable(read_node) and callable(write_node), "index transport")
        self._read = read_node
        self._write = write_node

    @staticmethod
    def _key(kind, key):
        check(kind in _INDEX_KINDS, "index kind")
        model.ident(key)
        return archive_digest(canonical([kind, key]))

    @staticmethod
    def _digest(value):
        check(isinstance(value, str) and _DIGEST.fullmatch(value), "index node digest")
        return value

    def _load(self, digest, prefix):
        raw = self._read(self._digest(digest))
        check(type(raw) is bytes and len(raw) <= MAX_LEDGER
              and archive_digest(raw) == digest, "missing or corrupt index node")
        node = decode(raw)
        check(type(node) is dict and raw == canonical(node), "invalid index node")
        if set(node) == {"kind", "key", "value"}:
            route = self._key(node["kind"], node["key"])
            check(route.startswith(prefix) and type(node["value"]) is dict,
                  "misplaced index leaf")
        else:
            check(set(node) == {"children"} and len(prefix) < 64
                  and type(node["children"]) is dict
                  and 1 <= len(node["children"]) <= 16, "invalid index branch")
            for label, child in node["children"].items():
                check(isinstance(label, str) and len(label) == 1
                      and label in "0123456789abcdef", "index branch label")
                self._digest(child)
        return node

    def _save(self, node):
        raw = canonical(node)
        check(len(raw) <= MAX_LEDGER, "index node size")
        digest = archive_digest(raw)
        self._write(digest, raw)
        return digest

    def get(self, root, kind, key):
        route = self._key(kind, key)
        prefix = ""
        while root is not None:
            node = self._load(root, prefix)
            if "children" not in node:
                if (node["kind"], node["key"]) == (kind, key):
                    return copy.deepcopy(node["value"])
                check(self._key(node["kind"], node["key"]) != route, "index hash collision")
                return None
            label = route[len(prefix)]
            root = node["children"].get(label)
            prefix += label
        return None

    def put(self, root, kind, key, value):
        route = self._key(kind, key)
        check(type(value) is dict, "index record")
        leaf = {"kind": kind, "key": key, "value": copy.deepcopy(value)}

        def insert(node_id, prefix):
            if node_id is None:
                return self._save(leaf)
            node = self._load(node_id, prefix)
            if "children" not in node:
                if (node["kind"], node["key"]) == (kind, key):
                    check(node["value"] == value, "immutable index record conflict")
                    return node_id
                old_route = self._key(node["kind"], node["key"])
                check(old_route != route, "index hash collision")
                depth = len(prefix)
                # Only the divergent path is created; the old leaf remains
                # shared. Maximum depth is the 64-character hash width.
                split = depth
                while old_route[split] == route[split]:
                    split += 1
                new_id = self._save(leaf)
                branch = self._save({"children": {old_route[split]: node_id,
                                                  route[split]: new_id}})
                for i in range(split - 1, depth - 1, -1):
                    branch = self._save({"children": {route[i]: branch}})
                return branch
            label = route[len(prefix)]
            children = dict(node["children"])
            children[label] = insert(children.get(label), prefix + label)
            if children == node["children"]:
                return node_id
            return self._save({"children": children})

        return insert(root, "")

    def record_receipt(self, root, operation, row):
        model.ident(operation)
        check(type(row) is dict and set(row) == {"revision", "digest"}, "index receipt")
        model.integer(row["revision"], "receipt revision")
        self._digest(row["digest"])
        match = _REQUEST_OP.fullmatch(operation)
        if match:
            prefix = match.group(1)
            # A separate exact key replaces unbounded prefix scans.
            root = self.put(root, "request", prefix, {"operation": operation})
        return self.put(root, "receipt", operation, row)


# The count map is bounded by the permanent task population, not transitions.
# Old prototype roots have no history and are deliberately not upgraded in place.
HOT_HISTORY_FORMAT = "indexed-hot-history-2"
MAX_HISTORY_BACKFILL = 5000


def event_key(task, sequence):
    model.ident(task)
    model.integer(sequence, "event sequence")
    return archive_digest(canonical([task, sequence]))


def history_manifest(manifest):
    check(type(manifest) is dict, "hot manifest")
    if manifest.get("format") == HOT_HISTORY_FORMAT:
        check(set(manifest) == {"format", "source_head", "state", "root", "event_counts"},
              "hot history manifest")
        counts = manifest["event_counts"]
        check(type(counts) is dict and set(counts) == set(manifest["state"]["tasks"]),
              "task event count coverage")
        for count in counts.values():
            check(model.integer(count, "event count") > 0, "empty task history")
    else:
        check(set(manifest) == {"format", "source_head", "state", "root"}
              and manifest.get("format") == "indexed-hot-prototype-1", "hot manifest")
    return manifest


def append_task_events(index, root, counts, before, after, operation, source_commit=None):
    """Index a transition before run compaction. No circular commit-SHA claim."""
    counts = dict(counts)
    model.ident(operation)
    if source_commit is not None:
        sha(source_commit)
    check(set(before["tasks"]) <= set(after["tasks"]), "task history removed")

    def emit(task, kind, data):
        nonlocal root
        sequence = counts.get(task, 0) + 1
        model.integer(sequence, "event sequence")
        row = {"task": task, "sequence": sequence, "kind": kind,
               "revision": after["revision"], "operation": operation,
               "clock": after["clock"], "source_commit": source_commit,
               "data": copy.deepcopy(data)}
        root = index.put(root, "event", event_key(task, sequence), row)
        counts[task] = sequence

    for task, new in sorted(after["tasks"].items()):
        old = before["tasks"].get(task)
        if old is None:
            emit(task, "created", new)
        elif old != new:
            emit(task, "task_changed", {"before": old, "after": new})
    for run_id, run in sorted(after["runs"].items()):
        old = before["runs"].get(run_id)
        if old != run:
            kind = ("claimed" if old is None else
                    ("expired" if run["outcome"] == "EXPIRED" else "released")
                    if run["status"] == "CLOSED" else "renewed")
            emit(run["task"], kind, {"run_id": run_id, "run": run})
    if before["oversight"] != after["oversight"]:
        emit(model.MANAGER, "oversight_changed", after["oversight"])
    return root, counts


def indexed_hot_projection(snapshot, index):
    """Create a pure hot manifest from a validated full-history snapshot.

    Artifact/publication handling is intentionally outside this prototype.
    All receipts and terminal runs are indexed before the root is returned.
    No state publication or durable object reachability is implied.
    """
    check(isinstance(snapshot, Snapshot), "snapshot required")
    sha(snapshot.head)
    validate_envelope(snapshot.envelope)
    check(not snapshot.envelope["artifacts"] and not snapshot.envelope["publications"],
          "indexed hot prototype does not support artifact/publication records")
    hot, cold = model.hot_projection(snapshot.state)
    root = None
    for key, row in sorted(snapshot.envelope["receipts"].items()):
        root = index.record_receipt(root, key, row)
    for key, row in sorted(cold.items()):
        root = index.put(root, "run", key, row)
    return {"format": "indexed-hot-prototype-1", "source_head": snapshot.head,
            "state": hot, "root": root}


def indexed_hot_transition(manifest, index, operation, digest, transition):
    """Pure host-only proposal; callback must implement an authorized action.

    The trusted caller supplies a previously verified manifest and commits
    the returned state and root together. No external effects are allowed
    in transition. This is not a broker or durable CAS implementation.
    """
    history_manifest(manifest)
    sha(manifest["source_head"])
    state = model.validate(manifest["state"])
    check(state["version"] == 3, "hot model required")
    root = manifest["root"]
    index._digest(root)
    model.ident(operation)
    index._digest(digest)
    match = _REQUEST_OP.fullmatch(operation)
    if match:
        prior = index.get(root, "request", match.group(1))
        check(prior is None or prior == {"operation": operation},
              "request ID reused with different payload")
    receipt = index.get(root, "receipt", operation)
    if receipt is not None:
        check(receipt["digest"] == digest, "operation ID reused with different payload")
        return copy.deepcopy(manifest), copy.deepcopy(receipt), True
    check(callable(transition), "hot transition callback required")
    proposed = transition(copy.deepcopy(state),
                          lambda key: index.get(root, "run", key) is not None)
    model.validate(proposed)
    check(proposed["version"] == 3 and proposed["revision"] == state["revision"] + 1
          and all(proposed["archived_fences"].get(k) == v
                  for k, v in state["archived_fences"].items())
          and all(v == 0 for k, v in proposed["archived_fences"].items()
                  if k not in state["archived_fences"]),
          "invalid hot transition revision or archive floors")
    hot, cold = model.compact_hot(proposed)
    for key, row in sorted(cold.items()):
        check(index.get(root, "run", key) is None, "archived run already exists")
        root = index.put(root, "run", key, row)
    result = {**manifest, "state": hot}
    if manifest["format"] == HOT_HISTORY_FORMAT:
        root, counts = append_task_events(index, root, manifest["event_counts"],
                                          state, proposed, operation)
        result["event_counts"] = counts
    receipt = {"revision": hot["revision"], "digest": digest}
    root = index.record_receipt(root, operation, receipt)
    result["root"] = root
    history_manifest(result)
    return result, receipt, False


_PUBLICATION_REF = re.compile(r"orchestration/v3-publication-test-[a-z0-9][a-z0-9-]{0,63}")


def pending_publication(envelope):
    pending = [key for key, row in envelope["publications"].items()
               if row["resolution"] is None]
    check(len(pending) <= 1, "multiple unresolved publication intents")
    return pending[0] if pending else None


def validate_publications(envelope):
    """Validate immutable intent and terminal receipt links; no source IO."""
    rows = envelope["publications"]
    check(type(rows) is dict, "publication journal")
    receipts, artifacts = envelope["receipts"], envelope["artifacts"]
    seen_artifacts, seen_resolutions = set(), set()
    for key, row in rows.items():
        check(key in receipts and key not in artifacts, "publication intent receipt")
        check(type(row) is dict and set(row) == {"artifact", "target", "resolution"},
              "publication row")
        artifact = row["artifact"]
        check(isinstance(artifact, str) and artifact in artifacts
              and artifact not in seen_artifacts, "publication artifact")
        seen_artifacts.add(artifact)
        check(isinstance(row["target"], str) and _PUBLICATION_REF.fullmatch(row["target"]),
              "publication target must be disposable")
        revision = receipts[key]["revision"]
        check(revision > receipts[artifact]["revision"], "intent must follow acceptance")
        resolution = row["resolution"]
        if resolution is None:
            check(revision == envelope["state"]["revision"], "mutation after unresolved intent")
            continue
        check(type(resolution) is dict and set(resolution) == {"operation", "observed_head"},
              "publication resolution")
        op = resolution["operation"]
        check(isinstance(op, str) and op in receipts and op not in artifacts
              and op not in rows and op not in seen_resolutions
              and receipts[op]["revision"] == revision + 1, "publication resolution receipt")
        seen_resolutions.add(op)
        check(sha(resolution["observed_head"]) in (artifacts[artifact]["base"],
              artifacts[artifact]["head"]), "unknown publication outcome")
    pending_publication(envelope)


def publication_transition(current, next_state, operation, publication):
    """Trusted host only. Reserve ledger until a settled outcome is verified.

    No source writes here. The future broker must independently verify
    settlement, including absence of in-flight IO, before resolution.
    """
    pending = pending_publication(current)
    rows = copy.deepcopy(current["publications"])
    if publication is None:
        check(pending is None, "publication unresolved; queue frozen")
        return rows
    check(type(publication) is dict, "publication mutation")
    expected = model.sweep(current["state"], next_state["clock"])
    expected["revision"] = current["state"]["revision"] + 1
    check(next_state == expected, "publication transition must only sweep")
    if set(publication) == {"artifact", "target"}:
        check(pending is None, "publication unresolved; queue frozen")
        key = publication["artifact"]
        check(isinstance(key, str) and key in current["artifacts"]
              and all(row["artifact"] != key for row in rows.values()),
              "artifact already used or missing")
        artifact = current["artifacts"][key]
        task, run_id, fence = (artifact[k] for k in ("task", "run_id", "fence"))
        model.active(next_state, task, run_id, fence)
        check(artifact["goal_sha"] == next_state["oversight"]["goal_sha"]
              and next_state["tasks"][task]["checkpoint"]["head"] == artifact["head"],
              "artifact no longer current")
        rows[operation] = {**publication, "resolution": None}
    elif set(publication) == {"intent", "observed_head"}:
        check(pending is not None and publication["intent"] == pending,
              "no matching unresolved intent")
        artifact = current["artifacts"][rows[pending]["artifact"]]
        check(sha(publication["observed_head"]) in (artifact["base"], artifact["head"]),
              "ambiguous publication outcome; queue remains frozen")
        rows[pending]["resolution"] = {"operation": operation,
                                       "observed_head": publication["observed_head"]}
    else:
        raise StoreError("invalid publication mutation")
    return rows


def fingerprint(base, next_state, artifact=None, publication=None):
    return hashlib.sha256(canonical({"parent": sha(base), "state": next_state,
                                      "artifact": artifact, "publication": publication})).hexdigest()


def archive_checkpoint_digest(parent, next_state, recent_receipts):
    return archive_digest(canonical({"archive_parent": sha(parent),
                                     "state": next_state,
                                     "recent_receipts": recent_receipts}))



@dataclass(frozen=True)
class HotSnapshot:
    """Pinned disposable hot ledger; never a worker-supplied capability."""
    head: str
    manifest: dict
    root_tree: str
    operation: str

    @property
    def state(self):
        return copy.deepcopy(self.manifest["state"])


class GitTreeIndex(IncrementalIndex):
    """Content-addressed radix nodes stored as real Git trees.

    A branch tree contains node.json and one child tree per radix label.
    The JSON digest is checked separately from Git object identity. Only
    references learned from the anchored root or newly written nodes may
    be loaded; a caller cannot supply an arbitrary Git object locator.
    Cache is disposable and scoped to this one traversal/proposal.
    """
    def __init__(self, store, root=None, root_tree=None):
        self._store = store
        self._trees = {}
        if root is not None:
            self._bind(root, root_tree)
        else:
            check(root_tree is None, "unexpected index tree")
        super().__init__(self._read_git, self._write_git)

    def _bind(self, digest, tree):
        self._digest(digest)
        sha(tree)
        check(digest not in self._trees or self._trees[digest] == tree,
              "conflicting index tree identity")
        self._trees[digest] = tree

    def tree_for(self, digest):
        self._digest(digest)
        check(digest in self._trees, "unanchored index node")
        return self._trees[digest]

    def _read_git(self, digest):
        entries = self._store._hot_tree(self.tree_for(digest))
        check("node.json" in entries and entries["node.json"]["type"] == "blob",
              "index node blob missing")
        raw = self._store._blob_at(entries.pop("node.json")["sha"])
        check(archive_digest(raw) == digest, "index node digest mismatch")
        node = decode(raw)
        check(type(node) is dict and raw == canonical(node), "invalid index node")
        children = node.get("children", {})
        check(type(children) is dict and set(entries) == set(children),
              "index child tree membership")
        for label, child in children.items():
            check(len(label) == 1 and label in "0123456789abcdef"
                  and entries[label]["type"] == "tree", "invalid index child")
            self._bind(child, entries[label]["sha"])
        return raw

    def _write_git(self, digest, raw):
        check(archive_digest(raw) == digest, "index write digest mismatch")
        if digest in self._trees:
            check(self._read_git(digest) == raw, "index node conflict")
            return
        node = decode(raw)
        entries = [{"path": "node.json", "mode": "100644", "type": "blob",
                    "sha": self._store._put_archive_blob(raw)}]
        for label, child in sorted(node.get("children", {}).items()):
            entries.append({"path": label, "mode": "040000", "type": "tree",
                            "sha": self.tree_for(child)})
        tree = self._store._put_hot_tree(entries)
        self._bind(digest, tree)


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
        check(type(entries) is list, "ledger tree entries")
        if any(isinstance(e, dict) and e.get("path") == "archive-root.json"
               for e in entries):
            # Physical archive encoding is test-only. Logical envelope remains
            # schema 3, including every receipt and fence.
            check(_TEST_REF.fullmatch(self.branch), "archive root reads are test-only")
            parents = commit.get("parents")
            check(type(parents) is list and len(parents) == 1 and type(parents[0]) is dict,
                  "archive root parent")
            parent = sha(parents[0].get("sha"))
            root = [e for e in entries if isinstance(e, dict)
                    and e.get("path") == "archive-root.json"]
            check(len(root) == 1, "archive root identity")
            raw = self._blob_at(root[0].get("sha"))
            digest = archive_digest(raw)
            manifest, read_page, _ = self._archive_parts(
                head, expected_digest=digest, expected_head=parent, root=True)
            restored = restore_archive(
                manifest, {row["digest"]: read_page(row["digest"]) for row in manifest["pages"]},
                expected_digest=digest, expected_head=parent)
            envelope = restored.envelope
            operation, receipt = next((k, v) for k, v in envelope["receipts"].items()
                                      if v["revision"] == envelope["state"]["revision"])
            check(operation.startswith("archive-") and receipt["digest"] ==
                  archive_checkpoint_digest(parent, envelope["state"], manifest["recent_receipts"]),
                  "archive root receipt mismatch")
            return Snapshot(head, envelope)
        check(len(entries) == 1, "not an initialized ledger tree")
        entry = entries[0]
        check(type(entry) is dict and entry.get("path") == LEDGER
              and entry.get("mode") == "100644" and entry.get("type") == "blob",
              "invalid ledger tree")
        raw = self._blob_at(entry.get("sha"))
        value = decode(raw)
        check(raw == canonical(value), "noncanonical ledger")
        return Snapshot(head, validate_envelope(value))

    def _blob_at(self, blob_sha):
        blob_sha = sha(blob_sha)
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
        return raw

    def _put_archive_blob(self, raw):
        check(type(raw) is bytes and len(raw) <= MAX_LEDGER, "archive blob size")
        blob = sha(self._api("POST", "blobs", {
            "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"
        }).get("sha"))
        expected = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        check(blob == expected, "created archive blob hash mismatch")
        return blob

    def _archive_parts(self, candidate, *, expected_digest, expected_head, root=False):
        commit = self._api("GET", "commits/" + sha(candidate))
        parents = commit.get("parents")
        check(commit.get("sha") == candidate and isinstance(parents, list)
              and len(parents) == 1 and isinstance(parents[0], dict)
              and parents[0].get("sha") == sha(expected_head), "archive parent mismatch")
        tree_sha = sha(commit["tree"]["sha"])
        tree = self._api("GET", "trees/" + tree_sha)
        check(tree.get("sha") == tree_sha and tree.get("truncated") is False
              and type(tree.get("tree")) is list, "archive tree identity")
        entries = {}
        for entry in tree["tree"]:
            check(type(entry) is dict and entry.get("type") == "blob"
                  and entry.get("mode") == "100644", "archive tree entry")
            name = entry.get("path")
            check(isinstance(name, str) and name not in entries, "archive tree path")
            entries[name] = sha(entry.get("sha"))
        name = "archive-root.json" if root else "archive.json"
        check(name in entries, "archive manifest missing")
        raw = self._blob_at(entries.pop(name))
        manifest = decode(raw)
        check(raw == canonical(manifest) and archive_digest(raw) == expected_digest,
              "archive manifest digest mismatch")
        def read_page(digest):
            check(digest + ".json" in entries, "archive page missing from tree")
            return self._blob_at(entries[digest + ".json"])
        index = ArchiveIndex(manifest, read_page, expected_digest=expected_digest,
                             expected_head=expected_head)
        check(set(entries) == {row["digest"] + ".json" for row in manifest["pages"]},
              "archive tree membership")
        return manifest, read_page, index

    def stage_archive(self, snapshot, *, recent_receipts=64):
        """Build and verify immutable objects; NEVER advance a ref.

        The returned candidate is not an authoritative ledger or a durable
        root. It can be garbage collected until a future reviewed scheme
        anchors it. Only disposable test contexts may create these objects.
        """
        self._writable()
        check(isinstance(snapshot, Snapshot), "snapshot required")
        current = self.read()
        if current != snapshot:
            raise Conflict("archive source moved or mismatched")
        candidate, digest = self._build_archive(current, recent_receipts=recent_receipts)
        if self._ref() != current.head:
            raise Conflict("archive source moved during staging")
        return {"candidate": candidate, "manifest_digest": digest, "source_head": current.head}

    def _build_archive(self, snapshot, *, recent_receipts, root=False):
        manifest, pages = archive_snapshot(snapshot, recent_receipts=recent_receipts)
        raw = canonical(manifest)
        digest = archive_digest(raw)
        name = "archive-root.json" if root else "archive.json"
        entries = [{"path": name, "mode": "100644", "type": "blob",
                    "sha": self._put_archive_blob(raw)}]
        for key, body in sorted(pages.items()):
            entries.append({"path": key + ".json", "mode": "100644", "type": "blob",
                            "sha": self._put_archive_blob(body)})
        tree = sha(self._api("POST", "trees", {"tree": entries}).get("sha"))
        obj = self._api("POST", "commits", {
            "message": "V3 test archive checkpoint" if root else "V3 offline archive candidate",
            "tree": tree, "parents": [snapshot.head]})
        candidate = sha(obj.get("sha"))
        observed, read_page, _ = self._archive_parts(
            candidate, expected_digest=digest, expected_head=snapshot.head, root=root)
        restored = restore_archive(observed, {k: read_page(k) for k in pages},
                                   expected_digest=digest, expected_head=snapshot.head)
        check(restored == snapshot, "archive candidate source mismatch")
        return candidate, digest

    def archive_checkpoint(self, expected, operation, *, recent_receipts=64):
        """Host-only disposable checkpoint; no active lease or time change.

        One new revision and receipt identify the physical encoding change.
        The existing schema-3 logical state is retained in full on hydration.
        No unresolved publication may be archived. This is a persistence
        prototype, not a bounded hot-state transition backend.
        """
        self._writable()
        check(isinstance(expected, Snapshot), "snapshot required")
        sha(expected.head)
        validate_envelope(expected.envelope)
        model.ident(operation)
        check(operation.startswith("archive-"), "archive operation prefix required")
        check(type(recent_receipts) is int and 1 <= recent_receipts <= 1024,
              "recent receipt count")
        check(pending_publication(expected.envelope) is None,
              "cannot archive unresolved publication")
        envelope = copy.deepcopy(expected.envelope)
        envelope["state"]["revision"] += 1
        revision = envelope["state"]["revision"]
        digest = archive_checkpoint_digest(expected.head, envelope["state"], recent_receipts)
        current = self.read()
        prior = self._record(current, operation, digest, True)
        if prior is not None:
            return prior
        if current != expected:
            raise Conflict("archive source moved or mismatched")
        envelope["receipts"][operation] = {"digest": digest, "revision": revision}
        candidate, _ = self._build_archive(Snapshot(current.head, envelope),
                                            recent_receipts=recent_receipts, root=True)
        check(self._at(candidate).envelope == envelope, "archive checkpoint readback mismatch")
        return self._advance(current.head, candidate, operation, digest)

    def open_archive_index(self, candidate, *, expected_digest, expected_head):
        """Read a pinned, previously verified candidate; never grant authority."""
        return self._archive_parts(candidate, expected_digest=expected_digest,
                                   expected_head=expected_head)[2]

    def read(self):
        return self._at(self._ref())

    def task_history(self, task, *, limit=20, cursor=None):
        """Read-only, bounded task projection from the authoritative commit chain.

        Pages count ledger revisions, not task events. Empty pages can have a
        continuation. Cursor is the next older ledger revision, not a Git object SHA.
        No uncommitted effective sweep is included.
        """
        model.ident(task)
        check(type(limit) is int and 1 <= limit <= 50, "history page limit")
        tip = self.read()
        check(task in tip.state["tasks"], "unknown task")
        # A cursor is a revision offset, not an arbitrary Git object locator.
        # Pin a page to the original tip; only accept a verified ancestor by
        # walking from the live tip. Limit traversal to a bounded window.
        start = tip.state["revision"] if cursor is None else cursor
        check(type(start) is int and 0 <= start <= tip.state["revision"]
              and tip.state["revision"] - start <= 500, "history cursor outside window")
        def parent(snap):
            commit = self._api("GET", "commits/" + snap.head)
            parents = commit.get("parents")
            check(commit.get("sha") == snap.head and type(parents) is list
                  and len(parents) == 1 and type(parents[0]) is dict,
                  "history commit is not single-parent")
            older = self._at(sha(parents[0].get("sha")))
            check(older.state["revision"] + 1 == snap.state["revision"],
                  "history revision discontinuity")
            old_receipts, new_receipts = older.envelope["receipts"], snap.envelope["receipts"]
            check(all(new_receipts.get(k) == v for k, v in old_receipts.items()),
                  "history receipt changed")
            check(all(snap.envelope["artifacts"].get(k) == v
                      for k, v in older.envelope["artifacts"].items()),
                  "history artifact changed")
            return older
        current = tip
        while current.state["revision"] > start:
            current = parent(current)
        events = []
        next_cursor = None
        for _ in range(limit):
            rev = current.state["revision"]
            prior = parent(current) if rev else None
            now = current.state
            before = prior.state if prior else {"tasks": {}, "runs": {}, "oversight": {}}
            op = next(k for k, v in current.envelope["receipts"].items()
                      if v["revision"] == rev)
            old, new = before["tasks"].get(task), now["tasks"].get(task)
            def emit(kind, data):
                events.append({"task": task, "kind": kind, "revision": rev,
                               "operation": op, "commit": current.head,
                               "clock": now["clock"], "data": data})
            if old is None and new is not None:
                emit("created", new)
            elif old != new:
                check(new is not None, "task history removed")
                emit("task_changed", {"before": old, "after": new})
            for run_id, run in sorted(now["runs"].items()):
                if run["task"] == task and before["runs"].get(run_id) != run:
                    old_run = before["runs"].get(run_id)
                    kind = ("claimed" if old_run is None else
                            ("expired" if run["outcome"] == "EXPIRED" else "released")
                            if run["status"] == "CLOSED" else "renewed")
                    emit(kind, {"run_id": run_id, "run": run})
            artifact = current.envelope["artifacts"].get(op)
            if artifact is not None and artifact["task"] == task:
                emit("artifact_accepted", artifact)
            for key, row in current.envelope["publications"].items():
                if current.envelope["artifacts"][row["artifact"]]["task"] != task:
                    continue
                if key == op:
                    emit("publication_intent", {"intent": key, **row})
                if row["resolution"] is not None and row["resolution"]["operation"] == op:
                    emit("publication_resolved", {"intent": key, **row})
            if task == model.MANAGER and before["oversight"] != now["oversight"]:
                emit("oversight_changed", now["oversight"])
            if prior is None:
                break
            next_cursor = prior.state["revision"]
            current = prior
        else:
            return {"task": task, "head": tip.head, "events": events,
                    "next_cursor": next_cursor}
        return {"task": task, "head": tip.head, "events": events, "next_cursor": None}


    def _hot_tree(self, tree_sha):
        obj = self._api("GET", "trees/" + sha(tree_sha))
        check(obj.get("sha") == tree_sha and obj.get("truncated") is False
              and type(obj.get("tree")) is list and len(obj["tree"]) <= 17,
              "hot tree identity or size")
        result = {}
        for row in obj["tree"]:
            check(type(row) is dict and type(row.get("path")) is str
                  and row["path"] not in result
                  and (row["path"] in {"node.json", "hot.json", "index"}
                       or len(row["path"]) == 1 and row["path"] in "0123456789abcdef"),
                  "invalid or duplicate hot tree entry")
            check((row.get("mode"), row.get("type")) in
                  (("100644", "blob"), ("040000", "tree")), "invalid hot tree mode")
            result[row["path"]] = {"path": row["path"], "mode": row["mode"],
                                   "type": row["type"], "sha": sha(row.get("sha"))}
        # Verify the real Git tree hash, including the type-specific sort
        # order and binary object IDs, not just the API's stated SHA.
        check(self._hot_tree_sha(list(result.values())) == tree_sha,
              "hot tree hash mismatch")
        return result

    @staticmethod
    def _hot_tree_sha(entries):
        ordered = sorted(entries, key=lambda e: e["path"] +
                         ("/" if e["type"] == "tree" else ""))
        raw = b"".join(
            (("40000" if e["type"] == "tree" else "100644") + " " +
             e["path"]).encode("ascii") + b"\0" + bytes.fromhex(e["sha"])
            for e in ordered)
        return hashlib.sha1(b"tree " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

    def _put_hot_tree(self, entries):
        expected = self._hot_tree_sha(entries)
        tree = sha(self._api("POST", "trees", {"tree": entries}).get("sha"))
        check(tree == expected, "created hot tree hash mismatch")
        return tree

    def _hot_at(self, head):
        self._writable()
        commit = self._api("GET", "commits/" + sha(head))
        check(commit.get("sha") == head and type(commit.get("tree")) is dict,
              "hot commit identity")
        parents = commit.get("parents")
        check(type(parents) is list and len(parents) == 1
              and type(parents[0]) is dict, "hot commit parent")
        parent = sha(parents[0].get("sha"))
        entries = self._hot_tree(commit["tree"]["sha"])
        check(set(entries) == {"hot.json", "index"}
              and entries["hot.json"]["type"] == "blob"
              and entries["index"]["type"] == "tree", "hot root membership")
        raw = self._blob_at(entries["hot.json"]["sha"])
        value = decode(raw)
        check(type(value) is dict and raw == canonical(value)
              and set(value) == {"manifest", "parent", "operation", "repository", "branch"}
              and value["parent"] == parent and value["repository"] == self.prefix
              and value["branch"] == self.branch, "hot root binding")
        manifest = value["manifest"]
        history_manifest(manifest)
        check(manifest["format"] == HOT_HISTORY_FORMAT,
              "old hot root requires reviewed history migration")
        sha(manifest["source_head"])
        model.validate(manifest["state"])
        check(manifest["state"]["version"] == 3
              and all(run["status"] == "IN_PROGRESS" for run in manifest["state"]["runs"].values()),
              "noncompact hot state")
        operation = model.ident(value["operation"])
        root_tree = entries["index"]["sha"]
        index = GitTreeIndex(self, manifest["root"], root_tree)
        row = index.get(manifest["root"], "receipt", operation)
        check(type(row) is dict and set(row) == {"revision", "digest"}
              and row["revision"] == manifest["state"]["revision"], "hot root receipt")
        index._digest(row["digest"])
        return HotSnapshot(head, manifest, root_tree, operation)

    def read_hot(self):
        """Read the authoritative disposable hot root, not an arbitrary SHA."""
        self._writable()
        return self._hot_at(self._ref())

    def hot_lookup_at(self, snap, kind, key):
        """Lookup against one host-pinned root, never a moving ref.

        The trusted caller obtains snap via read_hot. No worker-supplied
        snapshot is accepted by the broker.
        """
        self._writable()
        check(isinstance(snap, HotSnapshot), "hot snapshot required")
        index = GitTreeIndex(self, snap.manifest["root"], snap.root_tree)
        return index.get(snap.manifest["root"], kind, key)

    def hot_lookup(self, kind, key):
        return self.hot_lookup_at(self.read_hot(), kind, key)

    def hot_task_history(self, snap, task, *, limit=20, position=None):
        """Host-pinned event page, newest first; no revision scan or ref write.

        Position is a trusted host offset. Never expose this method directly
        to a worker or use a caller-supplied snapshot.
        """
        self._writable()
        check(isinstance(snap, HotSnapshot), "hot snapshot required")
        model.ident(task)
        check(type(limit) is int and 1 <= limit <= 50, "history page limit")
        counts = snap.manifest["event_counts"]
        check(task in counts, "unknown task")
        count = counts[task]
        start = count if position is None else position
        check(type(start) is int and 1 <= start <= count, "invalid event position")
        index = GitTreeIndex(self, snap.manifest["root"], snap.root_tree)
        rows = []
        for sequence in range(start, max(0, start - limit), -1):
            row = index.get(snap.manifest["root"], "event", event_key(task, sequence))
            check(type(row) is dict and set(row) ==
                  {"task", "sequence", "kind", "revision", "operation", "clock",
                   "source_commit", "data"} and row["task"] == task
                  and row["sequence"] == sequence
                  and model.integer(row["revision"], "event revision") <= snap.state["revision"],
                  "missing or corrupt task event")
            rows.append(row)
        return {"task": task, "head": snap.head, "event_count": count,
                "events": rows, "next_position": start - len(rows) or None}

    def _backfill_hot_history(self, expected, manifest, index):
        # One-time bounded import; all prior events or no conversion.
        check(expected.state["revision"] <= MAX_HISTORY_BACKFILL,
              "history backfill exceeds reviewed limit")
        chain = [expected]
        while chain[-1].state["revision"]:
            current = chain[-1]
            commit = self._api("GET", "commits/" + current.head)
            parents = commit.get("parents")
            check(commit.get("sha") == current.head and type(parents) is list
                  and len(parents) == 1 and type(parents[0]) is dict,
                  "history commit is not single-parent")
            older = self._at(sha(parents[0].get("sha")))
            check(older.state["revision"] + 1 == current.state["revision"]
                  and all(current.envelope["receipts"].get(k) == v
                          for k, v in older.envelope["receipts"].items())
                  and not older.envelope["artifacts"] and not older.envelope["publications"],
                  "history backfill discontinuity")
            chain.append(older)
        root, counts = manifest["root"], {}
        before = {"tasks": {}, "runs": {}, "oversight": {}}
        for snap in reversed(chain):
            after = snap.state
            operation = next(k for k, row in snap.envelope["receipts"].items()
                             if row["revision"] == after["revision"])
            root, counts = append_task_events(index, root, counts, before, after,
                                              operation, snap.head)
            before = after
        result = {**manifest, "format": HOT_HISTORY_FORMAT, "root": root,
                  "event_counts": counts}
        return history_manifest(result)

    def _hot_candidate(self, parent, manifest, index, operation):
        root = index.tree_for(manifest["root"])
        raw = canonical({"manifest": manifest, "parent": parent, "operation": operation,
                         "repository": self.prefix, "branch": self.branch})
        tree = self._put_hot_tree([
            {"path": "hot.json", "mode": "100644", "type": "blob",
             "sha": self._put_archive_blob(raw)},
            {"path": "index", "mode": "040000", "type": "tree", "sha": root}])
        obj = self._api("POST", "commits", {"message": "V3 disposable hot transition",
                                            "tree": tree, "parents": [parent]})
        candidate = sha(obj.get("sha"))
        check(isinstance(obj.get("tree"), dict) and obj["tree"].get("sha") == tree
              and isinstance(obj.get("parents"), list) and len(obj["parents"]) == 1
              and isinstance(obj["parents"][0], dict)
              and obj["parents"][0].get("sha") == parent, "hot candidate identity")
        observed = self._hot_at(candidate)
        check(observed.manifest == manifest and observed.root_tree == root
              and observed.operation == operation, "hot candidate readback mismatch")
        return candidate

    def _hot_receipt(self, snap, operation, digest, replayed):
        index = GitTreeIndex(self, snap.manifest["root"], snap.root_tree)
        row = index.get(snap.manifest["root"], "receipt", operation)
        if row is None:
            return None
        check(row["digest"] == digest, "operation ID reused with different payload")
        return Receipt(operation, row["revision"], digest, snap.head, replayed)

    def _advance_hot(self, parent, candidate, operation, digest):
        error = None
        try:
            obj = self._api("PATCH", "refs/heads/" + quote(self.branch, safe="/"),
                            {"sha": candidate, "force": False})
            check(obj.get("ref") == "refs/heads/" + self.branch
                  and isinstance(obj.get("object"), dict)
                  and obj["object"].get("sha") == candidate, "unexpected update response")
        except StoreError as exc:
            error = exc
        try:
            observed_head = self._ref()
            if observed_head == parent:
                if isinstance(error, HttpFailure) and error.status in (401, 403, 404, 409, 422):
                    raise error
                raise UncertainWrite("hot ref update not observed")
            observed = self._hot_at(observed_head)
            receipt = self._hot_receipt(observed, operation, digest, error is not None)
        except HttpFailure as exc:
            if exc is error:
                raise
            raise UncertainWrite("cannot reconcile hot ref update") from None
        except (StoreError, model.LeaseError, KeyError):
            raise UncertainWrite("cannot reconcile hot ref update") from None
        if receipt is not None:
            return receipt
        if isinstance(error, HttpFailure) and error.status in (409, 422):
            raise Conflict("non-fast-forward; reread and recompute")
        raise UncertainWrite("hot receipt not observed; do not replay")

    def initialize_hot(self, expected, operation):
        """Convert one full ledger to a hot root on a disposable ref only.

        Conversion is irreversible through this test API; full-state readers
        fail closed. No artifacts/publications are supported yet.
        """
        self._writable()
        check(isinstance(expected, Snapshot), "full snapshot required")
        validate_envelope(expected.envelope)
        model.ident(operation)
        check(operation.startswith("hot-"), "hot initialization operation prefix")
        check(operation not in expected.envelope["receipts"], "hot operation already used")
        digest = archive_digest(canonical(["initialize-hot", expected.head]))
        current = self._ref()
        if current != expected.head:
            # Do not stage objects against a stale source. Reconcile only
            # an exact initialization receipt on an already hot root.
            try:
                observed = self._hot_at(current)
            except (StoreError, model.LeaseError, KeyError):
                raise Conflict("hot source moved") from None
            receipt = self._hot_receipt(observed, operation, digest, True)
            if receipt is not None:
                return receipt
            raise Conflict("hot source moved")
        check(self._at(current) == expected, "hot source mismatch")
        index = GitTreeIndex(self)
        manifest = indexed_hot_projection(expected, index)
        manifest = self._backfill_hot_history(expected, manifest, index)
        state = copy.deepcopy(manifest["state"])
        state["revision"] += 1
        model.validate(state)
        manifest["state"] = state
        manifest["root"] = index.record_receipt(manifest["root"], operation,
                                                {"revision": state["revision"], "digest": digest})
        candidate = self._hot_candidate(current, manifest, index, operation)
        return self._advance_hot(current, candidate, operation, digest)

    def publish_hot(self, expected, operation, digest, transition):
        """Persist an authorized pure hot transition or return exact receipt.

        Host-only disposable integration; the caller must authorize the
        callback separately. Indexed events commit in the same root.
        """
        self._writable()
        check(isinstance(expected, HotSnapshot), "hot snapshot required")
        model.ident(operation)
        IncrementalIndex._digest(digest)
        current = self.read_hot()
        index = GitTreeIndex(self, current.manifest["root"], current.root_tree)
        match = _REQUEST_OP.fullmatch(operation)
        if match:
            prior = index.get(current.manifest["root"], "request", match.group(1))
            check(prior is None or prior == {"operation": operation},
                  "request ID reused with different payload")
        prior = self._hot_receipt(current, operation, digest, True)
        if prior is not None:
            return prior
        if current != expected:
            raise Conflict("stale hot snapshot; reread and recompute")
        manifest, _, replayed = indexed_hot_transition(
            current.manifest, index, operation, digest, transition)
        check(not replayed, "unexpected hot replay")
        candidate = self._hot_candidate(current.head, manifest, index, operation)
        return self._advance_hot(current.head, candidate, operation, digest)

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
        except (StoreError, model.LeaseError):
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
        check(not any(isinstance(e, dict) and e.get("path") in
                      (LEDGER, "archive-root.json", "archive.json", "hot.json")
                      for e in tree["tree"]), "already initialized")
        envelope = {"schema": 3, "state": copy.deepcopy(initial_state),
                    "receipts": {operation: {"digest": digest, "revision": 0}},
                    "artifacts": {}, "publications": {}}
        return self._advance(current, self._candidate(current, envelope), operation, digest)

    def publish(self, expected, next_state, operation, *, artifact=None, publication=None):
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
        if artifact is not None:
            from . import artifact_gateway as gateway
            gateway.validate_record(artifact, next_state)
            task, run_id, fence = (artifact[k] for k in ("task", "run_id", "fence"))
            model.active(next_state, task, run_id, fence)
            check(artifact["revision"] == next_state["revision"]
                  and artifact["admitted_at"] == next_state["clock"]
                  and artifact["goal_sha"] == next_state["oversight"]["goal_sha"]
                  and next_state["tasks"][task]["checkpoint"]["head"] == artifact["head"],
                  "artifact not bound to proposed checkpoint")
        check(artifact is None or publication is None, "separate artifact and publication operations")
        digest = fingerprint(expected.head, next_state, artifact, publication)
        current = self.read()
        prior = self._record(current, operation, digest, True)
        if prior is not None:
            return prior
        if current.head != expected.head:
            raise Conflict("stale snapshot; reread and recompute")
        check(current.envelope == expected.envelope, "snapshot payload mismatch")
        rows = publication_transition(current.envelope, next_state, operation, publication)
        envelope = copy.deepcopy(current.envelope)
        envelope["publications"] = rows
        envelope["state"] = copy.deepcopy(next_state)
        envelope["receipts"][operation] = {"digest": digest,
                                             "revision": next_state["revision"]}
        if artifact is not None:
            envelope["artifacts"][operation] = copy.deepcopy(artifact)
        if publication is not None and "target" in publication:
            # The queue is frozen until settlement; never admit an intent
            # whose own growth leaves insufficient room for its resolution.
            check(len(canonical(envelope)) + SETTLEMENT_RESERVE <= MAX_LEDGER,
                  "ledger capacity; insufficient publication settlement reserve")
        candidate = self._candidate(current.head, envelope)
        return self._advance(current.head, candidate, operation, digest)
