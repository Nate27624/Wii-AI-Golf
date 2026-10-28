#requires -Version 5.1
<#
Original B0 SHA-pinned source-only r3 argument syntax at RPGolPlayer
+0x2024 and +0x2520. Never launches Dolphin or writes RAM.
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
    throw 'ABSTAIN: source checkout differs from reviewed SHA'
}
$session=Join-Path $DataRoot 'ball-study-20261027-212633'
$script=Join-Path $PSScriptRoot 'audit_p0_player_r31_two_callsite_r3_private.py'
if (-not (Test-Path -LiteralPath (Join-Path $session 'checkpoint-manifest-PRIVATE.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'ABSTAIN: original B0 manifest or reviewed source missing'
}
Write-Host '=== FABRICATED PPC TWO-CALLSITE ARGUMENT REGRESSIONS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_player_r31_two_callsite_r3_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic regressions failed' }
Write-Host '=== AUTHENTICATED ORIGINAL B0 R3 ARGUMENT SOURCE AUDIT ==='
$json=& python -B $script --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $json) {
    throw 'ABSTAIN: original source gate or exact callsite drift'
}
try { $r=($json -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: invalid sanitized source JSON' }
if ($r.kind -ne 'S002-P0-PLAYER-R31-TWO-CALLSITE-R3-ARGUMENT-HINTS' -or
    $r.entry_source_relative -ne '+0x1BD4' -or
    $r.candidate_entry_after_exact_blr_verified -ne $true -or
    $r.original_private_B0_SHA_verified_before_after -ne $true -or
    $r.public_832_source_split_gate_verified -ne $true -or
    $r.exact_source_two_direct_calls_verified -ne $true -or
    @($r.source_calls).Count -ne 2 -or
    $r.incoming_r3_is_selected_player_record_verified -ne $false -or
    $r.dynamic_source_store_during_shot_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: expected source/schema/training invariant not satisfied'
}
Write-Host 'P0_ORIGINAL_B0_SOURCE_SHA=PASS'
foreach($call in $r.source_calls) {
    $origin=$call.nearest_post_barrier_r3_hint
    Write-Host ("CALL={0} TARGET={1} NEAREST_POSTBARRIER_R3_CLASS={2} FROM={3} SITE={4} BARRIERS={5} SUFFIX_EVENTS={6}" -f
        $call.source_call_site,$call.source_target_entry_candidate,
        $origin.class,$origin.source,$origin.site,$call.control_transfer_count_in_window,
        $call.post_last_barrier_r3_events)
    foreach($e in $call.r3_events_nearest_first) {
        Write-Host ("  R3_SOURCE_SITE={0} CLASS={1} FROM={2} DEFINITE={3}" -f
            $e.site,$e.class,$e.source,$e.definite_r3_write)
    }
}
Write-Host 'TYPED_SELECTED_PLAYER_RECORD_RECEIVER_VERIFIED=False'
Write-Host 'RUNTIME_EXECUTION_AND_TRAINING_APPROVED=False'
Write-Host 'P0_TWO_PLAYER_CALLSITE_R3_STUDY_COMPLETE'
