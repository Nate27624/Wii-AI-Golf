# S002-GOLFER-NULL-01 — does `main+0x74` change without a swing?

**Status:** preregistered, offline analysis implementation proposed; no new Dolphin trial, and actual operator raw capture has not been read in this repo branch. Source of the existing data: S002 PR #129's `capture_golfer_memory.py` private JSONL from human-approved Hitting the Green RSPE01 Rev1 read-only capture. Do not upload/reproduce those files.

## Motivation and hypothesis

S002 live operator report in PR #129: 20 snapshots (12 idle and 8 `aim_only`), maximum snapshot non-atomic span 2 emulated frames. The candidate main object word `+0x74` changed in 19/19 adjacent comparisons (17 *within phase* and two *between phase*). This sounds like a per-frame counter/animation value, not a uniquely swing-driven power measurement; it has **not** been identified or decoded. The 19 pairs share one emulated session and are NOT 19 independent swing trials.

- **Null/control question:** Does the candidate 32-bit `main+0x74` change between repeated samples while the user reports complete stationary idle, with no swing RPC?
- **Falsification rule:** Any confirmed change inside a repeated `idle` stage refutes the claim that this word *changes exclusively upon a swing event*. It **does not prove** that no power-related information can ever coexist in the same word, that the word represents a clock, or that the game accepted/not accepted A.
- **Secondary observation:** Does the unsigned modular word increment equal, or remain bounded by, the actual emulated start-frame gap on adjacent **same-stage** snapshots? This is suggestive of time dependence, not definitive counter identification.
- **Controls:** `idle (stage 0)` → `aim_only` (operator label, may reflect WASD pointer movement rather than actual 3D camera) → optionally `idle (stage 2)`. Do not infer that a stage prompt reliably changed controller/game state. Exclude both stage boundaries from specificity inference.
- **Evidence provenance:** Private local S002 JSONL includes source-gated candidate main bytes, emulation frame brackets, stable scene/main runtime identities and human labels. The offline audit rechecks consistency but **cannot independently re-verify RSPE01 revision/mode or class identity from stored rows**.

## Procedure and privacy

On the operator's Windows machine, from an isolated review checkout of this PR, run offline synthetic tests then:

```powershell
py -m unittest discover -s tests -p "test_outcome_golfer_null_controls.py" -v
py -m unittest discover -s tests -v
py scripts/audit_golfer_null_controls.py --latest
```

The command selects the newest canonical `golfer-*-RAW-PRIVATE.jsonl` from `<checkout-parent>/Wii-AI-Golf-Data/captures`. It reads locally, uses no RPC, launches no Dolphin, makes no filesystem writes, and returns **only** aggregated stage counts/rates and the relative `main+0x74` offset. It will never print private capture file names, paths, heap pointer values, raw bytes, or individual word values. No GitHub publication is initiated; operator may paste only sanitized JSON.

Inputs fail closed if outside sibling private `captures`, symlink, wrong canonical basename, >4MiB, >60 rows, missing scene/main identity, frame reversal, within-snapshot frame span >240 (flag >12 as timing limited), wrong stage order/label, malformed `0x100`-byte main snapshot. The code ignores private first-level child windows, does not dereference them, and reports no verified score/power/pose.

## Outcome categories / stop rule

1. `changes_during_idle_refutes_exclusive_swing_event_indicator`: **stop treating +0x74 as a swing-only sensor**; hand to S003 to classify as a nuisance/animation-clock candidate unless new independent evidence contradicts it.
2. `changes_only_during_pointer_control_not_verified_power`: camera/pointer confounding candidate; no calibration claim. Consider separate S001-approved A-only stationary negative control once owner-reviewed and no extra live shot until necessary.
3. `no_observed_control_change_inconclusive`: insufficient negative control, not positive power evidence.

Once data returned, compare counts per *stage*, not independent trials, and investigate whether exact frame-step agreement occurs. If existing raw files are missing/incompatible, **do not auto-trigger live Dolphin**. S002 PR #129 must be tested/reviewed/merged into canonical CLI before proposing a newly captured equivalent read-only study.

## Coordination

- Upstream S002 PR #129 owns *live* read-only candidate golfer capture and raw-file schema.
- S002 PR #122 provides independently verified static singleton slot `0x804BF4D8`.
- S000/S002 PR #130/#132 gate scene/vtable/sport; confirm consistent source IDs.
- S003 PR #125 may consume this sanitized verdict after its schema contract mismatch with #129 is resolved, but must not treat this offline output as a same-shot positive swing.
- S001 PR #112 and S003 PR #123 would be required for exact live bridge/frame-joined action specificity later.
- S000 PR #126 controls automatic public result schemas. This study **does not call that publisher**, preserving raw privacy and avoiding schema bypass.

