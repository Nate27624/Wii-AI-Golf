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
                      (LEDGER, "archive-root.json", "archive.json")
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
