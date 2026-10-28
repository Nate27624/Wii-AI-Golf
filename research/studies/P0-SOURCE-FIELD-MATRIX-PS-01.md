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
