# S002 — direct selected-player aiming ray, replacing inspector baseline drift

## Operator observation (original real Rev1 Dolphin run, 2026-11-10)

With Hitting the Green, read-only `p0_live_player_rotation_candidate_private.py`
in #427 returned `SOURCE_SELECTED_PLAYER_ROTATION_CANDIDATE_SUPPORTED`,
exit=0, and all four controls passed (source numeric matrix in each phase,
idle stable, left increased +0x3C, right decreased +0x3C). This is **real
operator-reported output**, not fabricated test data, though the raw private
JSONL was not independently obtained by the agent.

- B0 selected source scalar angle 112.20093°, 2D matrix rotation +22.20091°.
- B0 source tee→pin XZ candidate bearing −22.38945°.
- *Negated* matrix heading −22.20091° differs by only +0.18854° from
  tee→pin. The B0 prompt requested visually known aim, preferably flag,
  but did not require the operator to attest exact centered-to-flag
  alignment, so **do not treat 0.18854° as a calibrated offset**.
- LEFT scalar +11.93180° from B0; RIGHT scalar −14.65915° from B0,
  both matrices internally consistent. A direct source-frame XZ heading
  candidate should turn by **−11.93180° left** and **+14.65915° right**,
  opposite the old inspector's `+Δrecord_angle` sign.
- RETURN scalar +0.10018° from B0, so accumulated controller offsets
  could plausibly drift while the source scalar returns to independent
  value. No native absolute world frame/actor forward-axis proof yet.

## Cause of visual misalignment in current main / club PR #426

`src/wii_ai_golf/inspector/gui.py` originally draws the aim ray as
`R(+current_record_angle−baseline_angle) * (pin−tee)`,
with the initial packet automatically and **without evidence** assumed to
point at the flag. This can rotate the wrong way and jump when a new session
starts with a non-centered aim. It also cannot recover orientation from the
single source value if initial aim is unknown.

The verified numerical matrix in #178/#181 uses source selected-record
`[sin(a),cos(a);−cos(a),sin(a)]`, so a plausible forward vector from the
FIRST **ROW** (not first column) has XZ direction `(sin(a),cos(a))` and
`yaw_candidate=wrap(π/2−a)`. This relation fits B0 near the tee→pin
angle. The **row-vs-column convention is empirical**, not yet a typed
model-to-world forward transformation.

## Change: source-current heading, no integrated baseline

Stacked on #426 **without editing #426's branch or its live club reader**:
- NEW `world_heading_candidate.py`: strictly source-qualified same-packet
  +0x3C BE float and tee/pin candidate. Computes `yaw=π/2−a`,
  builds a forward ray using `sin(a),cos(a)`, and flag bearing residual.
  Tee is a *reference anchor only*, not proved player position.
  Pin defines **ray length only**, not direction. Neither previous
  packets nor button press counts influence direction.
- `gui.py`: default draws direct candidate instead of old baseline-relative
  `aim_ray_hypothesis`; removes automatically assumed first-packet flag aim
  and visible baseline button. Keeps old helper function only for
  compatibility with historical tests/scripts, not the rendered ray.
  Displays source scalar angle, instant XZ heading candidate, flag error,
  and conspicuous HYPOTHESIS/no-player-position label.
- No new Dolphin RPC, game input, shot, savestate, writes, training,
  club index changes or privacy format changes.

## Evidence gates

Original observed residual is extremely promising for a *particular hole*,
but **absolute world orientation remains UNVERIFIED**. An independent
cross-hole/restart test is required:
1. With source scene/hole/selected player qualified, manually center aim
   on the rendered flag on two DIFFERENT holes. Record raw source angle,
   tee→pin source XZ bearing and candidate signed heading difference.
2. On each hole, move left and right; direct candidate must move
   correctly with the visual on-screen aim, not just match one pin.
3. Repeat after Dolphin restart or controlled new session; no manual
   baseline adjustment should be necessary. Quantify residual and any
   fixed axis offset across holes and restarts.
4. If tests differ materially or ray does not follow the visual aim,
   reject this world-frame hypothesis, investigate render/view matrix and
   golfer/shot forward-vector consumer. Do not hardcode B0's +0.18854°
   residual into software.

No source model forward vector, player world XYZ, game-applied shot
heading or physics result is promoted. `training_approved=false`.

## Operator testing without overwriting working inspector

Fetch the stacked, isolated branch into a **new** worktree and start the
existing read-only inspector there. Do not reset or overwrite the
current club worktree. Replace the final launch with whatever exact
inspector invocation your current environment already uses if required.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-DirectAim-20261110'
$branch = 'agent/s002-inspector-absolute-aim-20261110'
if (-not (Test-Path -LiteralPath $repo)) { throw 'Repo path missing' }
if (Test-Path -LiteralPath $work) { throw 'Isolated test worktree exists, refusing overwrite' }
& git -C $repo fetch --no-tags origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
& git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Worktree add failed' }
& py -3 -I (Join-Path $work 'tests\test_p0_inspector_direct_world_heading.py')
if ($LASTEXITCODE -ne 0) { throw 'Focused direct aim tests failed' }
& py -3 -I (Join-Path $work 'scripts\p0_memory_inspector.py') --help
```

For actual GUI launch, see `docs/p0-memory-inspector.md` for the current
accepted CLI options; the above `--help` is intentionally non-invasive.
No automation starts a game or presses A. Confirm no other GUI/bridge
instance is holding the same port before connecting a new read-only viewer.

## Collaboration

This patch is stacked on open club inspector #426 (not main), with another
overlapping inspector GUI/terrain branch #419. Do NOT merge without
coordination and conflict/rebase resolution by S002 inspector owner. It
does not replace #427's source-audit probe or constitute final physics
validation. Draft and private until real operator visual comparison.
