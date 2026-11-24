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


if __name__ == "__main__":
    unittest.main()
