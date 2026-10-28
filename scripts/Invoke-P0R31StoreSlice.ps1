#requires -Version 5.1
<#
PR #244 narrow source-only r31 provenance, exact reviewed commit pinned by caller.
Reads existing SHA-verified private B0; no Dolphin, writes, uploads, or shots.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$session = Join-Path $DataRoot 'ball-study-20261027-212633'
$script = Join-Path $PSScriptRoot 'audit_p0_r31_store_slice_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) {
    throw 'ABSTAIN: reviewed script or original B0 manifest missing'
}
$head = (& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: exact pinned source revision mismatch'
}
Write-Host '=== SOURCE-PINNED P0 R31 STORE SLICE ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_r31_store_slice_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: fabricated source tests failed' }
$lines = & python -B $script --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $lines) {
    throw 'ABSTAIN: private source verification or instruction gate failed'
}
try { $r = ($lines -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: invalid sanitized study JSON' }
if ($r.kind -ne 'S002-P0-REV1-R31-STORE-SOURCE-SLICE' -or
    $r.original_B0_SHA256_verified_before_and_after_slice -ne $true -or
    $r.source_relative_store_site -ne '+0x1C18' -or
    $r.store_base_reg -ne 'r31' -or
    $r.record_90_actual_writer_verified -ne $false -or
    $r.r31_is_selected_player_record_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: study invariants or training guard failed'
}
Write-Host 'P0_R31_ORIGINAL_B0_SHA_PASS'
Write-Host ("STORE_SITE=RPGolPlayer {0} OP={1} SOURCE={2} BASE={3}" -f
    $r.source_relative_store_site, $r.store_op, $r.store_float_reg,
    $r.store_base_reg)
Write-Host ("SOURCE_INSTRUCTIONS_EXAMINED={0}" -f $r.instructions_examined)
Write-Host ("CONTROL_FLOW_HAZARDS={0}" -f $r.control_flow_hazard_count)
Write-Host ("R31_DEFINITION_OR_TOUCH_CANDIDATES={0}" -f $r.r31_assignment_or_touch_candidate_count)
foreach ($event in $r.event_sites_nearest_first) {
    Write-Host ("  {0} CLASS={1} FROM={2}" -f
        $event.source_relative_offset, $event.class, $event.from_register)
}
if ($r.additional_event_sites_omitted -gt 0) {
    Write-Host ("ADDITIONAL_EVENTS_OMITTED={0}" -f $r.additional_event_sites_omitted)
}
Write-Host 'R31_IS_SELECTED_PLAYER_RECORD_VERIFIED=False'
Write-Host 'RECORD_90_WRITER_EXECUTED_VERIFIED=False'
Write-Host 'TRAINING_APPROVED=False'
Write-Host 'P0_R31_SOURCE_SLICE_COMPLETED'
