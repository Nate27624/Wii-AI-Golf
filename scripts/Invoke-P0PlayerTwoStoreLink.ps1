#requires -Version 5.1
<#
One source-only P0 question: can RPGolPlayer stfs +0x30(r30)
locally pass the same r30 pointer to a callee stfs +0x90(r31)?
Exact original B0 SHA and published Rev1 code gated before/after.
Never invokes Dolphin, new shots, RAM writes or native data upload.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$head=(& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: wrong reviewed exact source commit'
}
$session=Join-Path $DataRoot 'ball-study-20261027-212633'
$manifest=Join-Path $session 'checkpoint-manifest-PRIVATE.json'
$script=Join-Path $PSScriptRoot 'audit_p0_player_two_store_same_receiver_private.py'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or
    -not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'ABSTAIN: original B0 manifest or reviewed module missing'
}
Write-Host '=== FABRICATED SAME-SOURCE-OBJECT LINK TESTS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_player_two_store_same_receiver_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic regression failed' }
Write-Host '=== ORIGINAL B0 VERIFIED SOURCE LINK AUDIT ==='
$lines=& python -B $script --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $lines) {
    throw 'ABSTAIN: source or private original B0 provenance failed'
}
try { $r=($lines -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: malformed sanitized report' }
# Strict fail-closed report contract with *field names only* on mismatch.
# In particular, do not conflate a successful Python exit with passed
# source evidence qualification, and never disclose raw native JSON.
$expected = [ordered]@{
    kind = 'S002-P0-PLAYER-TWO-FLOAT-STORE-SAME-RECEIVER-LOCAL-POSSIBILITY'
    original_B0_SHA_and_Rev1_verified_before_after = $true
    player_source_first_store = '+0x2008'
    caller_r30_to_r3_copy_site = '+0x201C'
    caller_direct_BL_site = '+0x2024'
    callee_candidate_entry = '+0x1BD4'
    same_object_runtime_write_proven = $false
    true_function_boundary_or_typed_receiver_verified = $false
    store_executed_in_same_shot_verified = $false
    approved_for_training = $false
    allowed_to_publish = $false
}
$violations = New-Object 'System.Collections.Generic.List[string]'
foreach ($key in $expected.Keys) {
    $prop = $r.PSObject.Properties[$key]
    if ($null -eq $prop) {
        $violations.Add("MISSING:$key")
        continue
    }
    $want = $expected[$key]
    $got = $prop.Value
    if ($want -is [bool]) {
        if ($got -isnot [bool] -or $got -ne $want) {
            $violations.Add("MISMATCH:$key")
        }
    } else {
        if ($got -isnot [string] -or $got -cne $want) {
            $violations.Add("MISMATCH:$key")
        }
    }
}
if ($violations.Count -gt 0) {
    # Only allowlisted key NAMES; no values, paths, hashes, pointer or ROM.
    Write-Host ("P0_TWO_STORE_REPORT_CONTRACT_ABSTAIN={0}" -f
        ($violations.ToArray() -join ','))
    throw 'ABSTAIN: exact original-source report contract mismatch; no claim promoted'
}
Write-Host 'P0_ORIGINAL_B0_SOURCE_SHA=PASS'
Write-Host ("CALLER_LOCAL_BL_REACHABLE={0}" -f $r.caller_local_path_reaches_BL)
Write-Host ("ORIGINAL_R30_FORWARDED_POSSIBLE={0}" -f $r.caller_path_forwards_original_r30_to_callee_possible)
Write-Host ("R30_MODIFIED_ON_SOME_CALLER_PATH={0}" -f $r.caller_path_r30_changed_before_call_possible)
Write-Host ("CALLER_REGISTER_UNCERTAINTY={0}" -f $r.caller_path_has_unresolved_r3_or_r30_possible)
Write-Host ("CALLEE_R31_COPY_PRESERVED_LOCAL_PATH_POSSIBLE={0}" -f $r.callee_local_source_path_preserves_copy_possible)
Write-Host ("JOINED_SAME_RECEIVER_SOURCE_PATH_POSSIBLE_ONLY={0}" -f $r.joined_two_store_source_possible_only)
foreach($edge in $r.caller_branch_edges) {
    Write-Host ("  BRANCH={0} KIND={1} LOCAL_TARGET={2}" -f
        $edge.source_site,$edge.kind,$edge.target_within_slice)
}
foreach($reason in $r.caller_incomplete_reasons) {
    Write-Host ("  UNRESOLVED={0}" -f $reason)
}
Write-Host 'ACTUAL_SELECTED_RECORD_AND_SHOT_EXECUTION_VERIFIED=False'
Write-Host 'PHYSICAL_XYZ_VELOCITY_POWER_VERIFIED=False'
Write-Host 'TRAINING_APPROVED=False'
Write-Host 'P0_TWO_PLAYER_FLOAT_STORES_LINK_COMPLETE'
