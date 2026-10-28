# S002 ROTATION-RELATION-01 — selected player aim-like matrix

## Private operator finding (no-shot B0-B3)

Existing RSPE01 US Rev1 four-checkpoint private game-memory report showed selected player-record 0 changes only during visible WASD aim at relative +0x3C, +0x40, +0x44, +0x48, +0x4C (source record stride 0xCC). All five unchanged during B0→B1 idle and B2→B3 post-aim idle. 18 selected-record words change over aim vs 1 in each idle control; all source-gated ball objects/start/pin/field remain stationary. The 0x90 word changes in all transitions and is treated as time/idle confound.

Paired samples suggest exact 32-bit equality in a repeated diagonal c and sign-bit negation in off-diagonals s, i.e. relative record window [c, -s; s, c]. The vector length is near one and selected +0x3C behaves like `atan2(s,c)+pi/2` modulo 2pi in both observations. This is a strict **orientation/rotation hypothesis**, not a verified gameplay heading, golfer pose, world axis or shot-power decoder. No private raw record bytes, float observations, runtime heap pointers, screenshot, disc image or provenance hashes are committed here.

## Code

`scripts/inspect_golf_aim_rotation_private.py` consumes only already-preserved ignored local `golf-object-windows-PRIVATE.json` and reuses the strict four-phase source-report parser in `inspect_golf_aim_offsets_private.py`. Reinterprets only five 32-bit words at fixed source-selected relative offsets; compares exact repeated diagonal bits and exact sign inversion, unit vector squared norm residual, angle/quarter-turn residual, relative angular change during B1→B2, and B0→B1/B2→B3 idle stability. Reports quantitative residuals and candidate angle, but never claims game angle/power/physics/training semantics. Does not start or attach Dolphin, send controller input, alter savestates, write output files, upload anything, or depend on ChatGPT Downloads.

Synthetic tests cover a known-angle quarter-turn matrix, confounded bad signs/diagonal, nonunit and wrong theta, malformed/NaN source reports and no-promotion flags; Windows/Linux CI under existing S002 workflow. Reviewer should still cross-check actual PPC writer/read callsites for record +0x3C..+0x4C on RSPE01 Rev1 (RPGolPlayer.cpp) before labeling angle as player aim.

## Standalone PowerShell invocation

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Expanded-Memory"
$branch = 'agent/research/golf-source-object-windows-private-20261027'
$report = "$root\Wii-AI-Golf-Data\ball-study-20261027-212633\golf-object-windows-PRIVATE.json"
if (-not (Test-Path -LiteralPath $report -PathType Leaf)) { throw 'Private report missing' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path -LiteralPath $work) {
    git -C $work rev-parse --show-toplevel | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Existing path is not a worktree' }
    if (@(git -C $work status --porcelain).Count -gt 0) { throw 'Local modifications detected: stop' }
    git -C $work switch --detach "origin/$branch"
} else {
    git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree checkout failed' }
py -m unittest discover -s "$work\tests" -p 'test_inspect_golf_aim_rotation_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed' }
py -I "$work\scripts\inspect_golf_aim_rotation_private.py" --report "$report"
if ($LASTEXITCODE -ne 0) { throw 'Rotation report failed' }
```

## Falsification plan

1. Check actual RSPE01 Rev1 PowerPC source writes to the five player-record-relative fields; verify receiver is the selected +0xCC roster record and distinguish golfer/body/shot-camera orientation.
2. After S001/owner approval, obtain human-observed direction changes in two opposing aim directions with frame- or GUI-correlated single-field reads, leaving ball motion absent. Expect derived angle monotonic and sign-reversing, while selected record and hole stay fixed.
3. Verify branch/angles across different holes/boots; current B0-B3 only support a strong within-session mathematical relation, not absolute world orientation.
4. Treat +0x94..+0xC0 as a second untyped orientation/matrix neighborhood pending independent PPC source trace; do not identify club quaternion/impact from plausible float values alone.

Keep verified-world XYZ, contact, swing power, velocity and training false.