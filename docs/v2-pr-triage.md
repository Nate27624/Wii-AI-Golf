# V2 PR Triage — dispositions, not mass closures

The research backlog is mostly stacked investigations. This ledger identifies family anchors; **it does not assert every child is redundant**. Check current PR state and file hashes before making a closure claim.

| Family | Parent | Children to adjudicate | Primary direction |
| --- | --- | --- | --- |
| Seven numbered captures | #231 | #232 #233 #234 #235 #237 #238 #239 #242 #243 #245 #250 #252 #277 #279 | S002 consolidate exact-archive reader, source/negative controls; cherry-pick unique guards/tests |
| Global ball provenance | #240 | #246 #247 #249 #253 #258 #265 #268 | S002 retain both archive SHA and receiver/caller drift checks; avoid competing reader |
| Historical selected ball | #163 | #174 #176 #180 #181 #182 #183 | S002 retain independent source-backed tests and findings |
| Airborne phases | #223 | #224 #225 #227 #230 #231 | S002 resolve phase/actor hypotheses; preserve D1 uncertainty |
| Source writer provenance | #219 | #244 #256 #257 #262 | S002 source-backed call relationships, not duplicate PPC scanners |
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
6. For *research evidence*, preserve source/hypothesis/negative results in the ledger or parent before closing.
7. Never close an active unique implementation merely to achieve a PR count.

## Immediate focus
- PR #243 has useful fail-closed manifest-shape guards, but it is an older divergent child of #231. Port the unique checks to latest #231 rather than merge outdated reader.
- PR #246 and #247 share pin/start/config drift guards; #246 uniquely checks caller/slot consistency; #247 uniquely checks all 14 source archive SHA values. Owner should reconcile both sets in latest #240.
- PR #248 incorporates the exact changes from closed child #306. This is not proof #248 itself is ready to merge.

S000 owns this ledger's accuracy. Other agents autonomously merge qualifying PRs under root `merging.md`.
