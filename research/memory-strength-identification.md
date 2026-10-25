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


## First operator study: read-only negative-control RAM pilot (STUDY-MEM-CTRL-01)

**This is the first runnable experiment, NOT the swing-power mapping yet.** It determines sample timing, memory-drift control, and response to aiming with **zero swings**. S002's phase recorder currently lives only in pending PR #116 and must pass local targeted AND full tests first. Do not merge this branch or #116 merely to enable the pilot.

**Safety:** one Dolphin boot from the up-to-date trusted MAIN checkout. A separate detached worktree contains PR #116's **read-only action** and cannot modify the running controller. Keep original main checkout clean and loaded savestate unchanged. Use `--no-upload` until PR #126 public-memory privacy validator is reviewed. Never share `RAW-PRIVATE.jsonl`.

PowerShell, commands one block at a time:

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Memory-Phase-Pilot"
if (Test-Path $work) { throw "Study worktree already exists. Do not overwrite it." }
git -C $repo fetch origin pull/116/head
if ($LASTEXITCODE -ne 0) { throw "Could not fetch S002 study PR" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Could not create isolated S002 worktree" }
Set-Location $work
py -m unittest discover -s tests -p "test_golf_memory_phase_capture.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused phase tests failed: do not launch Dolphin" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full offline suite failed: stop" }
```

Close any Dolphin process, then launch the validated intro FROM THE CANONICAL main checkout:

```powershell
Set-Location $repo
py scripts/launch_golf.py
if ($LASTEXITCODE -ne 0) { throw "Canonical game intro failed" }
```

Visually confirm Hitting the Green first-ball golfer is ready, and **leave Dolphin running**. From the isolated worktree, attach a read-only memory recorder (does NOT start/restore Dolphin a second time):

```powershell
Set-Location $work
py scripts/capture_golf_memory_phases.py --attach-running --scope focused `
  --phase idle:8 --phase aim_only:12 --phase idle:8 `
  --interval 0.75 --max-frame-span 30 --no-upload
```

At each phase prompt: idle means hands off; aim-only means move the configured Wii pointer with WASD while the phase records (~9 seconds); second idle means release all controls. Switching focus from terminal to Dolphin can consume early samples: report that honestly rather than inventing aim activity. No A press, no intentional ball hit, no emulator reset. Mark phase observations accurately. If no actual aim movement was seen, use `unknown` instead of `camera_moved`.

The experiment produces private `golf-memory-phases-...-RAW-PRIVATE.jsonl` and local **sanitized** `golf-memory-phases-...-summary.json` under sibling `Wii-AI-Golf-Data\captures`. Share only the sanitized summary and console frame-span status with S002/S003. The public summary currently reports aggregate within-stage and boundary counts; it **does not yet attribute changes to individual phase transitions**, so raw data should be retained locally for S002's revised phase-specific analyst. All zero changes are meaningful. A span over 30 frames stops the experiment; smaller samples still aren't atomic.

**Pass threshold:** valid RSPE01 Rev1 mode4, monotonic emulator frames, no relocations in compared windows (or explicitly reported), 28 samples, no uncontrolled contact, and a sanitized candidate count/frame latency summary. The follow-on swing-strength experiment needs (1) a source-validated live golfer/swing memory window, (2) per-phase candidate specificity under this negative control, (3) frame-linked S001 events during the SAME shot, and (4) three DISTINCT human-observed meter powers; absent any prerequisite, do not train power or use a 100ft penalty as carry.
