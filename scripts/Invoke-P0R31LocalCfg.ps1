#requires -Version 5.1
<#
Offline read-only P0 local PPC branch study. Exact pinned SHA required.
No Dolphin, controller, new shots, RAM writes, exports, or uploads.
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
$script = Join-Path $PSScriptRoot 'audit_p0_r31_local_cfg_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) {
    throw 'ABSTAIN: pinned script or existing original B0 checkpoint manifest missing'
}
$head = (& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: exact pinned source SHA mismatch'
}
Write-Host '=== P0 R31 BOUNDED SOURCE CFG SYNTHETIC ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_r31_local_cfg_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic local CFG regressions failed' }
Write-Host '=== ORIGINAL B0 STATIC CODE ONLY ==='
$lines = & python -B $script --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $lines) { throw 'ABSTAIN: native source SHA or PPC predicate gate failed' }
try { $r = ($lines -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: malformed redacted report' }
if ($r.kind -ne 'S002-P0-R31-LOCAL-CFG-CANDIDATES' -or
    $r.original_private_B0_SHA_verified_before_and_after -ne $true -or
    $r.copy_is_r3_to_r31_source_confirmed -ne $true -or
    $r.store_is_stfs_f0_to_r31_plus_90_source_confirmed -ne $true -or
    $r.full_function_cfg_dominance_proven -ne $false -or
    $r.runtime_receiver_is_selected_player_record_verified -ne $false -or
    $r.dynamic_store_execution_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: provenance or claim/approval safety invariant failed'
}
Write-Host 'P0_R31_ORIGINAL_B0_SOURCE_SHA_PASS'
Write-Host ("SOURCE_COPY_SITE={0} SOURCE_STORE_SITE={1}" -f $r.copy_site_source_offset,$r.store_site_source_offset)
Write-Host ("BOUNDED_LOCAL_PATH_REACHES_STORE={0}" -f $r.local_path_reaches_store)
Write-Host ("LOCAL_R31_PRESERVED_PATH_POSSIBLE={0}" -f $r.local_path_reaches_store_with_unmodified_r31)
Write-Host ("LOCAL_R31_UNCERTAIN_PATH_POSSIBLE={0}" -f $r.local_path_reaches_store_with_unknown_r31)
foreach ($edge in $r.control_flow_edges) {
    Write-Host ("  BRANCH site={0} class={1} target_within_slice={2}" -f
        $edge.site,$edge.kind,$edge.target_if_within_slice)
}
foreach ($reason in $r.incomplete_path_reasons) {
    Write-Host ("  INCOMPLETE={0}" -f $reason)
}
foreach ($site in $r.unresolved_r31_site_offsets) {
    Write-Host ("  UNRESOLVED_R31_SITE={0}" -f $site)
}
Write-Host 'FULL_FUNCTION_CFG_PROVEN=False'
Write-Host 'R31_IS_SELECTED_PLAYER_RECORD_VERIFIED=False'
Write-Host 'DYNAMIC_STORE_EXECUTION_VERIFIED=False'
Write-Host 'TRAINING_APPROVED=False'
Write-Host 'P0_R31_LOCAL_CFG_COMPLETE'
