"""Offline Work Queue broker admission tests; no real credentials or source writes."""
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
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
        self.tokens = {k: k * 40 for k in ("m", "a", "b", "s", "r")}
        self.credentials = b.Credentials([
            (b.token_digest(self.tokens["m"]), b.Principal("manager", frozenset({"S000"}), True)),
            (b.token_digest(self.tokens["a"]), b.Principal("alpha", frozenset({"S000"}))),
            (b.token_digest(self.tokens["b"]), b.Principal("beta", frozenset({"S000"}))),
            (b.token_digest(self.tokens["s"]), b.Principal("sweeper", frozenset(), False, True)),
            (b.token_digest(self.tokens["r"]), b.Principal("operator-read", frozenset(), read_only=True)),
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


    def test_manager_always_displayed_first_and_history_is_durable(self):
        m = self.lease("m", "manager")
        a = self.lease("a", "alpha")
        self.assertEqual(self.broker.status(self.tokens["a"])["task_order"][0], model.MANAGER)
        self.assertNotIn(model.MANAGER, self.broker.status(self.tokens["a"])["eligible"])
        self.now = 2
        self.req("a", "renew", "renew", a)
        self.req("a", "renew", "renew", a)
        self.now = 122
        self.assertEqual(self.broker.status(self.tokens["m"])["task_order"][0], model.MANAGER)
        self.req("s", "sweep", "sweep")
        count = self.api.patch_count
        events = self.broker.task_history(self.tokens["m"], a["task"])["events"]
        kinds = [x["kind"] for x in events]
        for kind in ("created", "claimed", "renewed", "expired"):
            self.assertEqual(kinds.count(kind), 1)
        self.assertEqual(self.api.patch_count, count)
        self.assertTrue(all(x["task"] == a["task"] for x in events))
        with self.assertRaises(b.AdmissionError):
            self.broker.task_history("x" * 40, a["task"])

    def test_history_pagination_and_invalid_cursor(self):
        a = self.lease("a", "alpha")
        self.now = 2
        self.req("a", "renew", "renew", a)
        first = self.broker.task_history(self.tokens["m"], a["task"], limit=1)
        self.assertEqual(first["next_cursor"], 1)
        second = self.broker.task_history(self.tokens["m"], a["task"], limit=1,
                                          cursor=first["next_cursor"])
        self.assertEqual(second["next_cursor"], 0)
        third = self.broker.task_history(self.tokens["m"], a["task"], limit=1, cursor=0)
        self.assertIsNone(third["next_cursor"])
        self.assertEqual([x["kind"] for x in third["events"]], ["created"])
        with self.assertRaises(storage.StoreError):
            self.broker.task_history(self.tokens["m"], a["task"], cursor=999)

    def test_read_only_principal_cannot_dispatch_or_mutate(self):
        a = self.lease("a", "alpha")
        count = self.api.patch_count
        view = self.broker.status(self.tokens["r"])
        self.assertEqual(view["eligible"], [])
        self.assertFalse(view["manager_authorized"])
        self.assertIn(a["task"], view["state"]["tasks"])
        self.assertTrue(self.broker.task_history(self.tokens["r"], a["task"])["events"])
        capacity = self.broker.capacity(self.tokens["r"])
        self.assertEqual(capacity["head"], view["head"])
        self.assertEqual(capacity["used_bytes"] + capacity["remaining_bytes"],
                         capacity["limit_bytes"])
        with self.assertRaises(b.AdmissionError):
            self.broker.capacity("x" * 40)
        for action in ("acquire", "renew", "finish", "manager_pass", "sweep",
                       "accept_artifact", "prepare_publication", "resolve_publication"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(b.AdmissionError, "read-only"):
                    self.req("r", "denied", action, {})
        self.assertEqual(count, self.api.patch_count)
        for principal in (
            b.Principal("bad", frozenset({"S000"}), read_only=True),
            b.Principal("bad", frozenset(), maintenance=True, read_only=True),
            b.Principal("bad", frozenset({"S000"}), manager=True, read_only=True),
        ):
            with self.assertRaises(b.AdmissionError):
                b.Credentials([(b.token_digest("z" * 40), principal)])

    def test_slow_history_does_not_block_heartbeat(self):
        a = self.lease("a", "alpha")
        old_head = self.store.read().head
        entered, release = threading.Event(), threading.Event()
        original = self.store._api

        def delay_history(method, endpoint, payload=None):
            # Suspend only the history thread after it pins its immutable tip.
            if (threading.current_thread().name.startswith("history-reader")
                    and method == "GET" and endpoint == "commits/" + old_head):
                if not entered.is_set():
                    entered.set()
                    if not release.wait(timeout=10):
                        raise AssertionError("history release not signaled")
            return original(method, endpoint, payload)

        self.store._api = delay_history
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="history-reader") as reader:
            with ThreadPoolExecutor(max_workers=1) as writer:
                history = reader.submit(self.broker.task_history, self.tokens["r"], a["task"])
                try:
                    self.assertTrue(entered.wait(timeout=5))
                    self.now = 2
                    heartbeat = writer.submit(self.req, "a", "heartbeat", "renew", a)
                    receipt = heartbeat.result(timeout=5)
                    self.assertNotEqual(receipt["head"], old_head)
                finally:
                    release.set()
                result = history.result(timeout=5)
        self.assertEqual(result["head"], old_head)
        self.assertNotIn("renewed", [event["kind"] for event in result["events"]])
        latest = self.broker.task_history(self.tokens["r"], a["task"])
        self.assertIn("renewed", [event["kind"] for event in latest["events"]])



    def test_operator_endpoint_fixed_project_and_no_io_on_invalid_requests(self):
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        root = "/v3/projects/wii-golf"
        read_auth = "Bearer " + self.tokens["r"]
        original = self.store.read
        calls = []
        def forbidden_read():
            calls.append(True)
            raise AssertionError("invalid request reached store")
        self.store.read = forbidden_read
        try:
            for method, path, auth, expected in (
                ("POST", root + "/status", read_auth, 405),
                ("GET", root + "/status", None, 401),
                ("GET", root + "/status", "Bearer " + "x" * 40, 401),
                ("GET", root + "/status", "Bearer " + self.tokens["m"], 403),
                ("GET", root + "/status", "Bearer " + self.tokens["a"], 403),
                ("GET", "/v3/projects/other/status", read_auth, 404),
                ("GET", root + "/status?x=1", read_auth, 404),
                ("GET", root + "/tasks/%2e%2e/history", read_auth, 404),
                ("GET", root + "/tasks/A/history?limit=0", read_auth, 400),
                ("GET", root + "/tasks/A/history?limit=51", read_auth, 400),
                ("GET", root + "/tasks/A/history?limit=1&limit=2", read_auth, 400),
                ("GET", root + "/tasks/A/history?cursor=-1", read_auth, 400),
                ("GET", root + "/tasks/A/history?cursor=9007199254740992", read_auth, 400),
                ("GET", root + "/tasks/A/history?repo=foreign", read_auth, 400),
                ("GET", root + "/tasks/A/history?limit=%31", read_auth, 400),
                ("GET", root + "/tasks/A/history?", read_auth, 400),
                ("GET", root + "/status\n", read_auth, 400),
                ("GET", root + "/" + "a" * 513, read_auth, 400),
            ):
                with self.subTest(method=method, path=path, expected=expected):
                    status, headers, body = endpoint.handle(method, path, auth)
                    self.assertEqual(status, expected)
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertEqual(int(headers["Content-Length"]), len(body))
                    self.assertEqual(set(json.loads(body)), {"error"})
                    self.assertNotIn(self.tokens["r"].encode(), body)
            self.assertEqual(calls, [])
        finally:
            self.store.read = original
        self.assertEqual(self.api.patch_count, 1)

    def test_operator_endpoint_status_history_capacity_no_mutation(self):
        lease = self.lease("a", "alpha")
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        root = "/v3/projects/wii-golf"
        auth = "Bearer " + self.tokens["r"]
        head = self.store.read().head
        patches = self.api.patch_count
        def get(route, expected=200):
            status, headers, body = endpoint.handle("GET", root + route, auth)
            self.assertEqual(status, expected)
            self.assertEqual(headers["Content-Type"], "application/json")
            return json.loads(body)
        view = get("/status")
        self.assertEqual(view["head"], head)
        self.assertEqual(view["task_order"][0], model.MANAGER)
        self.assertEqual(view["eligible"], [])
        self.assertFalse(view["manager_authorized"])
        self.assertEqual(view["state"]["version"], 2)
        task = view["state"]["tasks"][lease["task"]]
        self.assertEqual(task["run"], lease["run_id"])
        self.assertNotIn("objective", task)
        self.assertNotIn("paths", task)
        self.assertEqual(set(task["checkpoint"]), {"head", "evidence"})
        self.assertNotIn("accepted_artifacts", view)
        capacity = get("/capacity")
        self.assertEqual(capacity["head"], head)
        page = get("/tasks/" + lease["task"] + "/history?limit=1")
        self.assertEqual(page["head"], head)
        self.assertEqual(page["next_cursor"], 0)
        for event in page["events"]:
            self.assertEqual(event["task"], lease["task"])
            if event["kind"] == "task_changed":
                self.assertEqual(set(event["data"]["after"]), {"status"})
        page2 = get("/tasks/" + lease["task"] + "/history?cursor=0&limit=1")
        self.assertIsNone(page2["next_cursor"])
        self.assertEqual(page2["events"][0]["data"], {"status": "OPEN"})
        get("/tasks/nonexistent/history", 404)
        get("/tasks/" + lease["task"] + "/history?cursor=999", 409)
        self.now = 121
        preview = get("/status")
        self.assertEqual(preview["state"]["tasks"][lease["task"]]["status"], "OPEN")
        self.assertEqual(preview["state"]["runs"], {})
        self.assertEqual(self.store.read().head, head)
        self.assertEqual(self.api.patch_count, patches)

    def test_operator_endpoint_unavailable_and_oversized_are_sanitized(self):
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        auth = "Bearer " + self.tokens["r"]
        def fail(token):
            raise RuntimeError("PRIVATE SYNTHETIC DIAGNOSTIC")
        self.broker.capacity = fail
        status, _, body = endpoint.handle("GET", "/v3/projects/wii-golf/capacity", auth)
        self.assertEqual(status, 503)
        self.assertNotIn(b"PRIVATE", body)
        status, _, body = endpoint._reply(200, {"data": "x" * b._READ_LIMIT})
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {"error": "response unavailable"})
        self.assertEqual(self.api.patch_count, 1)



class HotBrokerTests(unittest.TestCase):
    """Exercise real broker admission against disposable persistent roots."""
    def setUp(self):
        self.api = FakeGit()
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.store.bootstrap_test(BASE, initial(), "seed")
        self.store.initialize_hot(self.store.read(), "hot-init")
        self.now = 1
        self.allow_review = True
        self.tokens = {k: k * 40 for k in ("m", "a", "b", "s", "r")}
        self.credentials = b.Credentials([
            (b.token_digest(self.tokens["m"]), b.Principal("manager", frozenset({"S000"}), True)),
            (b.token_digest(self.tokens["a"]), b.Principal("alpha", frozenset({"S000"}))),
            (b.token_digest(self.tokens["b"]), b.Principal("beta", frozenset({"S000"}))),
            (b.token_digest(self.tokens["s"]), b.Principal("sweeper", frozenset(), False, True)),
            (b.token_digest(self.tokens["r"]), b.Principal("operator-read", frozenset(), read_only=True)),
        ])
        self.reopen()

    def reopen(self):
        self.store = storage.GitHubStore(self.api, "owner/repo", BRANCH)
        self.broker = b.Broker(self.store, self.credentials, hot=True,
                               clock=lambda: self.now,
                               reviewer=lambda *args: self.allow_review)

    def req(self, who, request_id, action, payload=None):
        return self.broker.request(self.tokens[who], request_id, action,
                                   {} if payload is None else payload)

    def claim(self, who, request_id):
        lease = self.req(who, request_id, "acquire")["lease"]
        return {k: lease[k] for k in ("task", "run_id", "fence")}

    def test_reopen_terminal_replay_and_conflicting_request(self):
        a = self.claim("a", "claim")
        self.now = 121
        self.req("s", "expire", "sweep")
        self.reopen()
        self.assertNotIn(a["run_id"], self.store.read_hot().state["runs"])
        patches = self.api.patch_count
        replay = self.req("a", "claim", "acquire")
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["lease"]["active"])
        self.assertEqual(replay["lease"]["fence"], a["fence"])
        self.assertEqual(self.api.patch_count, patches)
        with self.assertRaises(b.AdmissionError):
            self.req("a", "claim", "sweep")
        with self.assertRaises(model.LeaseError):
            self.req("a", "late", "renew", a)
        next_lease = self.claim("b", "next")
        self.assertEqual(next_lease["task"], a["task"])
        self.assertEqual(next_lease["fence"], a["fence"] + 1)

    def test_fenced_review_and_manager_pass_share_admission(self):
        manager = self.claim("m", "manager")
        self.assertEqual(manager["task"], model.MANAGER)
        a = self.claim("a", "alpha")
        with self.assertRaises(b.AdmissionError):
            self.req("b", "steal", "renew", a)
        self.now = 2
        self.req("a", "heartbeat", "renew", a)
        self.allow_review = False
        patches = self.api.patch_count
        with self.assertRaises(b.AdmissionError):
            self.req("a", "finish", "finish", {**a, "outcome": "CLOSED",
                                                "progress": progress()})
        self.assertEqual(self.api.patch_count, patches)
        self.allow_review = True
        revision = self.store.read_hot().state["revision"]
        self.req("m", "review", "manager_pass", {**manager,
                 "observed_revision": revision, "progress": progress()})
        self.req("a", "finish", "finish", {**a, "outcome": "CLOSED",
                                            "progress": progress()})
        self.reopen()
        self.assertTrue(self.req("a", "finish", "finish", {**a,
                     "outcome": "CLOSED", "progress": progress()})["replayed"])
        self.assertEqual(self.store.read_hot().state["tasks"][a["task"]]["status"], "CLOSED")

    def test_unsupported_paths_and_read_only_fail_before_mutation(self):
        patches = self.api.patch_count
        for action in ("accept_artifact", "prepare_publication", "resolve_publication"):
            with self.assertRaises(b.AdmissionError):
                self.req("a", "unsupported", action)
        with self.assertRaises(b.AdmissionError):
            self.req("r", "denied", "acquire")
        view = self.broker.status(self.tokens["r"])
        self.assertEqual(view["state"]["version"], 3)
        self.assertEqual(view["eligible"], [])
        self.assertEqual(view["task_order"][0], model.MANAGER)
        endpoint = b.OperatorReadEndpoint("wii-golf", self.broker)
        for route in ("status", "capacity", "tasks/a/history"):
            code, _, body = endpoint.handle("GET", "/v3/projects/wii-golf/" + route,
                                            "Bearer " + self.tokens["r"])
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(body), {"error": "response unavailable"})
        self.assertEqual(self.api.patch_count, patches)

    def test_lost_response_replay_is_pinned_and_does_not_regrant(self):
        self.api.lose_response = True
        first = self.req("a", "claim", "acquire")
        self.assertTrue(first["lease"]["active"])
        self.reopen()
        self.now = first["lease"]["expires"]
        patches = self.api.patch_count
        second = self.req("a", "claim", "acquire")
        self.assertTrue(second["replayed"])
        self.assertFalse(second["lease"]["active"])
        self.assertEqual(self.api.patch_count, patches)


if __name__ == "__main__":
    unittest.main()
