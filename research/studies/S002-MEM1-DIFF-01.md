# S002-MEM1-DIFF-01 — Private full-MEM1 checkpoint differential

**Status:** OFFLINE analytical component of S000/S002 PR #148 `S002-FULL-STATE-DISCOVERY-01`. Does not authorize a new Dolphin game run, a raw memory dump, a controller action, or private data upload. Owner review requested from S002 #3, S001 #2 (Felk fork capability), S000 #94 (publication); S003 #4 downstream.

## Scientific hypothesis and priority

Historical source-gated first-level object probes (28 pointer-shaped child windows) yielded no verified aim-sensitive golfer fields. The recurring main `+0x074` and three child words share a positive frame-scaled change pattern during idle. Their clock-like behavior makes them poor discriminative power sensors. Stop repetitive child-window / ten-power sweeps. We now need an actual game-state dictionary: scene/hole/ball, player identity, club transform, per-shot power/velocity/landing, score, and provenance tiers.

**H0:** Across four native memory checkpoints B0 still → B1 delayed still → B2 human-labelled WASD pointer-only → B3 returned idle, all memory differences arise from timing, UI/scene, background state, relocation or other nuisance. **H1 (exploratory):** there exist 32-bit aligned words that are stable B0→B1 yet change B1→B2, possibly reversing B2→B3. This is a *candidate class only*, not club pose or power. One boot and human phase labelling cannot establish causality. A changed byte of a u32, including partial floats, counts as an entire aligned word; no value or float interpretation is provided.

## Capability gate: no live instructions until S001 confirms native dump

Use **ONLY** the operator's installed working Felk Dolphin fork, and only after S001 demonstrates a non-destructive NATIVE plain MEM1 dump from the debugger that does not alter canonical Dolphin boot, savestate, or RPC/bridge behavior. Verify: 24 MiB file length (25,165,824 bytes), PPC cached memory corresponds to `0x80000000–0x817FFFFF`, raw file begins RSPE01 and revision 1 at byte offset 7; no savestate wrapper/header; consistent same boot, scene, sport, mode, hole and checkpoint capture timestamps. WiiBrew memory map confirms 24MiB MEM1 and separate 64MiB MEM2. S001 must inspect *Felk Preview 4* explicitly; mainstream Dolphin UI screenshots are not evidence that the fork supports the same operation. Do NOT stream whole RAM via Felk's slow per-byte `memory.read_bytes`, attach a second bridge, or issue emulation.pause through frame-polled RPC.

Once separately approved, checkpoint labels are B0 first-ball stationary; B1 after timed stationary period; B2 WASD aim/camera only (no A or swing); B3 after release while idle. If B3 stays at a changed aim setting, `B2/B3 persistent` describes memory persistence, not game-power response. Repeat and vary conditions only after useful source leads. No shots or optimizer training during these controls.

## Implemented offline reducer (NEW paths only)

- `src/wii_ai_golf/audit/mem1_checkpoint_diff.py`: standard-library streaming/mmap page-level 4-way equalities, counts per 4KiB page, ranked B1→B2 candidates after B0→B1 still controls, returned-to-B1 and persisted-at-B3 counts. Cap 24 pages; an empty or identical whole image is explicitly diagnosed, not silently labelled static physics.
- `scripts/analyze_mem1_checkpoints.py`: opt-in OFFLINE-only CLI requiring exact four unique private files under operator-owned private directory, exact uncompressed MEM1 byte length and RSPE01 Rev1 header, refuses existing output, unsupported extension, symlink or mismatched roots. Prints only approved-for-local-review aggregate counts; no raw values, pointers, per-word offsets, local paths, or network.
- `tests/test_mem1_checkpoint_diff.py`: synthetic native binary fixtures, controls, 4K page word comparisons, false pointer/private value exclusion, duplicate/partial/savestate/revision errors and outputs. GitHub CI checks both Windows and Linux plus full suite; any failures are reported before merge.

Output kind `local-mem1-four-checkpoint-differential` is explicitly `allowed_to_publish:false`, `power_verified:false`, `club_pose_verified:false`, `ball_position_verified:false`, `game_mode_and_hole_verified:false`, `all_checkpoints_verified_same_live_boot:false`. The tool cannot independently prove a dump was taken at the intended moment, from the same emulator boot, or has the right game hole/mode; **separate human/source validation required**. Page-relative offsets are aggregates and should remain local until S000 approves a public schema. Actual contents, private MEM1 files, source code binaries, ROMs, Wii IDs and file paths must never be uploaded.

