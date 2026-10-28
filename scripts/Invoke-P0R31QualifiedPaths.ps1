#requires -Version 5.1
<#
Offline B0 SHA-pinned PPC local r31 paths. Does not start Dolphin, inject
controls, read other captures or disclose native instruction/data words.
The EABI-preservation scenario is a HYPOTHESIS, not runtime proof.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference = 'Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sha=(& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: source checkout differs from reviewed exact SHA'
}
$session=Join-Path $DataRoot 'ball-study-20261027-212633'
$module=Join-Path $PSScriptRoot 'audit_p0_r31_qualified_local_paths_private.py'
if (-not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf)) {
    throw 'ABSTAIN: original private B0 source or reviewed analyzer missing'
}
Write-Host '=== P0 QUALIFIED R31 PATHS: FABRICATED REGRESSIONS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_r31_qualified_local_paths_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic tests failed' }
Write-Host '=== ORIGINAL B0 VERIFIED PPC SOURCE ==='
$json=& python -B $module --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $json) {
    throw 'ABSTAIN: original private B0 / opcode site provenance failed'
}
try { $r=($json -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: malformed sanitized source result' }
if ($r.kind -ne 'S002-P0-PLAYER-R31-QUALIFIED-LOCAL-PATHS' -or
    $r.source_exact_copy_store_verified -ne $true -or
    $r.original_private_B0_SHA_verified_before_after -ne $true -or
    $r.EABI_callee_assumption_verified_by_this_source_study -ne $false -or
    $r.all_external_predecessors_to_store_excluded -ne $false -or
    $r.runtime_r3_is_selected_player_record_verified -ne $false -or
    $r.runtime_r31_store_executes_during_wedge_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: source/claim/training invariants violated'
}
Write-Host 'P0_ORIGINAL_B0_SOURCE_SHA=PASS'
Write-Host ("STORE_SOURCE={0} AFTER_COPY_SOURCE={1}" -f $r.store_source_site,$r.copy_source_site)
foreach ($name in @('no_callee_preservation_assumed', 'all_linked_calls_assumed_EABI_r31_preserved')) {
    $p=$r.$name
    Write-Host ("MODEL={0} REACH_STORE={1} R31_COPY_INTACT_POSSIBLE={2} R31_UNKNOWN_POSSIBLE={3} R31_DIRECT_CLOBBER_POSSIBLE={4}" -f
        $name,$p.store_path_exists,$p.store_path_with_copy_still_intact_possible,
        $p.store_path_with_unknown_r31_possible,$p.store_path_with_postcopy_r31_write_possible)
    foreach($why in $p.incomplete_reasons) {
        Write-Host ("  {0}: {1}" -f $name,$why)
    }
}
foreach($site in $r.known_source_instruction_classes) {
    Write-Host ("SOURCE_SITE={0} OPCODE_CLASS={1} R31_WRITE={2} UNKNOWN={3}" -f
        $site.source_site,$site.opcode_family,$site.direct_r31_write,$site.unknown_r31_effect)
}
Write-Host 'FULL_CFG_AND_SELECTED_PLAYER_RECORD_RECEIVER_PROVEN=False'
Write-Host 'EABI_RUNTIME_CALLEE_COMPLIANCE_VERIFIED=False'
Write-Host 'STORE_EXECUTED_IN_SHOT_VERIFIED=False'
Write-Host 'MODEL_TRAINING_APPROVED=False'
Write-Host 'P0_R31_REFINED_LOCAL_PATHS_COMPLETE'
