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

## Expanded 994-Golf-function controller-call results and source consumer audit

Operator SHA-qualified read-only trace with 1,342 public function-symbol entries scanned 994 Golf functions and found **3,925 static BL edges**, only 14 direct calls into named input-related code units (not necessarily D-pad!). Two early leading calls were disambiguated:

- `RPGolMain::fn_8028E0E4` -> `WPADControlMotor` at Main source +0x0009C: motor control, not a direct club-selection read.
- `RPGolPlayer::fn_8029EC30` -> `getNthController__Q23EGG17CoreControllerMgrFi` at Player +0x006B4: obtains an EGG controller object; **not** proof of a pressed button or selected club. This function nevertheless has three previously described Player +0x34/+0x35 flag writes; its upstream static chain remains Main fn_8028E158 -> PlayerManager fn_802A28DC -> Player fn_8029EC30.

More plausible controller-*status* consumers include Golf Scene `fn_802B4794` (three direct `getExCoreStatus__19RPSysCoreControllerFii` calls), `fn_802B439C` (one `getExCoreStatus` and one `getAccel`), and `fn_802B4474` (one `getAccel`). They could just as well service swing/acceleration rather than D-pad. Direct calls miss vtable dispatch, inlined EGG CoreStatus buffer reads and scene object handlers.

New `scripts/audit_p0_club_controller_status_consumers_private.py` inspects only these explicit published Rev1 function boundaries in the original SHA-qualified MEM1 bank. It emits bounded **decoded instruction** windows around the status getter calls with nearby return-value reads, bit-mask/rotate shapes, branch conditions and receiver-base stores. No original PPC instruction bytes, native RAM values, or executable addresses are emitted. `--focus scene-status` (default), `--focus player-controller`, and `--focus all`; `--limit 4` limits getter windows per function. It treats any unrecognized PPC op as *not decoded* rather than inventing semantics. It never claims an input-button bit, code execution, receiver ownership or club enum.

Operator-local offline example, using original seven-pair archive and a detached PR #412 checkout:

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_status_consumers_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_controller_status_consumers_private.py') --archive $originalArchive --capture 5 --focus scene-status --limit 4
```

Decision: inspect status-dependent branches and writes *before* another live experiment. If code only interprets accelerometer/pose data, explicitly drop this branch and pivot to static UI selection handlers with inlined status load patterns. Even a convincing static branch must be linked to the source-selected active club state and validated with an independent D-pad change/no-change test before training.


Synthetic unit tests cover big-endian PPC load/store decoding, signed displacements, negative branches, ordinal-store selection, negative stack and absolute base controls, unbounded displacements, unrelated copies, controller BL edge, public source map guard, and bad MEM1 guard. Windows and Ubuntu full offline CI required before merge.

All science gates false: `executed_dpad_path_verified=false`, `receiver_pointer_chain_verified=false`, `native_club_index_verified=false`, `training_approved=false`.


## Fourth stage: EGG/WPAD D-pad integer-source triage

The operator's original SHA-qualified scene-status trace shows motion/sensor-oriented control handling rather than a club index. `fn_802B4794` called three indexed `getExCoreStatus` and wrote 11 nonstack floats; `fn_802B439C` called `getExCoreStatus` and `getAccel` and had no nonstack stores in inspected range; `fn_802B4474` called `getAccel` and wrote floats and other state. These are lower-priority club-selection leads, not disproven unreachable code.

Published original ogws `include/egg/core/eggController.h` defines `cCORE_BUTTON_UP = 1 << 3` (0x0008), `cCORE_BUTTON_DOWN = 1 << 2` (0x0004); `include/revolution/WPAD/WPAD.h` defines corresponding Wii Remote Up/Down bits. These are SOURCE button definitions, not discovered native memory locations. The button bits provide a much tighter static search.

`scripts/audit_p0_club_dpad_integer_selector_private.py` SHA verifies the original seven-pair archive, read-only maps original Rev1 MEM1, and statically examines only published Golf function boundaries. It looks for exact `andi.`/ `andis.` masks of 0x4,0x8,0xC and `rlwinm[.]` masks whose **correct PPC rotate-left inverse** selects only those input bits (input bits = ROR32(output-mask,SH)), nearby +/-1 `addi`, small integer comparisons, conditional branches and nonstack `stw/stb/sth`. Broad masks such as 0xFFFF are explicitly **not treated as D-pad evidence**. It retains single-direction functions because Up/Down could use separate handlers. It lowers priority on the three motion-heavy functions already investigated. Results report source unit relative code offsets, public function name and unverified object-field displacement, never raw RAM bytes, original instruction words, selected heap roots or an actual selected-club mapping. It deliberately avoids dynamic input modification.

**Limitations:** An exact bit shape in a function does not prove it was applied to controller status, and proximity is not source-backed dataflow/branch ownership. Input could also be checked through register constants, inlined status buffers, virtual dispatch or computed lookups, which this first static search may miss. No club training promotion without independent heldout and aim-only controls.

Operator offline command from a fresh PR #412 detached worktree:

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_dpad_integer_selector_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_dpad_integer_selector_private.py') --archive $originalArchive --capture 5 --limit 30
```



