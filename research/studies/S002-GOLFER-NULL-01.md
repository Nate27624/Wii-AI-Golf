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


## Cross-check: separate already-PUBLISHED S002 all-child control study

Reviewed public sanitized record
`research/observations/20261025T034248Z-7c597d65.json`
(`kind=golf-golfer-control-specificity`, 20 snapshots, 16 watched first-level child regions,
`idle_opportunities=10`, `aim_opportunities=7`,
`max_non_atomic_frame_span=18`, `timing_limited=true`).
It lists **exactly 4 changing relative words**; **each** changed on
10/10 same-stage idle pairs and 7/7 pointer-only pairs:

- `main +0x074` (our explicit 17/17 frame-delta match applies to a
  DIFFERENT private capture; do not transpose its numerical increments).
- `child_at_main+0x008 +0x050`
- `child_at_main+0x020 +0x038`
- `child_at_main+0x044 +0x060`

All were classified `background_dynamic`. The existing public record
contains *change counts*, not the actual per-pair value/time deltas, so
it CANNOT prove the three child words track the emulation frame count,
that they are each other, or that they share a clock. Do not infer
cross-object numerical equality from matching 10/10 + 7/7 frequencies.

**Best next independent research if scientifically justified:** reuse
ONLY this already-captured private 16-child raw JSONL for a predeclared,
bounded comparison of these three explicit child relative words against
both `main+0x074` and observed `frame_start` deltas **within identical
stage intervals**, report counts/lag/range summaries only and mark
`timing_limited` whenever source snapshot span exceeds 12 frames.
No raw data or addresses in public output, no new swings or pointer sweeps.
Prefer extending existing owner-reviewed source #135/#137 rather than
creating another competing general purpose CLI. If a source-backed
class layout or cross-stage time-matched negative control explains
the candidates first, skip a new empirical study.

The two 20-sample records should NOT be described as independent
Dolphin boots unless their per-boot provenance is actually checked.


## S002-GOLFER-FOUR-CLOCK-02 — four-word *same-capture* comparison (proposed)

Operator approved proceeding after main+0x74 exact frame-step matching 17/17
in a shorter capture. Independent public #135/#137 summary
`20261025T034248Z-7c597d65.json` reports exactly four background-dynamic
words in 20 samples with 16 children: `main+0x074`,
`child_at_main+0x008 +0x050`, `child_at_main+0x020 +0x038`,
and `child_at_main+0x044 +0x060` (all 10/10 idle + 7/7 aim).
**These four have NOT been numerically compared in the same raw capture yet.**
The 17/17 numerical match at main+0x74 was a *different* 20-sample file;
it must not be projected onto child words without testing.

`scripts/audit_golfer_null_controls.py --latest-four` now automatically
selects the newest pre-existing canonical private raw file with all three
**specified first-level child windows**, without echoing filename or
addresses. It parses up to 60 rows, checks source collector's fixed
main/child sizes, stable source-private scene/main/child identities,
chronological same-stage frames and stage order. **No new capture**.
Alternatively `--input <canonical private path> --four-clock` selects
one particular capture. Outputs JSON **only** with relative region/offset
names, per-stage counts, and safe categorical metadata. No writes/uploads
or live Dolphin/bridge interactions.

Predeclared tests across adjacent pairs **WITHIN one human-labelled
stage only**:

1. Child and main modular unsigned 32-bit word increment vs observed
   `frame_start` increment; count exact matches and changed-pair denominator.
2. Each child incremental difference vs `main+0x074` *on the same pair*;
   count identical common-mode changes, no raw values published.
3. **Shifted-gap negative control:** compare a word's delta for one pair
   to the following pair's frame gap. Count its false matches.
4. Count distinct observed frame gaps (sampling cadence diversity).
   If cadence is constant, a perfect 17/17 delta/frame match is
   insufficient to distinguish frame-tracking from a fixed-rate
   sample-index counter, because the shifted control matches as well.
5. Keep per-stage (idle-before, aim-only, idle-after) opportunities and
   never treat two transition boundaries as evidence of a response.
6. Signal `timing_limited` if any non-atomic read window exceeds 12
   frames; gate out values over 240 per the source collector contract.
   Relative words in different child windows can have different actual
   within-snapshot read instants, so equality is exploratory.

**Decision:** Stronger time-candidate evidence requires variable observed
frame gaps, high correctly aligned matches **and low shifted-control
matches**, consistent within both idle stages. If gaps are constant,
`varied_frame_cadence_observed=false` and inference is INCONCLUSIVE.
Even strong evidence does not source-name an object member or verify
club pose or power. If a child field fails exact timing equality but
changes during idle, it is another background nuisance until more
specific positive/negative tests exist. One capture is not independent
sessions.

Tests: `tests/test_outcome_golfer_null_controls.py` adds eight
synthetic tests for variable-frame positive, constant-cadence
adversarial case, nonclock child, missing/invalid child pointer,
relocation, bounded slow snapshot, newest compatible private file
selection and CLI privacy. Windows host validation pending.

### Existing prior art and appropriate reuse

- **redoste, "Modding Wii Sports: Part I" (2020)**
  https://redoste.xyz/2020/04/21/modding-wii-sports-part-i-identifying-files-and-creating-a-debug-output/
  is specifically about original Wii Sports **golf**. Uses local
  main.dol + Ghidra/Dolphin, correctly documents `r13` EABI Small
  Data Area access and class/xref reconstruction. Its European
  *revision 2* disassembly locations are NOT compatible with RSPE01 Rev1.
  Valuable technique to repeat AFTER the numeric falsification:
  locate writer `stw`/possible `stfs` of a source/behavior-validated
  word and inspect instruction flow. Do not transplant absolute addresses.
- **Dolphin Memory Engine**, MIT:
  https://github.com/aldelaro5/dolphin-memory-engine
  supplies watchlists and changed/unchanged value scanning; our
  no-install offline comparison reuses the general method, not code.
  No extra reader should perturb existing S001/S002 frame sampling.
- **JackPriceBurns Dolphin GDB debugger MCP**:
  https://github.com/JackPriceBurns/dolphin-debugger-mcp
  demonstrates symbol-aware **write watchpoints** that can identify
  *what instruction modifies* a field. Integration would require S001
  approval and a verified paused/session-gated debug build, not a
  replacement input launcher or automated memory modification.
- **doldecomp/ogws**:
  https://github.com/doldecomp/ogws
  is the current matching Wii Sports decomp and source for scene
  layouts; it does not yet verify a named `RPGolMain+0x074` field
  or gameplay power word based on the checked sources.
- **PackProject Caddie**:
  https://github.com/PackProject/Caddie
  is GPL-3.0 **Wii Sports Resort** Golf practice mod, not original
  Wii Sports. Useful precedent that reverse-engineered golf engine
  hooks exist, but the other game and license make direct copying
  inappropriate without separate design/license analysis.

No outside project found during this search provides a verified
drop-in swing-power mapping for our exact US Rev1/Hitting-the-Green
target. Research and validation should be explicit about that gap.
