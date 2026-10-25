"""Safe, opt-in at GUI-level polling of merged tests from trusted origin/main.

Only FF-only update on a clean, ordinary main checkout of the expected repo.
Open/unmerged PRs are NOT executed or merged. Test execution remains manual.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Callable, Any

from .locks import any_lab_job_busy, lock_busy, session_lock

EXPECTED_REPOSITORY = "Nate27624/Wii-AI-Golf"
REMOTE = "origin"
BRANCH = "main"
TEST_DIFF = re.compile(r"^tests/test_[a-z0-9_]+\.py$")


@dataclass(frozen=True)
class SyncReport:
    status: str
    before: str | None = None
    after: str | None = None
    changed_tests: tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "before": self.before,
                "after": self.after, "changed_tests": list(self.changed_tests),
                "note": self.note}


def _trusted_url(url: str) -> bool:
    """Allow exact https and SSH origin URLs for THIS repo, not lookalikes."""
    return url.strip().rstrip("/") in {
        "https://github.com/Nate27624/Wii-AI-Golf",
        "https://github.com/Nate27624/Wii-AI-Golf.git",
        "git@github.com:Nate27624/Wii-AI-Golf",
        "git@github.com:Nate27624/Wii-AI-Golf.git",
        "ssh://git@github.com/Nate27624/Wii-AI-Golf",
        "ssh://git@github.com/Nate27624/Wii-AI-Golf.git",
    }


def sync_merged_main(
    root: Path, *, lab_data: Path | None = None,
    run: Callable[..., Any] = subprocess.run,
    timeout_s: int = 35,
) -> SyncReport:
    """Synchronize from merged main while holding a real cross-process run lock."""
    if lab_data is None:
        return _sync_impl(root, lab_data=None, run=run, timeout_s=timeout_s)
    if any_lab_job_busy(lab_data):
        return SyncReport("blocked", note="A Lab task is active; no Git changes.")
    try:
        with session_lock(lab_data / "run-session.lock", label="GitHub synchronization"):
            return _sync_impl(root, lab_data=lab_data, run=run, timeout_s=timeout_s)
    except ValueError as exc:
        return SyncReport("blocked", note=str(exc))


def _sync_impl(
    root: Path, *, lab_data: Path | None,
    run: Callable[..., Any], timeout_s: int,
) -> SyncReport:
    """Fast-forward local clean main only; never run newly fetched code."""
    root = Path(root).resolve()
    if lab_data is not None and lock_busy(lab_data / "live-session.lock"):
        return SyncReport("blocked", note="A Lab live experiment is active; no Git changes.")
    if not (root / ".git").exists():
        return SyncReport("blocked", note="Not an ordinary Git checkout; no automatic updates.")
    def git(*arguments: str, timeout: int = 8) -> str:
        try:
            p = run(["git", *arguments], cwd=root, text=True,
                    capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Git {' '.join(arguments[:2])} unavailable/timed out: {exc}") from exc
        if p.returncode != 0:
            message = (p.stderr or p.stdout or f"git exited {p.returncode}").strip()
            raise RuntimeError(f"Git {' '.join(arguments[:2])}: {message[:400]}")
        return p.stdout.strip()

    try:
        origin = git("remote", "get-url", REMOTE)
        if not _trusted_url(origin):
            return SyncReport("blocked", note="Git origin is not the approved Wii-AI-Golf repository.")
        if git("branch", "--show-current") != BRANCH:
            return SyncReport("blocked", note="Auto-update requires local main. Switch branches manually.")
        if git("status", "--porcelain", "--untracked-files=normal"):
            return SyncReport("blocked", note="Working tree has local changes; commit/move them before updating.")
        before = git("rev-parse", "HEAD")
        git("fetch", "--no-tags", REMOTE, BRANCH, timeout=timeout_s)
        after = git("rev-parse", "FETCH_HEAD")
        if before == after:
            return SyncReport("up_to_date", before, after,
                              note="Local main already matches origin/main; no tests executed.")
        # Fail CLOSED if local branch has diverged, remote was rewritten, or
        # updater would have to discard/rebase any local commits.
        p = run(["git", "merge-base", "--is-ancestor", "HEAD", "FETCH_HEAD"],
                cwd=root, text=True, capture_output=True, timeout=8, check=False)
        if p.returncode != 0:
            return SyncReport("blocked", before, after,
                              note="Local main diverged from origin/main; requires manual review.")
        changed = git("diff", "--name-only", "HEAD", "FETCH_HEAD", "--", "tests")
        changed_tests = tuple(sorted({x for x in changed.splitlines()
                                      if TEST_DIFF.fullmatch(x)}))
        # Recheck immediately before filesystem changes; Dolphin/Lab processes
        # may have begun during the network fetch.
        if lab_data is not None and lock_busy(lab_data / "live-session.lock"):
            return SyncReport("blocked", before, after, changed_tests,
                              note="Lab live task started during fetch; update deferred.")
        if git("status", "--porcelain", "--untracked-files=normal"):
            return SyncReport("blocked", before, after, changed_tests,
                              note="Working tree changed during fetch; update deferred.")
        if git("branch", "--show-current") != BRANCH:
            return SyncReport("blocked", before, after, changed_tests,
                              note="Branch changed during fetch; update deferred.")
        # No reset/stash/force. git merge --ff-only refuses changed/diverged trees.
        git("merge", "--ff-only", "FETCH_HEAD", timeout=timeout_s)
        final = git("rev-parse", "HEAD")
        if final != after:
            raise RuntimeError("Git changed unexpectedly during fast-forward verification.")
        return SyncReport("updated", before, after, changed_tests,
                          note=f"Fast-forwarded approved main; {len(changed_tests)} test files changed. "
                               "Tests were NOT executed automatically.")
    except RuntimeError as exc:
        return SyncReport("error", note=str(exc))
