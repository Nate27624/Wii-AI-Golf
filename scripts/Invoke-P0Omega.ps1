# Windows PowerShell 5.1/7 P0 OMEGA: review-pinned, local-only, read-only.
# Fetch and run from a separate, detached clean worktree. This launcher
# MUST NOT silently execute an unreviewed moving GitHub PR head.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ReviewedHead,
    [string]$Archive
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$actual = (& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $ReviewedHead) {
    throw 'ABSTAIN: omega source HEAD does not equal explicit reviewed source commit.'
}

$pyCommand = Get-Command 'py' -ErrorAction SilentlyContinue
if ($null -ne $pyCommand) {
    $python = $pyCommand.Source
    $prefix = @('-3')
}
else {
    $pyCommand = Get-Command 'python' -ErrorAction SilentlyContinue
    if ($null -eq $pyCommand) { throw 'ABSTAIN: Python 3 was not found.' }
    $python = $pyCommand.Source
    $prefix = @()
}

$omega = Join-Path $repo 'scripts\omega_p0_offline_private.py'
$commandArgs = @('-I', $omega, '--repo', $repo)
if ($Archive) {
    $commandArgs += @('--archive', $Archive)
}

Write-Output '=== P0 OMEGA: IMMUTABLE SOURCE PINS + ORIGINAL 14-BANK VALIDATION ==='
& $python @prefix @commandArgs
if ($LASTEXITCODE -ne 0) {
    throw 'ABSTAIN: Omega native source or original archive checks refused input.'
}
