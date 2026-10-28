#requires -Version 5.1
<#
Read-only original B0 PPC opcode classification; no emulator/shot/controller.
Requires SHA-pinned detached branch, authentic B0 manifest and strict abstention.
Outputs only categorized PPC syntax and unverified flags.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$DataRoot
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$actual=(& git -C $repo rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $ExpectedCommit.ToLowerInvariant()) {
    throw 'ABSTAIN: source checkout is not the reviewed exact SHA'
}
$session=Join-Path $DataRoot 'ball-study-20261027-212633'
$manifest=Join-Path $session 'checkpoint-manifest-PRIVATE.json'
$script=Join-Path $PSScriptRoot 'audit_p0_r31_opcode_classes_private.py'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or
    -not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'ABSTAIN: approved B0 checkpoint or source module not available'
}
Write-Host '=== FABRICATED REGRESSION TESTS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_r31_opcode_classes_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: focused synthetic regressions failed' }
Write-Host '=== ORIGINAL B0 SOURCE OPCODE CLASSIFICATION ==='
$lines=& python -B $script --data-root $DataRoot --private-session $session
if ($LASTEXITCODE -ne 0 -or -not $lines) {
    throw 'ABSTAIN: original private B0 source SHA / format / PPC gates failed'
}
try { $r=($lines -join [Environment]::NewLine) | ConvertFrom-Json }
catch { throw 'ABSTAIN: parser output malformed' }
if ($r.kind -ne 'S002-P0-R31-OPCODE-QUALIFIED-LOCAL-SLICE' -or
    $r.original_private_B0_SHA_verified_before_and_after -ne $true -or
    $r.exact_copy_and_store_source_verified -ne $true -or
    $r.target_site -ne '+0x1C00' -or
    $r.static_abi_assumption_is_runtime_callee_proof -ne $false -or
    $r.source_receiver_is_selected_player_record_verified -ne $false -or
    $r.dynamic_store_execution_verified -ne $false -or
    $r.approved_for_training -ne $false -or
    $r.allowed_to_publish -ne $false) {
    throw 'ABSTAIN: source evidence or privacy flags unexpected'
}
Write-Host 'P0_R31_EXACT_B0_SOURCE_SHA_PASS'
Write-Host ("TARGET_SITE={0} OPCODE_CLASS={1} R31_WRITE={2} WRITE_UNKNOWN={3}" -f
    $r.target_site,$r.target_opcode_family,
    $r.target_r31_direct_write_confirmed,$r.target_r31_write_unknown)
foreach($s in $r.local_source_sites) {
    Write-Host ("  SITE={0} FAMILY={1} GPR31_WRITE={2} GPR31_UNKNOWN={3} BRANCH={4} ABI_CALLEE_ASSUMPTION={5}" -f
        $s.source_unit_offset,$s.opcode_family,
        $s.r31_direct_instruction_write_confirmed,
        $s.r31_gpr_write_possible_unknown,
        $s.branch_kind_if_recognized,
        $s.callee_nonvolatile_r31_abi_assumption_needed)
}
Write-Host 'SELECTED_PLAYER_RECEIVER_VERIFIED=False'
Write-Host 'ACTUAL_WRITER_EXECUTION_VERIFIED=False'
Write-Host 'TRAINING_APPROVED=False'
Write-Host 'P0_R31_OPCODE_STUDY_COMPLETE'
