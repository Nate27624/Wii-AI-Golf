<#
.SYNOPSIS
  Run three PINNED, already source-gated S002 offline P0 analyzers and reconcile.
.DESCRIPTION
  User-initiated only. NO Dolphin, shot, screen, RAM modification or publication.
  Adds isolated DETACHED clean worktrees from pinned PR #224/#225 source SHAs;
  never resets main or mutable branches. Stores sanitized reports under ignored
  Data/captures, rejects contradictions. GUI export frame atomicity unverified.
#>
[CmdletBinding()]
param(
    [string]$Baseline = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-study-20261027-212633',
    [string]$Flight = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\in-flight-human-20261028-054537477',
    [switch]$TestsOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$matrixRepo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$workspace = Split-Path -Parent $matrixRepo
$repo = Join-Path $workspace 'Wii-AI-Golf'
$data = Join-Path $workspace 'Wii-AI-Golf-Data'
$captures = Join-Path $data 'captures'

$pinSHA = 'b66e656392488ae6277b7490074acbe49b152b44'
$cacheSHA = '8d202032ccefef01390ea1f5fe8d8e82bb9c7916'
$pinWork = Join-Path $workspace 'Wii-AI-Golf-P0-Pin-Source-Review'
$cacheWork = Join-Path $workspace 'Wii-AI-Golf-P0-Cache-Source-Review'

function Verify-Worktree {
    param([string]$Location, [string]$Expected)
    $head = (& git -C $Location rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $null -eq $head -or $head.Trim() -cne $Expected) {
        throw 'Review worktree unexpected source revision'
    }
    $dirty = @(& git -C $Location status --porcelain)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) {
        throw 'Review worktree dirty; refusing modification'
    }
}

function Ensure-PinnedWorktree {
    param([int]$Pr, [string]$Expected, [string]$Location)
    # Mutable PR is fetched ONLY to make its commit history available.
    & git -C $repo fetch --no-tags origin ("refs/pull/{0}/head" -f $Pr)
    if ($LASTEXITCODE -ne 0) { throw 'PR source fetch failed' }
    & git -C $repo cat-file -e ($Expected + '^{commit}')
    if ($LASTEXITCODE -ne 0) {
        throw 'Pinned source revision is no longer available; ABSTAIN'
    }
    if (-not (Test-Path -LiteralPath $Location)) {
        & git -C $repo worktree add --detach $Location $Expected
        if ($LASTEXITCODE -ne 0) { throw 'Could not create pinned review worktree' }
    }
    Verify-Worktree $Location $Expected
}

function Require-PrivateDirectory {
    param([string]$Candidate)
    $resolved = (Resolve-Path -LiteralPath $Candidate -ErrorAction Stop).Path
    $private = (Resolve-Path -LiteralPath $data -ErrorAction Stop).Path.TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($private, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Private P0 capture must be under ignored Data'
    }
    $item = Get-Item -LiteralPath $resolved
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Symlink or missing P0 capture directory'
    }
    return $resolved
}

function Invoke-SourceTests {
    param([string]$Root, [string]$Pattern)
    Push-Location -LiteralPath $Root
    try {
        & py -I -m unittest discover -s tests -p $Pattern -v
        if ($LASTEXITCODE -ne 0) { throw 'Pinned P0 synthetic tests FAILED' }
    } finally { Pop-Location }
}

function Read-Sanitized {
    param([string]$Script, [string]$ExpectedKind, [string]$Saved)
    $text = @(& py -I $Script --baseline $Baseline --flight $Flight)
    if ($LASTEXITCODE -ne 0) { throw 'P0 source analysis rejected banks; no claim allowed' }
    $joined = $text -join [Environment]::NewLine
    try { $payload = $joined | ConvertFrom-Json -ErrorAction Stop }
    catch { throw 'P0 source analysis returned invalid JSON' }
    if ($payload.kind -cne $ExpectedKind) { throw 'P0 source schema mismatch' }
    [IO.File]::WriteAllText($Saved, $joined, (New-Object System.Text.UTF8Encoding($false)))
    return $payload
}

