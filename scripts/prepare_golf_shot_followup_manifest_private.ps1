# PRIVATE offline only. Write hash manifest for optional SETTLED and RESULT.
# Do not call Dolphin, pause emulation, export native RAM, or send input.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PrivateDataRoot,
    [Parameter(Mandatory=$true)][string]$SessionFolder,
    [switch]$ConfirmSameDolphinProcess,
    [switch]$ConfirmSameOneShot,
    [switch]$ConfirmBothExportsUnderSamePauseForEachPresentPhase,
    [switch]$ConfirmSettledBallVisiblyStoppedBeforeReset,
    [switch]$ConfirmResultScreenVisible,
    [Nullable[double]]$DisplayedDistance,
    [ValidateSet('feet','yards','meters')][string]$DisplayedUnit
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Private([string]$why) {
    throw "Private shot follow-up manifest stopped: $why. No RAM, hashes or paths printed."
}

if (-not $ConfirmSameDolphinProcess -or -not $ConfirmSameOneShot -or
    -not $ConfirmBothExportsUnderSamePauseForEachPresentPhase) {
    Stop-Private 'operator capture/session attestations missing'
}

try {
    if (-not (Test-Path -LiteralPath $PrivateDataRoot -PathType Container) -or
        -not (Test-Path -LiteralPath $SessionFolder -PathType Container)) {
        Stop-Private 'private Data root / session missing'
    }
    $data = (Resolve-Path -LiteralPath $PrivateDataRoot).ProviderPath
    $session = (Resolve-Path -LiteralPath $SessionFolder).ProviderPath
    if ((Split-Path -Leaf $data) -cne 'Wii-AI-Golf-Data' -or
        -not $session.StartsWith(
            ($data.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar),
            [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Private 'session is outside ignored Data root'
    }
    $walk = Get-Item -LiteralPath $session -Force
    while ($null -ne $walk) {
        if ($walk.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Stop-Private 'private session directory link/junction refused'
        }
        if ([string]::Equals($walk.FullName, $data,
                             [StringComparison]::OrdinalIgnoreCase)) { break }
        $walk = $walk.Parent
    }
    if ($null -eq $walk) { Stop-Private 'private directory ancestry invalid' }
    $canonical = Join-Path $session 'shot-checkpoint-manifest-PRIVATE.json'
    if (-not (Test-Path -LiteralPath $canonical -PathType Leaf)) {
        Stop-Private 'original PRE/POST manifest must already exist'
    }

    $checkpoints = [ordered]@{}
    foreach ($phase in @('SETTLED','RESULT')) {
        $mem1 = Join-Path $session "$phase-MEM1.bin"
        $mem2 = Join-Path $session "$phase-MEM2.bin"
        $has1 = Test-Path -LiteralPath $mem1 -PathType Leaf
        $has2 = Test-Path -LiteralPath $mem2 -PathType Leaf
        if ($has1 -ne $has2) {
            Stop-Private 'optional native phase has only one bank'
        }
        if (-not $has1) { continue }
        $hashes = @{}
        foreach ($bank in @('MEM1', 'MEM2')) {
            $p = Join-Path $session "$phase-$bank.bin"
            $item = Get-Item -LiteralPath $p -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                Stop-Private 'linked native bank refused'
            }
            $size = if ($bank -eq 'MEM1') { 24MB } else { 64MB }
            if ($item.Length -ne $size) {
                Stop-Private 'wrong native bank size'
            }
            $hashes[$bank] = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        if ($phase -eq 'SETTLED') {
            if (-not $ConfirmSettledBallVisiblyStoppedBeforeReset) {
                Stop-Private 'SETTLED ball stop before reset not confirmed'
            }
            $checkpoints.SETTLED = [ordered]@{
                phase_operator_label = 'settled_before_reset'
                operator_reports_gui_paused = $true
                operator_reports_both_exports_same_pause = $true
                operator_reports_ball_visibly_stopped = $true
                operator_reports_no_hole_or_reset_transition = $true
                sha256 = $hashes
            }
        } else {
            if (-not $ConfirmResultScreenVisible) {
                Stop-Private 'RESULT screen not independently confirmed'
            }
            $checkpoints.RESULT = [ordered]@{
                phase_operator_label = 'visible_results_screen'
                operator_reports_gui_paused = $true
                operator_reports_both_exports_same_pause = $true
                operator_reports_result_screen_visible = $true
                sha256 = $hashes
            }
        }
    }
    if ($checkpoints.Count -eq 0) {
        Stop-Private 'no SETTLED or RESULT banks to report'
    }
    $reading = $null
    if ($PSBoundParameters.ContainsKey('DisplayedDistance') -or
        $PSBoundParameters.ContainsKey('DisplayedUnit')) {
        if (-not $PSBoundParameters.ContainsKey('DisplayedDistance') -or
            -not $PSBoundParameters.ContainsKey('DisplayedUnit') -or
            -not $checkpoints.Contains('RESULT')) {
            Stop-Private 'human distance requires actual RESULT and explicit unit'
        }
        $n = $DisplayedDistance.Value
        if ([double]::IsNaN($n) -or [double]::IsInfinity($n) -or
            $n -lt 0 -or $n -gt 10000) {
            Stop-Private 'human displayed distance out of bounds'
        }
        $reading = [ordered]@{ value = $n; unit = $DisplayedUnit }
    }
    $manifest = [ordered]@{
        kind = 'local-private-golf-shot-followup'
        schema_version = 1
        operator_reports_same_dolphin_process = $true
        operator_reports_same_one_shot = $true
        checkpoints = $checkpoints
        human_displayed_result_distance = $reading
    }
    $output = Join-Path $session 'shot-followup-manifest-PRIVATE.json'
    if (Test-Path -LiteralPath $output) {
        Stop-Private 'follow-up manifest already exists; preserve original'
    }
    $json = $manifest | ConvertTo-Json -Depth 8
    $stream = [IO.File]::Open($output, [IO.FileMode]::CreateNew,
                             [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
        try {
            $writer.Write($json)
            $writer.Flush()
        } finally { $writer.Dispose() }
    } finally { $stream.Dispose() }
    Write-Output 'Private optional SETTLED/RESULT SHA manifest recorded. No RAM, hashes, paths or UI numbers printed.'
} catch {
    Stop-Private 'native file, consent, SHA or exclusive manifest preparation failed'
}
