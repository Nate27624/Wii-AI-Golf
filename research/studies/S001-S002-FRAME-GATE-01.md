# S001/S002-FRAME-GATE-01 — proposed bridge callback frame-timing fixture

**Status:** synthetic acceptance oracle, NOT a merged runtime or public observation schema. **Issue:** #121. **Owner:** S000 supporting integration research; downstream S001/S002 must approve or revise before instrumentation. **Budget:** 0 Dolphin starts, 0 RAM reads, 0 shots.

## Hypothesis and falsification

Can one S001-owned in-bridge event timeline plus S002-owned source-gated tiny watchlist supply internally consistent read brackets at <=2 *observed* emulated frames per read without treating RPC ACK as game-applied input?

**Null:** timeline is client request only, missing phases, unreadable frame timing, overlapping/cross-phase or slow reads, or leaks raw/private fields.

Pure stdlib `wii_ai_golf.research_bridge_timing_gate.audit_bridge_timing_fixture` checks structure and timing only. **It does not authenticate the claimed producer** and never verifies game-recognized A, class identity, reciprocal same-shot linkage, observer noninterference, ball contact or physical power. Passing is **necessary but insufficient** for a future transient study.

## Proposed S001/S002 fixture contract (NOT approved public schema)

Top-level exact fields: `schema_version=1`, `kind='proposed-bridge-timing-fixture'`, `game_id='RSPE01'`, `revision=1`, `game_mode=4`, opaque `boot_id` and `shot_id`, lowercase `bridge_sha256` and `trace_sha256`, `event_provenance='bridge_callback_emulated_frame'`, `events`, `reads`. No arbitrary keys, absolute pointers, memory words/bytes, personal paths, scores, visual meter or verified controller fields.

Exactly seven strictly increasing emulated-frame events: `pre_a`, `a_hold`, `backswing`, `forward`, `follow_through`, `release`, `post`. Each event contains exactly `phase`, `emulated_frame`, `a_requested`. Requested A is true only for hold/backswing/forward/follow-through. This is an **intended V1 A-command sequence**, not an observation of the game accepting A.

Each read contains only `phase`, `frame_start`, `frame_end`. Reads must be ordered, nonoverlapping, inside the matching phase, and at least one per `a_hold`, `backswing`, `forward`, `follow_through`. Compare actual per-read spans using nearest-rank p95 **AND max <=2** for the preregistered *engineering* temporal-resolution target. The previous 6/10/18-frame coarse reads correctly fail this criterion without invalidating their older idle/aim negative-control findings.

**Stop/falsification:** S001 cannot demonstrate bridge-callback event frame markers (not merely timestamps or submitted 89 samples), S002 cannot source-confirm a small player/club window, or a read crosses a stage or exceeds the target. Do not invent frame anchors, add a parallel RPC writer or infer game input from `trace.status`. Do not promote background `main+0x074` to verified clock without source/independent pause-reset controls.

## Owner handoff (Issue #121)

- **S002 (#122/#129/#132):** offline Rev1 object-owner xrefs first; 1–4 source-grounded member candidates. `RPGolScene +0x9C` main pointer and 28 pointer-shaped first-level children are candidate identities, not verified player/club members. Do NOT repeat completed broad idle/WASD scan.
- **S001 (#112):** choose actual bridge callback hook and retain one canonical V1 waveform (A lead45, 89 swing samples), the same launcher and no extra controller RPCs. Check requested-A continuity separately from game-applied state.
- **S003 (#123/#125):** use the existing reciprocal same-shot boot/scene/bridge/waveform/frame-end join after owner approval. This oracle DOES NOT replace its production pairing module.
- **S000 (#126):** review privacy if and only if a typed sanitized publication kind is later required. No shared CLI/GUI, public schema, live bridge or publisher is modified here.

**Future live step, NOT approved here:** only after S001/S002 owner review and full Windows tests, test one separately consented known-good shot paired with an uninstrumented baseline, with true observed frame brackets and human contact labels. Stop on interference, missing same-shot linkage or read spans too long. No swing-power fitting until independently validated variable power exists.

## Validation

```powershell
py -m unittest discover -s tests -p 'test_research_bridge_timing_gate.py' -v
py -m unittest discover -s tests -v
```

13/13 focused SYNTHETIC tests and stdlib compilation passed in a separate Linux source-equivalent directory. **Not run:** full current checkout tests, Windows Dolphin, real callbacks or domain owner approvals. Keep this PR draft and unmerged until review/tests. No game assets, ROMs, savestates or RAW-PRIVATE evidence in this artifact.
