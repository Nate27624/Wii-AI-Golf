# S002 P0: source-global ball versus cache receiver provenance (Rev1)

## Specific target and existing ground truth

On the real 7-pair 2026-10-28 human-labeled driver/putter/wedge snapshots, S002 #230/#231/#236 verified that the **source-selected** ball object+0x30 changes 3/3 components in W5→W6→W7, player record+0x54/+0x60 remains constant, PIN/START and source object pointers stable, while cache+0xCC stays constant and equals the W7 source-selected ball at the end. But D1 visibly airborne nevertheless had current selected ball+0x30 equal START 3/3; model must not conflate the rendered ball and source-selected simulation-ball object. No guest-frame or axes/units proof.

Existing [#183](https://github.com/Nate27624/Wii-AI-Golf/pull/183) source validates **`fn_80299C70`** at 0x80299C90 saving r3 receiver to r27, at 0x80299CD4 following a distinct source-global ball object's translation+0x4C, writing its three f32 components to receiver+0xCC..D4; plus conditional goal-relative +0xF0 and middle-component +0xFC updates. [#219](https://github.com/Nate27624/Wii-AI-Golf/pull/219) established exact source callsites MapObjBall+0x2B8C (in fn_80299ACC) and +0x2C80 (in fn_80299C20) targeting `fn_80299C70`. Neither guarantees the receiver r3 is the current player-selected ball, nor execution in the wedge time window.

## New narrowly scoped probe

New `scripts/audit_p0_cache_global_receiver_private.py` **reuses #230 exact source-selected scene/player/hole/ball/pin/start reader** against all 7 existing private native bank pairs; checks original 24+64MiB bank lengths and before/after SHA256 on each pair. It checks PPC source signed D-form FieldManager r13 small-data anchor at 0x80299EE4, translation follow at 0x80299CD4, r3→r27 receiver save at 0x80299C90, then tests whether source `0x80299CD0` is exactly `lwz r3, disp(r13)`; if not it **reports unsupported**, rather than inventing a global address. If yes, derive the source-global word slot from public field singleton 0x804BF868 at -23320(r13), check the pointee is a valid MEM2 object with base+0x4C→base+0x30 constructor selfref and compare **only 0..3 equality counts** of source-global position vs source-selected current ball, cache+0xCC and fixed start. It also tests source-global pointer identity across W5,W6,W7 (never emits pointer).

Two **exact** `bl` sites are gated for targets to fn_80299C70, with bounded 0x40-byte backward static register-r3 definition classes (`mr_from_r31`, `lwz_from_rX`, etc.) and branch hazard flags. This is linear source syntax; *not* guaranteed true reaching definition over arbitrary branches/calls, not runtime r3 receiver. No attempt to identify an arbitrary pointer by numerical float scans. No new global source-map copy.

## Qualification / limits

Do NOT label source-global as simulation/prediction/live ball unless source-backed object owner validated against all 7 phases and static receiver provenance made explicit. Even if global pointer equals the selected ball, cache r27 receiver is separately unverified. Even if it differs, static global alias may switch dynamically between off-screen simulation and renderer. More stringent next step, if this audit narrows it, is owner-approved code-path-specific live watch with independent guest-frame and rendered-ball association. `cache_writer_executed_in_human_wedge_phases_verified=false`, `actual_ball_world_xyz_verified=false`, `ball_velocity_verified=false`, `training_approved=false`, `allowed_to_publish=false` regardless of static dataflow.

## Privacy / ownership

Existing source agents own static PPC disassembly (#183), aggregate caller map (#219), source reader and seven data (#230/#231), source/caches (#225), registry (#205). This PR only adds **runtime global source pointer identity comparisons** and bounded receiver input candidate classes. All native RAM, instruction words, precise pointers, hashes, float bits and user-private paths stay on local Windows. No Dolphin, shot, new capture, game ROM, nonprivate output file, uploads or training. Synthetic-only hosted CI before first operator execution. Remain draft pending owner review and full suite.
## 2026-10-28 ACTUAL seven native source-global operator run — exact code 2c05d59

Operator executed exact S002 #240 source code SHA `2c05d598421228929dd14d97dd9e18727007b735` against seven original native bank pairs, after 15/15 local synthetic tests PASS; `P0 GLOBAL RECEIVER STUDY COMPLETE`. All 7 source-global source-load forms were supported and source-selected identity gates passed. Source anchor r13 uses `lwz r3,disp(r13)` followed by `lwz r3,0x4C(r3)`. Source-global object is **NOT the source-selected player's ball object in any of 7 phases**. Its pointer stays identical across W5→W6→W7. A distinct object is now established for these snapshots; its class, simulation vs render role, and writer/consumer schedule remain unverified.

| Phase | Source-global == selected ball pointer | Global translation == selected current (3 components) | Global translation == selected CC cache | Global translation == source START |
| --- | --- | ---: | ---: | ---: |
| 1 driver human-labeled airborne | false | 0 | 0 | 0 |
| 2 driver stationary | false | 3 | 3 | 0 |
| 3 putter A released | false | 0 | 0 | 0 |
| 4 driver A held | false | 0 | 0 | 0 |
| 5 wedge near apex | false | 0 | 3 | 0 |
| 6 wedge descending | false | 0 | 3 | 0 |
| 7 wedge flag/on green | false | 3 | 3 | 0 |

For both static MapObjBall callsites (`fn_80299ACC` and `fn_80299C20`), direct BL into cache writer `fn_80299C70` is source-verified and the nearest bounded pre-call `r3` definition class is `mr_from_r31`; **each window has control-flow hazards**, so no reaching-def or runtime receiver identity was proven. `r3→r27` inside callee remains source-verified. No evidence that cache writer executes between W5/W6 or W6/W7; no independent guest-frame timing. User supplied output only (no raw bank, precise memory pointer or word upload).

**Next discriminating step:** determine whether the source-global object is any of the FOUR player roster ball pointers (rather than an independent simulation/global object), and whether each caller's persistent `r31` is copied from its incoming `r3` receiver. These are distinct from existing #219 broad source caller scan and #183 cache arithmetic. If source-only tracing cannot prove receiver across control flow, explicitly leave it unresolved. Do not promote the observed CC match to a verified predicted endpoint, position XYZ, velocity, score, power, contact or training.

