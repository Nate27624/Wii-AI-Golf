"""Offline deterministic dispatcher preview regression tests."""
import unittest

from scripts.preview_v2_dispatch import preview, parse_advisory, find_handoff

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

    def test_receipt_surfaces_stale_assigned_row_for_manager(self):
        receipt = [{"instance": "s1", "task_id": "old", "status": "COMPLETE_RELEASED",
                    "url": "https://github.com/test/issues/1#issuecomment-2", "main_sha": SHA}]
        got = preview({"main_sha": SHA, "assignments": [row("s1", "S001", "ASSIGNED", ["old.py"])]},
                      {"main_sha": SHA, "tasks": [task("fresh", "S001", ["new.py"])]},
                      verified_main=SHA, handoffs=receipt)
        self.assertTrue(got["proposals"][0]["requires_roster_reconciliation"])
        self.assertEqual(got["proposals"][0]["handoff"], receipt[0]["url"])

    def test_wrong_task_handoff_cannot_unlock(self):
        receipt = [{"instance": "s1", "task_id": "other", "status": "COMPLETE_RELEASED",
                    "url": "https://github.com/test/issues/1", "main_sha": SHA}]
        got = preview({"main_sha": SHA, "assignments": [row("s1", "S001", "ASSIGNED")]},
                      {"main_sha": SHA, "tasks": [task("fresh", "S001", ["new.py"])]},
                      verified_main=SHA, handoffs=receipt)
        self.assertFalse(got["proposals"])

    def test_reserve_order_and_dependencies(self):
        got = preview({"main_sha": SHA, "assignments": [row("s1", "S001")]},
                      {"main_sha": SHA, "tasks": [task("high", "S001", ["high.py"]),
                                                    task("reserve", "S001", ["reserve.py"], priority="P2")]},
                      verified_main=SHA, reserves={"s1": ["reserve", "high"]})
        self.assertEqual(got["proposals"][0]["task_id"], "reserve")


    def test_dispatch_advisory_verifies_main_and_roster(self):
        import json
        data = {"schema": "v2-dispatch-advisory-v1", "authority": "ADVISORY_ONLY_NOT_A_CLAIM",
                "main_sha": SHA, "roster_comment_id": 123, "tasks": []}
        comment = {"user": {"login": "AI-Bott"},
                   "body": "[S000-dispatcher-test] snapshot\\n"
                           "<!-- V2_DISPATCH_ADVISORY_JSON_BEGIN -->\\n"
                           + "```json\\n" + json.dumps(data) + "\\n```\\n"
                           + "<!-- V2_DISPATCH_ADVISORY_JSON_END -->"}
        got = parse_advisory([comment], verified_main=SHA, roster_comment_id=123)
        self.assertEqual(got["tasks"], [])
        with self.assertRaises(ValueError):
            parse_advisory([comment], verified_main=SHA, roster_comment_id=124)

    def test_dispatch_advisory_rejects_untrusted_author(self):
        import json
        data = {"schema": "v2-dispatch-advisory-v1", "authority": "ADVISORY_ONLY_NOT_A_CLAIM",
                "main_sha": SHA, "roster_comment_id": 123}
        comment = {"user": {"login": "attacker"},
                   "body": "[S000-dispatcher-spoof] " +
                           "<!-- V2_DISPATCH_ADVISORY_JSON_BEGIN -->" + json.dumps(data) +
                           "<!-- V2_DISPATCH_ADVISORY_JSON_END -->"}
        with self.assertRaises(ValueError):
            parse_advisory([comment], verified_main=SHA, roster_comment_id=123)

    def test_canonical_handoff_candidate_is_advisory(self):
        rr = row("S001-worker", "S001", "ASSIGNED", ["old.py"], "S001-OLD")
        comment = {"user": {"login": "AI-Bott"}, "created_at": "2026-10-29T18:11:00Z",
                   "body": "[S001-worker] HANDOFF S001-OLD complete. main " + SHA + " released ownership.",
                   "html_url": "https://github.com/Nate27624/Wii-AI-Golf/issues/308#issuecomment-123"}
        got = find_handoff(rr, [comment], verified_main=SHA,
                           roster_created_at="2026-10-29T18:00:00Z")
        self.assertEqual(got["task_id"], "S001-OLD")
        self.assertEqual(got["status"], "COMPLETE_RELEASED")

    def test_newer_claim_invalidates_prior_handoff(self):
        rr = row("S001-worker", "S001", "ASSIGNED", ["old.py"], "S001-OLD")
        history = [
            {"user": {"login": "AI-Bott"}, "created_at": "2026-10-29T18:11:00Z",
             "body": "[S001-worker] HANDOFF S001-OLD main " + SHA + " released.",
             "html_url": "https://github.com/Nate27624/Wii-AI-Golf/issues/308#issuecomment-123"},
            {"user": {"login": "AI-Bott"}, "created_at": "2026-10-29T18:12:00Z",
             "body": "[S001-worker] CLAIM new work"}
        ]
        self.assertIsNone(find_handoff(rr, history, verified_main=SHA,
                                       roster_created_at="2026-10-29T18:00:00Z"))

    def test_wrong_task_or_missing_release_not_accepted(self):
        rr = row("S001-worker", "S001", "ASSIGNED", ["old.py"], "S001-OLD")
        comment = {"user": {"login": "AI-Bott"}, "created_at": "2026-10-29T18:11:00Z",
                   "body": "[S001-worker] HANDOFF S001-NEW main " + SHA + " not released",
                   "html_url": "https://github.com/Nate27624/Wii-AI-Golf/issues/308#issuecomment-123"}
        self.assertIsNone(find_handoff(rr, [comment], verified_main=SHA,
                                       roster_created_at="2026-10-29T18:00:00Z"))

    def test_handoff_before_roster_does_not_unlock(self):
        rr = row("S001-worker", "S001", "ASSIGNED", ["old.py"], "S001-OLD")
        comment = {"user": {"login": "AI-Bott"}, "created_at": "2026-10-29T17:11:00Z",
                   "body": "[S001-worker] HANDOFF S001-OLD main " + SHA + " released.",
                   "html_url": "https://github.com/Nate27624/Wii-AI-Golf/issues/308#issuecomment-123"}
        self.assertIsNone(find_handoff(rr, [comment], verified_main=SHA,
                                       roster_created_at="2026-10-29T18:00:00Z"))

    def test_priority_order(self):
        got = self.run_preview([row("a", "S001")],
                               [task("low", "S001", ["l.py"], priority="P2"),
                                task("high", "S001", ["h.py"], priority="P0")])
        self.assertEqual(got["proposals"][0]["task_id"], "high")


if __name__ == "__main__":
    unittest.main()
