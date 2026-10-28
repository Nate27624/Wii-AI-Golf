<#
.SYNOPSIS
  PRIVATE read-only source-checked stationary B0 vs preserved human-airborne ball.
.DESCRIPTION
  Reuses existing S002 #160/#163/#181 native Rev1 source chain, B0 B0-B3
  private manifest and operator hash-verified in-flight archive. Never runs
  Dolphin, changes memory/saves, publishes raw data, or claims verified XYZ.
  Safe for Windows PowerShell 5.1. All scientific parsing is in the adjacent
  audited Python module; PowerShell is the only operator-facing entrypoint.
.EXAMPLE
  & .\scripts\Invoke-P0InFlightBallCompare.ps1
#>
[CmdletBinding()]
param(
    [string]$Baseline = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-study-20261027-212633',
    [string]$Flight = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\in-flight-human-20261028-054537477',
    [switch]$TestsOnly
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$workspace = Split-Path -Parent $repo
$data = Join-Path $workspace 'Wii-AI-Golf-Data'
$analyzer = Join-Path $PSScriptRoot 'audit_p0_inflight_vs_b0_private.py'
$tests = Join-Path $repo 'tests\test_p0_inflight_vs_b0_private.py'

if (-not (Test-Path -LiteralPath $analyzer -PathType Leaf) -or
    -not (Test-Path -LiteralPath $tests -PathType Leaf)) {
    throw 'S002 in-flight analyzer/tests missing; review worktree incomplete'
}
$exe = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $exe) { $exe = Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $exe) { throw 'Python not installed' }

Write-Host 'P0_INFLIGHT_MODE=READ_ONLY_OFFLINE_PRIVATE'
Write-Host 'P0_INFLIGHT_DOLPHIN_LAUNCHED=FALSE'

Push-Location -LiteralPath $repo
try {
    & $exe.Source -m unittest discover -s tests -p test_p0_inflight_vs_b0_private.py -v
    if ($LASTEXITCODE -ne 0) { throw 'Source comparison offline regression tests failed' }
} finally {
    Pop-Location
}
Write-Host 'P0_INFLIGHT_SYNTHETIC_TESTS=PASS'
if ($TestsOnly) { return }

if (-not (Test-Path -LiteralPath $data -PathType Container)) {
    throw 'Ignored private Data folder is missing'
}
foreach ($dir in @($Baseline, $Flight)) {
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
        throw 'Required preserved baseline or in-flight folder missing'
    }
    $resolved = (Resolve-Path -LiteralPath $dir).Path
    $allowed = (Resolve-Path -LiteralPath $data).Path.TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing a directory outside ignored private Data root'
    }
}
$baseline = (Resolve-Path -LiteralPath $Baseline).Path
$flightDir = (Resolve-Path -LiteralPath $Flight).Path
if ($baseline -eq $flightDir) { throw 'Baseline and flight must differ' }
if (-not (Test-Path -LiteralPath (Join-Path $baseline 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) {
    throw 'Preserved B0 private checkpoint manifest not found'
}
if (-not (Test-Path -LiteralPath (Join-Path $flightDir 'manifest-PRIVATE.json') -PathType Leaf)) {
    throw 'Archived airborne private manifest not found'
}

# Exclusive-create output inside ignored private Data; no overwrite.
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssfff')
$out = Join-Path $flightDir ('p0-b0-vs-airborne-source-contrast-' + $stamp + '-PRIVATE.json')
if (Test-Path -LiteralPath $out) { throw 'Refusing to overwrite existing result' }
Write-Host 'P0_INFLIGHT_AUDIT=SOURCE_GATED_STARTING'
$lines = @(& $exe.Source -I $analyzer --baseline $baseline --flight $flightDir --output $out)
if ($LASTEXITCODE -ne 0) {
    throw 'In-flight source gate failed; private inputs unchanged. STOP. Do not assume bank layout.'
}
$json = $lines -join [Environment]::NewLine
try {
    $report = $json | ConvertFrom-Json
} catch {
    throw 'Analyzer did not produce valid sanitized JSON'
}
if ($report.kind -ne 'PRIVATE-SANITIZED-B0-VS-HUMAN-IN_FLIGHT-SOURCE-COMPARE' -or
    $report.source_gated_both_snapshots -ne $true -or
    $report.actual_ball_world_xyz_verified -ne $false -or
    $report.mem1_mem2_exports_same_guest_frame_verified -ne $false -or
    $report.approved_for_training -ne $false -or
    $report.allowed_to_publish -ne $false) {
    throw 'Unexpected/unsafe sanitized result'
}
Write-Host 'P0_INFLIGHT_AUDIT=PASS'
Write-Output $json
Write-Host 'P0_INFLIGHT_PRIVATE_JSON_WRITTEN=TRUE'
Write-Host 'P0_INFLIGHT_RAW_RAM_PRINTED_OR_UPLOADED=FALSE'
Write-Host 'P0_INFLIGHT_BALL_XYZ_VERIFIED=FALSE'
Write-Host 'P0_INFLIGHT_TRAINING_APPROVED=FALSE'
