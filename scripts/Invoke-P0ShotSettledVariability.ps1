<#
.SYNOPSIS
  Offline ONLY: inspect the five unstable SETTLED words in the original V1 shot.
.DESCRIPTION
  Never launches Dolphin, executes another swing, changes game files or uploads
  raw RAM. The original shot's private capture and old sanitized result are
  read-only. New source-relative output is exclusive-created under ignored Data.
  GitHub auto-publisher does NOT support this study yet; issue handoff is separate.
#>
[CmdletBinding()]
param([switch]$TestsOnly)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo
$script = Join-Path $repo 'scripts\audit_p0_settled_variability_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'Missing reviewed offline settled-variability analyzer'
}

Write-Output 'P0_SETTLED_MODE=OFFLINE_PRIVATE_READ_ONLY'
py -m unittest discover -s tests -p 'test_p0_shot_transients_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Original synthetic controls failed; STOP' }
py -m unittest discover -s tests -p 'test_p0_settled_variability_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Settled-variability controls failed; STOP' }
if ($TestsOnly) {
    Write-Output 'P0_SETTLED_TESTS_ONLY=PASS'
    return
}

$private = Join-Path (Split-Path -Parent $repo) 'Wii-AI-Golf-Data\captures'
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    throw 'Expected local ignored private captures directory absent'
}
$run = 'outcome-20261028T033948Z-5cd47f00'
$summary = Join-Path $private ($run + '-candidates.json')
$raw = Join-Path $private ($run + '-RAW-PRIVATE.jsonl')
$prior = Join-Path $private ($run + '-POST-TRANSIENTS-SANITIZED.json')
$out = Join-Path $private ($run + '-SETTLED-VARIABILITY-SANITIZED.json')
foreach ($required in @($summary, $raw, $prior)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw 'Original local shot pair or prior sanitized report missing; STOP'
    }
}
if (Test-Path -LiteralPath $out) {
    throw 'Settled-variability output exists; preserve it, do not overwrite'
}

$priorReport = Get-Content -Raw -LiteralPath $prior | ConvertFrom-Json
if ($priorReport.kind -ne 'SANITIZED_P0_EXISTING_SHOT_POST_TRANSIENTS_V1' -or
    $priorReport.transient_unique_word_count -ne 0 -or
    $priorReport.persistent_unique_word_count_crosscheck -ne 8 -or
    $priorReport.unstable_SETTLED_absolute_word_count_excluded -ne 5 -or
    $priorReport.training_allowed -ne $false) {
    throw 'Prior operator-result evidence differs; STOP rather than assume same capture'
}

py -I $script --summary $summary --raw $raw --output $out
if ($LASTEXITCODE -ne 0) { throw 'Private settled-variability analysis refused' }

$report = Get-Content -Raw -LiteralPath $out | ConvertFrom-Json
if ($report.kind -ne 'SANITIZED_P0_EXISTING_SHOT_UNSTABLE_SETTLED_V1' -or
    $report.unstable_settled_unique_word_count -ne 5 -or
    $report.original_persistent_crosscheck -ne 8 -or
    $report.original_transients_crosscheck -ne 0 -or
    $report.training_allowed -ne $false -or
    $report.raw_word_values_present -ne $false -or
    $report.private_guest_addresses_present -ne $false) {
    throw 'Unexpected sanitized schema or counts; DO NOT PUBLISH'
}
Write-Output 'P0_SETTLED_VARIABILITY_SANITIZED_RESULT'
[pscustomobject]@{
    UnstableSettledWords = $report.unstable_settled_unique_word_count
    NonEffectCandidates = $report.non_effect_count
    EffectOnlyCandidates = $report.effect_only_count
    PersistentCrosscheck = $report.original_persistent_crosscheck
    PostOnlyTransients = $report.original_transients_crosscheck
    MaxNonAtomicFrameSpan = $report.max_snapshot_frame_span
    Truncated = $report.candidate_list_truncated
    TrainingApproved = $report.training_allowed
    AutoGitHubUpload = $report.automatic_github_publication
} | Format-List

$report.candidates | Select-Object -First 12 | ForEach-Object {
    $locations = @($_.source_relative_locations | ForEach-Object {
        "$($_.window):$($_.offset)"
    })
    [pscustomobject]@{
        ID = $_.candidate_id
        SourceOffsets = ($locations -join ', ')
        PostDiffFromPre = $_.post_samples_different_from_PRE
        SettledDiffFromPre = $_.settled_samples_different_from_PRE
        SettledDistinctPatterns = $_.settled_distinct_word_patterns
        LastSettledEqualsPre = $_.last_settled_equals_PRE
        EffectOnly = $_.effect_only_confound
        PointerShaped = $_.pointer_shaped_pattern
    }
} | Format-Table -AutoSize -Wrap

Write-Output 'RAW_RAM_NOT_UPLOADED; TRAINING_NOT_APPROVED'
Write-Output 'AUTO_GITHUB_UPLOAD=NOT_IMPLEMENTED_FOR_THIS_STUDY; SANITIZED_HANDOFF_TO_GITHUB_ISSUE_ONLY'
