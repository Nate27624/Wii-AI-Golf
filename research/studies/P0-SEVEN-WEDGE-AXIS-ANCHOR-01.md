# P0 — wedge coordinate-component anchor hypothesis (source-only, seven snapshots)

**Status: draft research; no operator RAM run yet; no physical axis or training approval.**

## Why this is separate from the existing agents

Canonical S002 #231 reads and verifies 14 native banks, all seven scene/source-selected phase snapshots. #230 proved within the human-reported single wedge W5 -> W6 -> W7 that selected ball translation +0x30 changes 3/3 while pin and tee stay 0/3 and the unselected ball slots are inert. #232 owns **Euclidean ordinal ball-to-cache/pin** comparisons, including +0xCC endpoint convergence. #219/#225 own static PPC ball/cache writer provenance. None of those studies classifies each *coordinate component* against the fixed pin and tee component **with an explicit identifiability abstention**.

This additive script does **not** call a guessed memory offset or scan new banks. It reuses #231 `_check_archive` (all 14 private original bank SHA), `_get` (RSPE01 Rev1 source/scene/mode/selected ownership), and the same source-selected ball, pin and start triplets. It refuses inconsistent owner, source-hole, pin/start coordinates, source Config +0xBC/+0xC0/+0xC4 and same-shot ball identity.

## Specific falsifiable question

In human-labeled W5 (near apex), W6 (descending), W7 (flag / 'Nice on'), which source-triplet components are:

1. monotone across W5 -> W6 -> W7;
2. exactly or numerically equal to a **fixed pin coordinate component** at W7;
3. closer to that fixed pin component in W6 than W5;
4. also equal/near the tee component at W7?

All numeric float values are kept in the private process. Public-safe output is three rows for source-component indices 0/1/2, with direction categories and booleans; a zero/one/multiple *coincidence candidate* count. This is **not** a vertical-axis classifier: a single component matching the pin at W7 may be coincidence, camera or course-geometry variation, sloped green, a snapped endpoint/UI state or unverified units. All physical XYZ/vertical axis/gravity/velocity/timing/power/score and model training flags remain FALSE. Matching PIN is **not proven equal to ground elevation**. Any source or source-geometry mismatch ABSTAINS. Numbers, RAM paths, full hashes, floats, native code/pointers and savestates must never be uploaded.

## Synthetic tests and operator validation

Run focused 11 synthetic tests (including 1, 2 and 0 possible matching components; missing phase; invalid float; cache/owner geometry confounds; privacy; isolated import from unrelated work directory). CI exercises Windows and Ubuntu and does not use private banks. For real data, after reviewer approval, run exact pinned PR head in a clean detached worktree and use:

`py -I scripts/audit_p0_seven_axis_anchor_private.py --archive <existing SHA-pinned p0-new-cohort-*-PRIVATE directory>`

No Dolphin, controller, shot, new dump, automatic GitHub publisher or training. The script accepts the canonical #231 **p0-private-numbered-capture-inventory** archive schema, not the distinct generic seven-dump inventory manifest. It intentionally never falls back to ungated files.

S000 #205 can catalog only the *coincidence result* after an actual local audit; S002 source owner must review whether +0x30 belongs to physics vs render object and independently calibrate axes; S001 can only do future observed frame-tied trajectory after separately approved safe live sampling. Remain unmerged DRAFT until full native suite and owners' reviews.
