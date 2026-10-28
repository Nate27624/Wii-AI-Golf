# PRIVATE, OFFLINE ONLY. Prepare the typed local shot-pair manifest
# after the operator has independently completed a reviewed PRE/POST export.
# Never launches Dolphin, sends input, pauses emulation, or exports memory.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PrivateDataRoot,
    [Parameter(Mandatory = $true)][string]$SessionFolder,
    [switch]$ConfirmSameDolphinProcess,
    [switch]$ConfirmExactlyOneShot,
    [switch]$ConfirmVisibleBallDisplacementBeforeReset,
    [switch]$ConfirmNoHoleResetOrTransition,
    [switch]$ConfirmBothMemBanksExportedUnderEachSamePause,
    [switch]$ConfirmGameRanBetweenPhases
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Stop-Redacted([string]$reason) {
    throw "Private shot manifest stopped: $reason. No private path or hash disclosed."
}

$required = @(
    $ConfirmSameDolphinProcess,
    $ConfirmExactlyOneShot,
    $ConfirmVisibleBallDisplacementBeforeReset,
    $ConfirmNoHoleResetOrTransition,
    $ConfirmBothMemBanksExportedUnderEachSamePause,
    $ConfirmGameRanBetweenPhases
)
foreach ($confirmation in $required) {
    if (-not [bool]$confirmation) {
        Stop-Redacted 'explicit operator observation missing'
    }
}

try {
    if (-not (Test-Path -LiteralPath $PrivateDataRoot -PathType Container) -or
        -not (Test-Path -LiteralPath $SessionFolder -PathType Container)) {
        Stop-Redacted 'ignored private Data root or session folder missing'
    }
    $dataRoot = (Resolve-Path -LiteralPath $PrivateDataRoot).ProviderPath
    $session = (Resolve-Path -LiteralPath $SessionFolder).ProviderPath
    $rootItem = Get-Item -LiteralPath $dataRoot -Force
    $sessionItem = Get-Item -LiteralPath $session -Force
    if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        ($sessionItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Stop-Redacted 'reparse point / linked folder not allowed'
    }
    $prefix = $dataRoot.TrimEnd([IO.Path]::DirectorySeparatorChar,
                                 [IO.Path]::AltDirectorySeparatorChar) +
                                 [IO.Path]::DirectorySeparatorChar
    if (-not $session.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Redacted 'session folder is outside ignored Data root'
    }
    if (-not $dataRoot.EndsWith('Wii-AI-Golf-Data',
            [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Redacted 'unexpected private Data root'
    }
    # Do not follow an intermediate directory junction out of the Data root.
    $walk = Get-Item -LiteralPath $session -Force
    while ($null -ne $walk) {
        if ($walk.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Stop-Redacted 'linked private session ancestor refused'
        }
        if ([string]::Equals($walk.FullName, $dataRoot,
                             [StringComparison]::OrdinalIgnoreCase)) { break }
        $walk = $walk.Parent
    }
    if ($null -eq $walk) { Stop-Redacted 'private session ancestry invalid' }

    $hashes = @{}
    foreach ($phase in @('PRE', 'POST')) {
        $bankHashes = @{}
        foreach ($bank in @('MEM1', 'MEM2')) {
            $file = Join-Path $session "$phase-$bank.bin"
            if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
                Stop-Redacted 'missing native bank'
            }
            $fi = Get-Item -LiteralPath $file -Force
            if ($fi.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                Stop-Redacted 'linked native bank rejected'
            }
            $expectedSize = if ($bank -eq 'MEM1') { 24MB } else { 64MB }
            if ($fi.Length -ne $expectedSize) {
                Stop-Redacted 'native bank wrong size'
            }
            $bankHashes[$bank] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        $hashes[$phase] = $bankHashes
    }
    $manifest = [ordered]@{
        kind = 'local-private-golf-prepost-paired-checkpoints'
        schema_version = 1
        operator_reports_same_dolphin_process = $true
        operator_reports_exactly_one_shot = $true
        operator_reports_visible_ball_displacement = $true
        operator_reports_no_hole_reset_or_transition = $true
        checkpoints = [ordered]@{
            PRE = [ordered]@{
                phase_operator_label = 'pre_shot_still'
                operator_reports_gui_paused = $true
                operator_reports_mem1_mem2_export_same_pause = $true
                sha256 = $hashes.PRE
            }
            POST = [ordered]@{
                phase_operator_label = 'post_shot_visible_displacement'
                operator_reports_gui_paused = $true
                operator_reports_mem1_mem2_export_same_pause = $true
                operator_reports_game_was_running_between_phases = $true
                sha256 = $hashes.POST
            }
        }
    }

    $manifestFile = Join-Path $session 'shot-checkpoint-manifest-PRIVATE.json'
    if (Test-Path -LiteralPath $manifestFile) {
        Stop-Redacted 'manifest exists; preserve original without overwriting'
    }
    # Materialize JSON before creating a new file: conversion failures
    # cannot leave behind a misleading empty private manifest.
    $manifestJson = $manifest | ConvertTo-Json -Depth 8
    # Exclusive file creation: another process cannot replace an existing
    # private manifest. No raw memory, hashes or absolute paths on stdout.
    $stream = [IO.File]::Open($manifestFile, [IO.FileMode]::CreateNew,
                             [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $writer = [IO.StreamWriter]::new($stream,
            [Text.UTF8Encoding]::new($false))
        try {
            $writer.Write($manifestJson)
            $writer.Flush()
        } finally {
            $writer.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
    Write-Output 'Private PRE/POST manifest created and local bank hashes recorded. No private values printed.'
}
catch {
    Stop-Redacted 'private file/size/hash/attestation validation or exclusive write failure'
}
