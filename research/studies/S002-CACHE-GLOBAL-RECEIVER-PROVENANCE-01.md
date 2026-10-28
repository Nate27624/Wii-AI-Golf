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


## Next offline P0 discriminator: four roster slots and caller r31 assignment, real result pending

New additive `scripts/audit_p0_global_ball_roster_receiver_private.py` **reuses** original seven selected-object reader and global pointer source verifier rather than broad RAM scanner. For each original private 24MiB/64MiB pair: verify selected manager and all four record `+0x88` ball pointers, distinct MEM2 map-object buffers, per-ball translation `ball+0x4C==ball+0x30`, original selected index pointer equality, and global source pointer membership in *any* of those four pointers. Emit booleans for global in roster, selected, other inactive slot, or OUTSIDE roster; **do not print pointer values or slot index**. This is the cleanest next falsifiable separation between alternate player slot and separate simulation/global object. If any slot is unallocated/untrusted, ABSTAIN, not unsupported physical inference.

Source-only second part: two exact `bl fn_80299C70` callsite gates in known functions `fn_80299ACC` and `fn_80299C20`; scan only from each known function entry to its call for bounded PPC writes to `r31`, report first candidate definition class (e.g. `mr r31,r3`), later recognized overwrites and control-flow hazards. A plausible incoming-`r3` receiver is **not an executed r27 receiver or branch-sensitive reaching-definition proof**; no callgraph recursion or arbitrary code scan.

**Synthetic verification:** 15/15 non-skipped fabricated native-free Python tests per Windows and Ubuntu PASS in [GitHub run 40648260430](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40648260430). Includes fake four-slot roster member, inactive alias, missing/broken record, duplicate pointers, PPC r31 copy, branch hazard, overwrite, wrong BL and privacy. Existing #240 15-test direct global pointer script remained unchanged.

Real operator run on original seven snapshots **not yet performed** for the roster/r31 extension; no inferred result or simulation endpoint promotion. `global_source_is_simulation_endpoint_verified=false`, `r31_runtime_receiver_verified=false`, source RAM atomic frame, physical XYZ, velocity, score and training all false.



## Actual operator results: seven-phase global versus roster, October 28

Operator ran exact reviewed code at 1d7e1e89d1a6a78dcf29b1d0105f0fa97f85f396. All 15 local synthetic tests passed and the native read-only comparison completed on seven original paired RAM captures. In every phase 1 through 7, all four source-selected player record +0x88 ball pointers were validated and were distinct from the source-global ball pointer. Thus global_matches_any_player_slot=false for all seven; wedge_source_global_outside_all_four_roster_balls=true. This disproves the possibility that the global source was merely a different roster player's ball in these samples, but does not establish its actual role.

In both cache-update callers fn_80299ACC and fn_80299C20, the first supported r31 assignment was mr r31,r3, with no later recognized assignment or branch before that first assignment. The subsequent call passes r3 from r31 to fn_80299C70, which saves receiver r3 in r27. This is a static linear candidate chain, not a branch-complete or runtime receiver proof.

Previous seven-phase run showed the distinct global object's translation equals selected cache +0xCC throughout wedge phases 5-7, while selected current position differs in 5 and 6 and equals global/cache in 7. No frame atomicity, observed-renderer linkage, physical XYZ axes, endpoint prediction, dynamic cache writes or training approval is established.

Next owner task: source-level ownership of the separate global object and dispatch argument feeding fn_80299ACC and fn_80299C20. Other agents are already developing independent source/manifests hardening in PRs #246 and #247, and a future watcher contract in PR #248; do not duplicate them.

## Next narrow direct-pointer writer search: existing W5/W6/W7 code only

New additive `scripts/audit_p0_global_ball_source_xrefs_private.py` inherits #240 `r13` source-global slot verifier, #230 owner/scene reader and 4-slot roster identity, using ONLY human wedge phases 5,6,7 from existing native pairs. Per phase hashes banks before and after read, compares selected ball/field/pin/start source pointers plus source PIN/START triplets and owner/hole, and verifies full bounded Golf PPC text windows are bitwise identical across the three phase memories (digest PRIVATE). Disagrees -> ABSTAIN.

Inside the already published six Rev1 Golf compilation-unit .text ranges from #219, enumerate **only PPC D-form instructions whose base is r13 and signed displacement is the exact previously source-verified global pointer slot**. Classify direct `lwz/lwzu` readers, `stw/stwu` stores, `addi/addis` possible address formation and emit bounded source-unit-relative text offsets/counts (NOT any source instruction words, local addresses, runtime pointers, float values, hashes or filenames). Assert the existing exact known `fn_80299CD0` load appears. This can locate a direct global pointer writer **if one exists inside the six Golf source units**; if none, other code units, indirect store, register pointer alias or init from global data remain possible.