## Fifth stage: strongest four-club D-pad selector candidate

Operator's SHA-qualified original seven-pair archive source scan from `audit_p0_club_dpad_integer_selector_private.py` scanned **994** Golf functions. Exactly **three** contained strict source-defined Up/Down bit shapes and only **one** contained both direction bits:

- **`RPGolPlayerManager::fn_802A28DC`** public unit-relative function +0x006CC, size 984 bytes: Up bit masks at +0x0081C and +0x00910, Down bit masks at +0x00834 and +0x00928, PPC `addi -1` at +0x0085C and `addi +1` at +0x008A8. Source source code confirms EGG/WPAD UP=0x8, DOWN=0x4. This combination in one manager function is a **strong source-supported selector-path hypothesis**; input register origin, executed control path and destination selected-club data are **NOT yet proved**. The existing callgraph also has a static `RPGolMain::fn_8028E158 -> RPGolPlayerManager::fn_802A28DC -> RPGolPlayer::fn_8029EC30` path, although `fn_8029EC30` primarily writes paired byte state flags +0x34/+0x35 and calls `getNthController`. No nearby nonstack D-form integer stores were detected in the manager's first scan: the value may be passed via a call, preserved in a register, sent to a non-D-form store, or written further away.
- `RPGolMapObjBall::fn_80298E70` contained one Up shape, integer `-1/+1` and unrelated possible writes (+0x94/+0x5C); likely ball/map processing but cannot dismiss without instruction-level evidence.
- `RPGolScene_unsplit::fn_802ABD50` contained one Up shape and nearby stores (+0x2C/+0x24) but no local ordinal-step witness. Its club significance is unknown.

New narrowly scoped `scripts/audit_p0_club_dpad_handler_flow_private.py` decodes original SHA-qualified private **entire named Rev1 source function** for just three previously anchored candidates. It collects exact masks and local increments, coalesces bounded +/-16-instruction windows, annotates all direct call targets with published function names, shows conditional branch targets in source/function-relative code offsets, and indexes integer/floating-point nonstack stores. **No raw PPC word, native executable absolute address, private memory, or live Dolphin interaction is printed**. It does not prove D-pad status provenance or club-index ownership. Tests cover direct call target attribution, branch math, register-mask operands, unknown receiver provenance, and output bounds.

