# S002-PLAYER-ORIENTATION-PPC-01: literal source writes to selected golfer candidate

**Status:** Source code reconnaissance, strictly private offline B0 native images; no Dolphin, game action, ROM capture or training. The user independently ran the B0-B3 selected record orientation diagnostic. Matrix angle before/after WASD aim = 37.257573° -> 12.130617°; +0x3C angle (minus quarter turn) agrees to ~0.00003° in change. Quaternion-like group +0xA0..+0xAC agrees with the same angular reading within 0.02°, +0xB0..+0xBC has norm ~1 but independent near-zero Y rotation. All idle control values unchanged. This is **same-record numerical corroboration, not multiple independent camera/gameplay measurements**.

## Implementation and limits

New `scripts/audit_golf_aim_ppc_offsets_private.py` validates B0-MEM1 and B0-MEM2 native 24MiB+64MiB images and their existing private manifest SHA256, then invokes canonical #160/#163 scene5/sport2/RSPE01 Rev1/mode4, record0 source index, selected child ball/start source gates. Only after those pass, it inspects fixed `RPGolPlayer.cpp` source .text 0x8029E62C..0x802A2210 (no broad RAM scan) for PPC D-form `lwz/lbz/lhz/lha/lfs/lfd` and `stw/stb/sth/stfs/stfd` with **literal displacements** equal to the observed selected record's aim-related changed relative offsets: +0x03C..+0x04C and +0x090..+0x0C0. Prints instruction PC/mnemonic/base and source-or-destination register, opcode word, per-offset read/write counts and writer PC lists. Everything from **local B0 memory**; no binary or runtime pointer is written to git.

Important scientific caveat: a PPC D-form instruction whose literal displacement matches a candidate record field does NOT establish that its base register is the selected 0xCC roster record. It might be some other pointer/class, and stores that use indexed registers or pointer arithmetic may be missed. Source owner must follow calling convention, register dataflow and object construction to establish true member ownership. Negative matched-write counts do not rule out a field.

## Completely standalone PowerShell procedure (no placeholder paths)

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Expanded-Memory'
$branch = 'agent/research/golf-source-object-windows-private-20261027'
$private = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633'
if (-not (Test-Path -LiteralPath (Join-Path $private 'B0-MEM1.bin') -PathType Leaf)) { throw 'Original B0 private checkpoint is missing' }
if (-not (Test-Path -LiteralPath (Join-Path $private 'B0-MEM2.bin') -PathType Leaf)) { throw 'Original B0 MEM2 checkpoint is missing' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (Test-Path -LiteralPath $work) {
  git -C $work rev-parse --show-toplevel | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Existing directory is not a worktree' }
  $dirty = @(git -C $work status --porcelain)
  if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Worktree has local edits; refusing to modify' }
  git -C $work switch --detach "origin/$branch"
} else {
  git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree update failed' }
py -m unittest discover -s "$work\tests" -p 'test_golf_aim_ppc_offsets_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Source scanner tests failed' }
py -I "$work\scripts\audit_golf_aim_ppc_offsets_private.py" --private-root "$private"
if ($LASTEXITCODE -ne 0) { throw 'Private source PPC scan failed' }
```

User can share the JSON text printed to their own terminal for code-site review; no files are written. Do not invent semantic field mapping from raw matches. S002 owner needs to establish actual receiver/writer dataflow. The training/physics/power flags remain FALSE.
