<#
.SYNOPSIS
  Verify existing human-hit golf_field+0x9C effect pointer and tail overlap.
.DESCRIPTION
  PRIVATE offline. No Dolphin, no game launch, no controller changes, no RAM
  access beyond the EXISTING ignored 8 original bounded snapshots.
  Reports only source-relative offsets / coverage counts.
  Not proof of allocated object size, ball XYZ, velocity, power, or training.
#>
[CmdletBinding()]
param([switch]$TestsOnly)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo

foreach ($script in @(
    'scripts\audit_p0_shot_transients_private.py',
    'scripts\audit_p0_settled_variability_private.py',
    'scripts\audit_p0_effect_tail_ownership_private.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo $script) -PathType Leaf)) {
        throw 'Reviewed parent or tail analyzer missing; STOP'
    }
}

Write-Output 'P0_EFFECT_TAIL_MODE=OFFLINE_READ_ONLY'
foreach ($test in @(
    'test_p0_shot_transients_private.py',
    'test_p0_settled_variability_private.py',
    'test_p0_effect_tail_ownership_private.py'
)) {
    py -m unittest discover -s tests -p $test -v
    if ($LASTEXITCODE -ne 0) {
        throw 'Source or privacy controls failed; no private analysis'
    }
}
if ($TestsOnly) {
    Write-Output 'P0_EFFECT_TAIL_TESTS_ONLY=PASS'
    return
}

$private = Join-Path (Split-Path -Parent $repo) 'Wii-AI-Golf-Data\captures'
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    throw 'Private captures directory absent; do not copy into Git'
}
$run = 'outcome-20261028T033948Z-5cd47f00'
$summary = Join-Path $private ($run + '-candidates.json')
$raw = Join-Path $private ($run + '-RAW-PRIVATE.jsonl')
$prior = Join-Path $private ($run + '-POST-TRANSIENTS-SANITIZED.json')
$settled = Join-Path $private ($run + '-SETTLED-VARIABILITY-SANITIZED.json')
$output = Join-Path $private ($run + '-EFFECT-TAIL-OWNERSHIP-SANITIZED.json')
foreach ($required in @($summary, $raw, $prior, $settled)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw 'Missing exact original private shot evidence or audited report; STOP'
    }
}

$p = Get-Content -LiteralPath $prior -Raw | ConvertFrom-Json
$s = Get-Content -LiteralPath $settled -Raw | ConvertFrom-Json
if ($p.kind -ne 'SANITIZED_P0_EXISTING_SHOT_POST_TRANSIENTS_V1' -or
    $p.transient_unique_word_count -ne 0 -or
    $p.persistent_unique_word_count_crosscheck -ne 8 -or
    $p.unstable_SETTLED_absolute_word_count_excluded -ne 5 -or
    $p.training_allowed -ne $false -or
    $s.kind -ne 'SANITIZED_P0_EXISTING_SHOT_UNSTABLE_SETTLED_V1' -or
    $s.unstable_settled_unique_word_count -ne 5 -or
    $s.non_effect_count -ne 0 -or
    $s.effect_only_count -ne 5 -or
    $s.training_allowed -ne $false) {
    throw 'Previous operator 0/8/5 and five-effect-tail baseline mismatch; STOP'
}

$script = Join-Path $repo 'scripts\audit_p0_effect_tail_ownership_private.py'
py -I $script --summary $summary --raw $raw --output $output
if ($LASTEXITCODE -ne 0) {
    throw 'Pointer/stride/overlap audit refused. No output uploaded'
}
$report = Get-Content -LiteralPath $output -Raw | ConvertFrom-Json
if ($report.kind -ne 'SANITIZED_P0_EFFECT_POINTER_TAIL_OWNERSHIP_V1' -or
    $report.pointer_word_matches_window_start_in_all_samples -ne $true -or
    $report.actual_unstable_settled_words_crosscheck -ne 5 -or
    $report.actual_post_restored_transients_crosscheck -ne 0 -or
    $report.actual_persistent_words_crosscheck -ne 8 -or
    $report.training_allowed -ne $false -or
    $report.private_guest_addresses_present -ne $false -or
    $report.raw_word_values_present -ne $false) {
    throw 'Unexpected report identity or safety flags; DO NOT PUBLISH'
}

Write-Output 'P0_EFFECT_TAIL_SANITIZED_RESULT'
[pscustomobject]@{
    SourcePointerMatchesAllEight = $report.pointer_word_matches_window_start_in_all_samples
    PointerStartsFixed = $report.pointer_bases_fixed_across_all_samples
    ObservedPointerSpacingBytes = $report.effect_pointer_start_spacing_bytes
    ExploratoryWindowReadBytes = $report.collector_per_window_read_bytes
    TailWindowCoverageOnlyOne = $report.last_five_only_observed_in_ball_named_window
    HypotheticalStrideIndex = $report.tail_corresponds_to_hypothetical_stride_index
    TailWithinStride = ($report.tail_relative_positions_in_hypothetical_stride -join ', ')
    NonAtomicFrameSpanMax = $report.max_nonatomic_frame_span
    SourceAllocationSizeVerified = $report.effect_allocation_ownership_verified
    TrainingApproved = $report.training_allowed
    AutoGitHubUpload = $report.automatic_github_publication
} | Format-List

$report.six_hypothetical_slot_profiles | ForEach-Object {
    [pscustomobject]@{
        StrideIndex = $_.arithmetic_stride_index
        CoveredByOneWindow = $_.word_coverage_by_number_of_source_windows.one_window
        CoveredByTwoWindows = $_.word_coverage_by_number_of_source_windows.two_windows
        CoveredByThreeWindows = $_.word_coverage_by_number_of_source_windows.three_windows
        UnstableSettledWords = $_.words_with_unstable_SETTLED
        WordsChangedDuringPOST = $_.words_with_any_POST_difference_from_stable_PRE
    }
} | Format-Table -AutoSize

Write-Output 'INTERPRETATION=SOURCE_WINDOW_OVERLAP_ONLY; NOT_PROVEN_EFFECT_OBJECT_OR_BALL_PHYSICS'
Write-Output 'RAW_PRIVATE_RETAINED_LOCAL; AUTO_GITHUB_UPLOAD=NOT_IMPLEMENTED; SANITIZED_GITHUB_FINDING_AFTER_REVIEW'