No power identification or independent shots are claimed.

## 2026-10-25: Operator feedback and duplicate-study reconciliation

The operator reported 369 full-suite PASS on the earlier branch head and 14
targeted PASS on 162fe393. The `--latest` run initially failed because
the author's arbitrary 12-frame input limit did not match S002 PR #129's
bounded live-capture limit of 240 frames. The successful separate
PR #137 offline analyzer likewise permits 240 while labelling >12 as
`timing_limited`. Corrected here to permit up to 240 frames, emit
`max_non_atomic_frame_span`, `timing_limited` and
`frame_delta_relation_is_exploratory`, with additional synthetic tests
for 30-frame acceptance and >240-frame rejection. No evidence was
discarded or raw input published.

IMPORTANT: The operator already ran PR #137 and produced a sanitized
`golfer-controls-20261025T035036Z-1f045152-summary.json`. Treat that
study as the **primary general idle/aim specificity analyzer**. This PR
is a narrow *secondary*, relative-frame-step test solely on
`main+0x74`; do not merge duplicated analyzers or publish a second
conflicting schema. If no new insight results, archive this branch and
reuse PR #137's reviewed public summary instead.

A frame delta matching a u32 increment is not identification of a game
clock; snapshots are non-atomic, and the stage labels are human-reported.
Current head still needs fresh Windows targeted/full validation.


## 2026-10-25 REAL OPERATOR-REPORTED RESULT: FAILS SWING-EXCLUSIVE HYPOTHESIS

**Evidence:** Windows user executed `py scripts/audit_golfer_null_controls.py --latest`
against locally held S002 golfer candidate raw JSONL. Only sanitized
report JSON was shared. Synthetic targeted suite passed 16 tests and
full suite's failure guard did not trigger (full test count not copied
into the final snippet). Capture analysis **succeeded**.

- `sample_count=20`; stages in order: 6 idle, 8 `aim_only`,
  6 idle. They belong to one observed capture, NOT twenty independent shots.
- Within-stage idle stage 0: **5/5 changed** at candidate
  `main+0x074`, **5/5 u32 increments equaled elapsed frame_start delta**.
- Pointer-only stage 1: **7/7 changed**, **7/7 frame deltas equal**.
- Return-to-idle stage 2: **5/5 changed**, **5/5 frame deltas equal**.
- Total **17/17 changed**, **17/17 modular u32 increments equal sampled
  start-frame differences**. The two across-stage boundaries are
  excluded from the 17 comparison denominator.
- Maximum within-snapshot non-atomic frame span **6 frames**.
  `timing_limited=false` according to the preregistered >12 threshold.
- `independent_sessions_verified=false`,
  `human_pointer_action_verified_by_sensor=false`,
  `wii_revision_reverified_from_saved_rows=false`,
  `game_power_field_verified=false`,
  `club_pose_verified=false`.

**Result / falsification:** Candidate `main+0x074` changes even in
both human-labelled stationary idle conditions. We can **reject the
hypothesis that changes to this single word occur exclusively when a
golf swing event happens**. Perfect agreement with elapsed emulator
frame differences makes an emulation-frame counter or time-linked
gameplay bookkeeping a *strong new hypothesis*, not proof of the exact
underlying type/identity. It does **not** prove the field can never
contain power information alongside timing, nor does it establish any
physical power or score decoder.

**Action:** Demote `main+0x074` to **time-varying nuisance / possible
frame-clock control** in S002 and S003 rankings. Explicitly exclude
its raw deltas as standalone power labels/features. In subsequent
calibration design prefer fields that remain quiet during time-matched
idle and pointer controls but react to human-verified movement,
subject to same-shot frame/RPC gate (#123) and independent verified
outcomes. No more repeated idle capture of this exact word is
warranted merely to reconfirm the 17/17 pattern.

**Source limitation:** Public `kiwi515/ogws_info` names
`RPGolScene+0x9C` as `RPGolMain*`, but no source-verified member
name for `RPGolMain+0x74` has been located in the consulted
upstream data (source map confirms object-code region, not field
type). We must not label +0x74 `mFrameCounter` in code/docs until a
separate source-backed or intervention-based validation identifies it.

**Coordination:** The general per-region control study in
S000/S002 PR #137 (analyzer PR #135) already ran and is the
canonical idle/aim specificity view. This narrow PR #138 adds only
the explicit `delta_word == delta_emulated_frame` falsification
with phase-stage partition. Avoid merging duplicate production
CLI/analyzers; retain result in research ledger/handoff, and
archive or fold the narrow numeric test into #135 when owner approved.
The report intentionally remains PRIVATE LOCAL + manually shared
sanitized JSON until S000 typed publisher schema is approved.
