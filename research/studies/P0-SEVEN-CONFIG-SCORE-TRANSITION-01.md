# P0 — Source-mapped 9×4 score table during existing driver/wedge phases

**Status: DRAFT, offline research only. Actual seven-capture score-table values have not been tested. No training permission.**

## Public Rev1 layout correction — external typed evidence

An independent published Wii Sports **NTSC-U Rev1** layout from
[PackProject/Kokeshi RPGolConfig.h](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolConfig.h)
(pinned immutable commit `dfbdda61aadad423911d5345f67f8793aa92cd5f`)
defines `u32 mStrokeTotal[HOLE_MAX=9][PLAYER_MAX=4]` at Config+0x04.
**Hole-major**: `selected_cell_index = selected_hole * 4 + selected_player`.
Old `mPlayerScores[4][9]` / `player * 9 + hole` was a transposed
interpretation and should not be used to infer selected player's active score.
This documentation does NOT prove current live game mode 4 uses this table
as its displayed Near Pin result; source object and type still need the
existing B0/Rev1 archive gate. Distinguish Config's `+0x04 u32[9][4]`
from RPSportsSequenceMgr `+0x14 u32[9][4]`, two different owners.

**Important historical compatibility:** Previously published real original
numbered-capture result `0 of 36 changed words` over four same-context
edges remains valid regardless of layout. Old four-element
`score_changed_cells_per_player_row` reports are INVALID as typed
per-player aggregates: the corrected nine-element output is
`score_changed_cells_per_hole_row`. The earlier all-stable active-cell
outcome is still equivalent when all 36 are identical. Do not fabricate
new per-hole changed counts without rerunning original SHA-qualified reader.
No new shot, frame clock, physical distance, score/unit or training approval.

## Distinct question and ownership

S002 #213 already source-mapped `RPGolConfig::mStrokeTotal[9][4]` at GolfConfig+0x04 (36 big-endian u32) and found it unchanged during B0–B3 *idle/aim* controls. That is not evidence about an actual shot result. S002 #231's preserved seven numbered pairs provide human-labeled D1 airborne→D2 stationary and W5 near apex→W6 descending→W7 flag/'Nice on' phases. #235 owns all 51 selected player-record words, #236 owns source ball writer/cache, #184 owns any actual screen reward/units, S000 #205 owns training gates.

This new-only audit reuses #231 `_check_archive` for **all 14 private SHA-verified MEM1/MEM2 banks** and `_get` for RSPE01 Rev1 scene/mode/selected player/hole/ball/pin/tee. Adds only source-mapped GolfConfig+0x04..+0x90 score-array words and three FieldManager object-count words (+0x30,+0x3C,+0x48) and tree-shadow timer (+0x10). Only compares D1→D2, W5→W6, W6→W7 and W5→W7; never P3 putter vs D4 driver as an A-button control or driver vs wedge as same shot. Strictly refuses a changed source-selected slot/hole, object owner, BC/C0/C4 selection, pin or tee geometry within each shot.

## Output, falsification, privacy

Only 0..36 changed score-table word counts, nine changed-cell counts by hole row, whether source-selected player/current source-hole *candidate* cell changed, 0..3 field-object-count changes, tree-shadow timer change, and source selected ball changed 0..3. **All 36 raw table values, private hashes, paths, dynamic pointers and raw position vectors stay private.**

A stable table in D1→D2 and W6→W7 would mean this specific score array is **not a snapshot-varying instantaneous outcome signal in these mode-4 captures**. It does not mean Wii Sports has no score, that '15.2 ft' is decoded, or that a later UI transition cannot update it. A changed cell is only a source-layout observation; physical distance, success, hole-out, reward, and power still require independent source semantics and visual same-shot confirmation.

## Local operator study after code owner review

Use an exact reviewed SHA in a clean detached worktree, then run `py -m unittest discover -s tests -p test_p0_seven_config_score_private.py -v` and `py -I scripts/audit_p0_seven_config_score_private.py --archive <unique existing p0-new-cohort-*-PRIVATE folder>`. The source-gated archive must be under ignored sibling `Wii-AI-Golf-Data/captures`, with manifest kind `p0-private-numbered-capture-inventory`; the alternate `seven-dump-inventory-*-PRIVATE` format is intentionally not accepted. No fresh Dolphin, new swing, writes, raw publication or publisher calls. Reader hashes all 14 banks before and after analysis.

**Not verified**: human phase-to-file machine linkage, atomic guest frame or tick intervals, actual world XYZ/velocity, impact, game-accepted power, score/reward or units; `training_approved=false`. Full Windows repo suite, source owner #213/#231 and registry #205 review required before merging.
