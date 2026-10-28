<#
.SYNOPSIS
  Offline source-validated P0 comparison of the existing 11 human-contact-positive
  Hitting-the-Green captures, split by human green YES/NO/UNKNOWN.
.DESCRIPTION
  Reuses the S000 #205 cross-hit contrast and S002 #199 per-shot reader.
  This script does not implement a second scientific audit.
  No Dolphin, bridge, RAM writes, new capture, Internet upload or modification
  to another agent's worktree. Sanitized output stays in ignored private Data.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$S002ReaderWorktree,
    [switch]$TestsOnly
)

$ErrorActionPreference = 'Stop'
$studyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$workspace = Split-Path -Parent $studyRoot
$private = Join-Path $workspace 'Wii-AI-Golf-Data\captures'
$contrast = Join-Path $studyRoot 'scripts\contrast_p0_hit_signatures_private.py'
$reader = Join-Path $S002ReaderWorktree 'scripts\audit_p0_successful_shot_private.py'
$readerSha = '4f9deea39be8511f1b68907164623d98bdb2f3dc'
$baselineParent = 'b1b886c86803a3a7fb39c61d575ed5b3aa9b0a1a'

Set-Location -LiteralPath $studyRoot
if (-not (Test-Path -LiteralPath $contrast -PathType Leaf)) {
    throw 'Missing reviewed #205 source contrast; refuse competing analyzer'
}
git -C $studyRoot merge-base --is-ancestor $baselineParent HEAD
if ($LASTEXITCODE -ne 0) {
    throw 'Study does not contain the reviewed #205 base'
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $python) { throw 'No supported Python interpreter found' }
Write-Output 'P0_CROSSHIT_MODE=OFFLINE_PRIVATE_READ_ONLY'
Write-Output 'P0_CROSSHIT_TESTS=SOURCE_205_SYNTHETIC'
& $python.Source -m unittest discover -s tests -p 'test_p0_hit_signatures_private.py' -v
if ($LASTEXITCODE -ne 0) {
    throw 'S000 existing stratification tests failed, no private audit'
}
if ($TestsOnly) {
    Write-Output 'P0_CROSSHIT_TESTS_ONLY=PASS; no private pairs inspected'
    return
}

if (-not (Test-Path -LiteralPath $S002ReaderWorktree -PathType Container)) {
    throw 'Exact S002 #199 reader worktree missing'
}
$rootResolved = (Resolve-Path -LiteralPath $S002ReaderWorktree).Path
if ((Split-Path -Parent $rootResolved) -ne $workspace) {
    throw 'S002 reader worktree must be sibling to private Data root'
}
$observed = (git -C $rootResolved rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $observed -ne $readerSha) {
    throw 'S002 audited reader SHA differs from reviewed #199 commit'
}
$readerChanges = @(git -C $rootResolved status --porcelain)
if ($LASTEXITCODE -ne 0 -or $readerChanges.Count -ne 0) {
    throw 'S002 reader worktree dirty; preserve changes and STOP'
}
if (-not (Test-Path -LiteralPath $reader -PathType Leaf)) {
    throw 'Missing exact S002 source auditor'
}
if (-not (Test-Path -LiteralPath $private -PathType Container)) {
    throw 'Private captures absent from ignored sibling Data directory'
}

# The existing #205 analyzer invokes existing #199.audit for EVERY pair.
# Its stdout is sanitized JSON: no per-shot names or private memory values.
$jsonLines = @(& $python.Source -I $contrast --captures $private --s002-reader $reader --top 200)
if ($LASTEXITCODE -ne 0) {
    throw 'Source-validated 11-pair private contrast refused'
}
$json = ($jsonLines -join [Environment]::NewLine)
try {
    $result = $json | ConvertFrom-Json
} catch {
    throw 'Unexpected sanitized JSON output; do not print or upload raw data'
}
if ($result.kind -ne 'PRIVATE-validated-crosshit-outcome-stratification' -or
    $result.validated_human_contact_captures -ne 11 -or
    ($result.human_labeled_green_yes + $result.human_labeled_green_no +
     $result.human_green_unknown) -ne 11 -or
    $result.model_training_allowed -ne $false -or
    $result.true_ball_xyz_verified -ne $false -or
    $result.independent_no_contact_control_checked -ne $false -or
    $result.guest_frame_atomicity_verified -ne $false -or
    $result.total_signatures_omitted_from_stdout -ne 0 -or
    $result.signature_recurrence.Count -ne $result.distinct_alias_signatures) {
    throw 'Unexpected incomplete/unsafe cohort result, refuse to save'
}
$allCounts = @($result.candidate_count_by_outcome.yes) +
             @($result.candidate_count_by_outcome.no) +
             @($result.candidate_count_by_outcome.unknown)
