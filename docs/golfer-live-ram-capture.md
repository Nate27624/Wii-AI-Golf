# S002 — actually capture candidate gameplay RAM (not minimap effects)

## Latest 20-sample live result: inspect private RAM BEFORE new Dolphin runs

Operator reported `golfer-20261025T033213Z-88fb5f3e` with 20 samples,
18-frame maximum sampling span, 16 first-level watched children and
more unobserved children. The source-anchored manager slot is `+0x4D8`;
the manager scene ID, scene's own ID and manager backlink passed live
checks. Only four words changed, ALL in 19 of 19 adjacent pairs including
idle:

- main `+0x074`
- child referenced by main `+0x008` at child `+0x050`
- child referenced by main `+0x020` at child `+0x038`
- child referenced by main `+0x044` at child `+0x060`

These continuous changes are counter-like negative controls, not a
confirmed club/power signal. Use the new OFFLINE private analyzer to
characterize their monotonic/cyclic signed differences and list
unwatched first-level pointer offsets, without Dolphin or GitHub:

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Golfer-RAM-Probe"
$raw = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\golfer-20261025T033213Z-88fb5f3e-RAW-PRIVATE.jsonl"

git -C $repo fetch origin
if ($LASTEXITCODE -ne 0) { throw "Fetch failed." }
if (git -C $work status --porcelain) {
    throw "Stop: worktree has uncommitted changes."
}
git -C $work switch --detach origin/agent/evaluation/live-golfer-ram-discovery
if ($LASTEXITCODE -ne 0) { throw "Could not update read-only research worktree." }
Set-Location $work
py -m unittest discover -s tests -p "test_analyze_golfer_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Private analyzer tests failed." }
py scripts/analyze_golfer_private.py --input $raw
if ($LASTEXITCODE -ne 0) { throw "Private RAM analysis failed." }
```

The output has no full 32-bit words, local addresses or private byte
strings. It groups equal word-change patterns, counts positive/negative
integer steps and identifies fields that change continuously during
idle as likely counters. Its aim-correlated classification is only
relative to a human-labeled stage: WASD pointer movement is NOT itself
proof of Wii Sports club movement.

## Only if needed: sample unobserved first-level children, in small batches

The read-only probe now has optional `--child-start` and
`--child-limit` to select non-overlapping 128-byte candidate windows,
without increasing overall RAM scan beyond the first 256 bytes of the
verified gameplay owner for pointer discovery. For example,
`--child-start 16 --child-limit 4` inspects indices 16–19, previously
excluded by the first-16 watchlist. Fewer child windows should reduce
non-atomic sample spans versus the original 18 frames, but actual spans
must be measured. This still does NOT guarantee those children are the
club; further source checks and S001 frame-aligned event capture are
required. Do not run an unattended swing or confuse Wii pointer movement
with the club changing state.

Only when a trustworthy input/phase control is confirmed and Dolphin
is already running, invoke the tested read-only script directly:

```powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Golfer-RAM-Probe"
py scripts/capture_golfer_memory.py --read-only `
    --child-start 16 --child-limit 4 `
    --phase idle:4 --phase aim_only:6 --phase idle:4
