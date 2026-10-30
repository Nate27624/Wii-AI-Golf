# P0 Club Selector Static Source Triage — 2026-10-30

## Evidence motivating source search

The authentic read-only operator club experiment generated 26 source-identity-stable packets in Hitting-the-Green (Driver, Iron, Wedge, Putter). SHA matched. Two train passes produced eight player-record +0x94..+0xC0 candidate 32-bit words with distinct values per club, but all failed the same-club AIM0 control and three valid heldout V0-V2 exact-value tests. The final V3 selected Wedge while prompted Putter, thus V3 is excluded as a Putter label. A specific visible-club ID was **not** established. Fields +0xA0..+0xBC look float/transform-like, +0xC0 exhibits relative club spacing but shifts with aim. These findings are operator-supplied, not published original native values.

## Implementation and boundaries

`scripts/audit_p0_club_selection_code_private.py` reuses the existing canonical original-seven-pair archive SHA and layout gate (`audit_p0_seven_numbered_source_pairs_private._check_archive`), reads one source-selected 24MiB **original** MEM1 bank by read-only mmap, validates RSPE01 revision 1 header, and limits static PPC instruction analysis to PUBLIC `doldecomp/ogws` Rev1 source units RPGolMain, RPGolConfig, RPGolPlayer, RPGolPlayerManager and RPGolScene_unsplit. It uses the committed `RSPE01_01_public_text_units.json` source map. No arbitrary heap scan, live Dolphin, code injection, controller calls, memory writes, disassembly bytes or private physical addresses in output.

The analyzer also indexes candidate source writes whose displacement matches the 26-packet observed player offsets (+0x34, +0x94..+0xC0), without asserting that the base register points to the selected player record.\n\nThe conservative PPC decoder handles D-form stw/stb/sth and nearby cmpi/cmpli 0..8, addi +1/-1, andi./andis., conditional branch and direct b/bl destinations into source-mapped RPSysController code. It **does not decode branch conditions, build a CFG or prove register/receiver ownership**. Static proximity is a ranking heuristic, not a native club selector witness. Source unit output uses source-relative code offsets and source object displacement only, not executable words or heap pointers. Code paths that use indirect calls, X-form/FP stores, packed control tables or external units may be missed.

### Operator-local read-only reproduction

Run from an independent detached worktree of the PR code. The archive should be the ORIGINAL seven-pair capture, not the 26-packet club JSONL.

```powershell
$orig = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
git -C $orig fetch origin pull/412/head
$work = Join-Path (Split-Path $orig -Parent) ('Wii-AI-Golf-P0-Club-Source-' + [guid]::NewGuid().ToString('N').Substring(0,8))
git -C $orig worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_selection_code_private.py') --selftest
$archive = Read-Host 'Absolute original PRIVATE seven-pair archive directory'
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_selection_code_private.py') --archive $archive --capture 5 --limit 25
```

The inspector is **offline** and cannot tell which static instruction actually executed on D-pad input. The next high-value step after reviewing its source-unit/offset results is to inspect candidate function neighborhoods, prove the caller/receiver chain into selected-player or club object, then separately compare executed D-pad club switch (without A or swing) against no-change control. No training promotion or club-ID mapping until independent runtime/semantic evidence.

## Tests

Synthetic unit tests cover big-endian PPC load/store decoding, signed displacements, negative branches, ordinal-store selection, negative stack and absolute base controls, unbounded displacements, unrelated copies, controller BL edge, public source map guard, and bad MEM1 guard. Windows and Ubuntu full offline CI required before merge.

All science gates false: `executed_dpad_path_verified=false`, `receiver_pointer_chain_verified=false`, `native_club_index_verified=false`, `training_approved=false`.
