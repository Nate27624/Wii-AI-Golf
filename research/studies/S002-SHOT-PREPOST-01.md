# S002-SHOT-PREPOST-01 — preregistered PRIVATE before/after Golf shot

**Status:** study implementation DRAFT; synthesized CI and source review
pending. **No Dolphin capture, swing, new savestate, controller input, or
background task has been initiated**. Preserves the separate working
`FelkDolphin-Clean` install with legacy V1 bridge and no assumed golf
savestate or controller profile. Requires explicit operator choice of
one human-observed shot later, after S001/S002/S000 safety review.

## Why snapshots alone require controls

Earlier real, source-gated B0/B1/B2/B3 **no-shot** checkpoints proved
that the selected ball-related `VEC3`, player-record `VEC3`, and
current START `VEC3` all stayed identical through idle, visibly
changing WASD aim, and idle again, even though both whole memory banks
changed in each transition. The main unresolved claim is whether
the selected ball-related vector changes when the visible ball moves.

Paired GUI memory dumps are **not native frame-atomic samples** unless
MEM1 and MEM2 exports occur under the *same GUI pause* in a single
Dolphin process. Even then, pausing/export timing and the human
description are attested, not independently proven guest frame IDs.
An end-of-hole/results-screen capture may have already reset the
ball to START, yielding unchanged values even after a real shot.

## First controlled milestone: PRE and displaced POST

Only when a real game is ready and an owner-approved single shot is
possible, stage **one** source-gated pre/post capture:

| Phase | Human condition | Export while paused |
| --- | --- | --- |
| PRE | First selected ball visibly stationary and ready, before A prime or any swing | pause emulation; export GUI MRAM and ExRAM without resuming; immediately preserve distinct copies |
| POST | SAME live process, after **one observed shot**, the ball is visibly DISPLACED, *before it resets/changes hole* | pause again; export both banks without resuming; immediately preserve distinct copies |

**Do not** try to pause inside the frame-polled Felk Python bridge
(`emulation.pause()` while RPC waits can deadlock). Only use the
reviewed GUI pause/export actions. Never overwrite an existing
`mem1.raw` or `mem2.raw` keeper: Felk's debugger Export/Dump MRAM
writes to the same `Dump/mem1.raw` by default each time.

**No unattended shot/power sweep**. One deliberate operator-approved
human-observed contact is enough for the first test; don't vary
the waveform, A-prime, club control, hole, camera or memory watcher
at the same time. If the ball never visibly moves, stop: no POST
displacement claim and no fabricated shot label. If the game
resets before pause, stop or mark the attempt **INCONCLUSIVE**; do
not substitute a results-screen PRE/POST pair for the specified
displaced-ball phase.

**Use actual portable active USER Dump location**, not an assumed
AppData folder or the previous installation. This study will never
launch/modify the active installation.

## Private file and provenance contract

Store four exact native banks in a fresh, ignored session directory
under the existing sibling `Wii-AI-Golf-Data`:

```
Wii-AI-Golf-Data/
  captures/
    SHOT-<local-run-id>-PRIVATE/
      PRE-MEM1.bin         [24 MiB]
      PRE-MEM2.bin         [64 MiB]
      POST-MEM1.bin        [24 MiB]
      POST-MEM2.bin        [64 MiB]
      shot-checkpoint-manifest-PRIVATE.json
```

Do not place any of these files on GitHub, in chat or in a remote
project. Preserve the original output and old B0–B3 capture separately.

The private manifest is typed `schema_version=1`,
`kind=local-private-golf-prepost-paired-checkpoints`,
and must contain operator-attested booleans:

```json
{
  "schema_version": 1,
  "kind": "local-private-golf-prepost-paired-checkpoints",
  "operator_reports_same_dolphin_process": true,
  "operator_reports_exactly_one_shot": true,
  "operator_reports_visible_ball_displacement": true,
  "operator_reports_no_hole_reset_or_transition": true,
  "checkpoints": {
    "PRE": {
      "phase_operator_label": "pre_shot_still",
      "operator_reports_gui_paused": true,
      "operator_reports_mem1_mem2_export_same_pause": true,
      "sha256": {
        "MEM1": "<64 lowercase hex chars computed from PRE-MEM1.bin>",
        "MEM2": "<64 lowercase hex chars computed from PRE-MEM2.bin>"
      }
    },
    "POST": {
      "phase_operator_label": "post_shot_visible_displacement",
      "operator_reports_gui_paused": true,
      "operator_reports_mem1_mem2_export_same_pause": true,
      "operator_reports_game_was_running_between_phases": true,
      "sha256": {
        "MEM1": "<64 lowercase hex chars computed from POST-MEM1.bin>",
        "MEM2": "<64 lowercase hex chars computed from POST-MEM2.bin>"
      }
    }
  }
}
```

**Only attest what was actually observed.** SHA256 hashes must be
computed locally from the preserved copies AFTER copying all four
banks. Native size and hash are checked before analysis. No
hash/private path is printed by our script, and raw memory stays
in local process.

## Offline analysis (AFTER capture and owner approval)

Source branch: `agent/research/private-shot-prepost-cohort-20261027`
stacked on S002 #163/#160. `scripts/audit_selected_ball_prepost_shot_private.py`
uses EXACT S002 source Rev1 game/mode4/scene5/selected-record PPC
source validation. It independently resolves both phases'
selected player-record slot, nested ball-related object+0x4C
translation (three u32), current start+0x4C translation and
player record+0x54 position (three u32). It enforces same raw
source hole, selected slot, **full pointer owner tuple stability**
and local start control, with no arbitrary pointers or page scanning.

