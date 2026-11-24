"""Offline transport contract tests; no credentials or real GitHub writes."""
import base64
import copy
import hashlib
import sys
import threading
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.orchestration import github_store as store
from wii_ai_golf.orchestration import state as model


BRANCH = "orchestration/v3-test-unit"
BASE = "a" * 40


def progress():
    return {"head": None, "next": "resume", "summary": "synthetic", "evidence": []}


def task(paths, resources=()):
    return model.new_task("S000", 0, paths, resources, [], 485,
                          "synthetic", "synthetic acceptance", progress())


def initial():
    return model.initial({
        model.MANAGER: task([], [model.MANAGER_RESOURCE]),
        "a": task(["src/a"]),
        "b": task(["src/b"]),
    }, goal_sha="b" * 40)


class FakeGit:
    """Minimal immutable Git graph with atomic non-forced ref updates."""
    def __init__(self):
        self.branch = BRANCH
        self.head = BASE
        self.trees = {"c" * 40: {"sha": "c" * 40, "tree": [], "truncated": False}}
        self.commits = {BASE: {"sha": BASE, "tree": {"sha": "c" * 40}, "parents": []}}
        self.blobs = {}
        self.lock = threading.Lock()
        self.barrier = None
        self.patch_count = 0
        self.lose_response = False
        self.deny = False
        self.fail_read = False

    def ref(self, head):
        return {"ref": "refs/heads/" + self.branch,
                "object": {"type": "commit", "sha": head}}

    def __call__(self, method, path, data=None):
        endpoint = path.split("/git/", 1)[1]
        if method == "PATCH":
            if self.barrier is not None:
                self.barrier.wait(timeout=5)
            with self.lock:
                self.patch_count += 1
                assert endpoint == "refs/heads/" + self.branch
                assert set(data) == {"sha", "force"} and data["force"] is False
                if self.deny:
                    raise store.HttpFailure(403)
                commit = self.commits[data["sha"]]
                if commit["parents"] != [{"sha": self.head}]:
                    raise store.HttpFailure(422)
                self.head = data["sha"]
                if self.lose_response:
                    self.lose_response = False
                    raise store.StoreError("lost response")
                return self.ref(self.head)
        with self.lock:
            if method == "GET":
                if self.fail_read:
                    raise store.StoreError("unavailable")
                if endpoint == "ref/heads/" + self.branch:
                    return self.ref(self.head)
                kind, key = endpoint.split("/", 1)
                return copy.deepcopy(getattr(self, kind)[key])
            assert method == "POST"
            if endpoint == "blobs":
                raw = base64.b64decode(data["content"])
                key = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                self.blobs[key] = {"sha": key, "encoding": "base64",
                                   "content": data["content"], "size": len(raw)}
                return {"sha": key}
            key = hashlib.sha1(store.canonical(data)).hexdigest()
            if endpoint == "trees":
                assert set(data) == {"tree"}
                obj = {"sha": key, "tree": data["tree"], "truncated": False}
                self.trees[key] = obj
            else:
                assert endpoint == "commits" and len(data["parents"]) == 1
                obj = {"sha": key, "tree": {"sha": data["tree"]},
                       "parents": [{"sha": x} for x in data["parents"]]}
                self.commits[key] = obj
            return copy.deepcopy(obj)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGit()
        self.store = store.GitHubStore(self.api, "owner/repo", BRANCH)
        self.bootstrap = self.store.bootstrap_test(BASE, initial(), "seed")
        self.snap = self.store.read()

    def advance(self, key="a", run="run1"):
        return model.acquire(self.snap.state, key, run, "S000", 1)[0]

    def test_bootstrap_and_no_reset(self):
        self.assertEqual(self.snap.state, initial())
        self.assertEqual(self.bootstrap.revision, 0)
        self.assertTrue(self.store.bootstrap_test(BASE, initial(), "seed").replayed)
        with self.assertRaises(store.StoreError):
            self.store.bootstrap_test(self.snap.head, initial(), "reset")
        self.assertEqual(self.api.patch_count, 1)

    def test_roundtrip_and_replay_after_newer_commit(self):
        next_state = self.advance()
        receipt = self.store.publish(self.snap, next_state, "one")
        self.assertEqual(receipt.revision, 1)
        later = self.store.read()
        final = model.renew(later.state, "a", "run1", 1, 2)
        self.store.publish(later, final, "two")
        replay = self.store.publish(self.snap, next_state, "one")
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.revision, 1)
        self.assertEqual(replay.digest, receipt.digest)
        self.assertEqual(self.api.patch_count, 3)
        self.assertEqual(self.store.read().state, final)
        with self.assertRaises(store.StoreError):
            self.store.publish(self.snap, self.advance("b", "run2"), "one")

    def test_concurrent_sibling_candidates_only_one_wins(self):
        self.api.barrier = threading.Barrier(2)
        def execute(key):
            try:
                return self.store.publish(self.snap, self.advance(key, "run-" + key), key)
            except store.Conflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, ["a", "b"]))
        self.assertEqual(sum(isinstance(x, store.Receipt) for x in results), 1)
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.store.read().state["revision"], 1)
        self.assertEqual(self.api.patch_count, 3)

    def test_lost_response_reconciled_without_second_patch(self):
        self.api.lose_response = True
        receipt = self.store.publish(self.snap, self.advance(), "one")
        self.assertTrue(receipt.replayed)
        self.assertEqual(self.api.patch_count, 2)
        self.assertEqual(self.store.read().state["revision"], 1)

    def test_permission_denied_no_retry(self):
        self.api.deny = True
        with self.assertRaises(store.HttpFailure) as cm:
            self.store.publish(self.snap, self.advance(), "one")
        self.assertEqual(cm.exception.status, 403)
        self.assertEqual(self.api.patch_count, 2)
        self.assertEqual(self.store.read().head, self.snap.head)

    def test_stale_and_forged_snapshot(self):
        fake = copy.deepcopy(self.snap.envelope)
        fake["state"]["tasks"]["a"]["priority"] = 99
        with self.assertRaises(store.StoreError):
            self.store.publish(store.Snapshot(self.snap.head, fake), self.advance(), "fake")
        self.store.publish(self.snap, self.advance(), "one")
        with self.assertRaises(store.Conflict):
            self.store.publish(self.snap, self.advance("b", "run2"), "two")
        self.assertEqual(self.api.patch_count, 2)

    def test_production_read_only_and_invalid_ref(self):
        live = store.GitHubStore(self.api, "owner/repo", store.STATE_REF)
        with self.assertRaises(store.StoreError):
            live.publish(self.snap, self.advance(), "one")
        with self.assertRaises(store.StoreError):
            live.bootstrap_test(BASE, initial(), "seed")
        for branch in ("main", "../main", "orchestration/v3-test-../x", "refs/heads/main"):
            with self.assertRaises(store.StoreError):
                store.GitHubStore(self.api, "owner/repo", branch)
        self.assertEqual(self.api.patch_count, 1)

    def test_corrupt_blob_and_duplicate_json_fail_closed(self):
        key = next(iter(self.api.blobs))
        self.api.blobs[key]["content"] = base64.b64encode(b"{}").decode()
        with self.assertRaises(store.StoreError):
            self.store.read()
        with self.assertRaises(store.StoreError):
            store.decode(b'{"a":1,"a":2}')

    def test_unreconciled_response_stops_without_replay(self):
        api = self.api
        def transport(method, path, data=None):
            if method == "PATCH":
                api(method, path, data)
                api.fail_read = True
                raise store.StoreError("lost response")
            return api(method, path, data)
        adapter = store.GitHubStore(transport, "owner/repo", BRANCH)
        with self.assertRaises(store.UncertainWrite):
            adapter.publish(self.snap, self.advance(), "one")
        self.assertEqual(api.patch_count, 2)
        api.fail_read = False
        self.assertTrue(self.store.publish(self.snap, self.advance(), "one").replayed)
        self.assertEqual(api.patch_count, 2)

    def test_schema_three_rejects_unanchored_hot_state(self):
        invalid = copy.deepcopy(self.snap.envelope)
        invalid["state"], _ = model.hot_projection(invalid["state"])
        with self.assertRaisesRegex(store.StoreError, "full-history model"):
            store.validate_envelope(invalid)
        self.assertEqual(self.api.patch_count, 1)

    def test_receipt_history_tamper(self):
        invalid = copy.deepcopy(self.snap.envelope)
        invalid["receipts"].clear()
        with self.assertRaises(store.StoreError):
            store.validate_envelope(invalid)

    def test_capacity_thresholds_are_exact_and_read_only(self):
        used = len(store.canonical(self.snap.envelope))
        count = self.api.patch_count
        for cap, expected in ((used * 2 + 2048, "normal"),
                              (max(used, used * 100 // 80), "warning"),
                              (used, "critical")):
            # Reserve may independently elevate a warning to critical.
            with patch.object(store, "MAX_LEDGER", cap), patch.object(store, "SETTLEMENT_RESERVE", 0):
                report = store.capacity_report(self.snap)
                self.assertEqual(report["level"], expected)
                self.assertEqual(report["used_bytes"], used)
                self.assertEqual(report["remaining_bytes"], cap - used)
                self.assertEqual(report["receipt_count"], 1)
                self.assertEqual(report["head"], self.snap.head)
        self.assertEqual(self.api.patch_count, count)

    def test_capacity_exhaustion_preserves_tip_and_receipt_replay(self):
        proposal = self.advance()
        receipt = self.store.publish(self.snap, proposal, "one")
        pinned = self.store.read()
        used = len(store.canonical(pinned.envelope))
        count = self.api.patch_count
        renewed = model.renew(pinned.state, "a", "run1", 1, 2)
        with patch.object(store, "MAX_LEDGER", used):
            self.assertEqual(store.capacity_report(pinned)["level"], "critical")
            with self.assertRaisesRegex(store.StoreError, "ledger capacity"):
                self.store.publish(pinned, renewed, "two")
            self.assertEqual(self.store.read().head, pinned.head)
            replay = self.store.publish(self.snap, proposal, "one")
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.digest, receipt.digest)
            self.assertEqual(self.api.patch_count, count)
        self.store.publish(pinned, renewed, "two")
        self.assertEqual(self.store.read().state, renewed)

    def test_archive_roundtrip_preserves_replay_and_fences(self):
        first = self.advance()
        receipt = self.store.publish(self.snap, first, "first")
        old = self.store.read()
        expired = model.sweep(old.state, 121)
        self.store.publish(old, expired, "expire")
        before = self.store.read()
        acquired, _ = model.acquire(before.state, "a", "run2", "S000", 122)
        self.store.publish(before, acquired, "second")
        for now in range(123, 190):
            tip = self.store.read()
            renewed = model.renew(tip.state, "a", "run2", 2, now)
            self.store.publish(tip, renewed, "heartbeat-" + str(now))
        tip = self.store.read()
        manifest, pages = store.archive_snapshot(tip, recent_receipts=2)
        pin = store.archive_digest(store.canonical(manifest))
        self.assertGreaterEqual(len(pages), 3)
        self.assertEqual(len(manifest["hot"]["receipts"]), 2)
        self.assertNotIn("run1", manifest["hot"]["state"]["runs"])
        self.assertIn("run2", manifest["hot"]["state"]["runs"])
        restored = store.restore_archive(manifest, pages,
                                         expected_digest=pin, expected_head=tip.head)
        self.assertEqual(restored, tip)
        self.assertEqual(restored.envelope["receipts"]["first"]["digest"], receipt.digest)
        self.assertEqual(restored.state["tasks"]["a"]["fence"], 2)
        with self.assertRaises(model.LeaseError):
            model.renew(restored.state, "a", "run1", 1, 190)
        self.assertEqual(model.renew(restored.state, "a", "run2", 2, 190),
                         model.renew(tip.state, "a", "run2", 2, 190))
        count = self.api.patch_count
        self.assertTrue(self.store.publish(self.snap, first, "first").replayed)
        self.assertEqual(self.api.patch_count, count)
        self.assertEqual(store.archive_snapshot(tip, recent_receipts=2), (manifest, pages))

    def test_archive_rejects_missing_corrupt_or_unpinned_data(self):
        self.store.publish(self.snap, self.advance(), "first")
        tip = self.store.read()
        manifest, pages = store.archive_snapshot(tip, recent_receipts=1)
        pin = store.archive_digest(store.canonical(manifest))
        key = next(iter(pages))
        for broken in ({}, {**pages, key: b"{}"}, {**pages, "f" * 64: b"{}"}):
            with self.assertRaises(store.StoreError):
                store.restore_archive(manifest, broken, expected_digest=pin,
                                      expected_head=tip.head)
        with self.assertRaises(store.StoreError):
            store.restore_archive(manifest, pages, expected_digest=pin,
                                  expected_head=BASE)
        tampered = copy.deepcopy(manifest)
        tampered["hot"]["state"]["tasks"]["a"]["priority"] += 1
        with self.assertRaises(store.StoreError):
            store.restore_archive(tampered, pages, expected_digest=pin,
                                  expected_head=tip.head)
        with self.assertRaises(store.StoreError):
            store.restore_archive(tampered, pages,
                                  expected_digest=store.archive_digest(store.canonical(tampered)),
                                  expected_head=tip.head)
        # Even with a new pin, noncanonical placement is rejected.
        duplicate = copy.deepcopy(manifest)
        duplicate["pages"].append(duplicate["pages"][0])
        with self.assertRaises(store.StoreError):
            store.restore_archive(duplicate, pages,
                                  expected_digest=store.archive_digest(store.canonical(duplicate)),
                                  expected_head=tip.head)

    def test_archive_no_old_records_and_no_ref_mutation(self):
        count = self.api.patch_count
        manifest, pages = store.archive_snapshot(self.snap)
        self.assertEqual(pages, {})
        self.assertEqual(store.restore_archive(
            manifest, pages, expected_digest=store.archive_digest(store.canonical(manifest)),
            expected_head=self.snap.head), self.snap)
        self.assertEqual(self.api.patch_count, count)
        self.assertEqual(self.store.read().head, self.snap.head)
        for bad in (0, True, 1025):
            with self.assertRaises(store.StoreError):
                store.archive_snapshot(self.snap, recent_receipts=bad)

    def test_archive_index_matches_full_snapshot_with_bounded_reads(self):
        self.store.publish(self.snap, self.advance(), "first")
        for now in range(2, 132):
            tip = self.store.read()
            renewed = model.renew(tip.state, "a", "run1", 1, now)
            self.store.publish(tip, renewed, "heartbeat-" + str(now).zfill(3))
        tip = self.store.read()
        manifest, pages = store.archive_snapshot(tip, recent_receipts=2)
        reads = []
        def fetch(key):
            reads.append(key)
            return pages.get(key)
        index = store.ArchiveIndex(manifest, fetch,
                                  expected_digest=store.archive_digest(store.canonical(manifest)),
                                  expected_head=tip.head)
        self.assertEqual(index.lookup("receipts", "first"), tip.envelope["receipts"]["first"])
        self.assertEqual(len(reads), 1)
        self.assertEqual(index.lookup("runs", "run1"), tip.state["runs"]["run1"])
        self.assertEqual(len(reads), 1)
        self.assertIsNone(index.lookup("receipts", "zzzzz"))
        self.assertEqual(len(reads), 1)
        expected = {k: v for k, v in tip.envelope["receipts"].items()
                    if k.startswith("heartbeat-")}
        self.assertEqual(index.receipt_prefix("heartbeat-"), expected)
        count = len(reads)
        with self.assertRaisesRegex(store.StoreError, "budget"):
            index.receipt_prefix("heartbeat-", max_pages=1)
        self.assertEqual(len(reads), count)
        missing = store.ArchiveIndex(manifest, lambda key: None,
                                    expected_digest=store.archive_digest(store.canonical(manifest)),
                                    expected_head=tip.head)
        with self.assertRaisesRegex(store.StoreError, "missing or corrupt"):
            missing.receipt_prefix("heartbeat-")

    def test_stage_archive_objects_without_ref_promotion(self):
        self.store.publish(self.snap, self.advance(), "first")
        tip = self.store.read()
        count = self.api.patch_count
        pin = self.store.stage_archive(tip, recent_receipts=1)
        self.assertEqual(pin["source_head"], tip.head)
        self.assertNotEqual(pin["candidate"], tip.head)
        self.assertEqual(self.api.patch_count, count)
        self.assertEqual(self.store.read(), tip)
        index = self.store.open_archive_index(pin["candidate"],
                    expected_digest=pin["manifest_digest"], expected_head=pin["source_head"])
        self.assertEqual(index.lookup("receipts", "seed"), tip.envelope["receipts"]["seed"])
        self.assertEqual(index.lookup("receipts", "first"), tip.envelope["receipts"]["first"])
        with self.assertRaises(store.StoreError):
            self.store.open_archive_index(pin["candidate"],
                        expected_digest="0" * 64, expected_head=tip.head)
        with self.assertRaises(store.StoreError):
            self.store.open_archive_index(pin["candidate"],
                        expected_digest=pin["manifest_digest"], expected_head=BASE)
        with self.assertRaises(store.StoreError):
            self.store._at(pin["candidate"])
        live = store.GitHubStore(self.api, "owner/repo", store.STATE_REF)
        with self.assertRaises(store.StoreError):
            live.stage_archive(tip)
        with self.assertRaises(store.Conflict):
            self.store.stage_archive(self.snap)
        self.assertEqual(self.api.patch_count, count)
        candidate_tree = self.api.commits[pin["candidate"]]["tree"]["sha"]
        self.api.trees[candidate_tree]["tree"] = [
            row for row in self.api.trees[candidate_tree]["tree"]
            if row["path"] == "archive.json"]
        with self.assertRaises(store.StoreError):
            self.store.open_archive_index(pin["candidate"],
                        expected_digest=pin["manifest_digest"], expected_head=tip.head)

    def test_archive_checkpoint_preserves_state_history_and_replay(self):
        proposal = self.advance()
        first = self.store.publish(self.snap, proposal, "first")
        source = self.store.read()
        self.api.lose_response = True
        count = self.api.patch_count
        receipt = self.store.archive_checkpoint(source, "archive-one", recent_receipts=1)
        self.assertTrue(receipt.replayed)
        self.assertEqual(self.api.patch_count, count + 1)
        reopened = store.GitHubStore(self.api, "owner/repo", BRANCH)
        tip = reopened.read()
        expected_state = source.state
        expected_state["revision"] += 1
        self.assertEqual(tip.state, expected_state)
        self.assertEqual(tip.envelope["receipts"]["first"]["digest"], first.digest)
        self.assertEqual(tip.envelope["receipts"]["archive-one"]["revision"], receipt.revision)
        self.assertTrue(reopened.archive_checkpoint(source, "archive-one",
                                                     recent_receipts=1).replayed)
        self.assertTrue(reopened.publish(self.snap, proposal, "first").replayed)
        with self.assertRaises(store.StoreError):
            reopened.archive_checkpoint(source, "archive-one", recent_receipts=2)
        with self.assertRaisesRegex(store.StoreError, "already initialized"):
            reopened.bootstrap_test(tip.head, initial(), "reset")
        self.assertEqual(self.api.patch_count, count + 1)
        history = reopened.task_history("a")
        self.assertIn("claimed", [event["kind"] for event in history["events"]])
        renewed = model.renew(tip.state, "a", "run1", 1, 2)
        reopened.publish(tip, renewed, "renew")
        self.assertEqual(reopened.read().state, renewed)
        self.assertTrue(reopened.archive_checkpoint(source, "archive-one",
                                                     recent_receipts=1).replayed)
        self.assertTrue(reopened.publish(self.snap, proposal, "first").replayed)
        self.assertIn("renewed", [e["kind"] for e in reopened.task_history("a")["events"]])
        self.assertEqual(self.api.patch_count, count + 2)
        with self.assertRaises(model.LeaseError):
            model.renew(reopened.read().state, "a", "run1", 0, 3)

    def test_archive_checkpoint_competes_with_ordinary_write(self):
        self.store.publish(self.snap, self.advance(), "first")
        tip = self.store.read()
        renewed = model.renew(tip.state, "a", "run1", 1, 2)
        self.api.barrier = threading.Barrier(2)
        def run(which):
            try:
                if which == "archive":
                    return self.store.archive_checkpoint(tip, "archive-race", recent_receipts=1)
                return self.store.publish(tip, renewed, "renew-race")
            except store.Conflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ("archive", "renew")))
        self.api.barrier = None
        self.assertEqual(sum(isinstance(r, store.Receipt) for r in results), 1)
        self.assertEqual(results.count("conflict"), 1)
        after = self.store.read()
        self.assertEqual(after.state["revision"], tip.state["revision"] + 1)
        self.assertEqual(after.state["tasks"]["a"]["fence"], 1)
        self.assertIn("first", after.envelope["receipts"])
        self.assertEqual(sum(k in after.envelope["receipts"]
                             for k in ("archive-race", "renew-race")), 1)

    def test_archive_checkpoint_rejects_production_and_corrupt_root(self):
        live = store.GitHubStore(self.api, "owner/repo", store.STATE_REF)
        with self.assertRaises(store.StoreError):
            live.archive_checkpoint(self.snap, "archive-no")
        self.store.publish(self.snap, self.advance(), "first")
        tip = self.store.read()
        with self.assertRaises(store.Conflict):
            self.store.archive_checkpoint(self.snap, "archive-stale")
        self.store.archive_checkpoint(tip, "archive-one", recent_receipts=1)
        with self.assertRaisesRegex(store.StoreError, "test-only"):
            live._at(self.api.head)
        root_tree = self.api.commits[self.api.head]["tree"]["sha"]
        for entry in self.api.trees[root_tree]["tree"]:
            if entry["path"] != "archive-root.json":
                self.api.blobs[entry["sha"]]["content"] = base64.b64encode(b"{}").decode()
                break
        with self.assertRaises(store.StoreError):
            self.store.read()