```

If the game is closed, restart via the canonical main launcher ONCE
before a new read-only capture. No raw RAM/public GitHub publication.



**Goal:** Follow a source-anchored *live* pointer chain to `RPGolMain`, and
record candidate gameplay-object bytes while the operator changes camera/aim.

**Observed October 25 result:** 20 samples found one candidate slot
`0x804BF4D8`, with the candidate gameplay object's `+0x74` word
changing in every one of 19 comparisons (including idle). That offset
looks counter-like, not confirmed rotation/power. Independently the
Rev1 split map places RPSysSceneMgr.cpp static storage in
`[0x804BF4D8,0x804BF4E0)`. This follow-up searches only **two 32-bit
cells** in that independently source-backed range. The exact singleton
cell and live identity are validated at runtime, not assumed.

Source-backed structural checks:
* `EGG::SceneManager +0x0C` active scene, `+0x18` scene ID;
* `EGG::Scene +0x1C` **current scene's own ID**, `+0x20` scene
  manager backlink (both required to match);
* `RPSysScene +0x40` **creator/previous** scene ID (recorded only;
  its mismatch with current golf scene ID is expected);
* `RPSportsBaseScene +0x54` sport ID = 2 (golf);
* `RPGolScene +0x9C` candidate `RPGolMain*`.
* `RPGolConfig +0x94` mode 4; RSPE01 revision byte 1.

Candidate addresses are only followed if they fall in bounded Wii RAM and
both manager scene ID and scene sport ID agree. Before every 0x100-byte
candidate `RPGolMain` snapshot, the pointer chain is checked again. A
missing or ambiguous chain returns diagnostics **without** saving gameplay
RAM; it does not pretend that power was found. Snapshots are non-atomic,
with frame counts before and after. The script invokes only
`frame.get_count`, `memory.read_u32` and `memory.read_bytes`.

## Operator test using a separate review worktree

The **canonical** main checkout must remain the owner of Dolphin startup.
Close Dolphin, then use one Windows PowerShell command block:

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Golfer-RAM-Probe"
git -C $repo fetch origin
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
if (-not (Test-Path $work)) {
  git -C $repo worktree add --detach $work origin/agent/evaluation/live-golfer-ram-discovery
} elseif (-not (git -C $work status --porcelain)) {
  git -C $work switch --detach origin/agent/evaluation/live-golfer-ram-discovery
} else {
  throw "Existing probe worktree has changes; do not overwrite"
}
if ($LASTEXITCODE -ne 0) { throw "Could not prepare probe worktree" }
py -m unittest discover -s "$work\tests" -p "test_capture_golfer_memory.py" -v
if ($LASTEXITCODE -ne 0) { throw "Read-only discovery tests failed" }

Set-Location $repo
py scripts/launch_golf.py
if ($LASTEXITCODE -ne 0) { throw "Canonical Dolphin startup failed" }

Set-Location $work
py scripts/capture_golfer_memory.py --read-only `
  --phase idle:6 --phase aim_only:8 --phase idle:6
if ($LASTEXITCODE -ne 0) { throw "Read-only gameplay capture failed" }
```

The runner's `--send-live` wrapper **forbids** passing `--attach-running`
to arbitrary action scripts; the probe uses a distinct explicit
`--read-only` flag. The separate worktree script merely connects to
the same already-running Dolphin RPC after main's single startup. No
second Dolphin is launched.

It prompts for Enter three times: no movement, manual WASD aim/camera
movement, no movement. No button press or swing is required. If Dolphin
is STILL running from the previous capture, skip the launch command and
only refresh the clean detached worktree followed by the read-only probe.

## What to share

**Only the printed sanitized JSON** or the local
`golfer-...-summary.json`, not `golfer-...-RAW-PRIVATE.jsonl`.

A successful unique chain saves private byte snapshots, candidate live
addresses and frame brackets to the local sidecar
`Wii-AI-Golf-Data/captures`; relative-offset change counts are printed.
No GitHub upload of private values, and no claim that changing fields
are power or club rotation. Even zero changed candidate words is useful
for deciding whether to traverse a next-level object pointer.

If no unique chain is found, provide the printed counts
`static_pointer_candidates`, `golf_scene_id_candidates`,
`validated_sport_scene_candidates`, `matching_golf_main_chains`.
Next hypotheses: source-backed singleton storage extraction from PPC code,
or review a bounded expanded singleton census. Do not assume game physics
do not exist when a heuristic 4 KiB search misses the manager.

The new public observation validator (S000 PR #126) does not yet approve
this new gameplay-candidate schema. The probe deliberately defaults to
**no upload**, with a locally generated report for user review.
