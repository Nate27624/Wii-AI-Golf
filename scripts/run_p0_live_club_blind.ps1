#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only manually labeled Wii Sports Golf club selection experiment.
.DESCRIPTION
  Run from detached Git worktree; uses active Felk bridge with ATTACH, or
  separately authorizes Clean Dolphin startup and A/A+B/A MENU navigation.
  The collector never sends input, swings, or writes guest memory.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$OriginalRepo,
  [ValidateRange(1,65535)][int]$BridgePort=55355,
  [ValidateRange(2,4)][int]$SamplesPerWindow=2,
  [ValidateRange(1,8)][int]$BlindWindows=4
)
$ErrorActionPreference='Stop'
try {
  $work=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
  $orig=[IO.Path]::GetFullPath($OriginalRepo)
  if ([string]::Equals($work,$orig,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Do not run against original checkout; detached worktree required.'
  }
  $parent=Split-Path $orig -Parent
  $data=Join-Path $parent 'Wii-AI-Golf-Data\captures'
  $script=Join-Path $work 'scripts\p0_live_club_blind.py'
  $launcher=Join-Path $work 'scripts\launch_golf.py'
  foreach ($p in @($data,$script,$launcher)) {
    if (-not (Test-Path -LiteralPath $p)) {throw ('Missing prerequisite: '+$p)}
  }
  $tcp=New-Object Net.Sockets.TcpClient
  $responsive=$false
  try {
    $ar=$tcp.BeginConnect('127.0.0.1',$BridgePort,$null,$null)
    $responsive=$ar.AsyncWaitHandle.WaitOne(750) -and $tcp.Connected
  } catch {$responsive=$false} finally {$tcp.Dispose()}
  if ($responsive) {
    Write-Host 'Bridge found. ATTACH does NOT reload a savestate or send menu inputs.'
    if ((Read-Host 'Type ATTACH to keep current in-game session') -cne 'ATTACH') {
      throw 'Operator declined attach.'
    }
  } else {
    if (@(Get-Process -Name Dolphin -ErrorAction SilentlyContinue).Count -gt 0) {
      throw 'Dolphin open but bridge unavailable: refusing duplicate launch.'
    }
    $exe=Join-Path $parent 'tools\FelkDolphin-Clean\Dolphin.exe'
    $user=Join-Path $parent 'tools\FelkDolphin-Clean\User'
    $bridge=Join-Path $parent 'tools\mcp_bridge_swing_legacy_eval.py'
    $srcConfig=Join-Path $orig 'research\launch.local.json'
    $srcCatalog=Join-Path $orig 'research\savestates.local.json'
    $config=Join-Path $work 'research\launch.local.json'
    $catalog=Join-Path $work 'research\savestates.local.json'
    foreach ($p in @($exe,$user,$bridge,$srcConfig,$srcCatalog,
                     (Join-Path (Split-Path $exe) 'portable.txt'))) {
      if (-not (Test-Path -LiteralPath $p)) {throw ('Missing Dolphin setup: '+$p)}
    }
    if ((Test-Path -LiteralPath $config) -or (Test-Path -LiteralPath $catalog)) {
      throw 'Existing worktree private configuration: refusing overwrite.'
    }
    Write-Host 'START loads green-pre-start and performs canonical MENU A -> A+B -> A only.'
    if ((Read-Host 'Type START to authorize Dolphin launch and menu') -cne 'START') {
      throw 'Operator declined START.'
    }
    Copy-Item -LiteralPath $srcConfig -Destination $config
    Copy-Item -LiteralPath $srcCatalog -Destination $catalog
    $launchArgs=@('--dolphin',$exe,'--dolphin-user',$user,'--bridge',$bridge,
                  '--config',$config,'--catalog',$catalog,'--profile','green-pre-start',
                  '--port',[string]$BridgePort)
    & py -3 -I $launcher @launchArgs
    if ($LASTEXITCODE -ne 0) {throw 'Clean Dolphin menu navigation failed.'}
  }
  Write-Host ''
  Write-Host 'CLUB STUDY: no A, no swing, no automated input.' -ForegroundColor Cyan
  Write-Host 'D-pad UP/DOWN changes club where permitted. Only list visibly selectable clubs.'
  Write-Host 'If current Hitting the Green mode locks club choice, enter STOP.'
  Write-Host 'Before each HIGH beep, switch to Dolphin and set requested club.'
  Write-Host 'Maintain club through LOW beep. Return to PowerShell for next phase.'
  Write-Host 'AIM0: keep the named club, change aim left/right only.'
  & py -3 -I $script --private-root $data --port $BridgePort `
      --samples-per-window $SamplesPerWindow --blind-windows $BlindWindows --focus-seconds 8
  if ($LASTEXITCODE -ne 0) {throw 'Club study ABSTAINED. Share the final JSON reason.'}
  Write-Host 'Club study complete. Share calibrated and blind JSON.' -ForegroundColor Green
} catch {
  Write-Host ('CLUB STUDY STOP: '+$_.Exception.Message) -ForegroundColor Yellow
  exit 2
}
