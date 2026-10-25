# S002 memory capture → sanitized GitHub → review → next hypothesis

This is a **CLI-only** research loop for Wii Sports US Rev1 `RSPE01` in Golf
Training / Hitting the Green, mode 4. It **does not** identify actual swing
power, club rotation, physics ball XYZ or a score.

The recorder is `scripts/capture_golf_memory_phases.py`. It is a
**read-only process** that attaches to an already running Felk Dolphin RPC
bridge on loopback. It does **not** launch the game, load savestates, issue
controller commands, or overwrite game memory.

## Memory scopes

* **Focused** (default; `--scope focused`): follow source-documented
  static pointers to the first `0xA0` bytes of `RPGolConfig`, all `0xA8`
  bytes of `RPGolFieldManager`, and all `0xD0` bytes of
  `RPSportsSequenceMgr`. These fields are *not* proven power or club
  variables. The smaller read helps reduce non-atomic frame spans.
* **Broad** (`--scope broad`): `RPGolConfig` `0x1C74` bytes and the
  same field manager/sequence objects, plus up to three valid minimap effect
  instances at `0x200` bytes each. This is roughly 9 KiB per sample.
  Slower reads can miss fast motion. Optional invalid effect pointers are
  excluded; required golf structures must be valid.

Sources: `kiwi515/ogws_info` RPGolConfig.h, RPGolFieldManager.h,
RPSportsSequenceMgr.h and existing
`wii_ai_golf.audit.outcome_transition` source gates.

## First experiment: stillness versus camera movement

**Only after the capture PR is merged into main and tests pass.**
Run it against an **already open Wii Sports Hitting the Green tee**
with the Felk RPC bridge active. If Dolphin is configured for a physical
Wii Remote, operate it manually as in the earlier read-only camera probe.
If Dolphin is configured for an emulated remote, use only the configured
input mechanism; this recorder never changes controller mode.

```powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only origin main

if (-not (Test-Path scripts\capture_golf_memory_phases.py)) {
    throw "Phase capture not merged into main yet."
}
py -m unittest discover -s tests -p "test_golf_memory_phase_capture.py" -v
if ($LASTEXITCODE -ne 0) { throw "Offline phase tests failed." }

py scripts/capture_golf_memory_phases.py --attach-running `
  --scope focused `
  --phase idle:6 `
  --phase aim_only:6
```

In the `idle` stage, remain still. When the `aim_only` stage prompts,
prepare the camera controls, press Enter, and move camera/aim without any
shot for the six snapshots. After each stage, choose the matching
observation label. Wrong mode, disconnected bridge, frame counter reset
or excessively long non-atomic sample fails safely. A partial private file
can remain on failure, with no false success report.

If you need **only a read-only baseline** under the canonical
emulated-controller launcher rather than attaching to a physical
session:

```powershell
py scripts/run_golf_experiment.py --send-live `
  --script capture_golf_memory_phases.py -- `
  --attach-running --scope focused `
  --phase idle:6 --phase idle:6
```

This outer wrapper launches Dolphin **once** and navigates to the tee.
The inner recorder never boots again. Two idle stages do not measure swing
power, but test capture stability and negative-control drift.

Do **not** request an automatic shot through this recorder. A future
S001/S003-owned actuator should be wired into a separately reviewed
phase-aligned capture so button events and memory share a frame timeline.

## Follow-up stages (only when controls are available and reliable)

```powershell
py scripts/capture_golf_memory_phases.py --attach-running `
  --scope focused `
  --phase idle:6 --phase a_hold:6 --phase club_motion:10
```

These are **operator-labeled intervals**, not instantaneous event
timestamps. Record `club_moved` only when you actually saw movement.
If no club moved, choose `unchanged` or `unknown`; do not interpret
a controller command acknowledgement as hit or power.

Use `--scope broad` on a separate controlled run when focused
capture shows no useful candidate, and inspect the reported
`max_non_atomic_frame_span`. This is *not* a high-rate game-frame
trace; adding more data can lower timing resolution.

## Files and privacy

* `Wii-AI-Golf-Data/captures/golf-memory-phases-<id>-RAW-PRIVATE.jsonl`
  stores source-validated window addresses and hexadecimal RAM for local
  offline work only. **Do not push, commit, or post this raw file publicly.**
* `golf-memory-phases-<id>-summary.json` contains relative offsets,
  source labels, change counts, phase labels, non-atomic frame spans and
  limited user-selected observations. No raw bytes, absolute runtime
  pointers, local paths or confirmed game-power claims.
* The completed recorder automatically calls the existing allowlisted
  `research_cli.publish_summary` which commits the sanitized report
  to the dedicated `research/observations` branch, without modifying main.
  It prints the returned URL and record ID. `--no-upload` suppresses this.
  A publishing failure leaves the local summary available for review.

Give the research agent the **record ID and GitHub observations branch
link**, not the raw JSONL. The agent will rank persistent/phase-specific
offsets, cross-reference documented roles, propose one new discrimination
test, then compare the next sanitized report.

**Limitations:** reading RAM over a frame-polled RPC bridge yields
non-atomic snapshots; stage boundaries depend on user timing and do not
measure exact power or club rotation. The documented `RPGolScene`
`mGolMain` member at scene `+0x9C` is a promising *future* pointer
chain, but the scene object's live address and gameplay substructures
have not been verified. Do not dereference fabricated addresses.
