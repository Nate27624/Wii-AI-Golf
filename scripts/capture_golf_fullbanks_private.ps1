# Full native Wii RAM capture from already running, operator-paused CLEAN Dolphin.
# Does NOT open GUI memory panels, swing, load states, pause/resume, or upload RAM.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Session,
    [Parameter(Mandatory=$true)][ValidateSet('PRE','POST','RESULT')][string]$Phase,
    [switch]$PausedConfirmed,
    [switch]$ShotObserved,
    [switch]$SameProcessConfirmed,
    [switch]$SameHoleConfirmed,
    [switch]$ResultVisible,
    [Nullable[double]]$DisplayedDistance,
    [ValidateSet('ft','yd','m')][string]$UiUnit
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$root = Split-Path -Parent $repo
$expectedExe = Join-Path $root 'tools\FelkDolphin-Clean\Dolphin.exe'
$script = Join-Path $PSScriptRoot 'capture_golf_fullbanks_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'Private native bank reader missing from this checkout'
}
if (-not $PausedConfirmed) {
    throw 'You must pause Dolphin before both banks; pass -PausedConfirmed'
}
$procs = @(Get-CimInstance Win32_Process -Filter "Name='Dolphin.exe'")
if ($procs.Count -ne 1) {
    throw 'Exactly ONE clean Dolphin.exe must be running; no banks read'
}
if ($procs[0].ExecutablePath -ine $expectedExe) {
    throw "Dolphin is not the expected clean portable executable: $($procs[0].ExecutablePath)"
}
if ($Phase -eq 'POST' -and
    (-not $ShotObserved -or -not $SameProcessConfirmed -or -not $SameHoleConfirmed)) {
    throw 'POST requires visible displaced shot before reset and same process/hole'
}
if ($Phase -eq 'RESULT' -and -not $ResultVisible) {
    throw 'RESULT requires an operator-confirmed visible result screen'
}
if ($PSBoundParameters.ContainsKey('DisplayedDistance') -xor
    $PSBoundParameters.ContainsKey('UiUnit')) {
    throw 'DisplayedDistance and UiUnit must be supplied together'
}
$parameters = @(
    '--session', $Session,
    '--phase', $Phase,
    '--paused-confirmed'
)
if ($ShotObserved) { $parameters += '--shot-observed' }
if ($SameProcessConfirmed) { $parameters += '--same-process-confirmed' }
if ($SameHoleConfirmed) { $parameters += '--same-hole-confirmed' }
if ($ResultVisible) { $parameters += '--result-visible' }
if ($PSBoundParameters.ContainsKey('DisplayedDistance')) {
    $parameters += @(
        '--displayed-distance',
        ([double]$DisplayedDistance).ToString([Globalization.CultureInfo]::InvariantCulture),
        '--ui-unit', $UiUnit
    )
}
& py $script @parameters
if ($LASTEXITCODE -ne 0) { throw "$Phase full-bank capture FAILED. Do NOT label it complete." }
# Validate real binary files, not just a JSON response.
$expected = @{ MEM1 = 24MB; MEM2 = 64MB }
foreach ($bank in @('MEM1', 'MEM2')) {
    $file = Join-Path $Session "$Phase-$bank.bin"
    if (-not (Test-Path -LiteralPath $file -PathType Leaf) -or
        (Get-Item -LiteralPath $file).Length -ne $expected[$bank]) {
        throw "$Phase $bank preserved binary missing or wrong-sized"
    }
}
Write-Host "${Phase}: Full native MEM1 (24 MiB) and MEM2 (64 MiB) saved privately." -ForegroundColor Green
Write-Host "Session: $Session"
