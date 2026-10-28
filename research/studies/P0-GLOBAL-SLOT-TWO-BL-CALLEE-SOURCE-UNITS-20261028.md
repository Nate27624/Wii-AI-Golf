# S002 P0 — Two public source callee units at global-slot writer

## Distinct source question

S002 #240's *real* original seven-bank investigation has source-backed evidence that a **fifth global ball-like object** differs from all 4 player-roster ball objects 7/7 and its candidate translation equals selected cache CC in W5/W6/W7. The **single direct global r13-slot store** in six Golf source units is `RPGolMapObjBall` +0x3084, PPC Rev1 PC 0x8029A05C, `stw r3, disp(r13)`.

Source review found a **preceding plain blr** at +0x305C, a positive literal loaded to r3 at +0x3068, `bl` at +0x3070, conditional `bc` to store at +0x3078, optional `bl` at +0x3080, and store at +0x3084. An earlier CFG starting *before* the blr falsely framed the store as unreachable from that start. **Hypothesis**: one call could allocate and an optional one initialize an object, with r3 stored afterward. Neither callee's public owner/function, entry, value, actual runtime execution or constructor role has been established.

## Contribution (new-only source-unit mapping)

`scripts/audit_p0_global_store_two_bl_public_units_private.py` does **not repeat #240 CFG**, and does not implement another arbitrary memory search. It uses #219's published **832-unit Rev1 compiled text object source index** `research/source_maps/RSPE01_01_public_text_units.json` and original private **B0** SHA-gated reader. It checks the exact return/literal/two BL/branch-to-store/global r13 load+store forms and source field anchor, then resolves **each BL destination** to the public compiled **source object unit + relative offset**, or `unknown` if not uniquely mapped. It intentionally refuses to label a function entry, allocation routine, constructor, dynamic receiver, physics ball, or shot impact.

The Python script accepts the original local B0 session via `--baseline`, default sibling data root from the trusted checkout's path; the user can run `py -I scripts/audit_p0_global_store_two_bl_public_units_private.py --baseline <PRIVATE-ORIGINAL-B0-FOLDER>`. It uses #219's original B0 `checkpoint-manifest-PRIVATE.json` and hash identity **before and after** fixed-code reads. No Dolphin, controller, game-memory write, new capture, network, ROM upload or GitHub publication. Output includes only source code PCs and public source unit-relative offsets: no PPC words, RAM bytes, heap addresses, ball floats or bank SHA.

**Key caveat**: `doldecomp/ogws` object-file source splits only map *compiled units*. They do not name exact target C++ functions and cannot establish actual `operator new`, constructor, register reaching-definition, or executed call path. This source lookup can suggest which source owner should inspect the target next. The original B0 is an idle baseline, not a verified ball-flight frame. All seven human shot phase labels remain unverified, all past shots hole 1 only, and no training approvals.

## Test/approval gate

New-only 13 fabricated adversarial tests and Windows+Ubuntu CI. Preserve existing source #219 ownership, source-global #240 writer CFG, receiver #254/#255, UI result #256, and registry #205. Draft until focused CI, native owner review, operator original private B0 run and full suite. Do not merge automatically or ask operator for new shots. If B0 code check fails, abstain rather than weakening exact instructions.

After the real result, #219/#240 owners can compare both destination public source units to known allocation and initialization functions in the published source index, *without* inventing names from proximity.


## REAL original B0 result and public symbol crosswalk (operator 2026-10-28)

The operator completed the **exact** #262 reviewed commit `737c6098ac2cfe4140710dac8f90ea7fc1c54be7` in Windows PowerShell. The command selected the original ignored B0 folder, verified its source revision, passed **13/13 local fabricated tests**, authenticated original B0 manifest SHA and game revision before/after, and printed `P0_TWO_CALLEE_SOURCE_STUDY_COMPLETE`, `P0_B0_SHA_VERIFIED_BEFORE_AFTER`. Source call destinations verified by the analyzer:

| Direct source call | Target public code PC | Unique published compiled object | Offset in object |
| --- | --- | --- | --- |
| First `bl`, MapObjBall +0x3070 | `0x800A3244` | `egg/core/eggHeap.cpp` | `+0x00618` |
| Optional second `bl`, MapObjBall +0x3080 | `0x8029AB78` | `Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp` | `+0x03BA0` |

Independent review of the published **doldecomp/ogws US Rev1** `config/RSPE01_01/symbols.txt` establishes an additional exact function-entry crosswalk: `0x800A3244` is **`__nw__FUl`**, global C++ `operator new(size_t)` (size `0x0C`), and `0x8029AB78` is **`fn_8029AB78`**, compiled function size `0x21C`. Independently the published EGG `eggHeap.cpp` implementation of global `operator new(size_t)` delegates to `EGG::Heap::alloc(size, 4, NULL)`. The published `kiwi515/ogws_info` Rev1 map similarly names `operator_new` and an **unnamed** `FUN_8029AB78`; these names are consistent, but the second target was not named a constructor by those two symbol maps.

Source citations:
- https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/symbols.txt
- https://github.com/doldecomp/ogws/blob/master/src/egg/core/eggHeap.cpp
- https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.map

**Corroborating separate owner evidence, not an inference made by #262:** The #240 source owner reports a later original W5–W7 Rev1 source-gated real BO/BI run: `cmpwi cr0,r3,0` after operator new; branch with CR0.EQ to the global-pointer store on a null allocation result; the nonnull path invokes `fn_8029AB78` before the global pointer store. Owner also cites an earlier #162 executable-derived class constructor provenance study identifying `fn_8029AB78` as RPGolMapObjBall constructor via RPGolMapObjBase and class initialization. That stronger **constructor hypothesis has distinct provenance** from this PR's purely public symbol/unit lookup and should be reviewed in the relevant source-owner PR. Its exact return-register preservation and runtime path execution are still unverified; no static source proof identifies the global object as a rendered or physics ball.

**Disposition:** #262's exact bounded test is complete. **Do not rerun identical B0 original banks or ask for any new Dolphin shot for this object-unit mapping.** The active next P0 is source-defined constructor **return-r3 preservation** and future source/cache receiver linkage, exclusively owned by #240/#219/#254. All physical XYZ, velocity, shot power, collision, scoring, timing, training and publishing flags remain unverified/false. Source owner review and full repository checks are still required before merging; draft retained.
