#requires -Version 5.1
<#
Offline private B0 P0 source-store candidate audit.
Run only in a detached, SHA-pinned PR #244 worktree. Does not start Dolphin,
send controls, upload anything, or print native memory words/paths/hashes.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory = $true)][string]$DataRoot
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$probe = Join-Path $repo 'scripts\audit_p0_player_record_store_candidates_private.py'
$session = Join-Path $DataRoot 'ball-study-20261027-212633'
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) {
    throw 'ABSTAIN: reviewed audit script missing'
}
if (-not (Test-Path -LiteralPath $session -PathType Container)) {
    throw 'ABSTAIN: original private B0 checkpoint absent; do not fabricate or recapture'
}
if (-not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) {
    throw 'ABSTAIN: original B0 manifest absent'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'ABSTAIN: Python executable unavailable'
}
$head = (& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: worktree commit mismatch; do not run a moving PR head'
}
Write-Host '=== SOURCE-PINNED P0 PLAYER-RECORD STORE AUDIT ==='
Write-Host 'Running fabricated synthetic tests (no Dolphin/native RAM)'
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_player_record_store_candidates_private.py' -v
if ($LASTEXITCODE -ne 0) {
    throw 'ABSTAIN: synthetic tests failed'
}
Write-Host '=== READ ORIGINAL B0 ONLY; NO SHOT / NO UPLOAD ==='
$lines = & python -B $probe --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $lines) {
    throw 'ABSTAIN: SHA, revision, private manifest or source gate failed'
}
try {
    $r = ($lines -join [Environment]::NewLine) | ConvertFrom-Json
} catch {
    throw 'ABSTAIN: sanitized parser output is invalid JSON'
}
if ($r.kind -ne 'S002-P0-REV1-PLAYER-RECORD-STORE-CANDIDATES' -or
    $r.native_source_b0_sha256_verified_before_and_after_read -ne $true -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false -or
    $r.runtime_store_execution_verified -ne $false -or
    $r.record_word_changes_source_attributed -ne $false) {
    throw 'ABSTAIN: source/report safety invariant failed'
}
Write-Host 'P0_PRIVATE_B0_SOURCE_SHA_PASS'
Write-Host 'P0_PLAYER_RECORD_STORES_SOURCE_ONLY_NOT_PHYSICS'
foreach ($entry in $r.candidates) {
    $offset = [string]$entry.record_relative_displacement_candidate
    $count = [int]$entry.dform_store_count
    $word = [int]$entry.word_width_store_count
    Write-Host ("FIELD_CANDIDATE={0} DFORM_SITES={1} FOUR_BYTE_SITES={2}" -f $offset,$count,$word)
    foreach ($site in $entry.candidate_sites) {
        $h = $site.local_base_definition_hint
        Write-Host ("  {0} {1} {2}({3}) ORIGIN={4} DEF={5}" -f
            $site.source_unit, $site.source_relative_instruction,
            $site.opcode, $site.base_register, $h.origin_class,
            $h.source_relative_definition)
    }
    if ($entry.additional_sites_omitted -gt 0) {
        Write-Host ("  ADDITIONAL_SITES_OMITTED={0}" -f $entry.additional_sites_omitted)
    }
}
Write-Host 'BASE_REGISTER_IS_SELECTED_RECORD_VERIFIED=False'
Write-Host 'RUNTIME_EXECUTION_VERIFIED=False'
Write-Host 'POWER_VELOCITY_XYZ_TRAINING_VERIFIED=False'
Write-Host 'P0_PLAYER_STORE_PRIVATE_STUDY_COMPLETED'
