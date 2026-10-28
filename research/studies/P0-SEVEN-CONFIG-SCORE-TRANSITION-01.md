# P0 — GolfConfig 36-word score table: conflicting Rev1 row orders, owner review

**Status: DRAFT, offline research only. Actual seven-capture score-table values have not been tested. No training permission.**

## Two public Rev1 annotations conflict — original PPC needed

Immutable [kiwi515/ogws_info RPGolConfig.h](https://github.com/kiwi515/ogws_info/blob/bcf62e22f9e7fc1d75acbb24bd8368b03cba1c81/RP/RPSports/RPGolScene/RPGolConfig.h)
declares `u32 mPlayerScores[PLAYER_MAX=4][HOLE_MAX=9]` at Config+0x04,
suggesting a **player-major** table. Independent
[PackProject/Kokeshi RPGolConfig.h](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolConfig.h)
(immutable `dfbdda61aadad423911d5345f67f8793aa92cd5f`, Wii Sports
NTSC-U Rev1 documented in README) declares
`u32 mStrokeTotal[HOLE_MAX=9][PLAYER_MAX=4]` at the **same Config+0x04**,
suggesting a **hole-major** table. These are two incompatible public
type annotations, NOT two independent validation results. The raw
36-u32 region, mode +0x94 and current hole +0x98 agree.

Before inspecting original PPC getter logic, **no row order is verified**.
For selected player p and relative hole h, the two potential flat indices
are `p*9+h` and `h*4+p`. Both can be emitted as HYPOTHESES,
but the authoritative `selected_player_source_hole_score_cell_changed`
must remain **null** until code resolves the conflict.
Do not call either candidate score the Near Pin result, power or contact.

New read-only study `scripts/audit_p0_golf_config_score_index_ppc_private.py`
and pinned `scripts/Invoke-P0GolfConfigScoreIndexSource.ps1` inspect only
published GolfConfig source-code ranges for the getters at
`0x8029CBD4` and `0x8029CC54` using original **14-bank SHA-verified**
Rev1 MEM1 code. Output is a bounded list of *PPC arithmetic syntax*
(mulli/shift/add/load/branch) at function-relative sites, with no
raw code words, game score values, RAM pointers or archive hashes.
This is deliberately NOT full reaching-definition proof; owner must
trace the actual argument registers before selecting the layout.

The prior real original numbered-capture **0 of 36 changed words**
for all four first-hole same-context edges remains correct regardless
of row order; absence of total score-table change is the only robust
scoring observation so far. Distinguish GolfConfig+0x04 from the separate
RPSportsSequenceMgr+0x14 table (both are 36 u32).

## Distinct question and ownership

S002 #213 originally annotated `RPGolConfig::mPlayerScores[4][9]` at GolfConfig+0x04 (36 big-endian u32) and found it unchanged during B0–B3 *idle/aim* controls. That is not evidence about an actual shot result. S002 #231's preserved seven numbered pairs provide human-labeled D1 airborne→D2 stationary and W5 near apex→W6 descending→W7 flag/'Nice on' phases. #235 owns all 51 selected player-record words, #236 owns source ball writer/cache, #184 owns any actual screen reward/units, S000 #205 owns training gates.

This new-only audit reuses #231 `_check_archive` for **all 14 private SHA-verified MEM1/MEM2 banks** and `_get` for RSPE01 Rev1 scene/mode/selected player/hole/ball/pin/tee. Adds only source-mapped GolfConfig+0x04..+0x90 score-array words and three FieldManager object-count words (+0x30,+0x3C,+0x48) and tree-shadow timer (+0x10). Only compares D1→D2, W5→W6, W6→W7 and W5→W7; never P3 putter vs D4 driver as an A-button control or driver vs wedge as same shot. Strictly refuses a changed source-selected slot/hole, object owner, BC/C0/C4 selection, pin or tee geometry within each shot.

## Output, falsification, privacy

Only 0..36 changed score-table word counts, nine changed-cell counts if hole-major, four changed-cell counts if player-major, and each *hypothetical* selected cell; the official selected-cell result stays null until PPC indexing is proven. Additional controls include 0..3 field-object-count changes, tree-shadow timer changes and selected-ball component changes. **All 36 raw table values, private hashes, paths, dynamic pointers and raw position vectors stay private.**

A stable table in D1→D2 and W6→W7 would mean this specific score array is **not a snapshot-varying instantaneous outcome signal in these mode-4 captures**. It does not mean Wii Sports has no score, that '15.2 ft' is decoded, or that a later UI transition cannot update it. A changed cell is only a source-layout observation; physical distance, success, hole-out, reward, and power still require independent source semantics and visual same-shot confirmation.

## Local operator study after code owner review

Use an exact reviewed SHA in a clean detached worktree, then run `py -m unittest discover -s tests -p test_p0_seven_config_score_private.py -v` and `py -I scripts/audit_p0_seven_config_score_private.py --archive <unique existing p0-new-cohort-*-PRIVATE folder>`. The source-gated archive must be under ignored sibling `Wii-AI-Golf-Data/captures`, with manifest kind `p0-private-numbered-capture-inventory`; the alternate `seven-dump-inventory-*-PRIVATE` format is intentionally not accepted. No fresh Dolphin, new swing, writes, raw publication or publisher calls. Reader hashes all 14 banks before and after analysis.

**Not verified**: human phase-to-file machine linkage, atomic guest frame or tick intervals, actual world XYZ/velocity, impact, game-accepted power, score/reward or units; `training_approved=false`. Full Windows repo suite, source owner #213/#231 and registry #205 review required before merging.

## Human-operated real Rev1 getter source: old suffix false negative explained

Operator ran exact #278 source `bae21e85b9706430c772359f5a6c7be82acb9bd8`
on the ORIGINAL numbered archive: 12/12 fabricated suffix tests PASS and
**all 14 original bank SHA before/after PASS**. The separate
`get_nth_hole_strokes` function yielded
`STROKES_HOLE_MAJOR_CANDIDATE=True` and
`SOURCE_SUFFIX_BRANCH_FREE=True`.

The initial first-getter flags `SCORE_GETTER_TWO_STRIDES=False` and
`SCORE_MINUS_PAR_CANDIDATE=False` were **NOT code-level counterevidence**.
The overly rigid decoder expected `lwz r3,+0x04(r3)` at +0x74 and
`subf r3,r4,r3` at +0x78; the actual source showed
`+0x70 lwz r4,+0x04(r4)`,
`+0x74 lwz r0,+0x04(r3)`,
`+0x78 subf r3,r4,r0`. The latter computes `r0-r4`.
Earlier real B0 source confirmed `mulli r5,r3,36`,
`slwi r3,r3,4` and `slwi r0,r4,2`.
Therefore **strokes minus the hole's par is a concrete, testable source
hypothesis**, not an inferred UI value.

New decoder on tested exact code commit
`1dd88821a6ca7653956382a6b1349893a14e9d2f` corrects those
register operands, updates the synthetic fixture to mirror the observed
`r0` result register, and adds independent checks:
1. `addis r6,r0,imm` at getter +0x50 followed by
   `addi r6,r6,imm` at +0x60 constructs the **public Rev1
   `RPGolConfig::sHoleInfo` symbol** candidate (boolean only).
2. Both getter candidates load roots into **r7** (score function)
   and **r5** (strokes function) from a possible **common r13 SDA slot**
   (compare code displacements, without emitting them).
3. Full effective original 14-bank source, revision, branch-free suffix and
   exact operand matches remain gated. Registered getter entry root, dynamic
   singleton value, actual live hole and selected score are NOT proven.

The new source report remains strictly `typed_score_row_orientation_fully_verified=false`
until an owner verifies the caller arguments and both base identities.
No raw private words, scores, pointers, SHA hashes, paths or capture data
are published. Do not merge/enable training based on this hypothesis.
Hosted focused synthetic tests for all current #278 suites **PASS on
Windows and Ubuntu**, [Actions run 40774802547](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40774802547).
One source-qualified operator re-read on the existing original archive is
still pending.



## Operator original 14-bank Rev1 final suffix result — all six source checks true

Owner operated exactly reviewed source commit \`1dd88821a6ca7653956382a6b1349893a14e9d2f\` in a clean worktree **sibling to the canonical ignored \`Wii-AI-Golf-Data\`**. This resolves the intervening *path layout* abstain (the incorrectly temporary-rooted worktree could not pass \`selected.DATA_ROOT\` ancestry). The operator reported \`P0_PRIVATE_DATA_LAYOUT=PASS\` and **\`P0_ORIGINAL_14_BANK_SHA=PASS\`**, meaning source files were rehashed before and after. The sanitized, authentic PPC results:

| Source-only predicate | Original Rev1 result |
| --- | --- |
| \`first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate\` | **true** |
| \`first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value\` | **true** |
| \`second_getter_16byte_row_4byte_player_column_candidate\` | **true** |
| \`public_HoleInfo_static_root_literal_matches_source_rev1_symbol\` | **true** |
| \`both_getters_load_candidate_config_root_from_same_r13_slot\` | **true** |
| \`source_suffix_branch_free\` | **true** |

Terminal \`P0_CONFIG_SCORE_SOURCE_AUDIT=PASS\`; the same exact source had 16/16 local synthetic checks PASS, while all reviewed #278 focused tests had Windows+Ubuntu success [40774802547](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40774802547).

**Strong source inference**: \`GetNthHoleStrokes\` effectively computes an address using a 16-byte row stride plus 4-byte inner index; \`GetNthHoleScore\` contains this same pointer-expression family as well as a separate 36-byte record stride. The latter independently matches public Rev1 \`HoleInfo\` size 0x24, and source \`addis/addi\` matches its published symbol; the terminal \`lwz/lwz/subf\` compares the loaded values with the difference corresponding to **strokes minus hole par**. Both getter candidate stroke roots load through the same \`r13\` small-data source slot. This resolves the formerly surprising 36-byte stride without assigning the stroke array a player-major 9-entry row.

**What this does not do**: prove all caller arguments are specifically hole/player identifiers in every mode, dereference live singleton identity, prove a displayed Near Pin result or actual stroke count update, or attest a true emulator game-physics frame. The report explicitly holds \`typed_score_row_orientation_fully_verified=false\`, \`actual_sda_runtime_pointer_value_verified=false\`, \`training_approved=false\`. The defensible status is **static source strongly supports hole-major**, not *runtime game scoring/training ready*. Historical all 36 score words unchanged remains unchanged regardless of orientation.

**Stop rule reached**: do not open another simple score-index microtrace. Parent #239 and S000 #205 should review these exact source results and label authoritative Config live-index mapping only after any additional *caller/runtime ownership* verification they require. Focus P0 resources on S001 #272 true post-game-update/guest-physics-frame source and #248/#240/#215 same-frame rendered-ball witness. No new Dolphin, shots, private uploads, merge, training or publishing.
