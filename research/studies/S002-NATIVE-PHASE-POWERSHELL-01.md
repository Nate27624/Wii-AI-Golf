# S002-NATIVE-PHASE-POWERSHELL-01 — private PRE/POST session and integrity

**Status: draft, offline support only.** Complements the existing #201 native RAM reader, #184 keeper, #210 private staging guard and S001 V1 watched contact work #206/#211. No new Dolphin startup, remote control, swing timing, memory reader, score decoder, UI, or GitHub publisher.

## What the PowerShell scripts do

- `scripts/New-GolfNativeShotSession.ps1`: create one unique, non-linked `SHOT-<id>-PRIVATE` folder under ignored sibling `Wii-AI-Golf-Data/captures`, refuse overwrite and output only its path to the local calling PowerShell session. No Dolphin interaction.
- `scripts/Test-GolfNativeShotPair.ps1`: read-only check of S002 keeper manifest `shot-distance-captures-PRIVATE.json` and complete native `PRE-MEM1.bin`/`PRE-MEM2.bin`, optional POST/RESULT; exact 24/64MiB lengths, RSPE01 Rev1 MEM1 header, SHA256 per native bank, phase prefix/order, manual pause attestations, observed displaced-ball/same-hole/same-process POST gates, refused publication/training claims. Output counts and booleans ONLY, no hashes/RAM/pointers/paths.

**Important:** size/hash integrity does not prove emulator was paused, both banks came from the same guest frame, or that the POST vector represents ball flight. It does not identify ball XYZ, velocity, power, or official score. Do not promote any model input from this checker alone.

## Offline test commands (PowerShell)

```powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
py -m unittest discover -s tests -p 'test_s002_native_phase_powershell.py' -v
```

Tests create **synthetic sparse files of real native bank sizes**, fake hashes and fake S002 manifests under a temporary sibling Data folder; they never open Dolphin, ROMs, savestates or genuine RAM. GitHub Actions tests exact PR head on Windows and Ubuntu PowerShell 7.

## Proposed operator sequence AFTER S001/S002/S000 approve native reader #201

These are **future guarded commands**, not permission to execute draft live capture today. Every shot still starts through the maintained canonical fresh Dolphin/green-pre-start/A→A+B→A route. Do not replace the 45 **observed Dolphin A frames** historical V1 lead with 45 RPC requests. The reader #201 does NOT automatically pause or resume Dolphin; operator must actually pause before each snapshot, and a POST after reset must be discarded.

```powershell
$root = 'D:\Projects\Wii Golf AI'
# $tools is an approved checkout containing these two scripts
$tools = Join-Path $root 'Wii-AI-Golf'
$session = & (Join-Path $tools 'scripts\New-GolfNativeShotSession.ps1')

# Set $reader to the reviewed #201 worktree, only after approved.
$reader = Join-Path $root 'Wii-AI-Golf-S002-Scripted-Fullbanks'
# Once the separately authorized canonical launcher has reached the stationary first ball,
# visibly PAUSE Dolphin. The existing S002 wrapper captures complete native binary files:
& (Join-Path $reader 'scripts\capture_golf_fullbanks_private.ps1') -Session $session -Phase PRE -PausedConfirmed

# Resume. Execute exactly ONE approved original V1 45-observed-frame shot via canonical launcher.
# If and only if the ball is visibly displaced on the same hole BEFORE reset, PAUSE again:
& (Join-Path $reader 'scripts\capture_golf_fullbanks_private.ps1') -Session $session -Phase POST -PausedConfirmed -ShotObserved -SameProcessConfirmed -SameHoleConfirmed

# Offline integrity verification; never publishes raw RAM:
& (Join-Path $tools 'scripts\Test-GolfNativeShotPair.ps1') -Session $session -RequirePost
```

The proposed commands do **not** create a new launcher, watched sensor, automatic pause or autonomous POST trigger. For an actual timed POST, S001 must first validate the frame watcher and S002 must prove a supported pause/freeze API. Until then the human pause requirement can miss the moving ball. The script will only validate an already preserved pair.

## Handoff and publication

Retain raw banks, keeper manifest and FAILED/STAGING directories locally, ignored and PRIVATE. Never push them to the code branch or research/observations. Only allowlisted summaries may use the existing publisher after S000 approval. S002 #201 owner handles actual integration and repeatable DME hook; S001 #206/#211 owns original V1 watch/shot; S000 coordinates operator command delivery. This PR is review-only, with new paths to avoid merge collisions.
