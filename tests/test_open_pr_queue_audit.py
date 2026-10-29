"""Offline synthetic tests for the read-only open-PR stack and backlog auditor."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_open_pr_queue.py"
SPEC = importlib.util.spec_from_file_location("open_pr_audit", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def pr(number, *, base="main", branch=None, draft=False, days=0,
       repo=audit.REPOSITORY):
    return {
        "number": number,
        "state": "open",
        "draft": draft,
        "base": {"ref": base, "repo": {"full_name": audit.REPOSITORY}},
        "head": {
            "ref": branch or f"agent/test-{number}",
            "repo": {"full_name": repo},
        },
        "updated_at": f"2026-10-{28-days:02d}T00:00:00Z" if days <= 27
                      else "2026-09-10T00:00:00Z",
        "title": "UNTRUSTED PR TITLE PRIVATE DATAPATH C:\\Users\\owner\\file.raw",
        "body": "NEVER PUBLISH RAW PRIVATE CONTENT",
    }


class QueueHealthAuditTests(unittest.TestCase):
    def test_empty_queue(self):
        result = audit.audit_open_prs([], now=NOW)
        self.assertEqual(result["open_pr_count"], 0)
        self.assertEqual(result["max_known_stack_depth"], 0)
        self.assertTrue(result["no_merge_close_or_branch_changes"])

    def test_direct_main_and_draft(self):
        result = audit.audit_open_prs([pr(1, draft=True), pr(2)], now=NOW)
        self.assertEqual(result["draft_pr_count"], 1)
        self.assertEqual(result["direct_main_pr_count"], 2)
        self.assertEqual(result["linked_stack_edge_count"], 0)

    def test_known_stacked_chain_and_depth(self):
        records = [pr(1, branch="agent/a"),
                   pr(2, base="agent/a", branch="agent/b"),
                   pr(3, base="agent/b", branch="agent/c")]
        result = audit.audit_open_prs(records, now=NOW)
        self.assertEqual(result["max_known_stack_depth"], 2)
        self.assertEqual(result["linked_stack_edge_count"], 2)
        self.assertEqual(result["nonmain_base_pr_count"], 2)
        self.assertEqual(result["linked_stack_edges_sample"],
                         [{"child_pr": 2, "parent_pr": 1},
                          {"child_pr": 3, "parent_pr": 2}])

    def test_unresolved_base_is_not_declared_deleted(self):
        result = audit.audit_open_prs([pr(7, base="retained-old-branch")], now=NOW)
        self.assertEqual(result["unresolved_nonmain_base_count"], 1)
        self.assertTrue(result["unresolved_base_does_not_mean_deleted_branch"])

    def test_fork_head_cannot_claim_local_stack_parent(self):
        result = audit.audit_open_prs([
            pr(11, branch="same", repo="outsider/repo"),
            pr(12, base="same"),
        ], now=NOW)
        self.assertEqual(result["linked_stack_edge_count"], 0)
        self.assertEqual(result["unresolved_nonmain_base_count"], 1)

    def test_ambiguous_or_self_link_does_not_invent_edge(self):
        report = audit.audit_open_prs([
            pr(21, branch="dup"),
            pr(22, branch="dup"),
            pr(23, base="dup"),
            pr(24, base="self", branch="self"),
        ], now=NOW)
        self.assertEqual(report["ambiguous_base_count"], 2)
        self.assertEqual(report["linked_stack_edge_count"], 0)

    def test_cycle_abstains(self):
        rows = [pr(31, branch="x", base="y"), pr(32, branch="y", base="x")]
        with self.assertRaisesRegex(ValueError, "Cycle"):
            audit.audit_open_prs(rows, now=NOW)

    def test_duplicate_ids_and_invalid_shapes_abstain(self):
        with self.assertRaises(ValueError):
            audit.audit_open_prs([pr(1), pr(1)], now=NOW)
        with self.assertRaises(ValueError):
            audit.audit_open_prs([{"number": 1}], now=NOW)
        with self.assertRaises(ValueError):
            audit.audit_open_prs([pr(True)], now=NOW)

    def test_age_and_pressure_are_only_advisory(self):
        rows = [pr(i, days=15) for i in range(1, 52)]
        result = audit.audit_open_prs(rows, now=NOW)
        self.assertEqual(result["stale_14d_count"], 51)
        self.assertEqual(result["review_pressure"], "high")
        self.assertEqual(len(result["stale_pr_numbers_sample"]), 30)
        self.assertTrue(result["dependency_links_are_review_hypotheses_only"])

    def test_invalid_timestamp_is_not_mistaken_for_stale(self):
        row = pr(52)
        row["updated_at"] = "not a date"
        report = audit.audit_open_prs([row], now=NOW)
        self.assertEqual(report["updated_utc_missing_or_invalid_count"], 1)
        self.assertEqual(report["stale_14d_count"], 0)

    def test_raw_pr_titles_and_bodies_never_in_sanitized_report(self):
        result = audit.audit_open_prs([pr(72)], now=NOW)
        output = json.dumps(result)
        self.assertNotIn("UNTRUSTED", output)
        self.assertNotIn("PRIVATE DATAPATH", output)
        self.assertNotIn("C:\\Users", output)
        self.assertNotIn("NEVER PUBLISH", output)
        self.assertFalse(result["raw_private_data_included"])

    def test_cli_writes_only_sanitized_report_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fixture = folder / "input.json"
            target = folder / "out.json"
            fixture.write_text(json.dumps([pr(22)]), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    audit.main(["--fixture", str(fixture), "--out", str(target)]), 0
                )
            self.assertIn("SANITIZED_PR_QUEUE_REPORT_WRITTEN", stdout.getvalue())
            self.assertNotIn("C:\\Users", target.read_text(encoding="utf-8"))
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(
                    audit.main(["--fixture", str(fixture), "--out", str(target)]), 2
                )
            self.assertIn("PR_QUEUE_AUDIT_FAILED", stderr.getvalue())
            self.assertNotIn(str(target), stderr.getvalue())

    def test_fixture_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            a = folder / "source.json"
            b = folder / "pointer.json"
            a.write_text("[]", encoding="utf-8")
            try:
                b.symlink_to(a)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink privilege unavailable")
            with self.assertRaises(ValueError):
                audit._load_fixture(b)

    def test_github_mode_without_token_does_not_call_network(self):
        with patch.dict("os.environ", {}, clear=True), \
                patch.object(audit, "urlopen") as network:
            with self.assertRaisesRegex(ValueError, "token"):
                audit._get_open_prs()
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
