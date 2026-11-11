#requires -Version 5.1
<#
.SYNOPSIS
  Standalone, OFFLINE S002 native shot session and PRE/POST integrity helper.
.DESCRIPTION
  Windows PowerShell 5.1 or PowerShell 7. No Python, pwsh installation, Git
  checkout, Dolphin, GUI, emulator, or other scripts required.
  Start: creates a unique ignored, RAW-PRIVATE SHOT folder.
  Status: prints AWAITING_PRE / AWAITING_POST / PREPOST_INTEGRITY_VERIFIED.
          A fresh empty folder is EXPECTED, not an error or successful capture.
  Verify: requires both genuine preserved native PRE and POST bank files;
          refuses missing evidence, inconsistent hashes or missing attestations.
  NEVER pauses/starts Dolphin, swings, acquires RAM, or publishes raw data.
.EXAMPLE
  $session = & .\Invoke-GolfNativeShot.ps1 -Action Start -Workspace 'D:\Projects\Wii Golf AI'
  & .\Invoke-GolfNativeShot.ps1 -Action Status -Session $session
  # Only after the existing S002 native capture has saved PRE and POST:
  & .\Invoke-GolfNativeShot.ps1 -Action Verify -Session $session
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Start', 'Status', 'Verify')]
    [string] $Action,
    [string] $Session,
    [string] $Workspace,
    [ValidatePattern('^[A-Za-z0-9_-]{4,60}$')]
    [string] $Id
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-RealDir([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    return (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)
}
function Assert-RealDir([string] $Path) {
    if (-not (Test-RealDir $Path)) {
        throw 'Missing or linked PRIVATE directory; refusing non-canonical evidence.'
    }
}
function Assert-RealFile([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or
        (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw 'Native PRIVATE artifact is linked or not a regular file.'
    }
    return $item
}
function Field($Object, [string] $Name) {
    if ($null -eq $Object -or $null -eq $Object.PSObject.Properties[$Name]) {
        throw 'Missing required S002 PRIVATE manifest field.'
    }
    return $Object.PSObject.Properties[$Name].Value
}
function Assert-Header([string] $FilePath) {
    $stream = [IO.File]::Open($FilePath, [IO.FileMode]::Open,
        [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $actual = New-Object byte[] 8
        if ($stream.Read($actual, 0, 8) -ne 8) {
            throw 'Incomplete native MEM1 header.'
        }
        $expected = [byte[]]@(82,83,80,69,48,49,0,1)
        for ($i=0; $i -lt 8; $i++) {
            if ($actual[$i] -ne $expected[$i]) {
                throw 'Wrong Wii Sports RSPE01 Rev1 native header.'
            }
        }
    } finally {
        $stream.Dispose()
    }
}
function Hash-PrivateFile([string] $FilePath) {
    # Works on native Windows PowerShell 5.1 even if Get-FileHash is absent.
    # Hash through a streamed .NET API, never loading 24/64 MiB into RAM.
    $stream = [IO.File]::Open($FilePath, [IO.FileMode]::Open,
        [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            $digest = $sha.ComputeHash($stream)
            return [BitConverter]::ToString($digest).Replace('-', '')
        } finally {
            $sha.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}
function Assert-Session([string] $Path, [string] $Captures) {
    Assert-RealDir $Path
    $actual = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Path).ProviderPath).TrimEnd([char[]]@('\','/'))
    $parent = [IO.Path]::GetFullPath($Captures).TrimEnd([char[]]@('\','/'))
    $name = Split-Path -Leaf $actual
    if ((Split-Path -Parent $actual) -ne $parent -or
        $name -cnotmatch '^SHOT-[A-Za-z0-9_-]{4,60}-PRIVATE$') {
        throw 'Session must be a direct canonical ignored SHOT-*-PRIVATE folder.'
    }
    return $actual
}

# Works either from a repository scripts folder or an arbitrary downloaded
# location when -Workspace is supplied. Never silently create an unrelated
# "Wii-AI-Golf-Data" directory next to Downloads.
if ($Workspace) {
    $workspace = (Resolve-Path -LiteralPath $Workspace -ErrorAction Stop).ProviderPath
} else {
    $parent = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
    $folder = Split-Path -Leaf $parent
    if ($folder -eq 'Wii-AI-Golf-Data' -or $folder -like 'Wii-AI-Golf*') {
        $workspace = Split-Path -Parent $parent
    } else {
        throw 'Set -Workspace to your Wii Golf AI workspace when running a downloaded script.'
    }
}
Assert-RealDir $workspace
$data = Join-Path $workspace 'Wii-AI-Golf-Data'
$captures = Join-Path $data 'captures'

if ($Action -eq 'Start') {
    if ($Session) { throw 'Start creates a NEW session; do not supply -Session.' }
    foreach ($directory in @($data, $captures)) {
        if (-not (Test-Path -LiteralPath $directory)) {
            [void][IO.Directory]::CreateDirectory($directory)
        }
        Assert-RealDir $directory
    }
    if (-not $Id) {
        $Id = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
            '-' + [guid]::NewGuid().ToString('N').Substring(0,10)
    }
    if ($Id -cnotmatch '^[A-Za-z0-9_-]{4,60}$') {
        throw 'Unsafe private shot ID.'
    }
    $new = Join-Path $captures ('SHOT-' + $Id + '-PRIVATE')
    if (Test-Path -LiteralPath $new) {
        throw 'Session already exists; never overwrite native evidence.'
    }
    [void](New-Item -Path $new -ItemType Directory -ErrorAction Stop)
    Assert-RealDir $new
    # Only output the session string so callers can use $session = & script.
    Write-Output $new
    return
}

if ($Id) { throw '-Id is available only with -Action Start.' }
if ([string]::IsNullOrWhiteSpace($Session)) {
    throw 'Specify -Session with -Action Status or -Action Verify.'
}
Assert-RealDir $data
Assert-RealDir $captures
$sessionPath = Assert-Session $Session $captures
$failedOrPartial = @(Get-ChildItem -LiteralPath $sessionPath -Directory -Force |
    Where-Object { $_.Name -like 'FAILED-*' -or $_.Name -like 'STAGING-*' }).Count
$manifestPath = Join-Path $sessionPath 'shot-distance-captures-PRIVATE.json'

if (-not (Test-Path -LiteralPath $manifestPath)) {
    $native = @(Get-ChildItem -LiteralPath $sessionPath -File -Force |
        Where-Object { $_.Name -match '^(PRE|POST|RESULT)-MEM[12]\.bin$' })
    if ($native.Count -gt 0) {
        throw 'Unindexed native banks exist with no keeper manifest; refusing false success.'
    }
    if ($Action -eq 'Verify') {
        throw 'NOT READY: no PRE/POST native snapshots. Capture PRE, then a confirmed displaced-ball POST before Verify.'
    }
    [pscustomobject]@{
        Status = 'AWAITING_PRE'
        HasNativePrePostPair = $false
        NativeEvidenceIntegrityVerified = $false
        PartialPrivateStageCount = $failedOrPartial
        SameGuestFrameVerified = $false
        BallWorldXYZOrVelocityVerified = $false
        TrainingApproved = $false
        AllowedToPublish = $false
    }
    return
}
$manifestFile = Assert-RealFile $manifestPath
if ($manifestFile.Length -gt 32768) { throw 'S002 PRIVATE manifest is too large.' }
try {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw 'S002 PRIVATE manifest cannot be parsed.'
}
if ((Field $manifest 'kind') -cne 'local-private-golf-shot-cup-distance-checkpoints' -or
    (Field $manifest 'schema_version') -ne 1) {
    throw 'Unexpected S002 keeper manifest schema.'
}
if ((Field $manifest 'allowed_to_publish') -cne $false -or
    (Field $manifest 'training_allowed') -cne $false -or
    (Field $manifest 'same_guest_frame_verified') -cne $false) {
    throw 'S002 manifest makes unsupported training, publication or same-frame claim.'
}
$records = Field $manifest 'checkpoints'
$present = @($records.PSObject.Properties.Name)
$order = @('PRE', 'POST', 'RESULT')
if ($present.Count -lt 1 -or $present.Count -gt 3) {
    throw 'Manifest contains no recognized checkpoint prefix.'
}
for ($i=0; $i -lt $present.Count; $i++) {
    if ($present -cnotcontains $order[$i]) {
        throw 'Checkpoint phase order must be PRE, then POST, optionally RESULT.'
    }
}
$hashes = @{}
foreach ($phase in $order) {
    if ($present -cnotcontains $phase) { continue }
    $entry = Field $records $phase
    if ((Field $entry 'phase_label') -cne $phase -or
        (Field $entry 'operator_reports_gui_paused') -cne $true -or
        (Field $entry 'operator_reports_same_pause_mem1_mem2') -cne $true) {
        throw ('Missing paused-checkpoint attestation for ' + $phase)
    }
    if ($phase -eq 'POST' -and
        ((Field $entry 'operator_observed_displaced_ball') -cne $true -or
         (Field $entry 'operator_reports_same_process') -cne $true -or
         (Field $entry 'operator_reports_same_hole') -cne $true)) {
        throw 'POST requires human-observed displacement, same process and same hole.'
    }
    if ($phase -eq 'RESULT' -and
        (Field $entry 'operator_observed_result_visible') -cne $true) {
        throw 'RESULT screen was not attested.'
    }
    $expectedSha = Field $entry 'sha256'
    $hashes[$phase] = @{}
    foreach ($bank in @('MEM1','MEM2')) {
        $bankPath = Join-Path $sessionPath ($phase + '-' + $bank + '.bin')
        $bankInfo = Assert-RealFile $bankPath
        $size = if ($bank -eq 'MEM1') { 24MB } else { 64MB }
        if ($bankInfo.Length -ne $size) {
            throw ($phase + ' ' + $bank + ' is not a complete native RAM bank.')
        }
        if ($bank -eq 'MEM1') { Assert-Header $bankPath }
        $claimed = Field $expectedSha $bank
        if ($claimed -isnot [string] -or $claimed -cnotmatch '^[a-fA-F0-9]{64}$') {
            throw 'Missing native bank digest in PRIVATE keeper manifest.'
        }
        $actualSha = (Hash-PrivateFile $bankPath)
        if ($actualSha -ine $claimed) {
            throw ($phase + ' ' + $bank + ' digest mismatch.')
        }
        $hashes[$phase][$bank] = $actualSha
    }
}
$hasPair = $present -ccontains 'PRE' -and $present -ccontains 'POST'
if ($hasPair -and
    $hashes['PRE']['MEM1'] -eq $hashes['POST']['MEM1'] -and
    $hashes['PRE']['MEM2'] -eq $hashes['POST']['MEM2']) {
    throw 'PRE and POST native banks are identical; not two distinct snapshots.'
}
if ($Action -eq 'Verify' -and -not $hasPair) {
    throw 'NOT READY: PRE integrity verified, but POST has not been preserved.'
}
$status = if ($hasPair) { 'PREPOST_INTEGRITY_VERIFIED' } else { 'AWAITING_POST' }
[pscustomobject]@{
    Status = $status
    PreservedPhaseCount = $present.Count
    HasNativePrePostPair = [bool]$hasPair
    NativeEvidenceIntegrityVerified = $true
    PartialPrivateStageCount = $failedOrPartial
    SameGuestFrameVerified = $false
    BallWorldXYZOrVelocityVerified = $false
    TrainingApproved = $false
    AllowedToPublish = $false
}
