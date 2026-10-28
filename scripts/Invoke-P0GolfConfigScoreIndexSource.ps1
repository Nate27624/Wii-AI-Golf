#requires -Version 5.1
<#
Review only: original GolfConfig Rev1 source-code arithmetic.
Requires original 14-bank archive, SHA before/after. No Dolphin, RAM writes,
score values, native code words, runtime pointers or private paths output.
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
if($LASTEXITCODE -ne 0 -or $actual -ne $ExpectedCommit.ToLowerInvariant()){
    throw 'ABSTAIN: not the exact reviewed code SHA'
}
$expectedData=Join-Path (Split-Path $repo -Parent) 'Wii-AI-Golf-Data'
$actualData=(Resolve-Path -LiteralPath $DataRoot -ErrorAction Stop).Path
if($actualData -ne $expectedData){
    throw 'ABSTAIN: original source loader requires ignored data root sibling to reviewed checkout'
}
$captures=Join-Path $DataRoot 'captures'
$eligible=@(Get-ChildItem -LiteralPath $captures -Directory -ErrorAction Stop | Where-Object {
    $_.Name -like 'p0-new-cohort-*-PRIVATE' -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'manifest-PRIVATE.json') -PathType Leaf)
})
if($eligible.Count -ne 1){
    throw 'ABSTAIN: require exactly one canonical seven-numbered private archive; no paths disclosed'
}
$script=Join-Path $PSScriptRoot 'audit_p0_golf_config_score_index_ppc_private.py'
if(-not (Test-Path -LiteralPath $script -PathType Leaf)){
    throw 'ABSTAIN: reviewed decoder missing'
}
Write-Host '=== FABRICATED PPC INDEX SOURCE TESTS ==='
& python -B -m unittest discover -s (Join-Path $repo 'tests') -p 'test_p0_golf_config_score_index_ppc_private.py' -v
if($LASTEXITCODE -ne 0){throw 'ABSTAIN: source decoder regressions failed'}
Write-Host '=== ORIGINAL 14-BANK SOURCE SHA AND GETTER ARITHMETIC ==='
$json=& python -I $script --archive $eligible[0].FullName
if($LASTEXITCODE -ne 0 -or -not $json){
    throw 'ABSTAIN: full archive integrity or original Rev1 PPC getter source failed'
}
try{$report=($json -join [Environment]::NewLine) | ConvertFrom-Json}
catch{throw 'ABSTAIN: invalid sanitized report'}
if($report.kind -ne 'P0-GOLF-CONFIG-DUAL-SOURCE-INDEX-CONFLICT-PPC-TRIAGE' -or
    $report.original_14_bank_SHA_verified_before_and_after -ne $true -or
    $report.ogws_public_config_text_unit_boundary_qualified -ne $true -or
    $report.function_addresses_independently_public_both_sources -ne $true -or
    $report.one_unique_row_order_selected -ne $false -or
    $report.training_approved -ne $false -or
    $report.allowed_to_publish -ne $false -or
    @($report.source_functions).Count -ne 2){
    throw 'ABSTAIN: source, schema, provenance or training invariant failed'
}
Write-Host 'P0_ALL_14_ORIGINAL_BANKS_SHA=PASS'
Write-Host 'SCORE_ROW_ORDER_CONFLICT=UNRESOLVED_PENDING_REGISTER_FLOW'
foreach($func in $report.source_functions){
    Write-Host ("FUNCTION={0} BOUNDED_INSTRUCTIONS={1} OPAQUE_INSTRUCTIONS={2}" -f
        $func.public_rev1_source_function,
        $func.bounded_source_instruction_count,
        $func.opaque_instruction_count)
    foreach($e in $func.recognized_source_syntax){
        $sources=(@($e.sources) -join ',')
        $opnd= if($null -ne $e.source_immediate){
            "IMM=$($e.source_immediate)"
        }elseif($null -ne $e.source_shift){
            "SHIFT=$($e.source_shift)"
        }elseif($null -ne $e.source_relative_member_offset){
            "MEMBER_OFFSET=$($e.source_relative_member_offset)"
        }else{''}
        Write-Host ("  SITE={0} OP={1} DEST={2} SOURCE={3} {4}" -f
            $e.function_relative_site,$e.opcode_class,$e.dest,$sources,$opnd)
    }
}
Write-Host 'PHYSICS_SCORE_AND_TRAINING_VERIFIED=False'
Write-Host 'P0_CONFIG_SCORE_LAYOUT_SOURCE_ARITHMETIC_COMPLETE'
