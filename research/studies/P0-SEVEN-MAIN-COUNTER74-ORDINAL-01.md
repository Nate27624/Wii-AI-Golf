# P0/P1 clock confound: source-selected RPGolMain +0x74 across seven real phases

**Scope:** new offline read-only, source-gated `u32` **counter hypothesis**. No RAM writer, controller, Dolphin startup, new dump, dynamic scan, numeric word publication, time/velocity/power/training promotion or duplicate selected-player 51-word study.

## Why this is worth testing

S000 registry `golf.unknown_main_counter` identifies the **Golf scene Main object +0x74**, which changed monotonically in historical stationary B0-B3 aim/idle snapshots (numerically 6048, 6410, 9012, 9591). Earlier [PR #135](https://github.com/Nate27624/Wii-AI-Golf/pull/135) explicitly observed this main-relative +0x74 changing 19/19 in a **20-frame study** and suspected background dynamics, not swing power. It is **not** selected-player record `+0x74` (a different object); do not conflate. The latest seven new D1/D2 and W5/W6/W7 captures include selected-ball motion but still lack independently stamped game-accepted guest frames. This candidate is an opportunity to test **counter behavior versus source-selected motion**, or reject simplistic "main+0x74=impact/power" interpretations.

A field that increments while the ball is perfectly still could eventually prove useful as a guest-game timebase *if* a source code writer and per-guest-frame rate are independently established. At present no such proof exists. Even numeric monotonicity in these seven human-labeled phases cannot convert `+0x74` into actual frame numbers.

## New tool

`scripts/audit_p0_seven_main_counter74_private.py` reuses exact canonical [PR #231](https://github.com/Nate27624/Wii-AI-Golf/pull/231) full **14-bank SHA/manifest verification** and Rev1 scene, sport, mode, hole, selected player, source-ball, pin and tee reader for all seven numbered captures. It adds ONLY a **registered** anchored read: `scene_mgr_static -> manager+0x0C scene -> scene+0x9C RPGolMain -> main+0x74 BE-u32`, with MEM2 address range and Main class/vtable source-region guard. Selected ball pointer `record+0x88 -> child+0x4C == child+0x30` verified as same source. Source geometry controls and `Config+0xBC/+0xC0/+0xC4` unchanged within D1-D2 and W5-W6-W7.

It compares ONLY original human same-shot edges D1->D2, W5->W6, W6->W7 and W5->W7, never treats P3 putter A-off vs D4 driver A-on as causal A intervention. The only reported data are `unchanged`, `numerically_increased`, or `numerically_decreased_or_wrapped_unknown`, 0..3 ball-change counts, and a categorical relative order of wedge numeric deltas *if both are positive*. A decreasing `u32` could be reset/wrap, not observed negative time. It never prints counter values, frame deltas, numeric vectors, private paths, SHA hashes, native code/heap addresses or raw data. It always returns `counter_is_guest_frame_number_verified=false`, `counter_is_swing_power_verified=false`, `training_approved=false`.

**Important:** this is about **field classification**, not mapping every memory address. Unknown P0 velocity, impact, accepted club/power, signed heading, shot score and physical XYZ remain unverified until source and timed controls prove otherwise. The table of 22 registry entries is a catalog of candidates, not 22 verified physical variables.

## Review gates

Focused 14 fabricated tests on Windows + Ubuntu cover all changed/unchanged/wrap categories, strict owner/scene/geometry and Config mismatch, malformed u32, 14-bank original SHA gate before any RAM read, privacy bounded output, and isolated Python -I from another working directory. CI runs no native RAM. S002 source code owner must review whether `main+0x74` is a counter and how it's updated. S001 must not treat numeric increments as applied game frames without exact per-frame controlled evidence and explicit human confirmation. S000 retains zero training approval.

For a local operator real run, after exact PR SHA and focused CI are verified, use ONE pasteable PowerShell 5.1 block to choose the existing **canonical p0-new-cohort-*-PRIVATE** archive by source manifest/14 SHA (do not substitute the earlier generic seven-inventory without conversion) and run `py -I scripts/audit_p0_seven_main_counter74_private.py --archive <verified canonical archive>`. Review sanitized printed categories only; no live Dolphin launch or new shots.


## CI status — actual cross-platform result (2026-10-28)

Exact tested code/CI head `ef33c52137d29b669b5069068f58e52fb9094964`: [GitHub Actions run 40647419445](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40647419445) **SUCCESS**, 14 synthetic tests passed on `windows-latest` and 14 on `ubuntu-latest`, including isolated Python -I smoke. Four-file-only PR [#238](https://github.com/Nate27624/Wii-AI-Golf/pull/238) remains DRAFT and stacked on canonical #231; operator real seven-phase RAM results PENDING. A CI pass is a source/fixture test, **not** evidence of actual counter advancement or frame rate. S000 variable registry entry updated as test-pending, 0 training approvals.


## Real local seven-snapshot operator result (2026-10-28)

The operator independently executed reviewed PR #238 commit `1475cb8f12a2f0a0f020493488eebf7f552204f3` from a clean detached worktree on the canonical SHA-preserved seven snapshot cohort. Focused **14/14 Windows synthetic tests PASS**, source archive `_check_archive` and all scene/Main/selected player/ball/pin/tee/Config gates PASS; output marker `P0_MAIN_COUNTER_74_ANALYSIS=COMPLETE` with no Dolphin launch or raw RAM output.

| Human-labeled same-shot interval | Selected ball+0x30 changed components | RPGolMain+0x74 numerical u32 comparison | Source owner/geometry |
| --- | ---: | --- | --- |
| Driver D1 airborne -> D2 settled | 3/3 | increased | stable |
| Wedge W5 near apex -> W6 descending | 3/3 | increased | stable |
| Wedge W6 descending -> W7 flag/UI result | 3/3 | increased | stable |
| Wedge W5 -> W7 | 3/3 | increased | stable |

**W5 < W6 < W7 for this native `u32`**, and `W6-W5 < W7-W6` numerically (the second numeric jump was larger); no actual counter words or numeric deltas were published or used as machine timestamps. This correlates change with elapsed *operator-reported* shot phases, **not** with motion-specific source semantics. Previous stationary B0-B3 and 19/19 no-shot observation make shot-power, contact and impact assignment especially unjustified.

**Classification:** `RPGolMain+0x74` is an *increasing background/elapsed-state counter candidate* (source-owned dynamic `u32`). Not yet a verified frame count/timebase, applied game tick, same-boot monotone counter, shot power or training feature. Larger later gap may simply reflect longer pause between exports, GUI timing, missed frames, non-atomic memory banks or counter rate, not faster ball.

**Next S002 source work:** narrow bounded PPC writer/read reference for the typed Main receiver +0x74; independently classify whether increments per frame, event, idle phase or pause using separately approved read-only game frame instrumentation. Do not map selected-player-record +0x74 to this field. No additional broad RAM scan or new shot warranted.
