# S002 P0: Separate RPSportsSequenceMgr score array and Hitting-the-Green persisted best

## Verified source-only distinctions

1. `RPGolConfig` (Golf scene) contains `mPlayerScores[4][9]` at +0x04 (player-major), from US Rev1 `RPGolConfig.h`. #213 mapped it during B0–B3 idle/aim; **real #239 operator read** measured zero of 36 words changed in D1→D2, W5→W6, W6→W7 while source-selected ball+0x30 changed 3/3 in each edge. Thus this table was NOT a changing immediate score in those selected mode4 snapshots, but no global negation is justified.
2. A different source class `RPSportsSequenceMgr` declares singleton static pointer at `0x804BF708`, `mSport+0x04` (golf=2), `mSequence+0x08`, `mTrainingGame+0x0C`, **`mGolfScores[9][4]` at +0x14 (HOLE-major)**, and `mGolfMode+0xAC`. See `kiwi515/ogws_info/RP/RPSports/RPSportsSequenceMgr.h`. GetGolfScore/SetGolfScore are source-labeled at 0x801E7480 and 0x801E7498. Actual use by Golf mode4 (Hitting the Green) is **not verified**.
3. Independent saved-data class `RPSportsPlayerData` declares `mGolTrainingBests[3]` as `u16` at **object+0x296**; `EGame_2nd` is Hitting the Green (the middle golf training game); `reset()` initializes that entry to **30000**, source-commented **"Hitting the Green - 300.0 meters"**, other two entries zero. See `doldecomp/ogws/include/Pack/RPSystem/RPSportsPlayerData.h` and `src/Pack/RPSystem/RPSportsPlayerData.cpp`. This is persisted BEST score, not an established live per-shot value. The static C++ number/comment suggests the saved best uses hundredths of a meter, but unit conversion, code invocation and user-displayed 15.2 feet must be separately verified. Do NOT read from guessed dynamic savedata addresses.

## Unique new test

This PR stacks on existing exact #231 seven-pair private SHA and Rev1 scene/owner reader. It reads only SequenceMgr's source-known static pointer and fields; checks if instance is absent, bounds, basic enum sanity, same-shot ownership, hole/slot/source-selected ball/pin/tee/Config BC/C0/C4. For D1→D2 and W5→W6→W7, it emits solely change counts for source SequenceMgr 36 u32 **HOLE-major** slots, 9 hole-row counts, selected hole/player cell changed flag, and whether sequence/training game/golf mode changed. If singleton is null, it prints **null** changed counts, never fabricated zero. `mSport` is separately compared with Golf enum=2; table presence alone does not prove active scoring. No source offset scanning beyond the declared class.

Mode4 score semantics, game result, score/units, 15.2-ft UI, impact/frame, actual world XYZ/velocity/power and training remain **UNVERIFIED**. Human 7-file phase labels not machine attested, and native bank pairs were exported sequentially. All raw RAM, numeric table values, dynamic pointers, file hashes and private paths remain local. No new Dolphin/shot/capture.

## Operator run AFTER owner review and successful focused CI

Use exactly reviewed SHA worktree and `py -m unittest discover -s tests -p test_p0_seven_sequence_scores_private.py -v`, then `py -I scripts/audit_p0_seven_sequence_scores_private.py --archive <unique-existing-p0-new-cohort-PRIVATE>`. The archive must match #231 `kind=p0-private-numbered-capture-inventory`, contain seven paired native files with exact saved SHA, and live beneath ignored sibling `Wii-AI-Golf-Data/captures`; older `seven-dump-inventory` does NOT match the canonical schema. Full 14-bank hashes checked before and after. Real native study PENDING, do not merge/self-approve or train.

Owner boundaries: #213 Config score, #239 Config shot transition, #231 canonical seven source resolver, #235 player record, #236 ball/cache writer, #184 outcome/UI, S000 #205 registry. This is only the *separate SequenceMgr* source-bound observation.
