#Requires -Version 5.1
<#
.SYNOPSIS
  Human-controlled source-gated A-state calibration and blind challenge.
.DESCRIPTION
  Run from a DETACHED worktree. May attach to the existing bridge WITHOUT
  resetting, or with explicit START approval launch Clean portable Dolphin
  and use the existing green-pre-start A/A+B/A MENU sequence.
  NO controller input, swing, or memory write is performed by the study.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$OriginalRepo,
    [ValidateRange(1,65535)][int]$BridgePort=55355,
    [ValidateRange(2,6)][int]$SamplesPerWindow=3,
    [ValidateRange(1,8)][int]$BlindWindows=4
)
$ErrorActionPreference='Stop'
try {
    $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $original=[IO.Path]::GetFullPath($OriginalRepo)
    if([string]::Equals($root,$original,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Use a detached experiment worktree; original checkout must be preserved.'
    }
    $parent=Split-Path $original -Parent
    $config=Join-Path $root 'research\launch.local.json'
    $catalog=Join-Path $root 'research\savestates.local.json'
    $oldConfig=Join-Path $original 'research\launch.local.json'
    $oldCatalog=Join-Path $original 'research\savestates.local.json'
    $data=Join-Path $parent 'Wii-AI-Golf-Data\captures'
    $script=Join-Path $root 'scripts\p0_live_a_state_blind.py'
    $launch=Join-Path $root 'scripts\launch_golf.py'
    $emu=Join-Path $parent 'tools\FelkDolphin-Clean\Dolphin.exe'
    $user=Join-Path $parent 'tools\FelkDolphin-Clean\User'
    $bridge=Join-Path $parent 'tools\mcp_bridge_swing_legacy_eval.py'
    foreach($f in @($oldConfig,$oldCatalog,$data,$script,$launch)) {
        if(-not(Test-Path -LiteralPath $f)) { throw ('Missing required setup: '+$f) }
    }
    if((Test-Path -LiteralPath $config) -or (Test-Path -LiteralPath $catalog)) {
        throw 'Private config files already present in isolated worktree; refusing overwrite.'
    }
    Copy-Item -LiteralPath $oldConfig -Destination $config
    Copy-Item -LiteralPath $oldCatalog -Destination $catalog
    $responsive=$false
    $tcp=New-Object Net.Sockets.TcpClient
    try {
        $ar=$tcp.BeginConnect('127.0.0.1',$BridgePort,$null,$null)
        $responsive=$ar.AsyncWaitHandle.WaitOne(800) -and $tcp.Connected
    } catch { $responsive=$false } finally { $tcp.Dispose() }
    if($responsive) {
        Write-Host 'Bridge found: ATTACH will NOT reset savestate or send menu A.'
        $consent=Read-Host 'Type ATTACH to reuse your ready-to-hit session; anything else cancels'
        if($consent -cne 'ATTACH') { throw 'Operator declined attach.' }
    } else {
        if(@(Get-Process -Name Dolphin -ErrorAction SilentlyContinue).Count -gt 0) {
            throw 'Dolphin open without bridge: refusing duplicate launch. Fix bridge or close manually.'
        }
        foreach($f in @($emu,$user,$bridge,(Join-Path (Split-Path $emu) 'portable.txt'))) {
            if(-not(Test-Path -LiteralPath $f)) { throw ('Missing clean Dolphin prerequisite: '+$f) }
        }
        Write-Host 'START will restore green-pre-start and automatically send MENU A -> A+B -> A.'
        Write-Host 'This replaces current in-game progress; live study itself sends NO input.'
        $consent=Read-Host 'Type START to authorize startup/menu presses; anything else cancels'
        if($consent -cne 'START') { throw 'Operator declined fresh launch.' }
        $launchArgs=@('--dolphin',$emu,'--dolphin-user',$user,'--bridge',$bridge,
                '--config',$config,'--catalog',$catalog,'--profile','green-pre-start',
                '--port',[string]$BridgePort)
        & py -3 -I $launch @launchArgs
        if($LASTEXITCODE -ne 0) { throw 'Dolphin menu navigation failed.' }
    }
    Write-Host 'Visually verify Hitting the Green / ball ready. NO swing or controller motion.'
    & py -3 -I $script --private-root $data --port $BridgePort --samples-per-window $SamplesPerWindow --blind-windows $BlindWindows
    if($LASTEXITCODE -ne 0) { throw 'Live A-state experiment abstained: review reason and local sealed manifest.' }
    Write-Host 'A-state study completed. Share the final JSON.'
} catch {
    Write-Host ('A-STATE STUDY STOP: '+$_.Exception.Message)
    exit 2
}