$expectedCounts = @(8, 9, 13, 13, 13, 13, 19, 45, 45, 45, 45)
if (($allCounts | Sort-Object) -join ',' -ne
    ($expectedCounts | Sort-Object) -join ',') {
    throw 'Original 11 positive-hit candidate counts changed; refuse comparison'
}
foreach ($entry in $result.signature_recurrence) {
    if ($entry.training_eligible -ne $false -or
        $entry.present_in_total -ne ($entry.present_in_green_yes +
              $entry.present_in_green_no + $entry.present_in_green_unknown)) {
        throw 'Unsafe alias signature or count mismatch'
    }
}

# Idempotent, sanitized-only local output; no overwrites.
$out = Join-Path $private 'p0-human-green-outcome-11hit-contrast-SANITIZED.json'
if (Test-Path -LiteralPath $out) {
    $previous = Get-Content -LiteralPath $out -Raw
    try {
        $old = $previous | ConvertFrom-Json
    } catch {
        throw 'Existing sanitized result malformed; preserve it and STOP'
    }
    if (($old | ConvertTo-Json -Depth 30 -Compress) -ne
        ($result | ConvertTo-Json -Depth 30 -Compress)) {
        throw 'Existing result is different; preserve it and STOP'
    }
    Write-Output 'P0_CROSSHIT_EXISTING_SANITIZED_REPORT_VERIFIED'
} else {
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes(
        $json + [Environment]::NewLine
    )
    $stream = [System.IO.File]::Open(
        $out, [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write, [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
    } finally {
        $stream.Dispose()
    }
    Write-Output 'P0_CROSSHIT_SANITIZED_REPORT_WRITTEN_PRIVATE'
}

Write-Output 'P0_CROSSHIT_SANITIZED_SUMMARY'
[pscustomobject]@{
    ValidatedContactPositivePairs = $result.validated_human_contact_captures
    HumanGreenYES = $result.human_labeled_green_yes
    HumanGreenNO = $result.human_labeled_green_no
    HumanGreenUNKNOWN = $result.human_green_unknown
    DistinctSourceAliasSignatures = $result.distinct_alias_signatures
    OneGreenPositiveInsufficient = $result.single_green_positive_insufficient_for_specificity
    NoHitControlsChecked = $result.independent_no_contact_control_checked
    FrameAtomic = $result.guest_frame_atomicity_verified
    VerifiedBallXYZ = $result.true_ball_xyz_verified
    TrainingApproved = $result.model_training_allowed
} | Format-List

@($result.signature_recurrence) |
    Select-Object -First 30 |
    ForEach-Object {
        [pscustomobject]@{
            SourceRelativeAlias = $_.source_relative_alias_signature
            GreenYES = $_.present_in_green_yes
            GreenNO = $_.present_in_green_no
            GreenUNKNOWN = $_.present_in_green_unknown
            Total = $_.present_in_total
            PointerShapedRuns = $_.pointer_shaped_run_count
            VisualOnly = $_.rendering_only_classified
            TrainingApproved = $_.training_eligible
        }
    } | Format-Table -Wrap -AutoSize
Write-Output 'PRIVATE_RAW_RETAINED_LOCAL; GITHUB_OBSERVATION=NOT_UPLOADED'
Write-Output 'P0_CROSSHIT_CONTRAST_COMPLETED; REQUEST_S000_S002_OWNER_REVIEW'
