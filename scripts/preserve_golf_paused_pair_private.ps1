# Preserve one already GUI-paused FelkDolphin-Clean native MEM1+MEM2 pair.
# PRIVATE LOCAL ONLY. No Dolphin launch, RPC, pause or controller operation.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CleanDolphinUserRoot,
    [Parameter(Mandatory=$true)][string]$SourceMem1Path,
    [Parameter(Mandatory=$true)][string]$SourceMem2Path,
    [Parameter(Mandatory=$true)][string]$PrivateDataRoot,
    [Parameter(Mandatory=$true)][string]$SessionFolder,
    [Parameter(Mandatory=$true)][ValidateSet('PRE','POST')][string]$Phase,
    [Parameter(Mandatory=$true)][datetime]$ExportStartedAfter,
    [switch]$ConfirmBothExportsUnderSameGuiPause,
    [switch]$ConfirmCorrectVisibleShotPhase,
    [switch]$ConfirmNoHoleOrDolphinProcessChange
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Private([string]$reason) {
    throw "Private paused-pair preservation stopped: $reason. No source path, RAM, or hashes printed."
}

function Resolve-SafeDirectory([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        Stop-Private 'required private directory unavailable'
    }
    $resolved = (Resolve-Path -LiteralPath $path).ProviderPath
    if ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Stop-Private 'linked directory refused'
    }
    return $resolved.TrimEnd([IO.Path]::DirectorySeparatorChar,
                             [IO.Path]::AltDirectorySeparatorChar)
}

function Is-StrictChild([string]$child, [string]$root) {
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    return $child.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
}

function Resolve-SafeSource([string]$path, [string]$userRoot, [long]$expectedSize, [datetime]$afterUtc) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Stop-Private 'paused exported source file unavailable'
    }
    $resolved = (Resolve-Path -LiteralPath $path).ProviderPath
    if (-not (Is-StrictChild $resolved $userRoot)) {
        Stop-Private 'source export is outside clean portable User tree'
    }
    $file = Get-Item -LiteralPath $resolved -Force
    if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        $file.Length -ne $expectedSize) {
        Stop-Private 'unsafe or wrong-sized native export'
    }
    $cursor = $file.Directory
    while ($null -ne $cursor) {
        if ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Stop-Private 'linked export parent refused'
        }
        if ([string]::Equals($cursor.FullName, $userRoot,
                             [StringComparison]::OrdinalIgnoreCase)) { break }
        $cursor = $cursor.Parent
    }
    if ($null -eq $cursor) { Stop-Private 'untrusted source directory' }
    if ($file.LastWriteTimeUtc -lt $afterUtc) {
        Stop-Private 'stale export; perform GUI export AFTER recording start time'
    }
    return $resolved
}

if (-not $ConfirmBothExportsUnderSameGuiPause -or
    -not $ConfirmCorrectVisibleShotPhase -or
    -not $ConfirmNoHoleOrDolphinProcessChange) {
    Stop-Private 'operator same-pause and shot-phase confirmations missing'
}
if ($ExportStartedAfter.ToUniversalTime() -gt [datetime]::UtcNow.AddMinutes(2)) {
    Stop-Private 'export start time appears to be in the future'
}

try {
    $cleanRoot = Resolve-SafeDirectory $CleanDolphinUserRoot
    $dataRoot = Resolve-SafeDirectory $PrivateDataRoot
    $session = Resolve-SafeDirectory $SessionFolder
    # The legacy/crash-prone installation and an arbitrary AppData Dolphin
    # directory must NEVER be silently substituted for the clean portable User.
    if ((Split-Path -Leaf $cleanRoot) -ne 'User' -or
        (Split-Path -Leaf (Split-Path -Parent $cleanRoot)) -ne 'FelkDolphin-Clean') {
        Stop-Private 'unexpected clean portable User root'
    }
    if ((Split-Path -Leaf $dataRoot) -ne 'Wii-AI-Golf-Data' -or
        -not (Is-StrictChild $session $dataRoot)) {
        Stop-Private 'session must be inside ignored sibling Data root'
    }
    $src1 = Resolve-SafeSource $SourceMem1Path $cleanRoot (24MB) $ExportStartedAfter.ToUniversalTime()
    $src2 = Resolve-SafeSource $SourceMem2Path $cleanRoot (64MB) $ExportStartedAfter.ToUniversalTime()
    if ([string]::Equals($src1, $src2, [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Private 'duplicated source bank'
    }
    $dst1 = Join-Path $session "$Phase-MEM1.bin"
    $dst2 = Join-Path $session "$Phase-MEM2.bin"
    if ((Test-Path -LiteralPath $dst1) -or (Test-Path -LiteralPath $dst2)) {
        Stop-Private 'destination pair already exists; never overwrite'
    }
    if ($Phase -eq 'POST' -and
        (-not (Test-Path -LiteralPath (Join-Path $session 'PRE-MEM1.bin')) -or
         -not (Test-Path -LiteralPath (Join-Path $session 'PRE-MEM2.bin')))) {
        Stop-Private 'POST requires a preserved PRE pair'
    }

    # Compare the exported source hashes before and after both copies to
    # catch a GUI overwrite/resume racing the copy. Not proof of guest-frame
    # atomicity; operator must keep the GUI paused throughout both exports.
    $before1 = (Get-FileHash -LiteralPath $src1 -Algorithm SHA256).Hash
    $before2 = (Get-FileHash -LiteralPath $src2 -Algorithm SHA256).Hash
    foreach ($pair in @(@($src1,$dst1), @($src2,$dst2))) {
        $inputStream = [IO.File]::Open($pair[0], [IO.FileMode]::Open,
                                        [IO.FileAccess]::Read, [IO.FileShare]::Read)
        try {
            $outputStream = [IO.File]::Open($pair[1], [IO.FileMode]::CreateNew,
                                             [IO.FileAccess]::Write, [IO.FileShare]::None)
            try {
                $inputStream.CopyTo($outputStream)
                $outputStream.Flush()
            } finally { $outputStream.Dispose() }
        } finally { $inputStream.Dispose() }
    }
    if ((Get-Item -LiteralPath $dst1).Length -ne 24MB -or
        (Get-Item -LiteralPath $dst2).Length -ne 64MB) {
        Stop-Private 'preserved native bank size changed'
    }
    $after1 = (Get-FileHash -LiteralPath $src1 -Algorithm SHA256).Hash
    $after2 = (Get-FileHash -LiteralPath $src2 -Algorithm SHA256).Hash
    $saved1 = (Get-FileHash -LiteralPath $dst1 -Algorithm SHA256).Hash
    $saved2 = (Get-FileHash -LiteralPath $dst2 -Algorithm SHA256).Hash
    if ($before1 -cne $after1 -or $before2 -cne $after2 -or
        $before1 -cne $saved1 -or $before2 -cne $saved2) {
        Stop-Private 'source changed during export preservation'
    }
    Write-Output "$Phase pair preserved privately: native sizes, source hashes and exclusive destination verified. No private values printed."
}
catch {
    Stop-Private 'file validation, snapshot copy or hash check failed; preserve any partial pair for inspection'
}
