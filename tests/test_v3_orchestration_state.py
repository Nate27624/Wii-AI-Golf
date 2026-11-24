import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.orchestration import state as v3


def progress(label="resume"):
    return {"head": "a" * 40, "next": label, "summary": "Synthetic checkpoint",
            "evidence": ["test-1"]}


def task(paths, resources=(), deps=(), priority=0, role="S000"):
    return v3.new_task(role, priority, paths, resources, deps, 485,
                       "Offline test", "Synthetic acceptance", progress())


GOAL = "b" * 40


def queue(tasks, holds=None):
    return v3.initial({v3.MANAGER: task([], [v3.MANAGER_RESOURCE]), **tasks},
                      holds, goal_sha=GOAL)


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.s = queue({
            "a": task(["src/alpha.py"], ["cpu"]),
            "b": task(["src/ALPHA.py"]),
            "c": task(["src/beta.py"], ["cpu"]),
            "d": task(["docs/x"], priority=1),
            "e": task(["docs/y"], deps=["a"]),
            "f": task(["tests/z"], role="S002"),
        })

    def acquire(self, key="a", run="run1", now=10):
        return v3.acquire(self.s, key, run, "S000", now)

    def test_acquire_copy_and_json(self):
        before = copy.deepcopy(self.s)
        s, f = self.acquire()
        self.assertEqual(self.s, before)
        self.assertEqual(f, 1)
        self.assertEqual(s["runs"]["run1"]["expires"], 130)
        self.assertEqual(s["tasks"]["a"]["status"], "IN_PROGRESS")
        self.assertEqual(v3.validate(json.loads(json.dumps(s))), s)

    def test_heartbeat_without_commit_extends(self):
        s, f = self.acquire()
        s = v3.renew(s, "a", "run1", f, 129)
        self.assertEqual(s["runs"]["run1"]["expires"], 249)
        self.assertEqual(v3.sweep(s, 248)["tasks"]["a"]["status"], "IN_PROGRESS")
        self.assertEqual(v3.sweep(s, 249)["tasks"]["a"]["status"], "OPEN")

    def test_checkpoint_survives_timeout(self):
        s, f = self.acquire()
        s = v3.renew(s, "a", "run1", f, 50, progress("next action"))
        s = v3.sweep(s, 170)
        self.assertEqual(s["runs"]["run1"]["outcome"], "EXPIRED")
        self.assertEqual(s["tasks"]["a"]["checkpoint"], progress("next action"))
        s, g = v3.acquire(s, "a", "run2", "S000", 170)
        self.assertEqual(g, f + 1)
        self.assertEqual(s["tasks"]["a"]["checkpoint"], progress("next action"))
        with self.assertRaises(v3.LeaseError):
            v3.finish(s, "a", "run1", f, 171, "CLOSED", progress())

    def test_expiry_at_boundary_and_run_reuse(self):
        s, f = self.acquire()
        for call in (
            lambda: v3.renew(s, "a", "run1", f, 130),
            lambda: v3.finish(s, "a", "run1", f, 130, "CLOSED", progress()),
            lambda: v3.acquire(s, "a", "run1", "S000", 130),
        ):
            with self.assertRaises(v3.LeaseError):
                call()
        s, _ = v3.acquire(s, "b", "run2", "S000", 130)
        self.assertEqual(s["runs"]["run1"]["outcome"], "EXPIRED")

    def test_duplicate_acquire_does_not_renew(self):
        s, f = self.acquire()
        q, g = v3.acquire(s, "a", "run1", "S000", 20)
        self.assertEqual(f, g)
        self.assertEqual(q["runs"]["run1"]["expires"], 130)

    def test_overlap_and_dependency(self):
        s, f = self.acquire()
        for key in ("a", "b", "c", "e", "f"):
            with self.subTest(key=key), self.assertRaises(v3.LeaseError):
                v3.acquire(s, key, "run2", "S000", 11)
        s, _ = v3.acquire(s, "d", "run2", "S000", 11)
        s = v3.finish(s, "a", "run1", f, 12, "CLOSED", progress())
        s, _ = v3.acquire(s, "e", "run3", "S000", 13)
        self.assertEqual(s["tasks"]["e"]["status"], "IN_PROGRESS")

    def test_terminal_retry_and_conflict(self):
        s, f = self.acquire()
        q = v3.finish(s, "a", "run1", f, 11, "OPEN", progress("later"))
        q, g = v3.acquire(q, "a", "run2", "S000", 12)
        self.assertEqual(g, f + 1)
        self.assertEqual(v3.finish(q, "a", "run1", f, 13, "OPEN",
                                   progress("later")), q)
        for outcome, p in (("CLOSED", progress("later")), ("OPEN", progress())):
            with self.assertRaises(v3.LeaseError):
                v3.finish(q, "a", "run1", f, 13, outcome, p)

    def test_blocked_and_parked_not_reopened_by_time(self):
        for outcome in ("BLOCKED", "PARKED", "CLOSED"):
            s, f = self.acquire()
            s = v3.finish(s, "a", "run1", f, 11, outcome, progress())
            s = v3.sweep(s, 999)
            self.assertEqual(s["tasks"]["a"]["status"], outcome)
            self.assertNotIn("a", v3.candidates(s, "S000", 999))
            self.assertIn("b", v3.candidates(s, "S000", 999))

    def test_legacy_hold_prefix_and_order(self):
        s = v3.initial(self.s["tasks"], {"legacy": {"paths": ["SRC"], "resources": []}}, goal_sha=GOAL)
        self.assertEqual(v3.candidates(s, "S000", 1), [v3.MANAGER, "d"])
        self.assertEqual(v3.candidates(self.s, "S000", 1), [v3.MANAGER, "a", "b", "c", "d"])
        self.assertEqual(v3.candidates(s, "S002", 1), ["f"])

    def test_path_rejects_windows_alias_and_traversal(self):
        for bad in ("../foo", "a/../foo", "C:/x", "/foo", "a\\b",
                    "a//b", "a/CON.txt", "a/thing.", ".git/config", "a/b c"):
            with self.subTest(bad=bad), self.assertRaises(v3.LeaseError):
                queue({"bad": task([bad])})
        self.assertTrue(v3.overlap("Src", "src/a.py"))
        self.assertFalse(v3.overlap("src/a", "src/ab"))

    def test_malformed_state(self):
        s, _ = self.acquire()
        for change in (
            lambda q: q.update(version=True),
            lambda q: q.update(clock=-1),
            lambda q: q["runs"]["run1"].update(fence=2),
            lambda q: q["runs"]["run1"].update(expires=999),
            lambda q: q["tasks"]["a"].update(run=None),
            lambda q: q["tasks"]["a"].update(dependencies=["e"]),
            lambda q: q["tasks"]["a"]["checkpoint"].update(raw_ram="bad"),
            lambda q: q["runs"].clear(),
        ):
            q = copy.deepcopy(s)
            change(q)
            with self.assertRaises(v3.LeaseError):
                v3.validate(q)

    def test_clock_rollback_and_wrong_token(self):
        s, f = self.acquire()
        for now, token in ((9, f), (11, True), (11, f + 1)):
            with self.assertRaises(v3.LeaseError):
                v3.renew(s, "a", "run1", token, now)
        self.assertEqual(s["tasks"]["a"]["checkpoint"], progress())


    def test_manager_singleton_scope_and_goal_pin(self):
        for change in (
            lambda s: s["tasks"].pop(v3.MANAGER),
            lambda s: s["tasks"][v3.MANAGER].update(status="CLOSED"),
            lambda s: s["tasks"][v3.MANAGER].update(role="S002"),
            lambda s: s["tasks"]["a"].update(resources=["WORK-QUEUE-METADATA"]),
            lambda s: s["tasks"]["a"].update(dependencies=[v3.MANAGER]),
            lambda s: s["oversight"].update(goal_sha="bad"),
        ):
            s = copy.deepcopy(self.s)
            change(s)
            with self.assertRaises(v3.LeaseError):
                v3.validate(s)

    def test_manager_first_concurrent_and_no_spin(self):
        s = self.s
        self.assertEqual(v3.dispatch_candidates(s, ["S000", "S002"], 1)[0], v3.MANAGER)
        s, m = v3.acquire(s, v3.MANAGER, "mgr", "S000", 1)
        s, f = v3.acquire(s, "a", "worker", "S000", 2)
        self.assertNotIn(v3.MANAGER, v3.candidates(s, "S000", 2))
        s = v3.manager_pass(s, "mgr", m, 3, s["revision"], progress("reviewed"))
        self.assertEqual(s["tasks"][v3.MANAGER]["status"], "OPEN")
        self.assertNotIn(v3.MANAGER, v3.candidates(s, "S000", 3))
        self.assertEqual(s["oversight"]["goal_sha"], GOAL)
        s = v3.finish(s, "a", "worker", f, 4, "CLOSED", progress())
        self.assertEqual(v3.candidates(s, "S000", 4)[0], v3.MANAGER)

    def test_manager_expires_while_specialist_runs(self):
        s, m = v3.acquire(self.s, v3.MANAGER, "mgr", "S000", 1)
        s, f = v3.acquire(s, "a", "worker", "S000", 2)
        s = v3.renew(s, "a", "worker", f, 100)
        s = v3.sweep(s, 121)
        self.assertEqual(s["tasks"]["a"]["status"], "IN_PROGRESS")
        self.assertEqual(v3.candidates(s, "S000", 121)[0], v3.MANAGER)
        s, g = v3.acquire(s, v3.MANAGER, "mgr2", "S000", 121)
        self.assertEqual(g, m + 1)
        with self.assertRaises(v3.LeaseError):
            v3.manager_pass(s, "mgr", m, 122, s["revision"], progress())

    def test_manager_cadence_and_no_terminal_close(self):
        s, m = v3.acquire(self.s, v3.MANAGER, "mgr", "S000", 1)
        with self.assertRaises(v3.LeaseError):
            v3.finish(s, v3.MANAGER, "mgr", m, 2, "CLOSED", progress())
        s = v3.manager_pass(s, "mgr", m, 2, s["revision"], progress())
        self.assertNotIn(v3.MANAGER, v3.candidates(s, "S000", 301))
        self.assertEqual(v3.candidates(s, "S000", 302)[0], v3.MANAGER)

    def test_manager_mutations_atomic_and_fenced(self):
        s, f = v3.acquire(self.s, "a", "worker", "S000", 1)
        s, m = v3.acquire(s, v3.MANAGER, "mgr", "S000", 2)
        before = copy.deepcopy(s)
        for args in (
            {"priorities": {"a": 3}},
            {"retire": [v3.MANAGER]},
            {"additions": {v3.MANAGER: task(["new"])}},
            {"priorities": {"d": 2}, "additions": {"new": task(["../bad"])}},
        ):
            with self.assertRaises(v3.LeaseError):
                v3.manager_pass(s, "mgr", m, 3, s["revision"], progress(), **args)
            self.assertEqual(s, before)
        with self.assertRaises(v3.LeaseError):
            v3.manager_pass(s, "worker", f, 3, s["revision"], progress())
        with self.assertRaises(v3.LeaseError):
            v3.manager_pass(s, "mgr", m, 3, s["revision"] - 1, progress())
        q = v3.manager_pass(s, "mgr", m, 3, s["revision"], progress(),
                            priorities={"d": 7}, retire=["b"],
                            additions={"new": task(["new/file.py"])})
        self.assertEqual(q["tasks"]["d"]["priority"], 7)
        self.assertEqual(q["tasks"]["b"]["status"], "PARKED")
        self.assertEqual(q["tasks"]["new"]["status"], "OPEN")
        self.assertEqual(q["tasks"]["a"], s["tasks"]["a"])
        with self.assertRaises(v3.LeaseError):
            v3.manager_pass(q, "mgr", m, 4, q["revision"], progress())

    def test_named_resource_case_alias(self):
        s = queue({"x": task(["x"], ["CPU"]), "y": task(["y"], ["cpu"])})
        s, _ = v3.acquire(s, "x", "run1", "S000", 1)
        with self.assertRaises(v3.LeaseError):
            v3.acquire(s, "y", "run2", "S000", 2)


