# S001/S002-BALL-TEMPORAL-01 — four-phase motion-identifiability gate

**Status: OFFLINE-ONLY preflight; no live Dolphin sampling, new game recording, or operator shot authorized.** Strictly stacked on #147 SAME-SHOT's unchanged V1 sample-index and A-held waveform manifest. S002 #160 owns runtime source/record identities; S002 #163 already owns B0 two-bank static equality and optional two-image compare. This script does NOT replace either. S001 retains sole ownership of future single Felk bridge frame-coroutine sampling. S000 alone authorizes new published schemas. No training.

## Scientific question and falsification

The user's existing separately exported Rev1 MEM1+MEM2 images support one selected slot (0) with exact 3-word equality: field-manager current-start translation, inline record+0x54 and +0x60, and selected ball-related object's +0x4C VEC3 destination. Public Rev1 PPC source write sites corroborate copying those floats. All this is **still-state initialization evidence, not motion**, and separate native GUI dumps approximately 112 seconds apart do NOT count as same-emulated-frame samples.

The NEXT discriminator is a *future operator-authorized, same-boot* read-only comparison: if the selected ball-related three-word destination changes **only after an independently witnessed ball move** while current-start marker and selected runtime pointers remain unchanged, it becomes a provisional moving-object correlation. No single trial can establish physics/world XYZ or velocity. If a no-shot control also changes, the source start moves, slot switches, read brackets are not actual emulator frames, or no human movement is observed: **ABSTAIN**.

## Design: four paired markers, no new controller writer

Requires a future S001 same-Felk-frame-coroutine opt-in integration, with current #147 immutable command waveform and human annotation. Do not launch a second Dolphin instance or RPC process, pause with frame-polled RPC, use GUI dump timestamps as emulated frame IDs, or modify a controller sequence. Each capture reads only the S002 source-gated selected record, the selected ball-related pointer +0x4C 3×32-bit words, current-start translation 3×32-bit words and record+0x54/+0x60 3×32-bit words. Keep runtime pointers, exact 32-bit data and boot token in a local PRIVATE file.

Stages in ONE boot and one unchanged hole/scene/mode (requested order):
- idle_before: stationary first-ball source-verified start; no controller action.
- idle_after: after a time-separated stationary negative control; no controller action.
- event_before: immediately before a human-observed scripted ball movement, using a frame-bracketed read.
- event_after: after independently witnessed hit / ball movement, using another frame-bracketed read; its source game-frame timestamp must be later.

S001 should record real emulator frame_start/frame_end for each snapshot (at most 2 frames per snapshot), S001 source bridge callback identity, source membership gates, private boot token, selected inline slot index and stable pointer ownership. S001 must independently validate the actual in-emulator read workload and prove it does NOT perturb known-good A45/V1 contact; this preflight does NOT validate noninterference. Sample index 12/27/46 of the 89-command trace is not automatically an emulated frame number or observed contact event.

Human fields (no-shot idle, ball movement, contact, event between brackets, waveform unchanged) are explicitly operator attestations; the script cannot verify human observation from memory. If any attestation is missing, return abstain. Same boot token matching is only an *operator declaration*; there is no independent same-boot proof in this design.

## Offline consumer now implemented (new-only, no integration changes)

- scripts/audit_selected_ball_temporal_controls_private.py consumes exactly four private JSON samples. Strict key allowlist (unknown fields rejected), native u32 big-endian word arrays for position-like candidates, mapped aligned MEM2 pointer guards, RSPE01 Rev1 scene5/sport2/mode4, stable hole, stable selected index/pointers, monotonic nonoverlapping emulated frame brackets at most 2 frames each, unchanged start position, no-shot control, pre-event baseline, human visual movement/contact and unchanged V1 attestation.
- A valid candidate returns only result **provisional_motion_correlated_candidate**, with 0..3 bitwise changed components and two optional post-event equality flags, plus privacy-safe gate outcomes. Every other unverified/broken control returns abstain, or rejects invalid schema. Always sets physical_world_xyz_verified=false, actual_ball_physics_object_verified=false, recognized_swing_power_verified=false, training_approved=false and automatic_publication_approved=false.
- CLI accepts a single future PRIVATE JSON file beneath ignored sibling Wii-AI-Golf-Data, max 128KiB, symlinks and outside worktrees refused. Never writes a report, scans RAM, starts Dolphin, uses any RPC, uploads logs or reads ROM/DOL. Console never reveals raw words, pointers, exact frame IDs, boot tokens or file paths.
- tests/test_selected_ball_temporal_controls_private.py contains 20 synthetic tests covering a candidate happy path, idle drift, start instability, slot/pointer reassignment, no actual changed words, missing human observation, changed waveform, boot/hole mismatch, overlapping/slow frame reads, wrong scene/source, malformed u32/addresses, extra schema fields, GUI native dump noneligibility and redacted error output.
- Windows/Ubuntu focused CI; full Windows suite must be checked at the final review head.

## Safe action today

No new native memory capture, physical swing, GPU training or special command is required from the operator. To run the **offline fabricated synthetic suite only** if desired:

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Ball-Temporal-Preflight"
if (Test-Path $work) { throw "Preserve existing worktree" }
git -C $repo fetch origin agent/research/selected-ball-temporal-controls-s001
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_selected_ball_temporal_controls_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Temporal synthetic suite failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full Windows repo regression failed" }
~~~

DO NOT invent a private evidence JSON from the current GUI dump to pass this script: no true emulated frame brackets or human-observed movement exist. Future S001 review must first implement an opt-in single-owner same-bridge reader, exact provenance, bounded read overhead, nonperturbation control and private artifact format, then seek operator explicit permission for ONE movement trial. S002 #163 remains owner of the already available B0 static two-bank analysis. S003 remains blocked.

## Acceptance for scientific field promotion

- Across multiple independent boots, reliably reproduce the source-selected record, nested target and stable start marker under each control.
- Demonstrate with real game-frame timestamps and human or video-correlated motion that selected ball-related vector changes when ball visibly moves, not during idle.
- Cross-check the coordinate system/units, axis orientation, actual writer PC and timing against independent known position/landmark.
- Only after these may the field evidence ledger consider behavioral verification of ball XYZ. **Do not promote power, velocity, swing phase or trainability merely because this gate returns a candidate.**
