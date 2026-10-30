#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only operator-controlled B0/B1/A0 memory-candidate comparison.
.DESCRIPTION
  Run from current checkout or any directory. Does NOT download anything,
  start Dolphin, send input, reset savestates, dump memory or upload evidence.
  The existing local Felk bridge must already be running.
#>
[CmdletBinding()]
param([ValidateRange(1,65535)][int]$BridgePort=55355)
$ErrorActionPreference = 'Stop'
try {
    $repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $script = Join-Path $PSScriptRoot 'p0_live_no_contact_compare.py'
    if (-not [IO.File]::Exists($script) -or
        -not [IO.File]::Exists((Join-Path $repo 'src\wii_ai_golf\integration\rpc.py'))) {
        throw 'Repository experiment files are missing. Update your checkout with git pull --ff-only.'
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        $exe = $py.Source
        $prefix = @('-3','-I')
    } else {
        $python = Get-Command python -ErrorAction Stop
        $exe = $python.Source
        $prefix = @('-I')
    }
    Write-Host 'P0 read-only synthetic self-test (no Dolphin):'
    & $exe @prefix $script --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic self-test failed.' }
    Write-Host 'Dolphin must ALREADY be running RSPE01 Rev1 Hitting-the-Green with the Felk bridge on loopback.'
    Write-Host 'This experiment sends NO inputs. Keep the game idle for B0/B1; aim manually only during A0.'
    & $exe @prefix $script --port $BridgePort
    if ($LASTEXITCODE -ne 0) { throw 'Experiment abstained: check already-running Felk bridge, scene, or source identity.' }
    Write-Host 'Done. Paste ONLY the sanitized JSON summary. Do not post game RAM or logs.'
} catch {
    Write-Host ('P0 EXPERIMENT STOP: ' + $_.Exception.Message)
    exit 2
}
