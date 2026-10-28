# OFFLINE integrity checker for S002 native PRE/POST/RESULT paused-memory artifacts.
# It reads existing private files only and prints no hashes, RAM, pointers, or paths.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Session,
    [switch] $RequirePost
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-SafeItem([string] $Path, [bool] $Directory) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -ne $Directory -or
        (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw 'Linked, missing, or unexpected PRIVATE artifact type.'
    }
    return $item
}
function PropertyValue($Object, [string] $Name) {
    if ($null -eq $Object) { throw 'Incomplete PRIVATE phase manifest.' }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { throw 'Incomplete PRIVATE phase manifest.' }
    return $prop.Value
}
function Assert-GameHeader([string] $FilePath) {
    $stream = [IO.File]::Open($FilePath, [IO.FileMode]::Open,
        [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $header = New-Object byte[] 8
        if ($stream.Read($header, 0, 8) -ne 8) { throw 'Incomplete native MEM1 header.' }
        $expected = [byte[]]@(82, 83, 80, 69, 48, 49, 0, 1) # RSPE01 Rev1
        for ($i = 0; $i -lt 8; $i++) {
            if ($header[$i] -ne $expected[$i]) { throw 'Wrong Wii Sports game/revision header.' }
        }
    } finally { $stream.Dispose() }
}

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$workspace = Split-Path -Parent $repo
$data = Join-Path $workspace 'Wii-AI-Golf-Data'
$captures = Join-Path $data 'captures'
[void](Assert-SafeItem $data $true)
[void](Assert-SafeItem $captures $true)
[void](Assert-SafeItem $Session $true)
$actual = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Session).ProviderPath).TrimEnd([char[]]@('\','/'))
$expectedParent = [IO.Path]::GetFullPath($captures).TrimEnd([char[]]@('\','/'))
if ((Split-Path -Parent $actual) -ne $expectedParent -or
    (Split-Path -Leaf $actual) -cnotmatch '^SHOT-[A-Za-z0-9_-]{4,60}-PRIVATE$') {
    throw 'The session must be a direct PRIVATE child of the canonical sibling captures directory.'
}
$manifestPath = Join-Path $actual 'shot-distance-captures-PRIVATE.json'
$manifestFile = Assert-SafeItem $manifestPath $false
if ($manifestFile.Length -gt 32768) { throw 'PRIVATE manifest exceeds its size limit.' }
try {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw 'Malformed PRIVATE shot checkpoint manifest.'
}
if ((PropertyValue $manifest 'kind') -cne 'local-private-golf-shot-cup-distance-checkpoints' -or
    (PropertyValue $manifest 'schema_version') -ne 1) {
    throw 'Unexpected PRIVATE shot checkpoint manifest schema.'
}
# A manifest must never be interpreted as evidence authorizing publication/training.
if ((PropertyValue $manifest 'allowed_to_publish') -cne $false -or
    (PropertyValue $manifest 'training_allowed') -cne $false -or
    (PropertyValue $manifest 'same_guest_frame_verified') -cne $false) {
    throw 'Unsupported training/publication/guest-frame claim in PRIVATE manifest.'
}
$checkpoints = PropertyValue $manifest 'checkpoints'
$present = @($checkpoints.PSObject.Properties.Name)
$phases = @('PRE', 'POST', 'RESULT')
if ($present.Count -lt 1 -or $present.Count -gt 3) {
    throw 'PRIVATE phase manifest is empty or has unsupported phases.'
}
foreach ($i in 0..($present.Count - 1)) {
    if ($present -cnotcontains $phases[$i]) { throw 'PRE -> POST -> RESULT phase prefix violated.' }
}
if ($RequirePost -and $present -cnotcontains 'POST') {
    throw 'POST native banks are required but absent; no shot pair is verified.'
}
$actualHashes = @{}
foreach ($phase in $phases) {
    if ($present -cnotcontains $phase) { continue }
    $entry = PropertyValue $checkpoints $phase
    if ((PropertyValue $entry 'phase_label') -cne $phase -or
        (PropertyValue $entry 'operator_reports_gui_paused') -cne $true -or
        (PropertyValue $entry 'operator_reports_same_pause_mem1_mem2') -cne $true) {
        throw ('Missing operator pause attestation for ' + $phase)
    }
    if ($phase -eq 'POST' -and
        ((PropertyValue $entry 'operator_observed_displaced_ball') -cne $true -or
         (PropertyValue $entry 'operator_reports_same_process') -cne $true -or
         (PropertyValue $entry 'operator_reports_same_hole') -cne $true)) {
        throw 'POST lacks required human displacement/process/hole attestations.'
    }
    if ($phase -eq 'RESULT' -and
        (PropertyValue $entry 'operator_observed_result_visible') -cne $true) {
        throw 'RESULT lacks visible result-screen attestation.'
    }
    $sha = PropertyValue $entry 'sha256'
    $actualHashes[$phase] = @{}
    foreach ($bank in @('MEM1', 'MEM2')) {
        $path = Join-Path $actual ($phase + '-' + $bank + '.bin')
        $file = Assert-SafeItem $path $false
        $size = if ($bank -eq 'MEM1') { 24MB } else { 64MB }
        if ($file.Length -ne $size) { throw ($phase + ' ' + $bank + ' has incorrect native bank size.') }
        if ($bank -eq 'MEM1') { Assert-GameHeader $path }
        $expected = PropertyValue $sha $bank
        if ($expected -isnot [string] -or $expected -cnotmatch '^[a-fA-F0-9]{64}$') {
            throw 'Manifest bank digest missing or invalid.'
        }
        $digest = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        if ($digest -ine $expected) { throw ($phase + ' ' + $bank + ' SHA256 mismatch.') }
        $actualHashes[$phase][$bank] = $digest
    }
}
if ($present -ccontains 'POST' -and
    $actualHashes['PRE']['MEM1'] -eq $actualHashes['POST']['MEM1'] -and
    $actualHashes['PRE']['MEM2'] -eq $actualHashes['POST']['MEM2']) {
    throw 'PRE and POST native banks are bitwise identical; no distinct POST checkpoint.'
}
$failedCount = @(Get-ChildItem -LiteralPath $actual -Directory -Force |
    Where-Object { $_.Name -like 'FAILED-*' -or $_.Name -like 'STAGING-*' }).Count
# Only count/boolean evidence is allowed into stdout. Never print hashes or RAM.
[pscustomobject]@{
    Kind = 's002-native-shot-phase-integrity-offline'
    PreservedPhaseCount = $present.Count
    HasPrePostBanks = [bool]($present -ccontains 'PRE' -and $present -ccontains 'POST')
    NativeBankLengthsAndSHA256Verified = $true
    IncompleteOrFailedPrivateStageCount = $failedCount
    SameGuestFrameVerified = $false
    ShotMotionVerifiedByMemory = $false
    BallWorldXYZOrVelocityVerified = $false
    OfficialScoreVerified = $false
    TrainingApproved = $false
    AllowedToPublish = $false
}
