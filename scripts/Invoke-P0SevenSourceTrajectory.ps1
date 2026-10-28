#requires -Version 5.1
<#
  Source-backed ordered driver 1->2 and wedge 5->6->7 selected-ball
  candidate comparison for seven HUMAN-labeled pre-existing raw dumps.
  All read only; no bridge, Dolphin, game input, file copy or GitHub upload.
  Preflight synthetic tests + real Python isolated module resolution.
  It DOES NOT replace the other agent's whole-bank seven-dump inventory.
#>
[CmdletBinding()]
param(
    [string]$DumpDirectory='D:\Projects\Wii Golf AI\tools\FelkDolphin-Clean\User\Dump',
    [switch]$TestsOnly
)
$ErrorActionPreference='Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$script = Join-Path $PSScriptRoot 'audit_p0_seven_source_trajectory_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'Missing exact source-backed seven phase Python reader'
}
$python=Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $python) { $python=Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $python) { throw 'Python required' }
Write-Host 'P0_SEVEN_SOURCE_TRAJECTORY=PRIVATE_READ_ONLY_OFFLINE'
Push-Location $repo
try {
    & $python.Source -m unittest discover -s tests -p 'test_p0_seven_source_trajectory_private.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic phase/source tests failed' }
} finally { Pop-Location }
Write-Host 'P0_SEVEN_SOURCE_SYNTHETIC=PASS'
$help=@(& $python.Source -I $script --help 2>&1)
if ($LASTEXITCODE -ne 0 -or
    -not (($help -join [Environment]::NewLine).Contains('--dump-directory'))) {
    throw 'Isolated Python source import failed; no private bank was inspected'
}
Write-Host 'P0_SEVEN_ISOLATED_PYTHON=PASS'
if ($TestsOnly) { return }
if (-not (Test-Path -LiteralPath $DumpDirectory -PathType Container)) {
    throw 'Private dump directory missing'
}
& $python.Source -I $script --dump-directory $DumpDirectory
if ($LASTEXITCODE -ne 0) {
    throw 'Source-gated seven phase comparison refused; no input modified'
}
Write-Host 'P0_SEVEN_SOURCE_TRAJECTORY=PASS'
Write-Host 'No Dolphin or controller invoked; all raw banks left unchanged.'