The output only contains component-change counts (0..3),
selected record-ball agreement counts per phase, whole-bank
changed flags and a cautious
`candidate_change_consistent_with_operator_observed_displacement`
boolean. It never reveals raw float values, pointers, bytes,
hashes, absolute file paths or personally identifying data.
`ball_motion_world_xyz_verified=false`, `velocity=false`,
`power=false`, `training=false`, `allowed_to_publish=false`
irrespective of the candidate result.

**Crucial distinctions:**
- A source-selected nested-ball VEC3 change with unchanged
  source START and owners after a visibly displaced shot is
  **supportive differential evidence**, not proof of physical
  XYZ, movement timing or causality.
- MEM1 contains executable/state roots while selected player/ball/start
  translations are already source-gated to MEM2; **MEM1 hashes may remain
  identical** across a legitimate ball-position change. A MEM2 bank change
  is expected for a changed selected ball vector. Full-bank hash equality
  is an integrity/diagnostic flag, not a physical-motion sensor.
- The ball may have been reset to START before the GUI pause;
  a no-change result is **inconclusive**, never proof the
  visible ball didn't move.
- A change in START or player/hole/owner identity invalidates
  the comparison; do not relabel as shot movement.
- Current snapshots do NOT create S001 #165 strict `<=2`
  emulated-frame witness or prove game-physics velocity. The
  in-frame S001 #166 sampler is separate and remains draft.
- S002 #178 is the broad *detailed object-window* owner; this
  deliberately adds just **one shot-labeled, count-only** comparison
  to already-established S002 selected-ball source readers.

**CLI** once owner review, green targeted+full Windows tests,
operator-consented shot, and valid private files are ready:

```powershell
py scripts/audit_selected_ball_prepost_shot_private.py --private-root "<exact ignored Data session folder>"
```

This is read-only offline. No current-user work is needed until
capture preflight is approved. Sharing even the sanitized
`allowed_to_publish=false` JSON outside private chat requires S000
review; it is not auto-uploaded to the public repository.


## AFTER APPROVAL: reusable PowerShell commands (do NOT run before review)

These are prepared now so the operator can receive a reviewed,
copy/paste-ready sequence **after** S001/S002/S000 sign off.
Never assume the separate clean Felk installation has the old
controller profile, named golf pre-start savestate, or working
on-screen ball-contact baseline.

### Worktree and offline tests

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Shot-PrePost"
$data = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"
$branch = "agent/research/private-shot-prepost-cohort-20261027"

if (Test-Path -LiteralPath $work) { throw "Existing worktree: preserve it" }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_selected_ball_prepost_shot_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused test failed: stop" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full test failed: stop" }
```

The live-capture steps **MUST come from the approved S001 owner**
because Dolphin GUI export commands/actual portable User Dump folder
must be verified locally before using them. Without an explicitly
verified contact baseline, STOP after the tests and do not send a shot.

### After operator has successfully exported and preserved all four banks

An approved capture folder should already contain these exact distinct
files; the scripts **do not export or populate them**:
`PRE-MEM1.bin`, `PRE-MEM2.bin`,
`POST-MEM1.bin`, `POST-MEM2.bin`.

```powershell
$session = Join-Path $data "captures\SHOT-<reviewed-local-id>-PRIVATE"

$expected = @{
    "PRE-MEM1.bin" = 24MB
    "PRE-MEM2.bin" = 64MB
    "POST-MEM1.bin" = 24MB
    "POST-MEM2.bin" = 64MB
}
foreach ($name in $expected.Keys) {
    $file = Join-Path $session $name
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Preserved native bank missing: $name"
    }
    if ((Get-Item -LiteralPath $file).Length -ne $expected[$name]) {
        throw "Wrong private native bank size: $name"
    }
}

& .\scripts\prepare_golf_prepost_manifest_private.ps1 `
    -PrivateDataRoot $data `
    -SessionFolder $session `
    -ConfirmSameDolphinProcess `
    -ConfirmExactlyOneShot `
    -ConfirmVisibleBallDisplacementBeforeReset `
    -ConfirmNoHoleResetOrTransition `
    -ConfirmBothMemBanksExportedUnderEachSamePause `
    -ConfirmGameRanBetweenPhases
if (-not $?) { throw "Private manifest preparation failed" }

py scripts/audit_selected_ball_prepost_shot_private.py --private-root $session
if ($LASTEXITCODE -ne 0) { throw "Private source comparator failed" }
```

Each `-Confirm` switch is a real **human observation
attestation**, never just a way to make the command pass. If any
observation was not true or the ball reset, DO NOT assert it. Preserve
the incomplete files privately, describe what occurred, and abstain
from the strict PRE/POST source comparator. The manifest creator
refuses to overwrite an existing manifest or to write outside the
ignored `Wii-AI-Golf-Data` sibling tree, checks exact sizes and SHA256
hashes of the original banks, and prints no raw values or hashes.
No private file or command from this run goes to GitHub.

**Approval gates:** S001 safe known-good clean Preview4 contact and
GUI-pause/export protocol, S002 source/selected-object semantics,
S000 private provenance and publication, targeted **exact-head**
Windows/Linux CI, complete Windows full regression, and explicit
operator consent for one shot. Do not mistake this prepared command
section for approval.
