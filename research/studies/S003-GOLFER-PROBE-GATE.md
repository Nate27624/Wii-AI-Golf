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
## First actual live source-gated object-graph study — operator returned

Stage A2 (2026-10-25 UTC) was conducted by the operator under canonical fresh-boot S001 launcher and S002 PR #129 memory probe. 20 snapshots (idle6 → aim_only8 → idle6; aggregated idle12 aim8), one validated source-constrained Golf scene/object pointer chain from the two Rev1 .sbss candidates, 7-frame initial census span, max 18-frame non-atomic sample. Sixteen pointer-shaped candidate child windows were sampled out of a **truncated** first-level inventory. This does NOT source-verify these child objects as golfer/club or decode a numerical power sensor. No swing was sent.

Sanitized changed 32-bit word evidence:

| Candidate region | Offset | Within-stage | Stage boundary | Plausible floats |
|---|---|---:|---:|---:|---:|
| main | +0x074 | 17 | 2 | 0 |
| child_at_main+0x008 | +0x050 | 17 | 2 | 0 |
| child_at_main+0x020 | +0x038 | 17 | 2 | 0 |
| child_at_main+0x044 | +0x060 | 17 | 2 | 0 |

All four change on **19/19 consecutive samples**, including 17 within-stage and two stage-boundary transitions. This favors *continuously advancing clock/counter-like* state over movement-specific state, but **step sizes, equality of deltas, and source member semantics were not examined**. No game power, club angle, speed or physical carry is identified. The local S003 reviewer was patched to accept S002's current creator-scene semantic `creator_scene_id_not_used_for_identity=true` rather than its obsolete field. It validates which child offsets actually appeared in `first_level_child_parent_offsets`, marks 19/19 continuously changing candidates and flags non-atomic-frame-span timing.

### New offline private-timing discriminative study S003-MEM-02

**No new game run first.** The existing S002 private JSONL contains 20 already recorded 0x100+0x80 object windows; use the new S003 analysis locally to determine: whether four u32s advance monotonically, by a constant integer step, in exact proportion to game-frame gaps, and whether they have identical 19-step delta sequences. The checker independently reconstructs S002 within-stage/boundary counts from private bytes and aborts if the sanitized report disagrees. It never emits actual word values, numerical deltas, absolute RAM pointers, frame timestamps or paths, and creates only an operator-local `-temporal-summary.json`. It does not upload anything. All interpretations remain negative controls because no real swing occurred.

**Operator Windows PowerShell (OFFLINE; use a clean isolated S003 PR #125 detached worktree; do not overwrite any existing worktree):**

~~~powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Temporal-S003"
$branch = 'agent/modeling/memory-informed-power-20261024'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path $work) {
  if (git -C $work status --porcelain) { throw 'Existing S003 worktree has changes' }
  git -C $work switch --detach "origin/$branch"
} else {
  git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
py -m unittest discover -s "$work\tests" -p 'test_model_golfer_temporal_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Timing tests failed' }
py -m unittest discover -s "$work\tests" -p 'test_model_golfer_probe_review.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Sanitized schema tests failed' }
$dir = "$root\Wii-AI-Golf-Data\captures"
$raw = "$dir\golfer-20261025T035348Z-6416c272-RAW-PRIVATE.jsonl"
$summary = "$dir\golfer-20261025T035348Z-6416c272-summary.json"
py "$work\scripts\analyze_golfer_temporal_private.py" --input $raw --summary $summary
if ($LASTEXITCODE -ne 0) { throw 'Local private timing audit stopped; NO upload' }
~~~

**Pass/fail decision:** For constant monotonic or frame-coupled strides across all 19 transitions with indistinguishable idle/aim behavior, deprioritize these four offsets as power sensors; owner S002 should source-disambiguate true player/club object members. If delta patterns differ, preserve them as **unknown candidate temporal state**, not power. A future optional independent fresh-boot source-gated S002 probe can cover remaining child-pointer candidates via the already implemented `--child-start 16 --child-limit 8` with at most 16 read-only snapshots to reduce frame span; **do not run before considering existing offline evidence**. These are negative controls; the next real swing sample needs per-shot/bridge/waveform IDs, direct club/gauge field ownership, frame alignment, and no duplicate launch.

**Privacy:** all private RAM remains exclusively on operator PC. Only user-approved local summarized booleans/counts can be pasted into chat. S000 PR #126 public schema does not yet allow the S003 timing summary kind; never GitHub-publish the raw files or the timing summary through an ad hoc uploader.
