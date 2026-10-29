# V2 PR Triage — dispositions, not mass closures

The research backlog is mostly stacked investigations. This is a **historical family index, not a live PR queue**: parent labels and statuses can become stale after selective merges. Consult current GitHub state and exact file hashes before making a closure claim. Many research parents remain useful evidence even if their minimal executable core has already been merged. Never imply that each open PR represents an independent missing feature.

| Family | Parent | Children to adjudicate | Primary direction |
| --- | --- | --- | --- |
| Seven numbered captures | historical #231 (closed unmerged; minimal reader merged #331) | #232 #233 #234 #235 #237 #238 #239 #242 #243 #245 #250 #252 #277 #279 | S002 consolidate exact-archive reader, source/negative controls; cherry-pick unique guards/tests |
| Global ball provenance | research #240 (minimal global core merged #337) | #246 #247 #249 #253 #258 #265 #268 | S002 retain both archive SHA and receiver/caller drift checks; avoid competing reader |
| Historical selected ball | #163 | #174 #176 #180 #181 #182 #183 | S002 retain independent source-backed tests and findings |
| Airborne phases | #223 | #224 #225 #227 #230 #231 | S002 resolve phase/actor hypotheses; preserve D1 uncertainty |
| Source writer provenance | research #219 (minimal source caller/CFG adapter merged #329) | #244 #256 #257 #262 | S002 source-backed call relationships, not duplicate PPC scanners |
| Runtime/capture | merged #304 #309 #311 #317 | #310 #315; legacy #302 | S001/S005 only harvest unique compatibility and evidence gates |
| V2 manager / merge policy | merged #320 #321 | none | S000 maintain canonical startup and root merge procedure |

## Confirmed safe closure example
- PR #306 was closed as superseded by parent #248 after **three exact matching blob SHAs** were checked for script, tests and study. Parent retained the changes. Preserve child branch and PR record.

## For each remaining PR
1. Check state, base, head and complete changed-file inventory.
2. Compare unique code/test/data-contract changes to canonical main or parent.
3. Assign exactly one disposition: **already merged**, **exact duplicate**, **unique integration work**, **research-only evidence**, **blocked incompatible**.
4. For *exact duplicate*, cite matching blobs or equivalent complete semantic analysis and close with a clear parent link.
5. For *unique integration work*, transfer guards and tests into canonical owner branch, execute full checks, then close child.
6. For *research evidence*, preserve the motivation, input provenance, observed findings, counterexamples, uncertainty/limitations, source commit and links, plus any reusable testing instructions in the canonical evidence ledger or parent **before** closing. The experimental script itself may be retired if no unique executable capability remains needed for V2. Operator explicitly authorized this evidence-preserving retirement.
7. Never close an active unique implementation merely to achieve a PR count.

## Current consolidation rule (2026-10-29 baseline)
- #331/#337/#329 selectively integrated existing seven-phase, global-ball, and source-caller components. #341 integrated the final outbound observation publication allowlist. Verify the latest current main; these are **not** claims of real ball XYZ, live contact or training-ready data.
- Research-only parent/child branches should be retired **after** their unique code, tests, evidence, and negative results have been compared to current main and preserved with source links. Do not replay old seven-bank source audits or reopen historical branches only to reduce the visible backlog.
- PR #246/#247 and related #240 child studies may contain nonidentical integrity tests; classify each against #337 and active owner work before closure. #248 contains changes from closed #306 but requires its own current-state review.
- **Successor agents:** read [navigation](v2-navigation.md), [continuity](v2-agent-continuity.md) and canonical GitHub claims; do not infer unfinished tasks from this dated ledger alone.

S000 owns this ledger's accuracy. Other agents autonomously merge qualifying PRs under root `merging.md`.
