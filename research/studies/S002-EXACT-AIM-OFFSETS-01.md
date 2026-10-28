# S002: offline exact aim-memory offset inspection (repo-native)

**User report:** `golf-object-windows-PRIVATE.json` from preserved B0/B1/B2/B3 passed source gates; selected `player_record_0` had [1,18,1] changed u32 words across idle / visible WASD aim / idle. RPGolMain had [1,1,1]. All four ball objects, other player records, config, field, start, pin, wind tables and scene had no changed words; pointer bases stayed stable. This is no-shot evidence only.

`scripts/inspect_golf_aim_offsets_private.py` analyzes this existing S002 source-window report with exact u32 hex B0/B1/B2/B3, flags idle-before, aim, idle-after changes and identifies offset candidates that changed only between B1 and B2. Big-endian f32 is printed as a **possible interpretation** only, not a typed field. Source-backed field hints for record+0x24/+0x54..0x68/+0x88/+0xC4 are clearly labeled; unknown offsets remain untyped. Read-only offline, no Dolphin, controller, savestate, memory write, new copy, upload, or file output.

## Self-contained PowerShell block from anywhere

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Expanded-Memory'
$branch = 'agent/research/golf-source-object-windows-private-20261027'
$report = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633\golf-object-windows-PRIVATE.json'
if (-not (Test-Path -LiteralPath $report -PathType Leaf)) { throw 'Existing private report not found' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (Test-Path -LiteralPath $work) {
    git -C $work rev-parse --show-toplevel | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Existing work path is not a Git checkout' }
    $dirty = @(git -C $work status --porcelain)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Existing worktree is not clean; not overwriting' }
    git -C $work switch --detach "origin/$branch"
} else {
    git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree selection failed' }
py -m unittest discover -s "$work\tests" -p 'test_inspect_golf_aim_offsets_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Aim inspector tests failed' }
py -I "$work\scripts\inspect_golf_aim_offsets_private.py" --report "$report"
if ($LASTEXITCODE -ne 0) { throw 'Private aim offset analysis failed' }
```

This command has no dependency on previous PowerShell variables and no Downloads or ChatGPT scratch file. Run in an ordinary Windows PowerShell terminal. The script itself checks that the input is under the known ignored `Wii-AI-Golf-Data` root. The output is the relevant offsets and per-phase numeric words, safe to share with the user's approval. Source/visual validation is still necessary before claiming aim yaw/pitch, contact, ball XYZ, power, velocity or training readiness.

S002/source-owning agents should review changed offsets, map writer/readers in the Rev1 PPC text, and avoid broad full-bank scans before using this new evidence.
