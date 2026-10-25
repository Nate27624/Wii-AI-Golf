# Memory-first swing power system identification (S001/S002/S003)

**Status:** research protocol and cross-agent contract; not a working live collector or a claim that a power address is known.

## Why the current power-map study is low-information

Operator-confirmed golf contacts at speed-scale 0.8, 0.9 and baseline 1.0, plus backswing-distance-scale 0.8, repeatedly showed approximately **75% human-read power**. The result `100.0 ft` for off-green shots is a **penalty/censored score, not a measured carry distance**. Do not regress power or distance against that output.

An S002 offline public `golf-memory-phase-differential` observation (`offline-20261025T024447Z-a37ee401`) found 21 changing aligned words, all in **minimap effect/rendering** regions, with a **22-frame span** across each non-atomic sample. There is no confirmed ball physics, club pose or power field. Existing canonical `collect_outcome_transition.py` reads only **pre**, **post** and **settled** snapshots, **not during swing**; it can therefore miss a transient power register entirely.

Current source-backed static pointer windows `RPGolConfig`, `RPGolFieldManager` and `RPSportsSequenceMgr` are game configuration/field/score-oriented, not documented club power storage. `RPGolScene` reportedly contains an `RPGolMain*` at **scene-instance-relative +0x9C**, but the actual scene-instance base and downstream structure remain unknown. Do **not** dereference guessed addresses. See S002 PR #109, https://github.com/kiwi515/ogws_info, and docs/golf-memory-discovery-plan.md on S002's branch.

## Research objective (ordered gates, not a blind 10-hole sweep)

1. **Locate gameplay-owned RAM**: S002 traces a **source-validated** `RPGolScene -> RPGolMain -> active golfer / swing` chain if available. Keep any addresses/private bytes in local RAW-PRIVATE only. Also characterize static control windows: score/mode, camera or minimap fields are **negative control**, not the presumed power location.
2. **Collect a same-shot, frame-bracketed experiment**: S001 and S002 attach bounded RAM reads to the **same live shot**, not a separately launched read-only experiment. Capture intervals: idle, A-only prehold, backswing, forward stroke **before impact**, at/after contact if measurable, early flight, settled. Use a shared explicit `shot_id`, `scene_id/hole_index`, `trace_sha256`, `bridge_sha256`, and **emulator frame brackets** per sampled window and input event. An RPC dispatch ACK means an input command was requested, **not game-applied A** or physical contact.
3. **Prove read overhead does not change power**: memory sampling via RPC adds time. Compare instrumented vs non-instrumented identical 45-A-lead, unmodified historical V1 control strokes; if hit rate, visible power or effective sample-frame progression diverges, the measurement procedure is perturbing the system. Prefer tiny gameplay-object watchlists, not a 9–12 KiB read in the middle of an 89-sample swing. Do not attempt parallel conflicting RPC writers.
4. **Find actual varying-power conditions**: before fitting memory to `power`, obtain at least **three genuinely different independent human-visible power readings** (not three commanded multipliers all yielding ~75%). First pilot can use controlled stroke duration or *forward travel* independently if S001 validates and exposes one additional parameter without changing A timing. Baseline controls + repeats required. If no visible power range appears, stop broad modeling and inspect how the Felk bridge synthesizes motion/swing events.
5. **Validate candidate specificity**: an offset must change around stroke/impact, not merely during stillness, camera/aim-only changes, or A-held stationary state. It must replicate under independent clean first-ball starts with the same golfer/club and vary across distinct displayed power bins. A score buffer, mode flag, pointer relocation, minimap effect, UI animation, or clock cannot be called a power variable. Confirm one run withheld from candidate search before accepting a model.
6. **Only then fit a local model**: start with one-dimensional (single offset) monotonic response, then simple regularized regression of verified candidate time-series features against independently observed **power-meter percent**. Hold out entire clean boots (not adjacent frames), report baseline error, uncertainty, and failed examples. Do not use the off-green 100-ft penalty as physical distance or target power. Ball-launch physics and on-green optimization follow as separate gates.

## Minimal same-shot evidence contract (proposed, not yet implemented)

The S001/S002/S003 owners must review a versioned local bundle with these *conceptual* fields:

