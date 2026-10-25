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

## Zero-live-test first run: reuse your existing outcome RAM

Before collecting any new memory, this separate offline path analyzes source-
validated `outcome-*-RAW-PRIVATE.jsonl` snapshots already on your PC. It
treats their original `pre`, `post`, and `settled` markers as recorded,
without assuming the ball was struck. It requires the legacy broad snapshots
and never runs Dolphin.

```powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$raw = Get-ChildItem "..\Wii-AI-Golf-Data\captures" `
    -Filter "outcome-*-RAW-PRIVATE.jsonl" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $raw) { throw "No earlier S002 outcome RAM capture to reprocess." }

py scripts/analyze_existing_golf_capture.py --input "$($raw.FullName)"
```

This creates a unique sanitized `golf-memory-audit-...-summary.json`
next to the existing private file and attempts to publish it to
`research/observations` through the established uploader.
Use `--no-upload` to inspect first. It does not move or expose raw RAM.

## Repeated-offset cohort analysis (no Dolphin)

After processing at least two existing outcome captures, compare *all*
eligible local private outcome sessions with a single aggregate report.
Use this step to eliminate changes seen only once. Incomplete or
unsupported source files are counted as exclusions, not treated as misses
or zero-power shots. At most 25 files, and no private bytes, original
absolute addresses or local filenames are published.

```powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Memory-Offline-116"
git fetch origin
git switch --detach origin/agent/evaluation/phase-labelled-memory-capture
py -m unittest discover -s tests -p "test_golf_memory_cohort.py" -v
if ($LASTEXITCODE -ne 0) { throw "Cohort tests failed." }

py scripts/analyze_golf_memory_cohort.py `
  --directory "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"
```

The script creates one local `golf-memory-cohort-...-summary.json`
and auto-publishes a single sanitized aggregate to
`research/observations`. It counts how many independent runs saw each
changed region-relative word, and how often changes were within stages
versus on stage boundaries. Identical rendering-effect metadata may be
highly repeatable yet still **not** be the physical ball or club.

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

**Canonical launch limitation:** the current S001 `run_golf_experiment.py`
rejects user-supplied `--attach-running`; `post_boot_action_args`
injects that flag ONLY for `probe_swing.py`. Do not attempt to pass
`--attach-running` through that wrapper for this recorder: it will
reject the command. The recorder only works directly against an
**already running** Felk RPC / tee session. A fresh-boot integration
requires an S001-owned handoff change and tests, not a second launcher.

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

## Next-source experiment: inspect the ACTIVE golf scene chain

The 24-run cohort report `cohort-20261025T025308Z-fbda2d0e` shows
16 universal offsets, all belonging to minimap effects. The documented
course configuration and manager fields provide no identified club/power
signal. The next target is the source-documented pointer chain:

```text
candidate EGG::SceneManager instance
   +0x0C -> current scene
       +0x40 -> scene ID (expected RP_GOL_SCENE = 5)
       +0x54 -> sport ID (expected golf = 2)
       +0x9C -> RPGolMain* (required RAM-like pointer; NOT yet decoded)
```

References: `doldecomp/ogws/include/egg/core/eggSceneManager.h`,
`kiwi515/ogws_info/RP/RPSports/RPSportsBaseScene.h`,
`kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolScene.h`.

The survey searches only a bounded 4 KiB page of candidate global
singleton pointers near source-documented golf-instance statics. This
page is a **heuristic search region**, not a confirmed static manager
slot. It is safe to get zero matches; the chain may be stored elsewhere
or scene timing could differ. The survey validates RSPE01 Rev1 and mode 4
before dereferencing any candidate, then checks RAM bounds and scene
identity before publishing the validated slot **relative offsets** only.
No raw addresses, bytes or screenshots are uploaded. It never invokes a
controller, savestate, or game-memory write.

Once PR #116 passes review, the source survey can run DIRECTLY against a
pre-existing, ready-to-play Felk Dolphin session on the canonical main
checkout:

```powershell
Set-Location "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
py scripts/probe_golf_scene_chain.py --attach-running
```

Do not launch a second Dolphin from the probe and do not pass the
attach flag through `run_golf_experiment.py`; the outer runner
explicitly forbids it. If a fresh-boot automated survey is desired,
S001 must review and implement the post-boot action handoff contract.

Use `--no-upload` to keep the sanitized report local during the first
read-only live test. Only use this tool when the exact active Dolphin
bridge/session has already been verified by S001; no new session starts.
