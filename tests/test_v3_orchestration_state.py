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


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.s = v3.initial({
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
        s = v3.initial(self.s["tasks"], {"legacy": {"paths": ["SRC"], "resources": []}})
        self.assertEqual(v3.candidates(s, "S000", 1), ["d"])
        self.assertEqual(v3.candidates(self.s, "S000", 1), ["a", "b", "c", "d"])
        self.assertEqual(v3.candidates(s, "S002", 1), ["f"])

    def test_path_rejects_windows_alias_and_traversal(self):
        for bad in ("../foo", "a/../foo", "C:/x", "/foo", "a\\b",
                    "a//b", "a/CON.txt", "a/thing.", ".git/config", "a/b c"):
            with self.subTest(bad=bad), self.assertRaises(v3.LeaseError):
                v3.initial({"bad": task([bad])})
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


if __name__ == "__main__":
    unittest.main()