class IncrementalIndexTests(unittest.TestCase):
    def setUp(self):
        self.nodes = {}
        self.reads = 0
        self.writes = 0
        def read(key):
            self.reads += 1
            return self.nodes.get(key)
        def write(key, raw):
            self.writes += 1
            self.assertTrue(key not in self.nodes or self.nodes[key] == raw)
            self.nodes[key] = raw
        self.index = store.IncrementalIndex(read, write)

    def test_immutable_roots_and_bounded_key_io(self):
        root = None
        for i in range(300):
            key = "run-" + str(i)
            before = self.reads, self.writes
            root = self.index.put(root, "run", key, {"n": i})
            self.assertLessEqual(self.reads - before[0], 65)
            self.assertLessEqual(self.writes - before[1], 65)
            if i == 0:
                old = root
        self.assertEqual(self.index.get(old, "run", "run-0"), {"n": 0})
        self.assertIsNone(self.index.get(old, "run", "run-299"))
        for i in range(300):
            before = self.reads
            self.assertEqual(self.index.get(root, "run", "run-" + str(i)), {"n": i})
            self.assertLessEqual(self.reads - before, 65)
        before = self.writes
        self.assertEqual(self.index.put(root, "run", "run-0", {"n": 0}), root)
        self.assertEqual(self.writes, before)
        with self.assertRaises(store.StoreError):
            self.index.put(root, "run", "run-0", {"n": 1})
        raw = self.nodes.pop(root)
        with self.assertRaisesRegex(store.StoreError, "missing or corrupt"):
            self.index.get(root, "run", "run-0")
        self.nodes[root] = raw + b" "
        with self.assertRaisesRegex(store.StoreError, "missing or corrupt"):
            self.index.get(root, "run", "run-0")

    def test_hot_proposals_match_full_model_and_preserve_request_identity(self):
        full = initial()
        envelope = {"schema": 3, "state": full,
                    "receipts": {"seed": {"revision": 0, "digest": "a" * 64}},
                    "artifacts": {}, "publications": {}}
        manifest = store.indexed_hot_projection(store.Snapshot(BASE, envelope), self.index)
        first = manifest
        cold = {}
        receipts = {}
        def advance(action, fn, expected):
            nonlocal manifest
            operation = "op-" + hashlib.sha256(action.encode()).hexdigest()[:32] + "-" + "b" * 64
            digest = hashlib.sha256(("digest-" + action).encode()).hexdigest()
            prior = manifest
            manifest, receipt, replayed = store.indexed_hot_transition(
                manifest, self.index, operation, digest, fn)
            self.assertFalse(replayed)
            receipts[operation] = receipt
            self.assertEqual(receipt["revision"], expected["revision"])
            for key, row in expected["runs"].items():
                if row["status"] == "CLOSED":
                    cold[key] = row
                    self.assertEqual(self.index.get(manifest["root"], "run", key), row)
            self.assertEqual(model.restore_hot(manifest["state"], cold), expected)
            self.assertIsNone(self.index.get(prior["root"], "receipt", operation))
            before = self.writes
            same, historical, replayed = store.indexed_hot_transition(
                manifest, self.index, operation, digest, None)
            self.assertEqual(same, manifest)
            self.assertEqual(historical, receipt)
            self.assertTrue(replayed)
            self.assertEqual(self.writes, before)
            with self.assertRaisesRegex(store.StoreError, "request ID reused"):
                store.indexed_hot_transition(manifest, self.index,
                                             operation[:-64] + "c" * 64, digest, None)
        for i in range(30):
            now = 200 * i + 1
            run = "run-" + str(i)
            full, fence = model.acquire(full, "a", run, "S000", now)
            advance("acquire-" + run, lambda state, exists:
                    model.acquire(state, "a", run, "S000", now,
                                  cold_run_exists=exists)[0], full)
            full = model.finish(full, "a", run, fence, now + 1, "OPEN", progress())
            advance("finish-" + run, lambda state, exists:
                    model.finish(state, "a", run, fence, now + 1, "OPEN", progress()), full)
            self.assertEqual(manifest["state"]["runs"], {})
        self.assertEqual(len(cold), 30)
        self.assertEqual(len(receipts), 60)
        self.assertEqual(first["state"]["revision"], 0)
        for key, receipt in receipts.items():
            self.assertEqual(self.index.get(manifest["root"], "receipt", key), receipt)
        with self.assertRaises(model.LeaseError):
            store.indexed_hot_transition(manifest, self.index, "new-attempt", "d" * 64,
                lambda state, exists: model.acquire(state, "a", "run-0", "S000",
                                                    6001, cold_run_exists=exists)[0])


if __name__ == "__main__":
    unittest.main()
