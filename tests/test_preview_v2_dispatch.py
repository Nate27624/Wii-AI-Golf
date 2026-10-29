"""Offline deterministic dispatcher preview regression tests."""
import unittest

from scripts.preview_v2_dispatch import preview

SHA = "a" * 40


def row(name, role, state="COMPLETED", paths=None, task_id="old"):
    return {"instance": name, "role": role, "state": state,
            "owned_paths": paths or [], "task_id": task_id}


def task(name, role, paths, status="READY", priority="P0", dependencies=None):
    return {"id": name, "role": role, "owned_paths": paths,
            "status": status, "priority": priority,
            "dependencies": dependencies or []}


class DispatchPreviewTests(unittest.TestCase):
    def run_preview(self, rows, tasks, sha=SHA):
        return preview({"main_sha": SHA, "assignments": rows},
                       {"main_sha": SHA, "tasks": tasks}, verified_main=sha)

    def test_finished_agent_gets_next_unblocked_task(self):
        got = self.run_preview([row("s1", "S001")],
                               [task("next", "S001", ["one.py"])])
        self.assertEqual(got["proposals"][0]["task_id"], "next")
        self.assertEqual(got["authorization"], "ADVISORY_ONLY_NOT_A_CLAIM")

    def test_active_ownership_never_reassigned(self):
        got = self.run_preview([row("s1", "S001", "CLAIMED", ["one.py"])],
                               [task("next", "S001", ["two.py"])])
        self.assertFalse(got["proposals"])

    def test_conflicting_files_skipped(self):
        got = self.run_preview([row("s1", "S001"), row("s2", "S002", "CLAIMED", ["busy.py"])],
                               [task("blocked", "S001", ["busy.py"]),
                                task("good", "S001", ["free.py"])])
        self.assertEqual(got["proposals"][0]["task_id"], "good")

    def test_only_one_agent_gets_same_task(self):
        got = self.run_preview([row("a", "S001"), row("b", "S001")],
                               [task("only", "S001", ["free.py"])])
        self.assertEqual(len(got["proposals"]), 1)
        self.assertEqual(len(got["skipped"]), 1)

    def test_dependency_and_blocked_candidates_abstain(self):
        got = self.run_preview([row("a", "S001")],
                               [task("wait", "S001", ["x.py"], dependencies=["S002-PROOF"]),
                                task("no", "S001", ["y.py"], status="blocked")])
        self.assertFalse(got["proposals"])

    def test_stale_main_fails_closed(self):
        with self.assertRaises(ValueError):
            self.run_preview([row("a", "S001")], [], sha="b" * 40)

    def test_duplicate_roster_file_claim_fails(self):
        with self.assertRaises(ValueError):
            self.run_preview([row("a", "S001", "CLAIMED", ["same.py"]),
                              row("b", "S002", "CLAIMED", ["same.py"])], [])

    def test_duplicate_backlog_ids_fail_closed(self):
        with self.assertRaises(ValueError):
            self.run_preview([row("a", "S001")],
                             [task("dupe", "S001", ["a.py"]),
                              task("dupe", "S001", ["b.py"])])

    def test_manager_cannot_be_auto_dispatched(self):
        got = self.run_preview([row("mgr", "S000", "PARKED")],
                               [task("takeover", "S000", ["manager.py"])])
        self.assertFalse(got["proposals"])

    def test_non_hex_sha_fails_closed(self):
        with self.assertRaises(ValueError):
            self.run_preview([row("a", "S001")], [], sha="z" * 40)

    def test_priority_order(self):
        got = self.run_preview([row("a", "S001")],
                               [task("low", "S001", ["l.py"], priority="P2"),
                                task("high", "S001", ["h.py"], priority="P0")])
        self.assertEqual(got["proposals"][0]["task_id"], "high")


if __name__ == "__main__":
    unittest.main()
