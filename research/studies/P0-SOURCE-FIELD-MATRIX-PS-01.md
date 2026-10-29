# P0 Source Field Matrix — Windows PowerShell B0–B3

Study: S002 support / P0-SOURCE-FIELD-MATRIX-PS-01. Status: DRAFT, offline only, no observed game launch, no training authorization. Owner reviews: S002 source/RAM and S000 privacy and memory registry. This contribution adds NEW files only.

## Purpose and coverage

The source-field matrix reuses existing source-linked memory hypotheses from #160/#163/#178 and the memory-variable catalog PR #205. It independently rechecks a selection of source/runtime structure gates and compares preserved B0–B3 private native 24 MiB MEM1 and 64 MiB MEM2 snapshots. Its Windows PowerShell 5.1+ script is at scripts/Invoke-P0SourceFieldMatrix.ps1.

The script checks private manifest kind/version/phase labels/pause flags, exact native bank lengths and SHA-256, RSPE01 US Rev 1 header, Golf scene5/sport2/mode4, selected PlayerManager inline 0xCC record, selected ball child at record +0x88, child +0x4C pointer to translation, start/ball source self-reference checks, and stable owner/slot/hole across all four images.

| Registry field ID or pending proposal | Source-relative locator | Components |
| --- | --- | --- |
| golf.player.selected_record.initial_position_candidate | selected record +0x54 | 3 |
| golf.player.selected_record.start_copy_candidate | selected record +0x60 | 3 |
| golf.ball_object.current_translation_candidate | selected record +0x88 -> child +0x4C -> pointer | 3 |
| golf.ball_object.initialized_cache_cc | ball object +0xCC | 3 |
| golf.ball_object.conditional_cache_f0 | ball object +0xF0 | 3 |
| golf.ball_object.conditional_cache_fc | ball object +0xFC | 3 |
| golf.player.selected_record.aim_rotation | selected record +0x3C | 1 |
| golf.player.selected_record.aim_transform_matrix_candidate | selected record +0x40 | 4 |
| golf.tee_start.map_translation_xyz | current start -> +0x30 | 3 |
| golf.pin.map_translation_xyz | pin -> +0x30 | 3 |
| golf.cup.map_translation_xyz | cup +0x30 (hypothetical inherited base) | 3 |

The aim_transform_matrix_candidate field is a proposed crosswalk, **not yet a registry ID** in #205. The user should share only sanitized per-transition changed-component counts, fixed geometry stability, and failure flags. The script never prints native words, heap addresses, vectors, hashes, filenames or local private paths.

## Scientific limitations

The script does not re-run the S002 PPC opcode/register-flow proof from #160, identify the true physical ball, infer velocity from candidate vector changes, verify contact, or establish same-frame MEM1/MEM2. It is NOT a replacement for #163's source-selected specialized analyzer. B0/B1/B2/B3 are operator-entered phase labels, not independently verified flight/settled timing. The user is confident at least one separate JSON-associated capture had a not-completely-stationary ball, but its exact B0–B3 linkage and downward velocity are unknown. Never relabel a B phase as observed ball flight based on changed words.

The eight real successful-shot changed words from #197/#199 are separate minimap effect-handle lifecycle candidates. They are not sampled as the physical ball by this matrix, and the two private cohorts cannot be joined without shot/frame provenance. All emitted reports explicitly set ball XYZ, velocity, contact, frame join and training to FALSE. The code has no controller/Dolphin/RPC/GUI logic and no upload pathway. Report prints NOT_UPLOADED until the S000/S002 publisher allowlist is reviewed.

## Single Windows PowerShell run (unmerged isolated research branch)