| Category | Required evidence | Rules |
| --- | --- | --- |
| Identity | unique `shot_id`, scenario identity, game ID/revision, hole index, controller/bridge fingerprints | No joins by timestamp alone, identical waveform SHA alone, or similar displayed power |
| Treatment | one manipulated parameter/value + original baseline waveform; `a_lead_observed_frames`; initial-club-pose label | 45-frame A lead is known-working as **requested and frame-observed**, not verified accepted by game |
| Input timing | sequenced controller motion commands with attempted frame markers; backswing/forward boundaries | Distinguish request/dispatch ACK from applied game action |
| Memory | source-gated bounded object-relative region/offset, same-instance identifier, exact sample `frame_start` / `frame_end`, phase/event tag | Detect non-atomic spans, instance relocation, overlapping windows and scene transitions |
| Human evidence | contact, visible power and source (HUD/result/recollection), on-green and screenshot/transition status | Keep unknowns, 100-ft score censoring, and missing Enter as explicit categories |
| Privacy | local RAW-PRIVATE frame values, runtime pointers, ROM/savestates remain local | Public record contains only relative offsets, candidate statistics, verified safety metadata and honest warnings |

**Hard validation:** reject ambiguous shot linkage; wrong US Rev1/mode 4; non-monotonic frame counts; mixed holes; overlapping captures or unbounded RPC reads; rapidly relocating objects; mismatched bridge/waveform; and unacknowledged meter source.

## Experimental controls and first useful study

**Do not ask the operator to redo the current 10-shot score-only schedule yet.** The priority is to make each shot produce informative memory data.

* **Negative controls** from SAME first-ball checkpoint: 2x stillness, 2x camera-only, 2x A-held stationary. No intentional shot. These teach which offsets track UI/camera/input flags.
* **Instrumented baseline**: 2x previously successful A-lead=45, V1 waveform unmodified. Compare to previous uninstrumented outcomes to detect observer interference.
* **Power-gradient pilot**: at most 6 individually approved, clean first-ball strokes of validated one-variable variants, intentionally spanning low/baseline/high **observed** power (not just programmed speed). Keep full input and memory records. If all are ~75%, stop and inspect bridge semantics; do not burn another ten shots.
* **Independent holdout**: 2 clean first-ball runs reserved before final candidate choice if a candidate survives.

Each segment must have a frame event marker and pointer-stable sample. Collect only one intentional stroke per explicit user-approved invocation. Ten *different holes* should not be pooled without their hole/green geometry and state labels; multi-hole progression is not implemented by the canonical first-shot launcher.

## Concrete ownership and dependencies

* **S001 controller:** PR #112 A-request journal can help, but cannot prove frame-applied A. Provide low-overhead swing-segment event/frame anchors, verify probe does not perturb 45-frame lead/hit rate, preserve canonical V1 bridge and startup; no independent launch process.
* **S002 evaluation:** PR #109 source-anchored regions, PR #120 cross-run consensus, PR #116 phase capture are useful offline groundwork. Currently #116 phase actions are **operator-controlled in a separate read-only run**, not guaranteed aligned to the canonical scripted V1 shot. Prioritize validated golfer/main chain and narrow during-shot RAM snapshots; record scene/phase/latency. Use #116's offline `analyze_existing_golf_capture.py` once tested/merged to reprocess existing raw snapshots without new live input.
* **S003 modeling:** Issue #121's join gates should require exact same-shot identity/frame anchors, treat absent input/memory data as **not joinable**, penalize control/score/minimap sources and cross-run relocation. Build negative-control-adjusted candidate rankings and held-out 3+ distinct *observed* power-bin response tests, not fit to 100-ft penalties.
* **S000 coordination:** One operator-facing CLI / canonical startup path. Require contract acknowledgement from S001/S002/S003 before adding an opt-in `memory-power` study adapter; no new GUI, no unreviewed raw data publishing and no autonomous continuous Dolphin shots.

## Stop/go

**GO for learning power from memory** only after: (a) one validated live golfer-owned memory region; (b) frame-aligned same-shot A/back/forward/contact capture with harmless overhead; (c) idle/A/camera negative controls; (d) two independent clean-boot repeats and >1 observed power level; (e) measured on-green/physical outcome distinct from 100-ft penalty. Until then label outputs `candidate_change`, NOT `measured_power`, `ball_speed`, or `learned_model`.
