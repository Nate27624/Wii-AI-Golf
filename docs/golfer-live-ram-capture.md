# S002 — actually capture candidate gameplay RAM (not minimap effects)

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
