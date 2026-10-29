# P0 GitHub PR consolidation: canonical integration lanes

**Status:** Maintainer cleanup inventory, 2026-10-29 UTC. The read-only tracker below reports current counts; this document is an owner handoff, not a substitute for checking live PRs. Do **not** close unique active research, delete branches or auto-merge safety-critical changes based on titles.

## Why the queue inflated

Initial audit: **170 open PRs, 143 drafts, 77 targeting main, 93 targeting non-main branches, 49 distinct target refs**. This is not 170 independent production features: many are small source experiments and corrections stacked on parent research snapshots. Counts are dynamic. PRs are for proposed *code integration*; evidence-only findings should normally be comments on canonical issues or a maintained research ledger.

The most visible fanout was 14 open children of #231 (seven preserved snapshots), 7 children of #240 (global ball pointer provenance), 6 children of #163 (selected-ball baseline), 5 children of #223 (airborne vs baseline) and 4 children of #219 (source writer call graph). Most of those are unique, unmerged offline readers and tests; **they remain review candidates rather than disposable duplicates**.

## Canonical lanes / merge order

| Lane / owner | Canonical review anchor | Related unmerged children | Action |
| --- | --- | --- | --- |
| S001 — B1 controller/launch | merged #304, #309, #311, #317 | #310 diagnostic; #315 exact timing join | Review any unique remaining safety guards against current main. Host-polled A45/A90 attempts are superseded by atomic callback; no unattended live shot. |
| S002 — source/phase archives | #231 seven-phase cohort | #232, #233, #234, #235, #237, #238, #239, #242, #243, #245, #250, #252, #277, #279 | Consolidate *compatible* verified offline analyses only after owner identifies shared input/manifest contract. Never promote raw captured values or training labels. |
| S002 — global-ball pointer provenance | #240 constructor/source | #246, #247, #249, #253, #258, #265, #268 | Integrate reproducible decoder/CFG fixes into one tested source tool before proposing ball coordinates; preserve rejected hypotheses. |
| S002 — historical ball and flight | #163 selected-ball, #223 airborne comparison, #219 writer audit | #174, #176, #180, #181, #182, #183; #224, #225, #227, #230, #231; #244, #256, #257, #262 | Source/boot/frame authenticity first, compare against same-shot negative controls; no unverified world-XYZ claim. |
| S000 — shared evidence and backlog | #205 variable registry and #200 archived queue prototype | #212, #221, #289, #260 | Keep one source-of-truth typed variable register; adopt safe read-only PR health tool from #200 into this main-based PR; do not duplicate memory readers. |
| S001/S000 — operator diagnostics | #308 startup issue, #310 diagnostic, #220 Qt recovery | #194 Lab clean launch, #214 PowerShell native shot keeper | Do not modify the user's working PowerShell launcher; audit unique improvements before merging. |

## Actual cleanup decisions

- Old Clean/result-first integration PRs **#195, #300, #305** closed as superseded by merged #304. Their branches and discussions remain available.
- Legacy host-polled A recheck **#198**, last-seen A getter review **#314**, and offline host timing receipt **#312** closed as obsolete after merged atomic A45 #317. These were *archived*, not merged.
- Keep unique source analysis open until S002/S000 reviews its input provenance. Do not close based on age alone; a draft is not necessarily useless.
- The historical queue audit #200 can be retired only after this main-based replacement is merged and full host tests pass.

## New agent policy / backlog budget

1. **Search existing PRs and issues before coding.** For a single research hypothesis, append evidence to its parent canonical issue/ledger; do not open a new PR for each static source observation.
2. **One active integration PR per owner per shared module.** Additional research branches may exist privately, but a new open PR must state exact unique behavior, owner, upstream/downstream contracts, and why an existing PR cannot carry it.
3. **No stacking by default.** Target `main` for independently testable additions; stack only where an explicit dependency is unavoidable, link parent/child and identify the merge order.
4. **Close or supersede after merge, retaining history.** First check for unique unmerged files/tests and open children. Never delete branches or silently discard research. If a parent is closed, notify children to reconcile on latest main.
5. **Review one actual bottleneck, not every hypothesis.** Highest P0: verified native B1 contact and reliable outcome, then genuine ball world XYZ/velocity with source-authenticated same-frame evidence; no training publication from synthetic/provenance-only results.

## Automated read-only health

`scripts/audit_open_pr_queue.py` (from the already-reviewed #200 prototype) reports sanitized counts, known stacked dependency edges, unmatched bases and oldest update dates. `.github/workflows/open-pr-queue-health.yml` executes Windows/Ubuntu offline tests and publishes a read-only numeric GitHub Actions artifact on a daily schedule. It **does not close PRs, merge code, mutate the repository, execute Dolphin, or upload private game data**. All changes to PR state must be human-authorized and reviewed on exact current heads.
