#requires -Version 5.1
<#
Read-only original B0 source function entry HYPOTHESES and PPC direct Golf BL xrefs.
Exact pinned commit required; no Dolphin, new shot, RAM writes or uploads.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sha=(& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: source checkout differs from reviewed exact SHA'
}
$session=Join-Path $DataRoot 'ball-study-20261027-212633'
$module=Join-Path $PSScriptRoot 'audit_p0_player_r31_prelude_callers_private.py'
if (-not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf)) {
    throw 'ABSTAIN: original private B0 source or reviewed analyzer missing'
}
Write-Host '=== SOURCE-ONLY P0 PRELUDE CALLERS FABRICATED TESTS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_player_r31_prelude_callers_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic tests failed' }
Write-Host '=== ORIGINAL B0 SOURCE-GATED DIRECT CALL XREFS ==='
$json=& python -B $module --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $json) {
    throw 'ABSTAIN: original private B0 / public source / PPC gate failed'
}
try { $r=($json -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: malformed sanitized source result' }
if ($r.kind -ne 'S002-P0-R31-POSTRETURN-DIRECT-GOLF-BL-CANDIDATES' -or
    $r.original_B0_SHA_verified_before_after -ne $true -or
    $r.public_832_split_index_verified -ne $true -or
    $r.caller_prologue_or_full_cfg_verified -ne $false -or
    $r.indirect_virtual_callers_complete -ne $false -or
    $r.r3_is_selected_player_record_verified -ne $false -or
    $r.r31_store_executed_in_shot_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: source, interpretation, privacy or training gate failed'
}
Write-Host 'P0_ORIGINAL_B0_SOURCE_SHA=PASS'
Write-Host ("PUBLIC_GOLF_CODE_UNITS_SCANNED={0}" -f $r.Golf_public_source_units_scanned)
foreach($entry in $r.entry_hypotheses) {
    Write-Host ("POST_RETURN_ENTRY_HYPOTHESIS={0} DIRECT_GOLF_BL_COUNT={1}" -f
        $entry.candidate_post_return_pc_relative,$entry.direct_Golf_BL_count)
    foreach($call in $entry.bounded_source_calls) {
        Write-Host ("  CALL_SOURCE={0} AT={1}" -f $call.source_file,$call.relative_BL_site)
    }
    if($entry.omitted_calls -gt 0) {
        Write-Host ("  ADDITIONAL_CALL_SITES_OMITTED={0}" -f $entry.omitted_calls)
    }
}
Write-Host 'FUNCTION_BOUNDARY_AND_SELECTED_PLAYER_RECORD_PROVEN=False'
Write-Host 'RUNTIME_EXECUTION_AND_TRAINING_APPROVED=False'
Write-Host 'P0_PLAYER_RECEIVER_ENTRY_XREF_COMPLETE'