The operator can copy this full block after S000/S002 source review. It fetches only the exact branch code, uses an isolated SHA-addressed worktree, executes synthetic tests then inspects the already existing B0–B3 private RAM read-only. It does not reset branches, alter ROM, launch Dolphin or play a shot.

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
    Set-Location -LiteralPath $repo
    $branch = 'agent/research/p0-powershell-source-field-matrix-20261028'
    $data = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data'
    $private = Join-Path $data 'ball-study-20261027-212633'
    if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) { throw 'Original B0-B3 checkpoint missing' }
    git fetch origin "refs/heads/agent/research/p0-powershell-source-field-matrix-20261028:refs/remotes/origin/agent/research/p0-powershell-source-field-matrix-20261028"
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    $sha = (git rev-parse "origin/$branch").Trim()
    if ($LASTEXITCODE -ne 0 -or $sha -notmatch '^[0-9a-f]{40}$') { throw 'Bad source revision' }
    $work = Join-Path 'D:\Projects\Wii Golf AI' "Wii-AI-Golf-P0-PS-Fields-$($sha.Substring(0,8))"
    if (Test-Path -LiteralPath $work) {
        $old = (git -C $work rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $old -ne $sha) { throw 'Existing worktree SHA mismatch; refusing overwrite' }
    } else {
        git worktree add --detach $work "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Worktree create failed' }
    }
    py -m unittest discover -s "$work\tests" -p 'test_p0_source_field_matrix.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic tests failed; stop' }
    & "$work\scripts\Invoke-P0SourceFieldMatrix.ps1" -PrivateRoot $private -DataRoot $data
    if ($LASTEXITCODE -ne 0) { throw 'Private matrix refused input; stop' }
}
~~~

Return only the short sanitized JSON terminal output, never raw memory, manifest, local paths, or unredacted logs.

## Tests and merge gate

A dedicated Windows GitHub Actions job executes native-size sparse SYNTHETIC positive fixtures and negative corrupt-SHA/wrong-scene fixtures. A Linux job runs source/static no-live contract checks (PowerShell-dependent cases skip if unavailable). These do not constitute tests against the user's native B0–B3 session; S002 and S000 review plus full Windows repository tests are required prior to merge. Do not initiate a new V1 or V2 swing merely for this study.


## 2026-10-28 actual operator B0–B3 evidence (initial 11-field version)

Operator executed EXACT SHA 65fb249233d40f0f77bc8c7f2e49d54814fa9ba4 on Windows. **Six synthetic tests passed and REAL preserved full-bank audit completed**. Hash, selected slot/hole and geometry stability all true; both banks differed in all three transitions; B0→B1 and B2→B3: zero changed word-components across all 11 fields. B1→B2: aim angle candidate +0x3C changed 1/1, four aim matrix words +0x40…0x4C changed 4/4; all other nine fields 0. This confirms an AIM-ONLY within-study correlation, not actual shot/ball motion or training data. Recorded in PR #213 / #205 / issue #121.

## Extended source-defined context/score and rendering-negative controls (PENDING real run)

This same existing script now includes **12 additional registry proposals**, with source-derived US Rev1 layout. These are direct in-struct member offsets after independently locating and gating the existing source-static manager pointer. **No new static addresses or heap pointers are published**. The 36 entries of the score table are a distinct array, not 36 independent sampled shots.

| Proposed registry ID | Exact relative memory expression | Source datatype | Semantic limitation |
| --- | --- | --- | --- |
| golf.config.mode_id | BE_u32(BE_ptr(0x804BF8C4)+0x94) | u32 | Source enum; existing 4-mode gate, not a recorded shot |
| golf.config.current_hole_index | BE_u32(BE_ptr(0x804BF8C4)+0x98) | u32 | Source's current-hole index; not independently verified by displayed hole |
| golf.config.player_scores_4x9_candidate | BE_u32[36](BE_ptr(0x804BF8C4)+0x04) | 4×9 u32 | Score table; NOT verified strokes, scoring delta, or landing label |
| golf.field.target_object_count | BE_u32(BE_ptr(0x804BF868)+0x30) | u32 | Target collection count |
| golf.field.pin_object_count | BE_u32(BE_ptr(0x804BF868)+0x3C) | u32 | Map pin objects |
| golf.field.player_start_object_count | BE_u32(BE_ptr(0x804BF868)+0x48) | u32 | Map start objects |
| golf.field.tree_shadow_update_timer | BE_u32(BE_ptr(0x804BF868)+0x10) | i32 bits | Camera/render timing, useful false-positive negative |
| golf.field.wind_object_pointer_present | bool(BE_ptr(BE_ptr(0x804BF868)+0x68) != null) | pointer-presence boolean | NOT wind direction/speed |
| golf.field.wind_arrow_visible | byte(BE_ptr(0x804BF868)+0x6C) | C++ bool u8 | Display only; NOT wind speed |
| golf.field.green_slope_visible | byte(BE_ptr(0x804BF868)+0x7C) | C++ bool u8 | Display only |
| golf.field.minimap_visible | byte(BE_ptr(0x804BF868)+0x88) | C++ bool u8 | UI false-positive control |
| golf.field.target_emitter_kill_flag | byte(BE_ptr(0x804BF868)+0xA4) | C++ bool u8 | Visual-effect lifecycle; NOT contact |

