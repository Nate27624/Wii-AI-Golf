# P0: Full selected-player 51-word phase-mask study (driver vs wedge)

**Scope:** Pure offline, uses preserved 14 native bank files from 7 human-labeled captures; no Dolphin, new shots, memory writes, new scan or training. P0 source owner #231 retains the Rev1 player/ball/pin/tee/scene/Hole and 14-bank manifest SHA checking. Stacked on #231 with new-only script, tests, CI and this note.

## Why

Real operator source-gated W5→W6 and W6→W7 current selected ball +0x30 changes 3/3 while selected-player record offsets `+0x34/+0x38/+0x74` stayed unchanged. D1 driver airborne→D2 stopped had record `+0x34` changed but `+0x38/+0x74` unchanged. The different-club P3 putter-A-released vs D4 driver-A-held comparison had `+0x74` changed but cannot infer button/pose causality. Hence these individual fields are weak candidates for universal shot power/impact. We should check **all 51 source-selected words** within the two same-human-shot cohorts for other phase-correlated offsets, without inventing semantic labels.

## Method and evidence boundaries

`scripts/audit_p0_seven_record_phase_masks_private.py` calls canonical #231 `_check_archive`, requiring all 14 native-bank SHA hashes and original manifest. It reads only phases 1,2,5,6,7 through #231 `_get` and confirms selected record +0xCC-word stride/slot index, pointer to source ball object at record+0x88 and its translation selfref; requires unchanged player-manager, selected record/ball, FieldManager, pin/start objects and source tee/pin triplets, selected source hole and Config BC/C0/C4 within D1↔D2 and W5↔W6↔W7. Any mismatch aborts, not zero motion. The script prints only relative 4-byte offsets of **bitwise differing words** in the pre-established 51-word selected record, grouped as D1→D2, W5→W6, W6→W7, W5→W7, early-only, late-only, early-and-late, changed-then-returned, driver-vs-wedge overlap. No private u32 values, floats, pointers, bank hashes, paths, file manifests, guest memory pages or ROM bytes exposed.

`wedge_changed_only_in_6_to_7_relative_offsets` can PRIORITIZE conditional late-phase source trace, **not certify impact/landed/score**. A word might change due to score UI, camera, phase, animation or unrelated game state. The old human labels are not machine-verified shot/frame timestamps; same boot and per-pair guest-frame atomicity remain unverified, with no velocity/power/calibrated XYZ or approved training. Source string `+0x34/+0x38/+0x74` is relative to selected-player record, not absolute RAM.

## Owners and next source work

S002 #231 remains canonical SHA/source reader; #227 owns B0-B3 vs human-airborne record contrast; #219/#225 own cache semantics. This script only adds a new *within same-shot entire record* comparison to prioritize source write-site checks. S000 #205 owns evidence approval; S001 no new live shot approval. Repeat/replicate after typed source and validated clock/owner.
