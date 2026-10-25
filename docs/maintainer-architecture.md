# Maintainer architecture and quality-of-life plan

Owner: S000 coordinator/UI maintainer. Scope: reviewed changes only, no destructive reorganizations.

## Current architecture (audited 2026-10-24)

- `scripts/golf.py` is the sole operator-facing entrypoint. Legacy `scripts/*.py` remain domain adapters; do **not** delete or move them until callers and tests are migrated.
- `src/wii_ai_golf/cli.py` is command routing; `src/wii_ai_golf/lab/core.py` owns typed experiment planning, execution and local run metadata; `lab/gui.py` is Tkinter presentation; `lab/github_sync.py` owns fail-closed fast-forward updates from the approved repository.
- `research/experiments.json` is the reviewed, typed experiment catalog. `tests/test_*.py` are discovered as manual offline tests after merged-main synchronization.
- Domain ownership: S001 integration, S002 evaluation/capture, S003 modeling, S004 optimization, S005 generalization. S000 owns UI, command consistency, integration and the merge gate.
- Local Dolphin/game/bridge configuration and RAW-PRIVATE artifacts stay outside Git. Controller ACK, human-observed contact, verified score, and synthetic results must remain separately labeled.

## Refactoring priorities (ordered)

1. **Integrate active work before editing shared modules.** PR #52 touches `lab/core.py`, `lab/gui.py`, `focused_trace.py`; PR #14 also touches `focused_trace.py`. Inspect diffs, reconcile overlap, and land focused tests first. Do not parallel-edit these files on an uncoordinated branch.
2. **Introduce testable UI helpers (behavior-preserving).** After #52 lands, extract experiment filtering/selection and parameter validation from Tk callbacks into pure functions, with offline unit tests. In particular, distinguish irrelevant input fields from per-experiment supported arguments; preserve exact command previews.
3. **Separate GUI process lifecycle from sync lifecycle.** Track running subprocesses and status updates through a small controller abstraction, ensuring stale process entries never block Git sync and that synchronization never mutates a running checkout. Test exit/exception/race paths with fakes; never auto-execute fetched tests.
4. **Reduce monolithic typed plan dispatch incrementally.** Group `lab/core.py` handlers by S001/S002/S003/S004 ownership behind explicit reviewed adapters while preserving stable experiment IDs, CLI flags, audit metadata and fail-closed validation. Avoid a dynamic arbitrary-shell plugin framework.
5. **Improve operator QOL.** Clear eligibility/status reasons per experiment, last-run outcome labels, visible sync timestamp/error, consistent multiline sanitized report rendering, and explicit UI restart notice when the GUI implementation itself updates. Human-observed vs verified-score status must be prominent.
6. **Consolidate documentation, not working scripts.** Keep README concise and link to `docs/research-lab.md`, `docs/cli.md`, domain-specific experiment docs and this maintainer plan. Retire duplicate instructions only after verifying all inbound references.

## Review/merge gate

- Prefer squash merges of narrow PRs targeting `main` after reviewing exact changes; preserve authorship and the linked issue. Refuse mismatched or stale head SHA.
- Require relevant `python -m unittest discover -s tests -v` evidence or record honestly when Windows/Dolphin-only behavior was not locally testable. Regression tests must cover every edited operator-facing route, especially fresh boot and lock behavior.
- No force pushes, branch deletion of others' work, destructive savestate changes, raw RAM uploads, hidden live actions, unexplained cloud costs, or bypass of protection rules.
- On shared-file collisions, ask the domain agent to rebase or coordinate a follow-up; prioritize operator safety over merge speed. Ask the operator only for unresolved requirements/safety trade-offs, never ordinary code decisions.
- Verify a merged PR's new experiment appears in the GUI through merged-main sync (test discovery alone is not sufficient for new *live* experiment kinds). Preserve a recorded regression baseline.

## Decision record / implementation sequencing

- **Now:** codify contracts without modifying active PR #52/#14 code.
- **After #52:** make the first small UI state/parameter-validation refactor with unit tests.
- **After S002 and S003 merge:** consolidate the measurement schemas and experiment adapters. Do not claim calibrated power or verified score before evidence supports it.
- **Later:** introduce real result comparison screens only when trustworthy result provenance is available.

This document is a maintainer roadmap, not a claim that listed refactors or physical Dolphin tests have already been completed.
