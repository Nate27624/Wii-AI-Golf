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
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_player_byte_source_private.py') --archive $originalArchive --capture 5 --source-unit player --target-offset 0x34 --limit 22 --context 6
```

Next: source-review the five +0x34 byte stores and corresponding `lbz` reads, trace what value and object base register feed them, and only then decide whether a single operator D-pad change/no-change runtime test is needed. Zero training promotion.


### Additional coverage gap: Config+0xBC

The original 26-packet live club collector's `golf_config` layout reads 39 words (4*39 = 156 bytes), i.e. offsets **+0x00..+0x98 inclusive**; it did **not** record Config+0xBC. The broad source scan ranked multiple `stw` sites at displacement +0xBC within the **RPGolConfig.cpp** text interval (source relative +0x00790,+0x007B4,+0x007D4,+0x007F0). Their base registers are unproven; there is no demonstrated receiver-to-config join, nor club semantics. Do not misinterpret this as an established config field. Nevertheless, code context is worth checking before any further operator capture. Second-stage decoder can isolate this with `--source-unit config --target-offset 0xBC` and `--source-unit player --target-offset 0x34`. This is a source-only analysis requiring no Dolphin session.

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_player_byte_source_private.py') --archive $originalArchive --capture 5 --source-unit config --target-offset 0xBC --limit 15 --context 7
```


### Second-stage authentic source result — two misleading original candidates

The original SHA-verified Rev1 `RPGolPlayer.cpp` PPC source shows **5** `stb` sites writing displacement `+0x34`; their adjacent `stb` instructions write `+0x35` using the same base register. At unit-relative +0x00658,+0x006A4,+0x02014 the nearby PowerPC `li` instruction pairs set `(+0x34,+0x35)=(1,0)`; at +0x006D8 the pair is `(0,1)`; at +0x00008 +0x34 becomes 0 and +0x35 is taken from an input register. These are **local static constant assignments** conditional on control flow, not dynamic value observations or proof of receiver being the selected player. Critically, `addi r3,r0,+1` in PowerPC with RA=0 means `li r3,1`, *not* `r3=r0+1`; the original simple context decoder printed this incorrectly. The decoder now prints `li`/`lis` when RA=0 and reports paired constant-store source witnesses.

The source-backed candidate `RPGolConfig.cpp +0xBC` is likewise not a verified club field: around +0x0080C it is loaded, incremented by one, written back, then compared with 16 in a loop. Nearby reads at +0xC4,+0xC8,+0xCC are checked against -1 and indexed. This is consistent with multi-entry loop/bookkeeping rather than a simple four-club enum, but game semantics and receiver roots remain UNPROVEN. New report field `plus_bc_counter_loop_patterns` detects the six-instruction counter signature conservatively.

**Decision:** Do not prioritize Player+0x34 as a four-valued club enum and do not prioritize Config+0xBC as a four-valued club enum based solely on displacement matches. Further work should locate a source consumer of actual D-pad club choices, table lookup, or runtime source-qualified club state in a broader object window, with aim-only and stationary negative controls. No new operator shot or A-button work.


## Third stage: exact public function boundary and static call graph

The public function boundaries resolve the five paired Player +0x34 write sites into exactly three functions: `fn_8029E62C` (+0x00008), `fn_8029EC30` (+0x00658, +0x006A4, +0x006D8), and `fn_802A0320` (+0x02014). The Config +0xBC sites around +0x006D0..+0x007D4 belong to `fn_8029D100`; the +0x007F0/+0x00814 loop sites belong to `fn_8029D238`. These are published function ownership claims, NOT runtime receiver or club evidence.\n\nAfter correcting the earlier local PPC immediate decode and rejecting simplistic offset matches, the next offline research task is to identify **which functions contain the real state transitions** and **who directly calls those functions**. The public upstream `doldecomp/ogws/config/RSPE01_01/symbols.txt` (Git blob `ec42efd5ef247dff7920e905f9004fc579dd3f74`) supplies exact function starts and lengths. A new checked-in public-only index `research/source_maps/RSPE01_01_public_golf_controller_functions.json` retains 643 nonoverlapping Golf and controller function intervals; all are checked against the existing public source-unit spans.

New `scripts/audit_p0_club_controller_callgraph_private.py` SHA-verifies original private seven-pair archive through existing gate, read-only maps original MEM1 and statically scans **only published Golf functions**. It decodes direct PowerPC `bl` edges, attributes each callsite and target to exact public function boundaries, finds static callers up to two hops of Player `+0x34` paired-state writer functions, reports calls into public Controller/KPAD/WPAD input source units, and ranks local Golf Player/PlayerMgr/Main/Config function candidates by nearby bytes writes, small compares and bit tests. Public function and source-unit relative offsets only; **no raw PPC words, ROM bytes, private heap address, native values, or execution assertion**.

IMPORTANT: The report cannot claim that a direct caller was executed on a D-pad event; code may use indirect/vtable calls, inline input reads or other unscanned source units. The original 26-packet experiment's unlabeled aim drift and missing independent Putter heldout also cannot be fixed by static graph ranking alone.

Reproduce in a clean PR #412 detached worktree (uses original 7-pair archive, does not use the 26-packet club JSONL):

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_callgraph_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_callgraph_private.py') --archive $originalArchive --capture 5 --limit 20
```

Find the direct upstream calls into the five bounded Player +0x34 functions, inspect any directly linked input reader and alternative byte/small-enum setter functions. These are static candidates until the source-selected receiver is proven. No emulator input is required for this offline stage, and `selected_club_variable_verified=false`.


### Authentic function graph result and expanded source coverage

Operator original B0 private SHA-qualified read-only callgraph (on earlier 643-public-function index) found **433** Golf functions, **1,331** direct PPC call edges, and two direct calls into input source units: `RPGolMain::fn_8028E0E4` to WPAD at Main unit +0x0009C and `RPGolPlayer::fn_8029EC30` to EGG Controller at Player unit +0x006B4. Static upstream of `fn_8029EC30` is PlayerManager `fn_802A28DC` then GolfMain `fn_8028E158`. These are source-only function call edges (not execution on actual D-pad events); `fn_8029EC30` also writes the +0x34/+0x35 paired flags, likely a separate state mechanism.

**Coverage correction:** The initial 643-function index omitted the enormous `RPGolScene_unsplit.o` source unit and did not include EGG/KPAD/WPAD function names. The updated index contains **1,342 exact source-qualified Rev1 function intervals** (public upstream metadata only). This expands the same original-archive static callgraph scan into the unsplit Golf Scene region and identifies the specific published EGG/WPAD called function entries. New `--focused` print mode emits only source-relative input calls and three known Player byte-writer function chains. This broader static scan may show more than the originally reported two controller calls. It is important not to call any source function the club-changing handler without a separate proof of its D-pad input semantics and selected receiver.

Operator-local command in PR worktree:

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_callgraph_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_callgraph_private.py') --archive $originalArchive --capture 5 --focused --limit 50
```

Avoid repeat A-button/shot test or unbounded raw memory uploads. Training approval remains false.

## Tests

Synthetic unit tests cover big-endian PPC load/store decoding, signed displacements, negative branches, ordinal-store selection, negative stack and absolute base controls, unbounded displacements, unrelated copies, controller BL edge, public source map guard, and bad MEM1 guard. Windows and Ubuntu full offline CI required before merge.

All science gates false: `executed_dpad_path_verified=false`, `receiver_pointer_chain_verified=false`, `native_club_index_verified=false`, `training_approved=false`.
