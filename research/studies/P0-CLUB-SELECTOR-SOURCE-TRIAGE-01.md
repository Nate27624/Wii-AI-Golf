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


## First authentic archive result (source-gated, 2026-10-30)

Operator original 7-pair archive and canonical archive SHA passed. The broad static scan yielded 896 source-mapped candidate stores (RPGolConfig 108, Main 7, Player 50, PlayerManager 10, unsplit 721), with 114 store displacements matching player candidate offsets. This is NOT a club-address identification: offsets are relative to the unproven base register, not necessarily the source-selected player record.

The higher-information focus is five **stb** stores in the public `RPGolPlayer.cpp` source unit with displacement +0x034 at source-unit-relative PCs +0x00008, +0x00658, +0x006A4, +0x006D8 and +0x02014. Candidate registers and receiver pointers remain unverified, and previous operator A-released motion changed +0x34; do not call it club index without negative-control separation. The +0xC0 derived float changes with both club and aim; displacements +0xC0 from *GolfConfig* or *unsplit* cannot be confused with player+0xC0. General score-15 store candidates were broad false-positive-heavy.

New `scripts/audit_p0_club_player_byte_source_private.py` performs a **narrow** second-stage decode of all candidate stores AND loads in the genuine RPGolPlayer text interval, including PPC byte loads/stores and floating-point `stfs`/ `lfs` previously absent from the D-form integer-only ranking. It shows only bounded decoded source-relative instruction contexts and register operands; no original raw PPC words or game bytes. This is a static context view, **not executed store witness, club field proof or register dataflow proof**.

Reproduce against original private seven-pair archive using the same exact PR #412 worktree:

```powershell
$originalArchive = Read-Host 'Absolute path to ORIGINAL seven-pair private archive'
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_player_byte_source_private.py') --archive $originalArchive --capture 5 --target-offset 0x34 --limit 22 --context 6
```

Next: source-review the five +0x34 byte stores and corresponding `lbz` reads, trace what value and object base register feed them, and only then decide whether a single operator D-pad change/no-change runtime test is needed. Zero training promotion.

## Tests

Synthetic unit tests cover big-endian PPC load/store decoding, signed displacements, negative branches, ordinal-store selection, negative stack and absolute base controls, unbounded displacements, unrelated copies, controller BL edge, public source map guard, and bad MEM1 guard. Windows and Ubuntu full offline CI required before merge.

All science gates false: `executed_dpad_path_verified=false`, `receiver_pointer_chain_verified=false`, `native_club_index_verified=false`, `training_approved=false`.