## Future operator OFFLINE command, ONLY AFTER vetted Felk native dump exists

~~~powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-Offline'
$branch = 'agent/research/offline-mem1-checkpoint-diff'
$private = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem1-checkpoints'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $work)) { git -C $repo worktree add --detach $work "origin/$branch" }
if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
py -m unittest discover -s "$work\tests" -p 'test_mem1_checkpoint_diff.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Comparator unit tests failed' }
py "$work\scripts\analyze_mem1_checkpoints.py" --private-root $private --b0 "$private\B0.bin" --b1 "$private\B1.bin" --b2 "$private\B2.bin" --b3 "$private\B3.bin" --output "$private\B0-B3-private-diff.json"
if ($LASTEXITCODE -ne 0) { throw 'Local-only MEM1 comparison failed' }
~~~

**Study budget:** one B0/B1/B2/B3 session and zero swings, ONLY after Felk-native capability and same-boot checks. No file exchange via chat; user may paste sanitized aggregate output after review. If unsupported debugger export, stop—S001/S002 should design vetted in-process memory snapshot rather than inventing commands.

## Next source validation, not modeling

Apply bounded relevant object ranges from RSPE01 Rev1 decomp and PR #122/PR #144/PR #146 access atlases, filtering page-level candidates for plausible player/club/ball object ownership and real PowerPC STORE write-site. Mainstream class names, `r3`-relative displacements and pointer-shaped data are **leads, not verified C++ instance fields**. Use debugger watchpoint to connect write PC and captured value meaning. Add verified field dictionary entries only when source-backed, runtime observed, independently repeated and corroborated by gameplay. S003 then tests same-shot inputs/outputs; S004/S005 wait.

**Do not merge** until S002 owner review, tests, branch freshness, S000 compatibility review and mandatory full suite pass. No direct main edits, raw private capture files or blind memory scans committed.
## Felk source-verified native debugger export (2026-10-27)

Checked `Felk/dolphin` upstream source, not an assumed mainline UI: `Source/Core/DolphinQt/Debugger/MemoryWidget.cpp` ~L260 registers Memory-dock menu `Export → Dump MRAM` and `Export → Dump ExRAM`. `OnDumpMRAM()` ~L749 obtains `AddressSpace::GetAccessors(AddressSpace::Type::Mem1)` and calls `DumpArray(File::GetUserPath(F_MEM1DUMP_IDX), begin, length)`; `DumpArray` opens with `"wb"` (so each dump can **overwrite the previous default file**). `Source/Core/Common/FileUtil.cpp` ~L902 maps `F_MEM1DUMP_IDX` to Dolphin user Dump directory + MEM1_DUMP. This is a genuinely direct native binary export code path, NOT 24MiB of per-byte Felk bridge RPC.

**STILL REQUIRES operator-binary UI verification**: the GitHub fork's current source is not proof that the separately packaged Felk Python Scripting Preview 4 executable contains/enables this exact dock/menu. Non-destructive Stage 0: close Dolphin before changing debugger mode; in the working fork enable Debugging UI (if available), launch via canonical script, inspect `View → Memory` dock for `Export → Dump MRAM`. DO NOT click a dump button until the output directory, overwrite behavior and safe pause/one-session procedure have been reviewed. MemoryWidget hides itself whenever `IsDebugModeEnabled()==false` (constructor). Report simply `menu present` or `menu absent` or send a screenshot of the menu; never upload RAM.

After Stage 0 passes, each native dump can be copied promptly to a distinct private B0/B1/B2/B3 filename *before the next Export → Dump MRAM*, retaining source `mem1.raw` as a temporary only. All writes are to local files; preserve existing savestates and no RPC pause/resume. Before comparison validate actual physical size and RSPE01 Rev1 header; our strict comparator refuses unknown formats.

External general reference (NOT claim for this packaged fork): https://www.wiibrew.org/wiki/Memory_map confirms 24MiB MEM1 address space. Historical Dolphin export guide: https://mariokartwii.com/showthread.php?tid=1141 ; this guide is older and may use a different menu layout, so prefer verified Felk source above.

## Initial CI (PR #151)