if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
    throw 'Expected main repo missing; no checkout reset performed'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher required'
}
$Baseline = Require-PrivateDirectory $Baseline
$Flight = Require-PrivateDirectory $Flight
if ($Baseline -ceq $Flight) { throw 'Baseline and flight cannot be identical directory' }

Write-Host 'P0_MATRIX_OFFLINE_READ_ONLY=True'
Ensure-PinnedWorktree 224 $pinSHA $pinWork
Ensure-PinnedWorktree 225 $cacheSHA $cacheWork
Invoke-SourceTests $matrixRepo 'test_p0_airborne_study_matrix.py'
Invoke-SourceTests $pinWork 'test_p0_flight_pin_control_private.py'
Invoke-SourceTests $cacheWork 'test_p0_inflight_cache_coherence_private.py'

if ($TestsOnly) {
    Write-Host 'P0_MATRIX_TESTS_ONLY=PASS'
    return
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmssfff')
$outdir = Join-Path $captures ('p0-evidence-matrix-' + $stamp + '-PRIVATE')
New-Item -ItemType Directory -Path $outdir -ErrorAction Stop | Out-Null
$baseJSON = Join-Path $outdir 'base-san-PRIVATE.json'
$pinJSON = Join-Path $outdir 'pin-san-PRIVATE.json'
$cacheJSON = Join-Path $outdir 'cache-san-PRIVATE.json'
$matrixJSON = Join-Path $outdir 'matrix-san-PRIVATE.json'
$baseScript = Join-Path $pinWork 'scripts\audit_p0_inflight_vs_b0_private.py'
$pinScript = Join-Path $pinWork 'scripts\audit_p0_flight_pin_control_private.py'
$cacheScript = Join-Path $cacheWork 'scripts\audit_p0_inflight_cache_coherence_private.py'

$base = Read-Sanitized $baseScript 'PRIVATE-SANITIZED-B0-VS-HUMAN-IN_FLIGHT-SOURCE-COMPARE' $baseJSON
$pin = Read-Sanitized $pinScript 'S002-B0-AIRBORNE-PIN-CONTROL-CONFOUND' $pinJSON
$cache = Read-Sanitized $cacheScript 'PRIVATE-SANITIZED-INFLIGHT-BALL-CACHE-COHERENCE' $cacheJSON

$validator = Join-Path $matrixRepo 'scripts\validate_p0_airborne_study_matrix.py'
$final = @(& py -I $validator --base $baseJSON --pin $pinJSON --cache $cacheJSON)
if ($LASTEXITCODE -ne 0) {
    throw 'P0 STUDY MATRIX ABSTAIN; keep private reports and investigate mismatched evidence'
}
$finalText = $final -join [Environment]::NewLine
$matrix = $finalText | ConvertFrom-Json
if ($matrix.kind -cne 'S000-PRIVATE-SANITIZED-P0-FLIGHT-THREE-STUDY-EVIDENCE-GATE' -or
    $matrix.three_independent_reader_outputs_consistent -ne $true -or
    $matrix.model_training_allowed -ne $false -or
    $matrix.physical_world_xyz_verified -ne $false) {
    throw 'Final P0 source evidence/training contract mismatch'
}
[IO.File]::WriteAllText($matrixJSON, $finalText, (New-Object System.Text.UTF8Encoding($false)))
Write-Host 'P0_MATRIX_SOURCE_GATES=PASS'
Write-Output $finalText
Write-Host 'P0_MATRIX_PRIVATE_REPORT_SAVED=True'
Write-Host 'P0_DOLPHIN_LAUNCHED=False'
Write-Host 'P0_PHYSICAL_XYZ_VELOCITY_TRAINING_APPROVED=False'