Operator-local exact PR #412 worktree command, original private **seven-pair** archive only (NOT the 26-packet club study):

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_dpad_handler_flow_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_dpad_handler_flow_private.py') --archive $originalArchive --capture 5 --focus player-manager --context 16 --max-lines 140
```

The next proof must identify a source-qualified path from the observed D-pad input register via conditional branches and the +1/-1 arithmetic into the **live selected-club owner field**, not merely a bit mask adjacent to a counter. Validate player/scene identity, aim-only negative controls and heldout club switching before any training claim.



## Sixth stage: actual direction-call argument witness and two unrelated manager counters

Original archive's source-qualified PPC handler flow contains **four** directional branch sites in `RPGolPlayerManager::fn_802A28DC`: Up masks +0x0081C and +0x00910; Down masks +0x00834 and +0x00928. In **both branches** the same static callee `RPGolScene_unsplit.o::fn_802A9BC8` (absolute public source function start 0x802A9BC8, size **1048** bytes) receives `r4=0` after the Up test and `r4=1` after Down, at manager public source +0x0082C/+0x00844 and +0x00920/+0x00938 respectively. `r3` is loaded from a `r13` global immediately before these calls, whose object identity is unproven. Button-word source is repeated `lwz r0,+0x18(r31)` then exact `rlwinm` mask; `r31` remains an unverified pointer to an actual controller-status buffer.

The nearby signed ordinal steps **do not write the same field**:
- manager source +0x0085C `addi r0,r3,-1`, then +0x00860 `stw r0,+0x4F4(r29)` after loading `+0x4F4(r29)`;
- manager source +0x008A8 `addi r0,r3,+1`, then +0x008AC `stw r0,+0x340(r29)` after loading `+0x340(r29)`.

Therefore, the original scanner's proximity score 20 is not proof of symmetric `club--` / `club++`. Source reports also reveal writes `+0x340(r29)` initialized to zero elsewhere and bytes +0x33C/+0x33D; these must be traced separately from the Up/Down dispatch.

New `scripts/audit_p0_club_direction_dispatch_private.py` uses **only** the canonically SHA-verified original private seven-pair archive and exact published Rev1 function bounds to inspect `fn_802A9BC8` (public upstream function length 1048 bytes), with optional `--focus post-direction` for `fn_802A8850`. It prints bounded decoded instruction windows around the shared callee's entry `r4` parameter, small integer compares and non-stack stores, and lists its source-resolved direct calls and writes. No native instruction words, heap values or emulator writes escape. A direct call with `r4=0/1` does **not** establish whether the callee changes a club, plays a UI sound, or changes another mode. The new test suite checks relative source call boundaries, r4 comparisons, possible writes and refusal gates. Never promote club field, D-pad runtime, or training without a separately proven receiver chain and heldout evidence.

Clean PR #412 worktree, original seven-pair archive only:

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_direction_dispatch_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_direction_dispatch_private.py') --archive $originalArchive --capture 5 --focus direction-dispatch --max-lines 120
```



## Seventh stage — four-state index write source evidence (not club-ID validation)

A new operator ORIGINAL SHA-qualified exact function decode for `RPGolScene_unsplit::fn_802A9BC8` shows a **symmetric read/modify/write of the SAME field** `+0x01C(r3)` with integer bounds 0 and 3. This is the first robust discrete-state writer found (unlike the earlier unrelated manager +0x4F4 and +0x340 counters). Four manager callsites load `r3` from `-0x5A80(r13)`, set `r4` to literal 0 on the Up(0x0008) branch and literal 1 on the Down(0x0004) branch, then directly `bl fn_802A9BC8`.

**Precise semantics of the callee:** At handler function +0x0E8, `cmpwi r4,0`, then **PPC BO=12 BI=2 is `beq`**, so `r4 == 0` (Up caller) branches to +0x234. That arm loads `lwz r4,0x1c(r3)`, compares to 0, applies `addi r0,r4,-1` and `stw r0,0x1c(r3)`. The other arm (`r4 != 0`, Down caller) loads the same field, compares to 3, applies `addi r0,r4,+1` and writes to the same field. This matters: reversing the equal/not-equal branch would erroneously invert the directions. The upstream trace also showed source calls into PlayerManager and Golf Scene after index changes, as well as audio/indirect-dispatch paths. Actual receiver object identity must still be established.

**Likely semantics:** source-qualified **four-state integer index** (0..3), consistent with 4 visible clubs. It is **not yet a game-owned verified club selection ID**, because user-visible Driver/Iron/Wedge/Putter value mapping, live receiver pointer, Hitting-the-Green state, and heldout controls are not established for this object. No training promotion.

A new narrowly scoped source proof `scripts/audit_p0_club_four_state_writer_private.py` performs original seven-pair SHA preflight, reads exact public Rev1 PlayerManager and Scene function ranges, fails closed unless all four manager callsite argument and r13 global loads match, and unless both comparison bounds, `+1/-1` instructions, PPC equality branch target, and both same-object `stw +0x01C(r3)` instructions match. It emits only short decoded code context and source-based pointer expressions, no native data or executable code bytes. Synthetic tests reject changed bounds, different field offsets, fake direction arguments, wrong branch targets and wrong global roots.

Run in PR #412 worktree:

