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

## Real operator B0 source-hit outcome: 3,833 instructions scanned

The user actually ran `audit_golf_aim_ppc_offsets_private.py`; six targeted synthetic tests passed. There were 179 direct literal displacement matches in Rev1 Player source unit. Most are NOT shown to be selected-record writes: stack-relative `r1` save/restore addresses, code-vtable-related `r12`/arbitrary structure loads, integer/byte access to same numeric offset, and non-float source uses are confounds. Specifically **do not equate the offset match to a verified selected player object write**.

Priority NONSTACK float writes grouped spatially in source text:

- `0x8029ED9C stfs f1,+0x3C(r3)`; `0x8029EDB4 stfs f0,+0x4C(r29)` and `0x8029EDB8 stfs f1,+0x48(r29)`.
- `0x8029EE2C stfs f1,+0x3C(r29)`, `0x8029EE40 stfs f0,+0x4C(r29)`, `0x8029EE44 stfs f1,+0x48(r29)`.
- `0x802A042C/0430/0434` via r30, `0x802A0554/0568/056C` via r30; similar groups at `0x802A07D0/E4/E8` via r31, `0x802A09B8/BC/C0` and `0x802A0AE8/AFC/B00` via r30.
- Separate position-like triplet `0x8029FAEC/FAF4/FAFC stfs +0x94/+0x98/+0x9C(r28)`; again receiver class unproven.
- No nonstack direct `stfs` at +0x40/+0x44 or +0xA0..+0xBC in the matched D-form list. Actual changed words may be copied via `stw`, indirect addressing, vector/memory helper, or other source unit; absence from this literal scan is NOT proof of immutable source fields. Angle/rotation and quaternion numeric observations remain source-untyped.

New-only `scripts/audit_golf_aim_ppc_context_private.py` prints a fixed set of SHORT source-PC instruction neighborhoods (actual BE PPC instruction values and partial mnemonics) around the grouped candidate sites, reusing the verified private B0 game scene+selected pointer/hash guard. No new dump or Dolphin action. Output enables **manual PPC register/dataflow review** of r29/r30/r31 vs r3 and helper calls instead of collecting meaningless more idle snapshots. Synthetic tests and S002 Windows/Linux CI.

## Next self-contained PowerShell invocation

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Expanded-Memory"
$branch = 'agent/research/golf-source-object-windows-private-20261027'
$private = "$root\Wii-AI-Golf-Data\ball-study-20261027-212633"
if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) { throw 'Missing original B0-B3 checkpoint manifest' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path -LiteralPath $work) {
    git -C $work rev-parse --show-toplevel | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Not an existing worktree' }
    $dirty = @(git -C $work status --porcelain)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Local edits; refusing to update' }
    git -C $work switch --detach "origin/$branch"
} else {
    git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree checkout failed' }
py -m unittest discover -s "$work\tests" -p 'test_golf_aim_ppc_context_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Source-context tests failed' }
py -I "$work\scripts\audit_golf_aim_ppc_context_private.py" --private-root "$private"
if ($LASTEXITCODE -ne 0) { throw 'Source-context audit failed' }
```

The user can paste source-PC neighborhood terminal output in chat for actual dataflow review. Stack r1 should be excluded from any selected-player write claim. Does not identify actual hit, physical XYZ, game-applied heading or power. User's latest raw PPC source output exists only in the private conversation, not as a committed public research artifact.