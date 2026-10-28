<#
.SYNOPSIS
  Compare TWO already preserved human-airborne MEM1/MEM2 archives, offline.
.DESCRIPTION
  Tests first. Never launches Dolphin, issues a swing, captures RAM,
  modifies either archive, publishes GitHub data or prints private hashes.
  Accepts a unique p0-airborne-*-PRIVATE directory or explicit RightArchive.
  This is NOT an XYZ/world-axes/velocity/frame/training proof.
#>
[CmdletBinding()]
param(
    [string]$CapturesRoot = '',
    [string]$RightArchive = '',
    [switch]$TestsOnly
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo
$data = Join-Path (Split-Path -Parent $repo) 'Wii-AI-Golf-Data'
if ([string]::IsNullOrWhiteSpace($CapturesRoot)) {
    $CapturesRoot = Join-Path $data 'captures'
}
$analyzer = Join-Path $repo 'scripts\audit_p0_dual_airborne_archive_identity_private.py'
if (-not (Test-Path -LiteralPath $analyzer -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $repo 'tests\test_p0_dual_airborne_archive_identity_private.py') -PathType Leaf)) {
    throw 'Auditor/tests unavailable in this isolated source revision'
}
$python = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $python) {
    throw 'No Python interpreter available'
}

Write-Output 'P0_ARCHIVE_IDENTITY_MODE=READ_ONLY_PRIVATE'
Write-Output 'DOLPHIN_STARTED=FALSE'
& $python.Source -I -m unittest discover -s tests -p test_p0_dual_airborne_archive_identity_private.py -v
if ($LASTEXITCODE -ne 0) {
    throw 'Synthetic privacy/provenance tests failed'
}
Write-Output 'P0_ARCHIVE_IDENTITY_SYNTHETIC_TESTS=PASS'
if ($TestsOnly) {
    return
}

# Validate user-provided root without exposing the private directory name.
if (-not (Test-Path -LiteralPath $CapturesRoot -PathType Container)) {
    throw 'Private captures root is missing; no bank data was read'
}
$expected = Join-Path $data 'captures'
$cap = (Resolve-Path -LiteralPath $CapturesRoot).Path
$allowed = (Resolve-Path -LiteralPath $expected).Path
if (-not [string]::Equals($cap, $allowed, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Refusing captures root outside the ignored sibling Data folder'
}

$arguments = @('-I', $analyzer, '--captures-root', $cap)
if (-not [string]::IsNullOrWhiteSpace($RightArchive)) {
    $arguments += @('--right-archive', $RightArchive)
}
$out = @(& $python.Source @arguments)
if ($LASTEXITCODE -ne 0 -or $out.Count -ne 1) {
    throw 'Archive identity audit safely abstained; no result published'
}
$result = $out[0] | ConvertFrom-Json
if ($result.kind -ne 'S002-P0-TWO-AIRBORNE-ARCHIVES-BYTE-IDENTITY' -or
    $result.schema_version -ne 1 -or
    $result.allowed_to_publish -ne $false -or
    $result.training_approved -ne $false -or
    $result.both_banks_same_guest_frame_verified -ne $false -or
    $result.source_selected_ball_world_xyz_verified -ne $false) {
    throw 'Unexpected output schema or falsely elevated physics claims'
}
Write-Output 'P0_ARCHIVE_IDENTITY=PASS'
Write-Output $out[0]
Write-Output 'PRIVATE_BANK_HASHES_OR_PATHS_PRINTED=FALSE'
Write-Output 'AUTOMATIC_GITHUB_UPLOAD=FALSE'
