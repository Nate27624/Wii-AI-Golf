#Requires -Version 5.1
<#
.SYNOPSIS
  Guided high-information P0 aim-direction test using existing clean Dolphin.
.DESCRIPTION
  Entrypoint after a separate git worktree checkout from origin/main.
  Copies local private config/catalog into that checkout; launches the audited
  existing green-pre-start A -> A+B -> A menu path (or attaches to a responsive
  already-running bridge). NO A/swing during the experiment itself.
  Does not upload raw candidate values or touch the original Git branch.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$OriginalRepo,
    [ValidateRange(2,12)][int]$SamplesPerPhase=8,
    [ValidateRange(1,65535)][int]$BridgePort=55355
)
$ErrorActionPreference='Stop'
try {
    $checkout=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $original=[IO.Path]::GetFullPath($OriginalRepo)
    if ([string]::Equals($checkout,$original,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Run from isolated experiment worktree, not original checkout.'
    }
    $parent=Split-Path $original -Parent
    $tools=Join-Path $parent 'tools'
    $exe=Join-Path $tools 'FelkDolphin-Clean\Dolphin.exe'
    $user=Join-Path $tools 'FelkDolphin-Clean\User'
    $bridge=Join-Path $tools 'mcp_bridge_swing_legacy_eval.py'
    $catalog=Join-Path $checkout 'research\savestates.local.json'
    $config=Join-Path $checkout 'research\launch.local.json'
    $sourceCatalog=Join-Path $original 'research\savestates.local.json'
    $sourceConfig=Join-Path $original 'research\launch.local.json'
    $data=Join-Path $parent 'Wii-AI-Golf-Data\captures'
    $launcher=Join-Path $checkout 'scripts\launch_golf.py'
    $navigator=Join-Path $checkout 'scripts\launch_hitting_green.py'
    $series=Join-Path $checkout 'scripts\p0_live_directional_aim_series.py'
    foreach($path in @($exe,$user,$bridge,$sourceCatalog,$sourceConfig,$data,$launcher,$navigator,$series)) {
        if(-not (Test-Path -LiteralPath $path)) { throw ('Missing existing prerequisite: '+$path) }
    }
    if (-not (Test-Path -LiteralPath (Join-Path (Split-Path $exe) 'portable.txt'))) {
        throw 'Clean Dolphin must be portable; no launch.'
    }
    if ((Test-Path -LiteralPath $catalog) -or (Test-Path -LiteralPath $config)) {
        throw 'Isolated checkout already contains private config/catalog; refusing overwrite.'
    }
    Copy-Item -LiteralPath $sourceCatalog -Destination $catalog
    Copy-Item -LiteralPath $sourceConfig -Destination $config
    Write-Host 'P0 directional experiment: synthetic self-test; no emulator access.'
    & py -3 -I $series --selftest
    if($LASTEXITCODE -ne 0) { throw 'Synthetic test failed.' }

    # Check only the loopback bridge; never start a duplicate instance.
    $bridgeReady=$false
    $tcp=New-Object System.Net.Sockets.TcpClient
    try {
        $async=$tcp.BeginConnect('127.0.0.1',$BridgePort,$null,$null)
        $bridgeReady=$async.AsyncWaitHandle.WaitOne(750) -and $tcp.Connected
    } catch { $bridgeReady=$false } finally { $tcp.Dispose() }
    if($bridgeReady) {
        Write-Host 'Using existing responsive Felk bridge; restoring existing green-pre-start checkpoint.'
        & py -3 -I $navigator --attach-running --catalog $catalog --profile green-pre-start --port $BridgePort --send-live
    } else {
        $running=@(Get-Process -Name Dolphin -ErrorAction SilentlyContinue)
        if($running.Count -gt 0) {
            Write-Host 'Dolphin is open without a responsive Felk bridge.'
            $answer=Read-Host 'To close it gracefully for fresh launch, type CLOSE (anything else cancels)'
            if($answer -cne 'CLOSE') { throw 'Cancelled. Dolphin left running.' }
            foreach($process in $running) {
                $process.Refresh()
                if(-not $process.HasExited) {
                    if(-not $process.CloseMainWindow()) { throw 'Cannot gracefully close Dolphin.' }
                }
            }
            foreach($process in $running) {
                $process.WaitForExit(30000) | Out-Null
                $process.Refresh()
                if(-not $process.HasExited) { throw 'Dolphin still running: no duplicate launch.' }
            }
        }
        Write-Host 'Launching clean Felk Dolphin, restoring green-pre-start, dispatching A / A+B / A menu only.'
        & py -3 -I $launcher --dolphin $exe --dolphin-user $user --bridge $bridge --config $config --catalog $catalog --profile green-pre-start --port $BridgePort
    }
    if($LASTEXITCODE -ne 0) { throw 'Navigation failed. Did NOT start directional captures.' }

    Write-Host ''
    Write-Host 'Visually verify Hitting the Green and selected ball. No swing or A during study.'
    $ack=Read-Host 'Type READY only when the Hitting the Green aim screen is visible'
    if($ack -cne 'READY') { throw 'No verified operator readiness; no sample.' }
    Write-Host 'Seven conditions: B0 idle, B1 repeat, L1 left, C1 center, R1 right, C2 center, L2 repeat left.'
    Write-Host 'Raw exact 32-bit candidate words stay in private Wii-AI-Golf-Data/captures; only sanitized metrics printed.'
    & py -3 -I $series --private-root $data --port $BridgePort --samples-per-phase $SamplesPerPhase
    if($LASTEXITCODE -ne 0) { throw 'Experiment ABSTAINED; no game/physics label promoted.' }
    Write-Host 'P0 directional test completed. Share only the final sanitized JSON.'
} catch {
    Write-Host ('P0 directional launcher STOP: '+$_.Exception.Message)
    exit 2
}