Github Actions workflow 40607500241 (Ubuntu and Windows, Python 3.13): compile PASS, new targeted 13/13 tests PASS on BOTH OS. Full regression not green for pre-existing unrelated failures: Ubuntu `test_lab_core` lock message `may be active` vs `already active` 1/375 failure (PR #131), Windows 7/375 short Windows Temp `RUNNER~1` versus `runneradmin` mismatches (Windows test-env alias known from #141). Not a passing merge gate; PR remains draft pending owner review/full tests.
## First real paired bank B0 confirmed — original captures (2026-10-27)

The operator provided paired native MEM1 and ExRAM snapshots for local-only analysis, which passed the 24MiB/64MiB sizes, `RSPE01` Rev1 header and source-gated source-mapped pointer chain. We do NOT know whether two GUI export actions were at the exact same emulated frame or same boot; cross-bank backlink coherence is evidence of compatible snapshots, not a timestamp guarantee. Missing locally extracted `main.dol` blocks PR #144/#146 STATIC CODE atlas only, NOT this RAM source checks.

Sanitized source-backed findings (no actual RAM pointer bytes, values or paths released): the two `.sbss` manager static candidates contain one readable scene manager in MEM1. Manager current scene ID5, its active Golf scene in MEM2 at expected +0x0C, scene+0x1C ID5 and scene+0x20 backlink to manager, sport2 at +0x54. `RPGolScene+0x9C` points to readable candidate `RPGolMain` in MEM2. Main object +0x004 points back to scene; its first word falls in the Rev1 RPGolMain `.data` range (data-region hint; NOT verified C++ vtable). The static golf config object points to MEM2 and has mode4 and raw current hole index1 at documented +0x94/+0x98.

Source-static field manager is readable in MEM2: 6 pin objects and 31 start objects, with current pin, current start, cup, wind, course and map data source-named pointers all resolving to MEM2. Candidate player manager singleton also points to MEM2 and first word falls in Rev1 player-manager `.data` interval (not verified class identity). The 0x100-byte candidate golf-main window contains 29 *pointer-shaped* 32-bit words with readable 0x80-byte targets: 25 point to MEM2 and four to MEM1. Includes potential vtable/text data and overlapping targets; NOT 29 proven owned children. This is an object relationship map, not proof of club pose, ball XYZ, power or timing.

**Implementation added to PR #151:** `src/wii_ai_golf/audit/golf_cross_bank_state.py` and `scripts/audit_golf_cross_bank_private.py` now reproduce source-gated paired snapshots OFFLINE, plus eight synthetic false-provenance and no-pointer-leak tests at `tests/test_audit_golf_cross_bank_state.py`. Only operator-private *paired* raw files under a private folder can be read; output is fresh local `kind=local-private-cross-bank-golf-source-audit` v1, no raw bytes, no runtime pointers and explicit `same_game_frame_proven=false`, `same_boot_proven=false`, `power_verified=false`. No auto-uploader or Dolphin commands.

**Follow-on capture decision:** Stop the previously proposed MEM1-only B1/B2/B3 series, as live source-named golf objects are MEM2. If obtaining later checkpoints, export and preserve **both** native `Dump MRAM` and `Dump ExRAM` at each paused checkpoint (B1 delayed idle, B2 WASD-aim only, B3 after returning idle), verifying exact sizes and no overwrite for each. `DumpArray` in Felk source opens `wb`; without copying, second dump overwrites the first. No independent same-boot/scene/phase verification is inferred by parser; any mismatch -> stop.

### Private-only Windows paired B0 validation (no new game action)

~~~powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-Offline'
$private = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem1-checkpoints'
$branch = 'agent/research/offline-mem1-checkpoint-diff'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $work)) { git -C $repo worktree add --detach $work "origin/$branch" }
if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
py -m unittest discover -s "$work\tests" -p 'test_audit_golf_cross_bank_state.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Source gates failed' }
py "$work\scripts\audit_golf_cross_bank_private.py" --private-root $private --mem1 "$private\B0-MEM1.bin" --mem2 "$private\B0-MEM2.bin" --output "$private\B0-golf-source-audit.json"
if ($LASTEXITCODE -ne 0) { throw 'Private paired audit failed' }
~~~

**Agent handoff:** S002 should confirm RPGolMain +0 vtable-like `.data` reference and actual player-manager ownership with a private Rev1 DOL/source xref when available, then decode only source-verified ball/club members in MEM2. S000 should review any future bounded public report schema; S003 must abstain from training. No new first-level 28-child idle/aim probe; all prior batches already exhausted.