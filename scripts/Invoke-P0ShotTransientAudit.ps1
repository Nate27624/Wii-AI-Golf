<#
.SYNOPSIS
  P0 existing successful-shot POST-only memory candidate triage (OFFLINE ONLY).
.DESCRIPTION
  Reuses already captured 3 PRE / 2 POST / 3 SETTLED private windows.
  Runs synthetic controls then a read-only source audit, writing ONLY
  source-relative, bounded SANITIZED candidate flags to ignored Data.
  NEVER launches Dolphin, reads live guest memory, changes the swing,
  uploads raw RAM/JSON, or declares P0 variables training-approved.
  The existing research CLI does NOT yet support this study's publisher
  schema; no automatic public GitHub publication is claimed.
#>
[CmdletBinding()]
param(
    [switch]$TestsOnly
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo
$script = Join-Path $repo 'scripts\audit_p0_shot_transients_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'P0 transient analyzer absent from checked-out study branch'
}

# Do not trust the current working directory, old Felk or retired GUI.
Write-Output 'P0_TRANSIENT_MODE=OFFLINE_READ_ONLY'
Write-Output 'P0_TRANSIENT_TESTING=synthetic_before_private'
py -m unittest discover -s tests -p 'test_p0_shot_transients_private.py' -v
if ($LASTEXITCODE -ne 0) {
    throw 'P0 transient synthetic controls failed; private analysis refused'
}
if ($TestsOnly) {
    Write-Output 'P0_TRANSIENT_TESTS_ONLY=PASS; no private captures inspected'
    return
}

$private = Join-Path (Split-Path -Path $repo -Parent) 'Wii-AI-Golf-Data\captures'
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    throw 'Ignored private captures directory absent; do not relocate source into Git'
}
$run = 'outcome-20261028T033948Z-5cd47f00'
$summary = Join-Path $private ($run + '-candidates.json')
$raw = Join-Path $private ($run + '-RAW-PRIVATE.jsonl')
$out = Join-Path $private ($run + '-POST-TRANSIENTS-SANITIZED.json')
foreach ($required in @($summary, $raw)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw 'Expected paired human-positive capture unavailable; no source guesses permitted'
    }
}
if (Test-Path -LiteralPath $out) {
    throw 'Private sanitized result already exists; refuse overwrite or stale-success claim'
}
# All private-path, capture-shape, alias and cross-ranking gates are rechecked by Python.
py -I $script --summary $summary --raw $raw --output $out
if ($LASTEXITCODE -ne 0) {
    throw 'P0 transient analyzer refused; keep raw evidence local and report the failure'
}
$report = Get-Content -LiteralPath $out -Raw | ConvertFrom-Json
if ($report.kind -ne 'SANITIZED_P0_EXISTING_SHOT_POST_TRANSIENTS_V1' -or
    $report.training_allowed -ne $false -or
    $report.raw_word_values_present -ne $false) {
    throw 'Unexpected output schema, refuse to display'
}
Write-Output 'P0_TRANSIENT_SANITIZED_RESULT'
[pscustomobject]@{
    TransientUniqueWords = $report.transient_unique_word_count
    PersistentCrosscheck = $report.persistent_unique_word_count_crosscheck
    UnstablePreExcluded = $report.unstable_PRE_absolute_word_count_excluded
    UnstableSettledExcluded = $report.unstable_SETTLED_absolute_word_count_excluded
    SinglePostOnly = $report.post_changed_in_only_subset_count
    MaxNonAtomicFrameSpan = $report.max_snapshot_frame_span
    CandidateListTruncated = $report.candidate_list_truncated
    TrainingApproved = $report.training_allowed
    AutoGitHubUpload = $report.automatic_github_publication
} | Format-List
# Output source-relative labels only; no raw RAM / dynamic pointer / word values.
$report.candidates | Select-Object -First 12 | ForEach-Object {
    $names = @($_.source_relative_locations | ForEach-Object {
        "$($_.window):$($_.offset)"
    })
    [pscustomobject]@{
        Candidate = $_.candidate_id
        SourceOffsets = ($names -join ', ')
        PostChanged = "$($_.post_differing_count)/$($_.post_sample_count)"
        EffectOnly = $_.visual_effect_only
        PointerShaped = $_.pointer_shaped_confound
        TrainingApproved = $_.training_eligible
    }
} | Format-Table -AutoSize
Write-Output 'PUBLIC_EVIDENCE=SANITIZED_ONLY; RAW_PRIVATE_RETAINED_LOCAL'
Write-Output 'AUTO_GITHUB_UPLOAD=NOT_IMPLEMENTED_FOR_THIS_UNMERGED_STUDY; DO_NOT_UPLOAD_RAW'
