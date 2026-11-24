"""Offline Work Queue broker admission tests; no real credentials or source writes."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.orchestration import broker as b
from wii_ai_golf.orchestration import github_store as storage
from wii_ai_golf.orchestration import state as model
from test_v3_github_store import FakeGit, BASE, BRANCH, initial, progress, task


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGit()
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.store.bootstrap_test(BASE, initial(), "seed")
        self.now = 1
        self.allow_review = True
        self.reviews = []
        self.tokens = {k: k * 40 for k in ("m", "a", "b", "s")}
        self.credentials = b.Credentials([
            (b.token_digest(self.tokens["m"]), b.Principal("manager", frozenset({"S000"}), True)),
            (b.token_digest(self.tokens["a"]), b.Principal("alpha", frozenset({"S000"}))),
            (b.token_digest(self.tokens["b"]), b.Principal("beta", frozenset({"S000"}))),
            (b.token_digest(self.tokens["s"]), b.Principal("sweeper", frozenset(), False, True)),
        ])
        def review(principal, action, payload, current):
            self.reviews.append((principal.identity, action))
            return self.allow_review
        self.broker = b.Broker(self.store, self.credentials, clock=lambda: self.now,
                               reviewer=review)

    def req(self, who, request_id, action, payload=None):
        return self.broker.request(self.tokens[who], request_id, action,
                                   {} if payload is None else payload)

    def lease(self, who, request_id):
        result = self.req(who, request_id, "acquire")["lease"]
        return {k: result[k] for k in ("task", "run_id", "fence")}

    def test_authentication_and_no_worker_supplied_time_or_role(self):
        with self.assertRaises(b.AdmissionError):
            self.broker.request("x" * 40, "x", "acquire", {})
        for payload in ({"now": 999}, {"role": "S000"}, {"task": model.MANAGER}):
            with self.assertRaises(b.AdmissionError):
                self.req("a", "bad", "acquire", payload)
        self.assertEqual(self.api.patch_count, 1)
        with self.assertRaises(b.AdmissionError):
            self.req("a", "sweep", "sweep")

    def test_manager_first_specialist_concurrency_and_global_visibility(self):
        m = self.lease("m", "manager-1")
        a = self.lease("a", "alpha-1")
        self.assertEqual(m["task"], model.MANAGER)
        self.assertNotEqual(a["task"], model.MANAGER)
        self.assertEqual(self.broker.status(self.tokens["m"])["state"]["tasks"][a["task"]]["status"],
                         "IN_PROGRESS")
        with self.assertRaises(b.AdmissionError):
            self.req("a", "another", "acquire")

    def test_only_authenticated_owner_can_renew_finish_or_manage(self):
        a = self.lease("a", "alpha")
        for action, extra in (("renew", {}), ("finish", {"outcome": "CLOSED", "progress": progress()}),
                              ("manager_pass", {"observed_revision": self.store.read().state["revision"],
                                                "progress": progress()})):
            with self.assertRaises(b.AdmissionError):
                self.req("b", action, action, {**a, **extra})
        with self.assertRaises(b.AdmissionError):
            self.req("a", "fake-manager", "manager_pass",
                     {**a, "observed_revision": self.store.read().state["revision"],
                      "progress": progress()})

    def test_idempotent_receipt_replay_and_conflicting_request(self):
        first = self.req("a", "claim", "acquire")
        patches = self.api.patch_count
        self.now = 2
        second = self.req("a", "claim", "acquire")
        self.assertTrue(second["replayed"])
        self.assertEqual(first["lease"], second["lease"])
        self.assertEqual(self.api.patch_count, patches)
        with self.assertRaises(b.AdmissionError):
            self.req("a", "claim", "sweep")
        self.now = first["lease"]["expires"]
        expired = self.req("a", "claim", "acquire")
        self.assertFalse(expired["lease"]["active"])
        self.assertEqual(self.api.patch_count, patches)

    def test_expired_worker_cannot_finish_and_sweeper_reopens(self):
        a = self.lease("a", "claim")
        self.now = 121
        with self.assertRaises(model.LeaseError):
            self.req("a", "late", "renew", a)
        effective = self.broker.status(self.tokens["m"])
        self.assertEqual(effective["state"]["tasks"][a["task"]]["status"], "OPEN")
        self.req("s", "sweep", "sweep")
        self.assertEqual(self.store.read().state["runs"][a["run_id"]]["outcome"], "EXPIRED")
        again = self.lease("b", "next")
        self.assertEqual(again["task"], a["task"])
        self.assertEqual(again["fence"], a["fence"] + 1)

    def test_checkpoint_review_required_and_heartbeat_without_progress(self):
        a = self.lease("a", "claim")
        self.allow_review = False
        self.now = 2
        self.req("a", "heartbeat", "renew", a)
        count = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("a", "bad-result", "finish",
                     {**a, "outcome": "CLOSED", "progress": progress()})
        self.assertEqual(count, self.api.patch_count)
        self.allow_review = True
        self.req("a", "good-result", "finish",
                 {**a, "outcome": "CLOSED", "progress": progress()})
        self.assertEqual(self.store.read().state["tasks"][a["task"]]["status"], "CLOSED")
        self.assertIn(("alpha", "finish"), self.reviews)

    def test_manager_pass_preserves_active_specialist_and_releases(self):
        m = self.lease("m", "manager")
        a = self.lease("a", "alpha")
        revision = self.store.read().state["revision"]
        before = copy.deepcopy(self.store.read().state["tasks"][a["task"]])
        self.req("m", "review", "manager_pass",
                 {**m, "observed_revision": revision, "progress": progress(),
                  "additions": {"new": task(["new/file.py"])}})
        after = self.store.read().state
        self.assertEqual(after["tasks"][a["task"]], before)
        self.assertEqual(after["tasks"][model.MANAGER]["status"], "OPEN")
        self.assertIn("new", after["tasks"])
        self.assertNotIn(model.MANAGER, self.broker.status(self.tokens["m"])["eligible"])

    def test_clock_rollback_and_review_expiry(self):
        a = self.lease("a", "claim")
        self.now = 0
        with self.assertRaises(b.AdmissionError):
            self.req("a", "rollback", "renew", a)
        self.now = 2
        def slow(*args):
            self.now = 121
            return True
        broker = b.Broker(self.store, self.credentials, clock=lambda: self.now, reviewer=slow)
        with self.assertRaises(model.LeaseError):
            broker.request(self.tokens["a"], "slow", "finish",
                           {**a, "outcome": "CLOSED", "progress": progress()})

    def test_lost_ref_response_and_no_blind_replay(self):
        self.api.lose_response = True
        first = self.req("a", "claim", "acquire")
        self.assertTrue(first["replayed"])
        patches = self.api.patch_count
        self.req("a", "claim", "acquire")
        self.assertEqual(patches, self.api.patch_count)

    def test_no_review_callback_fails_closed(self):
        a = self.lease("a", "claim")
        broker = b.Broker(self.store, self.credentials, clock=lambda: self.now)
        with self.assertRaises(b.AdmissionError):
            broker.request(self.tokens["a"], "result", "finish",
                           {**a, "outcome": "CLOSED", "progress": progress()})


if __name__ == "__main__":
    unittest.main()
