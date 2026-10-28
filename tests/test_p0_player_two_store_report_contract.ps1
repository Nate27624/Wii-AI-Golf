#requires -Version 5.1
# Entirely fabricated fixture. Evaluates ACTUAL wrapper report qualifier AST,
# without invoking the source reader, Git, Dolphin, Python or private native B0.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$scriptPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts/Invoke-P0PlayerTwoStoreLink.ps1'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw 'CONTRACT_TEST_FAILED: expected reviewed wrapper missing'
}
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath, [ref]$tokens, [ref]$errors)
if ($null -ne $errors -and @($errors).Count -ne 0) {
    throw 'CONTRACT_TEST_FAILED: PowerShell 5.1 syntax invalid'
}

$qualifiers = @($ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.IfStatementAst] -and
    $node.Extent.Text.Contains('integrity/interpretation/training invariant unexpected')
}, $true))
if ($qualifiers.Count -ne 1 -or $qualifiers[0].Clauses.Count -ne 1) {
    throw 'CONTRACT_TEST_FAILED: source-gated report qualifier not uniquely found'
}
# AST exact source expression; tests DO NOT replicate a hand-written predicate.
$sourceCondition = $qualifiers[0].Clauses[0].Item1.Extent.Text
$expectedRequiredFields = @(
    'kind', 'original_B0_SHA_and_Rev1_verified_before_after',
    'player_source_first_store', 'caller_r30_to_r3_copy_site',
    'caller_direct_BL_site', 'callee_candidate_entry',
    'same_object_runtime_write_proven',
    'true_function_boundary_or_typed_receiver_verified',
    'store_executed_in_same_shot_verified', 'training_approved',
    'allowed_to_publish'
)
foreach ($field in $expectedRequiredFields) {
    if (-not $sourceCondition.Contains('$r.' + $field)) {
        throw 'CONTRACT_TEST_FAILED: a required scientific or provenance guard is missing'
    }
}
if ($sourceCondition.Contains('$r.approved_for_training')) {
    throw 'CONTRACT_TEST_FAILED: stale non-schema training field'
}

# Safely fabricate only the Python emitter's canonical allowlisted envelope.
$fixture = [ordered]@{
    kind = 'S002-P0-PLAYER-TWO-FLOAT-STORE-SAME-RECEIVER-LOCAL-POSSIBILITY'
    original_B0_SHA_and_Rev1_verified_before_after = $true
    player_source_first_store = '+0x2008'
    caller_r30_to_r3_copy_site = '+0x201C'
    caller_direct_BL_site = '+0x2024'
    callee_candidate_entry = '+0x1BD4'
    caller_local_path_reaches_BL = $true
    caller_path_forwards_original_r30_to_callee_possible = $false
    callee_local_source_path_preserves_copy_possible = $true
    joined_two_store_source_possible_only = $false
    same_object_runtime_write_proven = $false
    true_function_boundary_or_typed_receiver_verified = $false
    store_executed_in_same_shot_verified = $false
    training_approved = $false
    allowed_to_publish = $false
}
# Check that JSON types survive the same parser used by the operator wrapper.
$baseJson = ConvertTo-Json -InputObject $fixture -Depth 6 -Compress
function Assert-Case {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][bool]$ShouldReject,
        [hashtable]$Changes = @{},
        [string]$Remove = ''
    )
    $r = $baseJson | ConvertFrom-Json
    foreach ($k in $Changes.Keys) {
        $r.PSObject.Properties[$k].Value = $Changes[$k]
    }
    if ($Remove) {
        $r.PSObject.Properties.Remove($Remove)
    }
    # Evaluate the actual source AST qualifier with a synthetic sanitized $r.
    $rejected = [bool](Invoke-Expression $sourceCondition)
    if ($rejected -ne $ShouldReject) {
        throw 'CONTRACT_TEST_FAILED: incorrect acceptance/rejection of fabricated report'
    }
    Write-Host ("CONTRACT_CASE={0}:PASS" -f $Label)
}

Assert-Case -Label 'genuine_python_schema' -ShouldReject $false
Assert-Case -Label 'training_true_rejected' -ShouldReject $true -Changes @{training_approved=$true}
Assert-Case -Label 'training_missing_rejected' -ShouldReject $true -Remove 'training_approved'
Assert-Case -Label 'publication_true_rejected' -ShouldReject $true -Changes @{allowed_to_publish=$true}
Assert-Case -Label 'sha_gate_false_rejected' -ShouldReject $true -Changes @{original_B0_SHA_and_Rev1_verified_before_after=$false}
Assert-Case -Label 'runtime_receiver_true_rejected' -ShouldReject $true -Changes @{same_object_runtime_write_proven=$true}
Assert-Case -Label 'dynamic_shot_true_rejected' -ShouldReject $true -Changes @{store_executed_in_same_shot_verified=$true}
Assert-Case -Label 'typed_receiver_true_rejected' -ShouldReject $true -Changes @{true_function_boundary_or_typed_receiver_verified=$true}
Assert-Case -Label 'wrong_bl_offset_rejected' -ShouldReject $true -Changes @{caller_direct_BL_site='+0xFFFF'}
Assert-Case -Label 'wrong_kind_rejected' -ShouldReject $true -Changes @{kind='FABRICATED-BAD-KIND'}
Write-Host 'P0_TWO_STORE_WRAPPER_REPORT_CONTRACT=PASS'
