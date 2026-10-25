"""Regression tests: safely update ONLY merged origin/main and discover tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab.agent_tests import combined_catalog, discover_agent_tests
from wii_ai_golf.lab import core
from wii_ai_golf.lab.github_sync import _trusted_url, sync_merged_main


class FakeGit:
    def __init__(self, *, remote="https://github.com/Nate27624/Wii-AI-Golf.git",
                 branch="main", dirty=False, diverged=False, new=True,
                 changed_during_fetch=False):
        self.remote, self.branch = remote, branch
        self.dirty, self.diverged, self.new = dirty, diverged, new
        self.changed_during_fetch = changed_during_fetch
        self.calls = []
        self.merged = False
        self.fetched = False

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert argv[0] == "git", "updater must ONLY invoke git"
        args = argv[1:]
        if args[:2] == ["remote", "get-url"]:
            result = self.remote
        elif args[:2] == ["branch", "--show-current"]:
            result = self.branch
        elif args[:2] == ["status", "--porcelain"]:
            result = " M local-work.py" if self.dirty or (
                self.fetched and self.changed_during_fetch) else ""
        elif args[:2] == ["rev-parse", "HEAD"]:
            result = "after" if self.merged else "before"
        elif args[:2] == ["rev-parse", "FETCH_HEAD"]:
            result = "after" if self.new else "before"
        elif args[:2] == ["fetch", "--no-tags"]:
            self.fetched = True
            result = ""
        elif args[:3] == ["merge-base", "--is-ancestor", "HEAD"]:
            return SimpleNamespace(returncode=1 if self.diverged else 0,
                                   stdout="", stderr="")
        elif args[:2] == ["diff", "--name-only"]:
            result = "tests/test_integration_new.py\ntests/test_outcome_more.py\nsrc/other.py\n"
        elif args[:2] == ["merge", "--ff-only"]:
            self.merged = True
            result = "Updating main"
        else:
            raise AssertionError(f"unexpected git command {argv}")
        return SimpleNamespace(returncode=0, stdout=result, stderr="")


class LabGitSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Wii-AI-Golf"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        self.data = self.root.parent / "Wii-AI-Golf-Data" / "lab"

    def test_approved_origins_exact_match_not_fake_hostname(self):
        self.assertTrue(_trusted_url("https://github.com/Nate27624/Wii-AI-Golf.git"))
        self.assertTrue(_trusted_url("git@github.com:Nate27624/Wii-AI-Golf.git"))
        for bad in ("https://github.com.evil/Nate27624/Wii-AI-Golf",
                    "https://github.com/Nate27624/other",
                    "git@evil.com:Nate27624/Wii-AI-Golf", ""):
            with self.subTest(url=bad):
                self.assertFalse(_trusted_url(bad))

    def test_ff_updates_only_main_and_lists_changed_agent_tests(self):
        fake = FakeGit()
        result = sync_merged_main(self.root, lab_data=self.data, run=fake)
        self.assertEqual(result.status, "updated")
        self.assertEqual(result.before, "before")
        self.assertEqual(result.after, "after")
        self.assertEqual(result.changed_tests, (
            "tests/test_integration_new.py", "tests/test_outcome_more.py"))
        self.assertTrue(fake.merged)
        self.assertEqual(fake.calls[-2][1:3], ["merge", "--ff-only"])
        self.assertFalse(any(call[0] not in ("git",) for call in fake.calls))

    def test_unchanged_repo_does_not_merge(self):
        fake = FakeGit(new=False)
        result = sync_merged_main(self.root, lab_data=self.data, run=fake)
        self.assertEqual(result.status, "up_to_date")
        self.assertFalse(fake.merged)

    def test_blocks_wrong_origin_branch_dirty_and_diverged_before_merge(self):
        conditions = [
            FakeGit(remote="https://example.org/malicious"),
            FakeGit(branch="agent/temp"),
            FakeGit(dirty=True),
            FakeGit(diverged=True),
            FakeGit(changed_during_fetch=True),
        ]
        for fake in conditions:
            with self.subTest(remote=fake.remote, branch=fake.branch,
                              dirty=fake.dirty, diverged=fake.diverged,
                              changed=fake.changed_during_fetch):
                result = sync_merged_main(self.root, lab_data=self.data, run=fake)
                self.assertEqual(result.status, "blocked")
                self.assertFalse(fake.merged)

    def test_active_live_lock_never_fetches_or_updates(self):
        self.data.mkdir(parents=True)
        (self.data / "live-session.lock").write_text(
            json.dumps({"pid": __import__("os").getpid()}))
        fake = FakeGit()
        result = sync_merged_main(self.root, lab_data=self.data, run=fake)
        self.assertEqual(result.status, "blocked")
        self.assertFalse(fake.calls)

    def test_offline_lab_test_lock_blocks_git_update(self):
        self.data.mkdir(parents=True)
        with core.lab_run_lock(self.data):
            fake = FakeGit()
            result = sync_merged_main(self.root, lab_data=self.data, run=fake)
            self.assertEqual(result.status, "blocked")
            self.assertFalse(fake.calls)
            with self.assertRaisesRegex(ValueError, "Lab test is already active"):
                with core.lab_run_lock(self.data):
                    self.fail("must not start a second overlapping Lab run")
        self.assertFalse(core.lock_busy(self.data / "run-session.lock"))

    def test_live_session_started_during_fetch_prevents_merge(self):
        fake = FakeGit()
        def injecting_runner(argv, **kw):
            result = fake(argv, **kw)
            if argv[1:3] == ["fetch", "--no-tags"]:
                # The synchronizer already created this directory for its run lock.
                self.data.mkdir(parents=True, exist_ok=True)
                (self.data / "live-session.lock").write_text("session")
            return result
        result = sync_merged_main(self.root, lab_data=self.data, run=injecting_runner)
        self.assertEqual(result.status, "blocked", result.note)
        self.assertIn("marker changed during fetch", result.note)
        self.assertFalse(fake.merged)
        # A live task arriving during fetch must halt before even checking
        # FETCH_HEAD, much less performing a fast-forward merge.
        self.assertFalse(any(call[1:3] == ["rev-parse", "FETCH_HEAD"]
                             for call in fake.calls))

    def test_new_merged_files_automatically_become_offline_experiments(self):
        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_integration_new.py").write_text("import unittest")
        (tests / "test_outcome_new.py").write_text("import unittest")
        (tests / "test_learning_new.py").write_text("import unittest")
        (tests / "not_a_test.py").write_text("print('unsafe')")
        items = discover_agent_tests(self.root)
        self.assertEqual(len(items), 3)
        self.assertEqual([x["owner"] for x in items], ["S001", "S004", "S002"])
        merged = combined_catalog(self.root, [])
        self.assertEqual(len(merged), 3)
        with patch.object(core, "load_catalog", return_value=[]):
            entries = core.available_experiments(self.root)
            self.assertEqual(len(entries), 3)
        item = core.plan("agent-tests.test_outcome_new", catalog=merged,
                         root=self.root, python="python")
        self.assertFalse(item.live)
        self.assertEqual(item.command[-3:], ("-p", "test_outcome_new.py", "-v"))
        self.assertNotIn("launch_golf.py", item.command)

    def test_rejects_path_traversal_and_unexisting_test(self):
        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_safe.py").write_text("# safe")
        items = discover_agent_tests(self.root)
        for name in ("agent-tests.../evil", "agent-tests.test_absent", "agent-tests.test_foo.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                core.plan(name, catalog=[dict(items[0], id=name)],
                          root=self.root, python="python")


if __name__ == "__main__":
    unittest.main()
