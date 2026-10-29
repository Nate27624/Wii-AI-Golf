"""Read-only, privacy-safe audit of the OPEN GitHub PR queue.

This audits PR review dependencies, NOT actual game telemetry or training readiness.
No git writes, merges, branch deletions, live Dolphin, RAM, or game artifacts.

GitHub mode is for read-only Actions with the built-in GITHUB_TOKEN.
Fixture mode is for deterministic offline synthetic tests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "Nate27624/Wii-AI-Golf"
API_ROOT = "https://api.github.com"
MAX_PAGES = 10
PER_PAGE = 100
MAX_RESULTS = MAX_PAGES * PER_PAGE
MAX_INPUT_BYTES = 5_000_000
MAX_PUBLIC_IDS = 30
MAX_PUBLIC_EDGES = 50


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return date.astimezone(timezone.utc) if date.tzinfo else None


def _ref(record: dict, field: str) -> str:
    obj = record.get(field)
    if not isinstance(obj, dict):
        raise ValueError("Invalid PR reference")
    value = obj.get("ref")
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError("Invalid PR branch reference")
    return value


def _head_in_repo(record: dict, repository: str) -> bool:
    head = record["head"]
    repo = head.get("repo")
    return isinstance(repo, dict) and repo.get("full_name") == repository


def audit_open_prs(
    records: list[dict], *, now: datetime | None = None, repository: str = REPOSITORY
) -> dict:
    """Return public-safe counts and small ID-only dependency examples.

    A non-main base that is not another OPEN PR head is *unresolved for review*,
    not necessarily a deleted branch: merged PRs may retain source branches.
    """
    if not isinstance(records, list) or len(records) > MAX_RESULTS:
        raise ValueError("PR input limit exceeded")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Audit clock must contain timezone")
    now = now.astimezone(timezone.utc)
    by_number: dict[int, dict] = {}
    heads: dict[str, list[int]] = {}
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Invalid PR metadata")
        num = item.get("number")
        if type(num) is not int or num <= 0 or num in by_number:
            raise ValueError("Duplicate or invalid PR number")
        if item.get("state") != "open" or type(item.get("draft")) is not bool:
            raise ValueError("Expected open PR with explicit draft state")
        _ref(item, "base")
        head_ref = _ref(item, "head")
        by_number[num] = item
        if _head_in_repo(item, repository):
            heads.setdefault(head_ref, []).append(num)

    edges: list[tuple[int, int]] = []
    unresolved: list[int] = []
    ambiguities: list[int] = []
    draft: list[int] = []
    direct_main: list[int] = []
    stale: list[int] = []
    missing_dates = 0
    for num, item in sorted(by_number.items()):
        if item["draft"]:
            draft.append(num)
        base = _ref(item, "base")
        if base == "main":
            direct_main.append(num)
        else:
            parents = heads.get(base, [])
            if len(parents) == 1 and parents[0] != num:
                edges.append((num, parents[0]))
            elif len(parents) > 1 or (len(parents) == 1 and parents[0] == num):
                ambiguities.append(num)
            else:
                unresolved.append(num)
        updated = _timestamp(item.get("updated_at"))
        if updated is None:
            missing_dates += 1
        elif 0 <= (now - updated).total_seconds() and (now - updated).days >= 14:
            stale.append(num)

    parents_by_child = dict(edges)
    visiting: set[int] = set()
    depths: dict[int, int] = {}
    def depth(num: int) -> int:
        if num in visiting:
            raise ValueError("Cycle in PR stacking graph")
        if num in depths:
            return depths[num]
        visiting.add(num)
        parent = parents_by_child.get(num)
        value = (1 + depth(parent)) if parent is not None else 0
        visiting.remove(num)
        depths[num] = value
        return value

    for number in by_number:
        depth(number)

    edges.sort()
    high_pressure = len(records) >= 50 or len(unresolved) >= 10
    return {
        "kind": "sanitized-open-pr-queue-health",
        "schema_version": 1,
        "repository": repository,
        "observed_at_utc": now.isoformat(timespec="seconds"),
        "open_pr_count": len(records),
        "draft_pr_count": len(draft),
        "direct_main_pr_count": len(direct_main),
        "nonmain_base_pr_count": len(records) - len(direct_main),
        "linked_stack_edge_count": len(edges),
        "linked_stack_edges_sample": [
            {"child_pr": child, "parent_pr": parent}
            for child, parent in edges[:MAX_PUBLIC_EDGES]
        ],
        "stack_edge_sample_truncated": len(edges) > MAX_PUBLIC_EDGES,
        "max_known_stack_depth": max(depths.values(), default=0),
        "unresolved_nonmain_base_count": len(unresolved),
        "unresolved_nonmain_base_pr_numbers_sample": unresolved[:MAX_PUBLIC_IDS],
        "ambiguous_base_count": len(ambiguities),
        "ambiguous_base_pr_numbers_sample": ambiguities[:MAX_PUBLIC_IDS],
        "updated_utc_missing_or_invalid_count": missing_dates,
        "stale_14d_count": len(stale),
        "stale_pr_numbers_sample": stale[:MAX_PUBLIC_IDS],
        "review_pressure": "high" if high_pressure else "normal",
        "dependency_links_are_review_hypotheses_only": True,
        "unresolved_base_does_not_mean_deleted_branch": True,
        "no_merge_close_or_branch_changes": True,
        "real_emulator_outcomes_verified": False,
        "raw_private_data_included": False,
    }


def _load_fixture(path: Path) -> list:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Untrusted fixture size or type")
    return json.loads(path.read_text(encoding="utf-8"))


def _get_open_prs() -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub read-only token unavailable")
    result: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        url = (f"{API_ROOT}/repos/{REPOSITORY}/pulls"
               f"?state=open&per_page={PER_PAGE}&page={page}")
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "Wii-AI-Golf-ReadOnly-PR-Queue-Audit",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET",
        )
        with urlopen(request, timeout=20) as response:
            payload = response.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("Oversized API response")
        page_records = json.loads(payload)
        if not isinstance(page_records, list) or len(page_records) > PER_PAGE:
            raise ValueError("Invalid PR API response")
        result.extend(page_records)
        if len(page_records) < PER_PAGE:
            return result
    raise ValueError("PR list pagination limit reached; refuse incomplete audit")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--github", action="store_true", help="Read public-safe PR metadata via GitHub Actions token")
    mode.add_argument("--fixture", type=Path, help="Offline JSON array fixture")
    parser.add_argument("--out", type=Path, required=True, help="Save SANITIZED JSON summary")
    args = parser.parse_args(argv)
    try:
        records = _get_open_prs() if args.github else _load_fixture(args.fixture)
        report = audit_open_prs(records)
        encoded = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.out.is_symlink() or args.out.exists():
            raise ValueError("Refuse overwrite of existing report")
        if not args.out.parent.is_dir():
            raise ValueError("Output parent must exist")
        with args.out.open("x", encoding="utf-8") as out:
            out.write(encoded)
        # Never print token, API response bodies, raw PR titles or repository file paths.
        print("SANITIZED_PR_QUEUE_REPORT_WRITTEN",
              "open=", report["open_pr_count"],
              "draft=", report["draft_pr_count"],
              "stacked=", report["nonmain_base_pr_count"],
              "unresolved=", report["unresolved_nonmain_base_count"])
        return 0
    except (OSError, HTTPError, URLError, ValueError, TypeError, KeyError,
            UnicodeError, OverflowError, json.JSONDecodeError):
        print("PR_QUEUE_AUDIT_FAILED: read-only audit incomplete; no data published",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
