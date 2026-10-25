# S003-GOLFER-PROBE-GATE — Source-gated RPGolMain candidate review

**Owner:** S003 modeling, draft PR #125. This is a strictly OFFLINE consumer of S002 live-candidate probe PR #129's CURRENT **schema v2** sanitized summaries. It does not run Dolphin, send Wii inputs, publish observations, read ROM/RAM, start a second launcher, modify S002's recorder, or train a power model. The provisional code consumes the exact S002 source-anchored .sbss cell probe contract and will need updates if S002 revises it.

## Scientific question and preregistration

**H0:** A changed candidate word observed during IDLE/AIM controls is not a validated club angle, real shot power or carry. **Exploratory H1:** if one active-game-scene object chain is established with source-level + runtime checks, recurrent relative words in main/child object windows may justify a later true same-shot memory study.

Budget: zero new game trials for the offline reviewer; 1–32 existing locally SANITIZED S002 audit summaries. No inference of distinct boots from different filenames; no train/test split or held-out evaluation, and no convergence claim from off-green 100ft penalties.

## Current S002 acquisition provenance

Source-anchored two-cell RPSysSceneMgr .sbss hypothesis: [0x804BF4D8,0x804BF4E0) as described by the upstream Rev1 splits. S002 checks EGG::SceneManager current scene member +0x0C, current scene ID +0x18 =5, EGG::Scene current scene ID +0x1C =5 and parent manager backlink +0x20, RPSportsBaseScene golf sport ID +0x54=2, and RPGolScene main-object pointer +0x9C. It rechecks US RSPE01 Rev1 and RPGolConfig mode 4 before bounded 0x100-byte main snapshots. Up to 16 plausible first-level pointers into 0x80-byte candidate child windows are also read, privately, when still stable.

**Correction about +0x40**: doldecomp/ogws RPSysScene.h identifies s32 mCreatorSceneID at +0x40 as the **previous/parent creator scene ID**, not the active golf scene ID. Therefore `observed_creator_scene_id_matches_golf=false` is legitimate. My earlier call to require that boolean true was wrong; I corrected S002 PR #129 review and fixed S003 code/tests. The authoritative active scene ID gate is the EGG::Scene +0x1C field and scene-manager +0x18, with the +0x20 manager backlink.

The two .sbss cells are SOURCE-BACKED CANDIDATE STORAGE, not yet a real-game verified singleton pointer. First-level child pointers are merely pointer-shaped, not source-confirmed club/physics member pointers; never claim these point to the golfer arm, swing gauge or ball.

## S003 sanitized reviewer API

`wii_ai_golf.modeling.golfer_probe_review.review_golfer_probe_summaries(reports)` consumes only sanitized S002 schema2 `local-golfer-memory-audit` dictionaries plus no-unique-scene diagnostics; rejects raw/private fields, unrecognized source note, wrong revision/mode, missing active scene/backlink validation, duplicate report IDs, invalid stage/control counts, malformed relative offsets, and fabricated per-offset counts.

Each relative memory word is keyed by **(region, relative offset)**. A `main` +0x030 and a `child_at_main+0x024` +0x030 are DIFFERENT data sources. Parent offsets are source-relative, not absolute Wii addresses. The reviewer accounts for S002's top-100 candidate row cap and the 16-child-watch cap as **partial candidate outputs**, not complete inventories. Non-atomic capture frame spans greater than 12 frames are marked timing-limited, not fast swing observations.

The output is small and allowlisted, never echoes raw hex, runtime addresses, file paths, arbitrary comments or input free-text, and returns `real_swing_observations=0`, `confirmed_club_position=false`, `confirmed_game_power=false`, `ready_for_power_regression=false`, `estimated_power_percent=null`. Any 'float shaped' change observed during idle/aim is a NEGATIVE CONTROL, not a measured real-world strength response.

## Decision tree after operator obtains S002 summary

| Safe S002 outcome | S003 interpretation / next action |
| --- | --- |
| Zero/ambiguous source-gated scene chains | No verified gameplay owner; S002 investigates scene-manager static cell source/instance. No power model. |
| Unique source-gated chain, candidate windows static under idle/aim | No changed words under THESE controls in THESE 0x100+child0x80 windows; source-inspect true player/club ownership before adding motion |
| Unique source-gated chain, candidate words change during idle/aim | Confounded with camera/scene/time; request per-stage negative controls and verified member owner, not power response |
| Slow non-atomic frames or child-watch truncation | Timing/coverage limitation; avoid phase-level claims |
| Actual in-swing capture unavailable | Keep calibration blocked until S001 controller frames, S002 source-backed player/club fields and S000 publication gates are coordinated |

## Downstream and validation

PR #123 owns stricter *future same-shot* swing/RAM join gates; #125 is solely current local probe output triage. S000 #126 must separately allowlist new public kinds before any automatic sanitized publication; until then only local sanitized S002 `golfer-*-summary.json` may be shared, never `golfer-*-RAW-PRIVATE.jsonl`. S001 remains owner of the canonical fresh-boot first-shot dispatcher and waveform; no stand-alone exposed live attach commands.

Tests: new synthetic `tests/test_model_golfer_probe_review.py` covers current schema v2, main vs child offset separation, previous scene semantics, Rev1/mode/backlink controls, duplicate IDs, private-field rejection, bounds, slow non-atomic reads, censored-power abstention, and bounded iterables. **These added tests have NOT been run against the full canonical Windows checkout in this session.** No live game attempts were executed by S003.