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


## REAL operator source: preceding return invalidates old window CFG interpretation

At pinned #240 source head `0fd7505c2dc0e105240e63b4246dd83fe19152a2`, operator ran 13/13 and 10/10 synthetic tests PASS then all original wedge W5/W6/W7 source, geometry, pointer and native read-only gates PASS. Crucial real PPC micro-CFG result: `RPGolMapObjBall+0x3068` is `addi r3,r0,<positive immediate>` (in PPC D-form RA=0 gives literal zero-base). At unit `+0x305C` there is a return/indirect-control opcode; the helper initialized traversal at unit `+0x3058`, **before** that exit, so `bounded_cfg_paths_reach_store=false` and `bounded_cfg_reaching_r3_candidate_classes=[]` are artifacts of the hypothetically chosen window entry, **NOT evidence the only direct slot writer is unreachable or unused**.

The real code contains direct BL source sites unit `+0x3070` and `+0x3080`, and a conditional branch at `+0x3078` targeting the sole global slot stw at `+0x3084`. A program-flow hypothesis is a separate post-return source entry near `+0x3060`, followed by positive literal passed to first BL, conditional skip of second BL, and storage of a return/derived r3 value into source-global pointer slot. This resembles an **allocation + optional construction + global registration pattern** but neither BL's destination symbol was independently resolved, the post-return function entry has not been verified, and no r3 dynamic value or execution timing was measured. In particular, the first addi's positive literal is NOT by itself the r3 stored after function calls.

### New separate post-return path checker, synthetic only so far

New pure static `scripts/review_p0_global_slot_post_return_paths.py` asserts the preceding exact plain PPC `blr` (instead of any return-like op), the positive zero-base `addi`, direct BLs at +0x3070 and +0x3080, and the exact `bc` target +0x3084. Traverses a **hypothetical after-return local entry +0x3060**, distinguishing possible r3 returned from first versus second BL along the branch-taken/fall-through paths. It prints only public PPC program counter destinations for both calls, source-unit relative offsets and categorical provenance, and still explicitly declines proof of code entry, complete branch-sensitive reaching definitions, constructor/operator-new roles or runtime call execution. Calls into unrecognized dynamic control flow remain unresolved. Existing #254 owner is independently tracing the cache *receiver*, not this source-global pointer *store*.

It is wired into #240's existing W5-W7 offline `scripts/audit_p0_global_ball_source_xrefs_private.py` as `static_source_global_slot_xrefs.single_direct_slot_store_post_return_paths`. New [CI run 40650958103](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40650958103) **13/13 new synthetic tests PASS Windows & Ubuntu**, plus existing earlier-window 13/13 regression PASS on each platform. Additional source word/heap pointer/private banks never uploaded. Native post-return result **not yet run by operator**. Full repository suite and S002/S000/PR #246/#247/#249/#253 owner hardening remain pending; do not merge or approve training yet.

## Actual original wedge result: two global-pointer store call destinations and symbol resolution

Operator ran exact #240 `2b6cbfe9b8b737aa187ee509b0fb10499baa9196` against original W5/W6/W7 native 24MiB+64MiB pairs, 13/13 new post-return tests and 13/13 earlier tests passed locally; native Rev1 source-global, selected geometry and bank source checks passed. Direct PPC BL callsite `RPGolMapObjBall+0x3070` targets public Rev1 code PC `0x800A3244`. Direct BL `RPGolMapObjBall+0x3080` targets public Rev1 code PC `0x8029AB78`. Source conditional BC +0x3078 targets global slot stw +0x3084. Plain `blr` +0x305C precedes the post-return candidate. Hypothetical post-return entry can reach store with candidate r3 return from first or second BL, per initial conservative two-way BC analysis. The old earlier-window CFG `bounded_cfg_paths_reach_store=false` is not evidence of dead writer; it was seeded before preceding return.

**NOW IDENTIFIED EXACTLY from PUBLIC `doldecomp/ogws` Rev1 `config/RSPE01_01/symbols.txt` git blob SHA `ec42efd5ef247dff7920e905f9004fc579dd3f74`, cross-checked with public source `src/egg/core/eggHeap.cpp`:**