```powershell
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_four_state_writer_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\audit_p0_club_four_state_writer_private.py') --archive $originalArchive --capture 5
```

Next P0: resolve the original code’s `r13` static small-data base for this exact Rev1 executable or read current r13 from an explicitly source-qualified Dolphin register interface; follow `lwz r3,-0x5A80(r13)` read-only, check RAM object identity and `lwz current_index,0x1c(r3)` for valid 0..3, then independently check visible four clubs with a no-change and aim-only control. Operator's original 26-packet study sampled different objects and is not proof of this field. **Do not collect more shot or A-button captures for club mapping**.



## Live test authorized: four-state source index against visible clubs

The original seven-pair source audit `audit_p0_club_four_state_writer_private.py` passed against the operator's preserved original Rev1 private archive and established a **source-code bounded 4-state writer at `+0x1C(r3)`**. It does NOT prove r3 is the selected club object, or index order. Earlier console JSON reversed the directional labels (`r4_eq_0` vs `r4_ne_0`) despite decoding `beq`; the correct PPC source is **D-pad Up(r4=0) -> decrement** and **D-pad Down(r4=1) -> increment**, both bounded [0..3].

Original source-side callee r3 is loaded `lwz r3,-0x5A80(r13)`. Independently the canonical existing source-gated live experiment reader maps `PLAYER_MANAGER_STATIC = 0x804BF8D0`, validating its pointed-to MEM2 PlayerManager vtable, active Golf scene, mode 4, selected player and ball. The arithmetic `0x804BF8D0 + 0x5A80 = 0x804C5350` is an **inferred possible static r13**, not a directly read runtime register or proof that this is the identical global slot. The new live experiment deliberately reads the already validated PlayerManager root; it must NOT claim r13 registration certainty.

`scripts/p0_live_four_state_club_index_private.py` uses only loopback `memory.read_u32`, `memory.read_bytes`, `frame.get_count`, `bridge.ping`; no Dolphin launch, button injection, memory writes, savestate, or automated swing. Operator controls the visible clubs and confirms label for every phase. It reads the candidate `pm+0x1C` twice, cross-checks scene/config/hole/selected owner and ball position for unchanged trial identity, and refuses a non-[0..3] index. One idle negative control; manual Up and Down single-step tests; aim-only negative control; full four-club training pass forward and reverse; four withheld self-selected club trials with labels reported only after selecting. The event stream and SHA manifest stay in a fresh PRIVATE directory outside Git, with only label/index status in stdout.

The result `LIVE_FOUR_STATE_CANDIDATE_VALIDATED` means all of these local observational checks passed; **`game_club_id_verified` and `training_approved` remain false** until explicit science-owner review of source/global receiver join and independent hidden validation. `LIVE_FOUR_STATE_CANDIDATE_NOT_VALIDATED` and any `ABSTAIN_*` must not be promoted.

Command in exact pinned detached PR #412 worktree (operator launches Dolphin manually and gets to ready-to-hit Golf mode 4):

```powershell
& py -3 -I (Join-Path $work 'scripts\p0_live_four_state_club_index_private.py') --selftest
& py -3 -I (Join-Path $work 'scripts\p0_live_four_state_club_index_private.py') --private-root 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures' --port 55355
```

This is **only** selected-club index research. Do not collect ball/aim/power repeated sweeps, press A, or launch unsolicited controller automation.



### Five-phase fast live candidate check before full study

Prefer the new `--quick` path first, using the SAME source-gated PlayerManager root and read-only RPC. It asks the operator for five phases: B0 visible club, unchanged IDLE, exactly one manual D-pad UP, one manual D-pad DOWN, and an AIM-only change retaining the current visible club. It reads `pm+0x1C` twice per phase, checks global pointers, scene/mode/hole, selected player and ball position, and rejects mode/player changes. The result must agree with UP index decrement, DOWN index increment (each bounded 0..3) **and each club-name change must match whether the index changed**. At least one club must visibly change. No claim of a full 4-club mapping from this quick check. Only then run the same script without `--quick` to obtain two full club passes and four operator-labelled heldout selections.

```powershell
& py -3 -I (Join-Path $work 'scripts\p0_live_four_state_club_index_private.py') --private-root 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures' --port 55355 --quick
```