**Synthetic test evidence:** all 10/10 non-skipped fabricated PPC test cases PASS on Windows+Ubuntu in [GitHub CI #40649101192](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40649101192). Tests include static known load positive, store/read separation, signed displacement false positives, store-update, addi, missing known site, invalid offset, cap, safe output, isolated Python import. Actual operator W5/W6/W7 xref run is NOT performed yet; no source writer identity result can be claimed until user runs the exact reviewed code.

**Ownership:** #219 owns general caller graph, #183 owns cache update predicates, #246/#247 hardening owner should review native manifest/SHA limits, #248 future frame contract. This probe does not duplicate those, creates no emulator actions/swing/dumps, and does not approve physical XYZ/velocity, runtime receiver, training, or publication.



## 2026-10-28 REAL source-global pointer-slot xrefs: exactly one direct store

The operator executed exact pinned #240 source head 6b926d88c7a2b69037c9b900662d0a0610124ea9, with 10/10 local fabricated tests PASS. Real 5/6/7 source-gated wedge RAM comparisons and PPC text consistency PASS, with stable selected PIN/START and source-global slot, and same 3-component relationships: source-global == selected cache CC throughout W5/W6/W7, selected live != global W5/W6 and == W7.

The six published Golf .text compilation-unit windows contain 13,934 PPC instructions; EXACT direct source-global r13-slot references: 15 lwz reads, **1 stw write**, 0 lwzu/stwu, 0 addi/addis pointer formation. All 16 references lie in RPGolMapObjBall source unit. Sole direct source-global pointer-slot writer at **RPGolMapObjBall +0x3084**, equivalent to public RSPE01 Rev1 source PC **0x8029A05C**. This identifies an instruction capable of writing that pointer, NOT an executed initializer, owner, constructor, in-flight writer or score/velocity signal. No raw native instructions/heap pointers/bytes/hashes published. Other source units, linked library code and indirect stores remain unexamined and possible.

The next target is the STORE VALUE (PowerPC stw uses source register in bits 21-25). Does the writer store a zero/null value (destructor/cleanup hypothesis), a saved receiver, newly allocated object or other computed pointer? New code in scripts/audit_p0_global_ball_source_xrefs_private.py adds a **bounded exact source-only register-writer classification** at that single code PC, without extending memory searches or claiming branch-sensitive reaching definitions. It prints only register label and categorical nearest recognized definition class, whether a control transfer intervenes, and explicit FALSE for runtime register value / executed writer. The examined window starts after the previous source-identified cache writer routine, but is NOT an independently verified function entry. Synthetic tests include literal zero, register move, memory-load source, branch hazard, wrong store and privacy. The real source-store-value result is pending user execution of pinned revised branch.

Keep false: global owner function, source-global as simulator/forecast, cache receiver identity, active shot execution, world XYZ, guest-frame atomicity, velocity, power, collision, score, training and raw publication. Coordinate source ownership with #219 and #183; the reader hardening in #246/#247 and watcher contract #248 are independent.


## REAL source-global direct writer value probe — 2026-10-28

Operator ran exact source revision `6cf36c094b6b1a7d6fbed234fc5d4f90c858ffb8` with local 10/10 synthetic tests PASS and read-only original wedge W5/W6/W7 source and geometry checks PASS. Sole direct global slot `stw` at `RPGolMapObjBall+0x3084` (public Rev1 PC `0x8029A05C`) stores from **r3**. The nearest *recognized* bounded assignment to r3 is an **addi_OTHER** at `RPGolMapObjBall+0x3068` (public Rev1 PC `0x8029A040`). There is at least one control-transfer hazard AFTER that assignment and before the stw. The original audit explicitly returned `source_register_reaching_definition_fully_verified=false`, `store_value_runtime_zero_verified=false`, `source_writer_ran_during_wedge_verified=false`, and `source_value_may_be_zero_candidate=false` (limited syntactic hint, not proof of nonzero runtime value). Do not identify the writer as constructor, finalizer, zero store, or global simulation owner on this evidence alone.

### Additional branch-bounded source-only discriminator (native real run pending)

NEW `scripts/review_p0_global_slot_store_cfg.py` is a **pure static micro-CFG analyzer** called from the existing W5/W6/W7 source-gated xref script. It checks exact previously verified stw slot and reviewed addi r3 at the one known PC, and reports source `addi` base-register class and sign/zero of its signed immediate; bounded `b/bc/bl` edges and whether a local path from a *hypothetical window entry* reaches the store with one or multiple recognized last-r3-definition classes; exit, function-call clobber, and outside-window incompleteness flags. It NEVER claims source function boundaries, complete PPC reaching definitions, active runtime store execution, zero vs nonzero runtime pointer value, or object ownership. Calls and unknown branches are treated conservatively. The code only consumes the original source-checked private RAM read callback; it cannot launch Dolphin or expose RAM/ROM instruction words, heap pointers, private paths, data-bank hashes or floats.

Fabricated adversarial unit tests in `tests/test_p0_global_slot_store_cfg_private.py`: 13/13 PASS on Windows and 13/13 PASS on Ubuntu; existing writer-value 10/10 PASS each in [dedicated CI run 40650349748](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40650349748). Exact code head `556c0792d2c71c82dcc31c55d37bb1b29ebb62b7`, BEFORE this documentation-only commit. **This new CFG result has not yet been run on the original native memory; no inferred branch targets or runtime values are claimed.** PR #254 separately owns whole caller-r31 CFG for the **receiver**, not the global pointer writer; this new helper does NOT duplicate it.

Explicit verification flags remain FALSE: global ball's function owner and simulation role, actual execution during shot, r3 value at store, cache receiver runtime identity, original MEM1/MEM2 same physics frame, physical XYZ axes/units, ball velocity, power/impact/score, training and public raw publication. #246/#247/#249/#253 preserve other agent hardening responsibilities.