| Public source code PC | Exact symbol | Source unit and offset | Verification |
| --- | --- | --- | --- |
| `0x8029A038` | `fn_8029A038` size 0xA8 | `RPGolMapObjBall.cpp+0x3060` | VERIFIED symbol-defined actual function start, not a guess |
| `0x800A3244` | `__nw__FUl` == C++ `operator new(size_t)` | `egg/core/eggHeap.cpp+0x0618` | VERIFIED source function entry and EGG allocation semantics |
| `0x8029AB78` | `fn_8029AB78` size 0x21C | `RPGolMapObjBall.cpp+0x3BA0` | VERIFIED function entry; constructor/body behavior NOT yet proven |

Public source unit split index is independently pinned from #219's `research/source_maps/RSPE01_01_public_text_units.json` git blob `df4085de5285b0d188fdfec8c097b301382263d3`, source interval `egg/core/eggHeap.cpp` 0x800A2C2C..0x800A341C and `RPGolMapObjBall.cpp` 0x80296FD8..0x8029B240. Note: source-code addresses are public fixed Rev1 locations; no heap pointers or private bank values published.

**Correctness next gate:** Earlier post-return helper conservatively treated every `bc` as two-way conditional. PPC BO=20 could instead mean an ALWAYS branch. New pure source helper `scripts/review_p0_global_slot_symbol_nullguard.py` pins these three public symbols and asks the exact source-gated native reader to decode `bc` BO/BI and the instruction immediately following `operator new`. A `cmplwi/cmpwi cr0,r3,0` plus `BO=12, BI=2` equals an allocation-null-check pattern that skips optional second call; but we MUST let native source words decide. BO always would eliminate the second-return path from this local entry. Any unrecognized compare/BO => no null-guard proof. Even a null check does not prove `fn_8029AB78` is a constructor or that its return pointer has a specific identity.

**New test gate:** 13/13 synthetic exact public symbol/branch tests PASS Windows + Ubuntu and 13/13 earlier two-call post-return tests PASS each, [dedicated CI 40651834799](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40651834799). Tested source code commit `c5bee48ce4347b417837ce69f4e3ec6d9a01f798`; no real operator run of new BO/compare checker yet. Results will appear under `single_direct_slot_store_public_symbols_and_BO` in same #240 existing offline W5/W6/W7 audit. S002 #219 source owner notified to trace `fn_8029AB78`'s body and r3 receiver/return, NOT duplicate #240 global store analysis; #254/#255 own separate cache receiver path.

Keep all critical gates FALSE: physical rendered-ball XYZ, velocity, impact/contact, power, score, frame atomicity/guest frame IDs, function actual execution, second constructor identification, global ball role as forecast, model training, publishing. All original memory remains local read-only; owner review and canonical manifest hardening PRs pending.


## REAL 2026-10-28 W5/W6/W7: BO/BI and zero check authenticate allocator-null guard

The user executed exact reviewed pinned #240 source `fd39683205056d67e82fe1a3a5518011940365e1` against original W5/W6/W7 private native banks after 13/13 focused native-free source tests PASS. The source verifier reported `source_code_identical_across_wedge=true`, stable global slot and source-selected geometry. The new report's `single_direct_slot_store_public_symbols_and_BO` records:

