# P0 seven-pair ordinal endpoint and pin-distance study

**Status: offline only, no emulator, no controller, no new snapshots, no training.** Stacked on canonical PR #231 source reader; new-only script, tests and workflow.

## Existing real evidence

The preserved seven numbered paired banks were independently SHA-verified by source agent. Operator reports wedge W5 (near apex), W6 (descending), W7 (flag/on-green UI) are three phases of the SAME wedge shot. Source-selected active-ball +0x30 changes all 3 components at both transitions, while three inactive ball candidates, selected start and pin, Config selectors, and source owner pointers are stable. The +0xCC ball-object cache is BITWISE CONSTANT across all three wedge phases and W7 current-ball +0x30 equals it 3/3. W5 and W6 current ball differ from the cache 3/3. Conditional caches F0/FC remain distinct. D1 to D2 is a separate DRIVER shot with both selected current ball and cache+CC changing 3/3, so no universal CC=static-endpoint claim.

## New falsifiable distinction

`scripts/audit_p0_seven_endpoint_order_private.py` delegates exact 14-bank private manifest and SHA checks to existing #231 `_check_archive` (no duplicate parser), then source-gates five relevant phases D1,D2,W5,W6,W7 via the SAME existing #231 `_get` for native Rev1 / scene5 / mode4 / selected ball, and validates selected object selfrefs and owner/geometry/Config identity. Privately decodes only source-selected ball+0x30, its cache+0xCC, source PIN+0x30 and tee+0x30 (and finite bounded F0/FC vectors). Reports ONLY two stepwise distance ordering categories `decreased`, `increased`, or `equal_within_numeric_tolerance`; three bitwise cache-ball equality counts; whether W7 ball equals unchanged CC; whether CC equals selected pin; whether W7 ball equals pin; driver owner/cache stability flags. No raw coordinates/distances/heap pointers/paths/hashes/specific float values printed. Numeric tolerances are arbitrary computational thresholds, **NOT verified physical units**. The script ABSTAINS if wedge owner, pin, tee, selector or cache identity is unstable, or if either wedge ball candidate fails to change.

Source code field meanings remain hypotheses. `ball +0xCC` might be an endpoint, predictive landing object, target reference, delayed simulation buffer or something else; a decreasing distance to CC and W7 equality is *correlation*, not proof of prediction. Camera motion is not controlled by this calculation. Physical axes, units, timestamps and exact guest game frames are unverified; the human W7 label does not necessarily mean fully settled. No velocity, power, score, reward or training approval. The preserved operator same-frame attestation from earlier in-flight MRAM+EXRAM applies to that specific capture and MUST NOT be automatically assigned to all seven pairs.

## Next source-specific work

To promote CC semantics, S002 #225 should trace read/write sites for ball+0xCC in Rev1 PPC and find when initialized or recomputed; S000 records evidence with untyped source-relative classification; S001 fixes timing/physical play validation. Independently replicate CC-vs-current-ball convergence at an additional single shot with stable pin/tee and measured game-frame timestamps before training. No new shot now.

## How to run

Use clean SHA-pinned detached worktree of `agent/research/p0-seven-phase-endpoint-order-check`, run `py -I -m unittest discover -s tests -p test_p0_seven_endpoint_order_private.py -v`, then run `py -I scripts/audit_p0_seven_endpoint_order_private.py --archive <ONE previously preserved p0-new-cohort-*-PRIVATE folder in ignored Data/captures>`. If more than one match exists, require explicit archive choice; do not guess. Output only JSON booleans/order categories. Never upload raw banks or manifests.
