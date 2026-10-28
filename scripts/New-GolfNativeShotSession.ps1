# Create only a fresh PRIVATE directory for the canonical S002 shot checkpoint keeper.
# Does not connect to Dolphin, capture RAM, run a swing or publish anything.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_-]{4,60}$')]
    [string] $Id
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-RealDirectory([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (-not $item.PSIsContainer -or
        (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw 'The PRIVATE data path is not a real directory; linked paths are refused.'
    }
}

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$workspace = Split-Path -Parent $repo
$data = Join-Path $workspace 'Wii-AI-Golf-Data'
$captures = Join-Path $data 'captures'
foreach ($directory in @($data, $captures)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        [void][IO.Directory]::CreateDirectory($directory)
    }
    Assert-RealDirectory $directory
}
if (-not $Id) {
    $Id = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 10)
}
if ($Id -notmatch '^[A-Za-z0-9_-]{4,60}$') {
    throw 'Unsafe session identifier.'
}
$session = Join-Path $captures ('SHOT-' + $Id + '-PRIVATE')
# Never use -Force: an existing session is evidence and must not be reused.
if (Test-Path -LiteralPath $session) { throw 'PRIVATE session already exists; refusing reuse.' }
try {
    $null = New-Item -Path $session -ItemType Directory -ErrorAction Stop
} catch {
    throw 'Could not create a fresh PRIVATE session; existing data was not changed.'
}
Assert-RealDirectory $session
# A single output lets the operator bind this to $session without parsing prose.
Write-Output $session