- `source_function_entry_symbol=fn_8029A038` with exact public source-map entry authenticated.
- First `bl` is exact `__nw__FUl`, C++ `operator new(size_t)` (EGG Heap), public source unit entry +0x0618.
- PPC instruction after the allocation call is **`cmpwi cr0,r3,0`** (`compare_r3_zero_verified=true`), not a guessed null test.
- Branch to global store has `BO_category=CR_condition`, `CR0_EQ_bit_selected=true`, `CR0_EQ_desired_true=true`, `branch_to_store_unconditionally=false`, `requires_ctr_state=false`.
- `null_allocation_skips_second_call_pattern_verified=true`: on a zero pointer from `operator new`, the `beq`-type branch skips `fn_8029AB78` and heads to the sole r13 global-pointer slot `stw`. On nonzero pointer, the branch falls through to the second direct `bl` in the static code.
- Exact second public symbol remains `fn_8029AB78` source unit `RPGolMapObjBall.cpp+0x3BA0`; syntax checker conservatively leaves `second_callee_is_ball_constructor_verified=false`. **Independent earlier SOURCE report** `research/memory/rev1-coordinate-ball-wind-source-trace.md` (PR #162) already documents this same function at 0x8029AB78 as an RPGolMapObjBall constructor that calls RPGolMapObjBase at 0x8029AB90 and stores a class-table/data-word hint at 0x8029ABA4; it is also reused by four inline SimulateManager ball objects via the 0x8029BACC array-ctor wrapper. This evidence is distinct from this #240 BO/BI checker and strengthens the constructor interpretation, but does not by itself prove the constructor returns the same pointer on every executable path.

CRITICAL qualifiers: the two possible r3 sources at the global store are the return value from `operator new` on its **null** path and `fn_8029AB78` on its **non-null** path; these sources are not arbitrary unconditional choices. Code supports allocation → null check → candidate constructor → global assignment in `fn_8029A038`, but construction **at runtime during the captured shot**, actual return-pointer identity, independent guest frame, rendered-ball ownership, physical world XYZ/velocity/power/impact/score and training remain unverified. The separate global MapObjBall-like object pointer lies outside all four player roster balls 7/7; W5-W7 global current equals selected CC while only W7 live catches up. Do not promote cache to predicted landing target without full ownership and timing.

Next owner scope: **avoid duplicating PR #262** (already maps two BL targets to public .text compilation units) or #254/#255 receiver CFG. Narrow useful new offline work is *return-value preservation through `fn_8029AB78`* and whether the source-global runtime object's class/table/base selfrefs match `fn_8029AB78` initialization; reuse the authenticated private archive #231/#253 once integrated. Source construction semantics from original trace should be linked rather than reinvented.


## Additional distinct narrow constructor-return test after real null-guard proof

Existing independent #162 `research/memory/rev1-coordinate-ball-wind-source-trace.md` documented `fn_8029AB78` called as RPGolMapObjBall constructor (with base class constructor at Rev1 PC 0x80290A48 and source direct call at 0x8029AB90). It is reused as four SimulateManager inline ball-object constructors; the newly verified source-global pointer was a FIFTH non-roster ball object in 7/7 original captures. The code at `fn_8029A038` allocates via C++ `operator new(size_t)`, checks `cmpwi cr0,r3,0`, branches on EQ directly to the store, and otherwise calls that same ball constructor. This supports an **allocation + failure-null guard + ball constructor + global registration** source path, but constructor return-value ownership across all paths is not yet proven.

NEW `scripts/review_p0_ball_constructor_return.py` examines ONLY the known published `fn_8029AB78` function span 0x21C. It requires direct `bl` at the earlier-proven PC 0x8029AB90 to the public base-map constructor entry `fn_80290A48`; classifies early `mr r28-r31,r3` receiver-save candidates and the last supported `r3` register-writer in up to 0x24 preceding each exact PPC `blr` exit, and tags class-table-data store opcode at 0x8029ABA4. These are **syntactic hints, not full branch-sensitive reaching definitions**, and all definitive ownership, runtime allocation, renderer and physical/training flags stay false. It prints only source unit-relative code PCs and register categories (no source instruction words, native pointer addresses, floats, path, manifest hashes or raw game banks).

Integrated into existing source-gated, before/after-hashed wedge W5/W6/W7 native audit under `static_source_global_slot_xrefs.separate_global_ball_constructor_return_candidates`. It does not duplicate #262's separate two-BL public object-unit index mapping, #254/#255 receiver CFG, #219 caller whole-function trace, or #258 PPC clobber review. NEW [CI 40652790573](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40652790573) **11/11 constructor tests PASS Ubuntu + 11/11 Windows; existing symbol-nullguard 13/13 PASS each**. New REAL constructor return evidence is PENDING user's execution against original private W5-W7 bank pairs; tests are fabricated only.

Do not merge until original canonical #231 14-bank SHA trust gate and #247/#253 archive hardening have been reviewed. `allowed_to_publish=false`, model training not approved, same guest frame/real ball XYZ/velocity/power/contact/score still unknown.


## 2026-10-28 REAL constructor return study — exact reviewed source 1d250d3

Operator executed source HEAD `1d250d3bcd8d1b9ea2b78d6279c6a2713fe8e953` in a detached local Windows worktree, 11/11 constructor and 13/13 null-guard synthetic tests PASS, and real original W5/W6/W7 source-selected native memory audit PASS. The sanitized new result `static_source_global_slot_xrefs.separate_global_ball_constructor_return_candidates` reports:

| Item | Actual result |
| --- | --- |
| Exact public function entry | `fn_8029AB78`, RPGolMapObjBall, 0x21C-byte function |
| Exact BL to MapObjBase constructor | VERIFIED at unit `+0x3BB8` → `fn_80290A48` |
| Incoming `r3` source save | ONE candidate: `r31` |
| Identified plain `blr` returns in function | ONE at unit `+0x3DB8` |
| Nearest supported `r3` value-side writer | `mr r3,r31` at unit `+0x3DA4` |
| `r3` return from entry saved register | Syntactically possible TRUE |
| Class/data opcode at unit `+0x3BCC` | Integer store opcode; exact class meaning UNKNOWN |
| All paths preserve receiver and return it | FALSE / unproven |
| Runtime construction/flight or predicted endpoint | FALSE / unproven |

This independently corroborates source-level C++ constructor returning its input object pointer *candidate*, now combined with previously real-verified `fn_8029A038` `operator new(size_t)` → `cmpwi cr0,r3,0` → `beq` null-skip → `bl fn_8029AB78` → `stw r3,source-global-ball-slot`. The only missing source-level edge for constructed-pointer preservation is whether `r31` is altered along reachable constructor paths and whether `r3` can be clobbered after `mr r3,r31` before the final `blr`; even a static proof will NOT establish active runtime execution, rendered ball, world XYZ, projectile velocity, touch/contact/power/score, same guest frame, forecast role or training.

Next distinct S002 target owned by #240: conservative in-function register clobber/return suffix classification for `r31` and `r3` in exactly known public function range; source-only, no broad RAM or source scan, avoid #258 existing **different** global slot-store `r3` micro-CFG and #254/#255 cache receiver CFG. Preserve original private archive and manifest gates; no code changes or uploads outside S002. #219/#262 own source public BL mapping already concluded.


### Next owner-only native source checker: return register risks (new real result pending)

Added `scripts/review_p0_ball_ctor_return_register_risks.py` and source-gated integration, alongside 19 fabricated PPC tests and Windows/Linux workflow. It enforces exactly one incoming `mr r31,r3` in the known function entry prefix, exact `mr r3,r31` at real public unit `+0x3DA4` (`0x8029AD7C`) and exact plain `blr` at unit `+0x3DB8` (`0x8029AD90`), then classifies supported possible register r31 writes between save and final copy and r3 writes after final copy before return. It also finds possible direct branch bypass of that copy, indirect and outside function control-transfer sites. **Source-only read callback: no memory scanning or emulator action**. Outputs categorical registers, source-unit-relative PCs and risk counts, no source words, private heap pointers, bank hashes, paths, float values or human phase descriptors.

This intentionally remains **weaker than a complete PPC must-definition proof**. Some X-form effects are only conservatively POSSIBLE GPR writes; the full opcode semantics and ABI preservation across calls are NOT verified. Direct static branches are not fully path-exhaustive; a clean result only means no classified hazards were found in the inspected source. `whole_function_receiver_to_return_must_def_verified=false`, `actual_global_pointer_runtime_identity_verified=false`, `actual_inflight_execution_verified=false`, `training_approved=false`. New real native run PENDING. Existing #258 independently corrects the OTHER source-global-slot writer r3 classifier, #254/#255 independently own cache receiver, #262 owns two-BL code-unit lookup; no duplicates.


## 2026-10-28 REAL operator return-register hazard audit — exact reviewed source

Operator executed exact [#240](https://github.com/Nate27624/Wii-AI-Golf/pull/240) `25f9660cc068983999f3cc6f44915f3803f8b614` on original W5/W6/W7 private banks after **19/19 fabricated register-risk tests + 11/11 previous constructor tests PASS** on local Windows. `P0 CONSTRUCTOR REGISTER AUDIT COMPLETE`, original source/selected ball and geometry gates PASS. Exact sanitized actual source findings:

| Source claim | Observed result |
| --- | --- |
| Entry receiver source | `mr r31,r3` at `RPGolMapObjBall+0x3BB0` |
| r31 writes recognized after save before return copy | **0**, empty list |
| Return value source | `mr r3,r31` at `+0x3DA4` |
| r3 writes recognized after copy before blr | **0**, empty list |
| Bypassing direct branches to return | **false**, empty list |
| External direct branch sites and indirect branch sites | **empty lists** |
| Return instruction | `blr` at `+0x3DB8` |
| No classified r31/r3 clobber or direct bypass | **true** |
| Full PPC register classifier / whole-function must-def | **false / false** |

The result is now a particularly strong **static constructor receiver-preserving return** hypothesis. Existing independent source evidence verified first BL `operator new(size_t)`, compare r3==0, branch on CR0.EQ to store for allocation failure, second BL `fn_8029AB78` for nonnull, and global r13 singleton `stw r3`. Separate native runtime source-global object is outside all four roster balls in all seven snapshots and its translation matches selected CC in W5/W6/W7. This source result does **NOT** prove actual constructor execution during shot, source-global object class at runtime via vtable, global-vs-renderer association, predicted endpoint, same guest physics frame, physical XYZ/velocity/power/contact/score or training readiness. `all_callee_nonvolatile_r31_preservation_verified=false` and `whole_function_receiver_to_return_must_def_verified=false` remain correct; a clean bounded risk scan cannot exclude unmodeled PPC writes, dynamic branches or ABI issues.

### Research priority decision

Do NOT spend more operator compute on additional 10–20 instruction linear proximity searches to reconfirm the already strong static constructor pathway. Best next **distinct P0** is owner-approved *guest-physics-frame-qualified* dual-object observation during a human-verified no-shot control and one controlled shot, keeping source-global and selected player ball separate and checking rendered projectile association. The current [PR #248](https://github.com/Nate27624/Wii-AI-Golf/pull/248) defines a PURE offline frame contract; [PR #215](https://github.com/Nate27624/Wii-AI-Golf/pull/215) only qualifies stationary source watcher; [PR #166](https://github.com/Nate27624/Wii-AI-Golf/pull/166) is an opt-in source-selected live watcher, **NOT** a proven source-global dual-object or physics guest-frame sampler. These owners must review/integrate and pass S001/S002/S000 gates before any real Dolphin run. Do not call an ordinary bridge tick an emulated guest physics frame. Do not use the disputed operator W7 on-green label as verified physical landing or training target; see #205 corrections. No background, auto-run or writes.


## 2026-10-28 static decoder trust repair and next-run gate

Following user instruction to continue autonomous high-ROI P0 research, source owner reviewed two independent PPC decoder correctness PRs and **adopted their audited code + tests selectively into draft #240**, without merging the reviewer PRs or promoting game-memory claims:

1. **#265:** `scripts/review_p0_ball_constructor_return.py` now recognizes `r3` writes via integer load-update `lwzu/lbzu/lhzu/lhau`, integer and floating store/update `rA`, immediate op12/13 and distinguish non-writing canonical `mr r4,r3` and plain `stmw`/FP stores. It no longer mistakes an old `mr r3,r31` for a safe candidate if such an intervening `rA=r3` update is present. Adopted review code + all synthetic tests unchanged in owner branch.
2. **#258:** `scripts/review_p0_global_slot_store_cfg.py` now correctly models `rA` writes for PPC rotate and logical operations, `lmw` destination ranges, `stmw` as nonwrite, and load-update/store-update/FPR base effects. The old micro-CFG remains **bounded**, seeded before a real `blr`; its `bounded_cfg_paths_reach_store=false` was already proven a window-boundary artifact, not dead game code. Adopted reviewed code + tests unchanged.

**Verified hosted CI on exact owner head `86ec0138186119072c2caceb319549a5abe2d5dd`, Win+Ubuntu jobs completed SUCCESS:**

- [#40770298230](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40770298230): **16/16 constructor return +13/13 nullguard synthetic PASS per OS**.
- [#40770298386](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40770298386): **21/21 global store PPC CFG +10/10 writer value synthetic PASS per OS**.
- [#40770298314](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40770298314): **19/19 constructor r31/r3 write risk +16/16 corrected constructor-return synthetic PASS per OS**.

These results validate *corrected source decoders only*, not original user native RAM. The original seven-bank global-outside-four and W5/W6/W7 CC relationships are separate earlier source-gated real results. The previously real `r31` entry save and `mr r3,r31` return are source-observed but **the corrected constructor last-writer scanner and PPC CFG have NOT been run on the private native archive**. Do not claim corrected native `r3` must-def, owner-verified runtime execution, guest frame, rendered-ball XYZ, velocity, contact/score, predictor role or training.

**Stop/priority rule:** No need to ask operator to rerun these decoder tests alone; the corrected source issue is now synthetic-CI qualified. Highest-information next offline P0 is the separately owned [#268](https://github.com/Nate27624/Wii-AI-Golf/pull/268) first-use classification of 15 source-global pointer reads, *only* after it rebases/qualifies exact corrected parent #240 and has one reviewed immutable #231 fourteen-bank manifest SHA before/after operator wrapper. The other path is #248/S001 reviewed guest-physics-frame dual-object runtime and independent visual identification; bridge ticks and disputed W7 landing labels are NOT valid substitutes. Avoid another capture or shotgun heap scan until those decisions.



## 2026-10-29 support analysis — unresolved D1/D2 cross-time equality on preserved memory

The existing real seven-phase results identify a **specific untested relation**. Human D1 (operator-labeled airborne) has selected current = START = CC (3/3), but a *different* global-ball translation (0/3 equal). Human D2 (operator-labeled landed/still) has selected current = CC = global (3/3), distinct from START (0/3). Existing #233 measured within-phase equality and driver changes, while #240 established **source-global outside all four roster balls**. Neither establishes whether **D1's global translation bitpattern already equals D2's later selected current**. In contrast, W5→W7 already has such a same-shot equality at W7, so this driver relation is the missing independent shot-context discriminator rather than a fourth wedge endpoint study.

Stacked review child [#318](https://github.com/Nate27624/Wii-AI-Golf/pull/318) changes only this #240 analyzer, its existing tests and study. It adds `driver_D1_global_to_D2_selected_existing_memory_relation` computed **in the existing seven-bank read**: D1-global vs D2-selected, D2-CC, D2-global; categorical 0–3 component counts only. No additional raw read, no new Dolphin session or RAM scan, no raw words/pointers/positions/hashes/paths in output.

The reviewer **refuses** to report that cross-time comparison unless both exact source-qualified global loads succeeded, the selected source owner/hole/scene/pin/start object refs are unchanged across D1/D2, selected tee/pin triplet words are unchanged, the source-global pointer is the SAME object in both phases, and all compared vectors are validated native u32 triples. Failing any guard reports `ABSTAIN` with a public-safe reason and no equality counts. Config BC/C0/C4 equality and true same-boot/guest-time linkage are **NOT re-attested by this source-global reader**; those still depend on independent #231/owner evidence and remain insufficient for physical claims.

**Decision rules, not physical claims:**
- D1-global = D2-selected 3/3 and global pointer stable: stronger *exact bitpattern lookahead/terminal-cache candidate*, not predicted endpoint proof or renderer ownership.
- D1-global ≠ D2-selected in any component: refutes that **specific exact cross-time equality**, not all simulation/cache/forecast behavior.
- Different source-global pointer, source geometry, unsupported loads or malformed vectors: `ABSTAIN` instead of equating different objects.
- All cases: no actual physics step, axes, velocity, observed-rendered object, training or publication approval.

**Execution status:** [CI run 40809394503](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40809394503) completed SUCCESS with all focused synthetic tests on Windows and Ubuntu, at reviewed code SHA `570502019837a3fcf86da4c05f1e43b6799e8e7d` (doc-only follow-up excluded). The new **real D1/D2 cross-phase comparison has NOT been run** on the private archive until the reviewed owner explicitly chooses to incorporate and execute the changed summary against the same already preserved seven pairs. No new operator PowerShell request should be sent for this child; if owner reuses #240's canonical private analyzer later, the relation is included automatically.