class HotStateTests(unittest.TestCase):
    def test_hot_model_matches_full_history_over_many_cycles(self):
        full = queue({"a": task(["a"]), "b": task(["b"])})
        hot, cold = v3.hot_projection(full)

        def compare():
            nonlocal hot
            hot, delta = v3.compact_hot(hot)
            self.assertFalse(set(cold) & set(delta))
            cold.update(delta)
            self.assertEqual(v3.restore_hot(hot, cold), full)
            self.assertLessEqual(len(hot["runs"]), 2)
            self.assertEqual(v3.dispatch_candidates(hot, ["S000"], hot["clock"]),
                             v3.dispatch_candidates(full, ["S000"], full["clock"]))

        for i in range(100):
            now = 1 + 200 * i
            run = "worker-" + str(i)
            full, f = v3.acquire(full, "a", run, "S000", now)
            hot, g = v3.acquire(hot, "a", run, "S000", now,
                                cold_run_exists=lambda key: key in cold)
            self.assertEqual(f, g)
            compare()
            full = v3.renew(full, "a", run, f, now + 10, progress("checkpoint"))
            hot = v3.renew(hot, "a", run, g, now + 10, progress("checkpoint"))
            compare()
            if i % 2:
                full = v3.sweep(full, now + 130)
                hot = v3.sweep(hot, now + 130)
            else:
                full = v3.finish(full, "a", run, f, now + 11, "OPEN", progress())
                hot = v3.finish(hot, "a", run, g, now + 11, "OPEN", progress())
            compare()
        self.assertEqual(len(cold), 100)
        self.assertEqual(hot["archived_fences"]["a"], 100)
        self.assertEqual(hot["runs"], {})
        with self.assertRaises(v3.LeaseError):
            v3.acquire(hot, "a", "worker-0", "S000", 20001,
                       cold_run_exists=lambda key: key in cold)
        with self.assertRaises(v3.LeaseError):
            v3.renew(hot, "a", "worker-0", 1, 20001)

    def test_hot_manager_review_and_fail_closed_membership(self):
        full = queue({"a": task(["a"])})
        hot, cold = v3.hot_projection(full)
        for lookup in (None, lambda key: None, lambda key: True):
            with self.assertRaises(v3.LeaseError):
                v3.acquire(hot, v3.MANAGER, "mgr", "S000", 1,
                           cold_run_exists=lookup)
        full, f = v3.acquire(full, v3.MANAGER, "mgr", "S000", 1)
        hot, g = v3.acquire(hot, v3.MANAGER, "mgr", "S000", 1,
                            cold_run_exists=lambda key: key in cold)
        self.assertEqual(f, g)
        for mode in ("full", "hot"):
            state = full if mode == "full" else hot
            result = v3.manager_pass(state, "mgr", f, 2, state["revision"], progress(),
                                     additions={"new": task(["new"])})
            if mode == "full":
                full = result
            else:
                hot = result
        hot, delta = v3.compact_hot(hot)
        cold.update(delta)
        self.assertEqual(hot["archived_fences"]["new"], 0)
        self.assertEqual(v3.restore_hot(hot, cold), full)
        with self.assertRaises(v3.LeaseError):
            v3.restore_hot(hot, {})
        forged = copy.deepcopy(hot)
        forged["archived_fences"][v3.MANAGER] += 1
        with self.assertRaises(v3.LeaseError):
            v3.validate(forged)
        with self.assertRaises(v3.LeaseError):
            v3.hot_projection(hot)


if __name__ == "__main__":
    unittest.main()