Source: [RPGolConfig.h](https://github.com/kiwi515/ogws_info/blob/master/RP/RPSports/RPGolScene/RPGolConfig.h) and [RPGolFieldManager.h](https://github.com/kiwi515/ogws_info/blob/master/RP/RPSports/RPGolScene/RPGolFieldManager.h) (Wii Sports RSPE01 US revision 1 scope). The upstream canonical registry PR #205 still owns semantics, stable IDs and training gates. These proposed keys must not be treated as accepted schema until S000 review. The source declares RPGolConfig::GetWind but its implementation fields for actual speed/direction are NOT mapped here; an mWindObj pointer is only an object-presence marker.

The extended mapper checks 1-byte bool fields as bytes (0 or 1), preserves u32/i32 bit patterns for difference counts (no casting scores to float), refuses unmapped non-null wind-object pointers, and reports only word-component difference counts. It NEVER prints the 36 score values, underlying pointer words, UI status values or unverified ball/score data. Source-relative locations are verified by public headers; actual-score semantics and shot labels require controlled observed before/after shot provenance. No operator action until synthetic Windows CI has passed the extended branch.

## 2026-10-28 real Windows operator run — expanded 23-field audit

Evidence type: actual OFFLINE operator-owned native RAM B0–B3 comparison, NOT a positive hit or independently frame-verified ball flight. Operator checked out exact detached source head 26ecccad528a5b8d29a22527c607a866ff97331b; locally executed 7 synthetic tests, all PASS, then executed source-field analyzer against the actual preserved private B0–B3. Report hash_checks_passed=true, selected_slot_hole_stable=true, new_field_count=12, training_approved=false. No raw RAM or private paths public.

| New proposed source-relative field | Components | B0→B1 / B1→B2 / B2→B3 |
| --- | ---: | --- |
| golf.config.mode_id | 1 | 0 / 0 / 0 |
| golf.config.current_hole_index | 1 | 0 / 0 / 0 |
| golf.config.player_scores_4x9_candidate | 36 | 0 / 0 / 0 |
| golf.field.target_object_count | 1 | 0 / 0 / 0 |
| golf.field.pin_object_count | 1 | 0 / 0 / 0 |
| golf.field.player_start_object_count | 1 | 0 / 0 / 0 |
| golf.field.tree_shadow_update_timer | 1 | 0 / 0 / 0 |
| golf.field.wind_object_pointer_present | 1 | 0 / 0 / 0 |
| golf.field.wind_arrow_visible | 1 | 0 / 0 / 0 |
| golf.field.green_slope_visible | 1 | 0 / 0 / 0 |
| golf.field.minimap_visible | 1 | 0 / 0 / 0 |
| golf.field.target_emitter_kill_flag | 1 | 0 / 0 / 0 |

Across ALL 23 logical mapped fields on this same no-shot/aim B0–B3 cohort, only the aim scalar selected player record +0x3C (1 changed word at B1→B2) and its 2×2 aim transform +0x40..+0x4C (4 changed words at B1→B2) vary. The remaining 21 fields stay bitwise equal across all three transition pairs. A source-derived field and unchanged score table are NOT proof of a validated per-shot score label or ball physics. The source ball-related translation may be an initialization/tee copy. The user's separate potentially nonstationary ball capture is not linked to B0–B3; real ball XYZ, velocity, power, contact-frame alignment and all training permissions remain unresolved/false.

Next: S000 memory-variable registry PR #205 owner reviews 12 proposed IDs as source-backed context or negative controls; no overlapping registry files edited here. S002 PR #217 explores historical ball position addresses for US v1.00 versus operator Rev1 (version mismatch; no semantics promoted). S002 PRs #216/#209 investigate the five effect-window tail words from the distinct human-confirmed positive-hit capture. No new broad B0–B3 scan or new swing is warranted from this audit. Native RAM remains private; standalone report NOT automatically uploaded.
