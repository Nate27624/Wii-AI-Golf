# Restore/generate the 94-tree PRIVATE JSON from the original source-qualified
# seven-phase capture. Never invent coordinates or commit private game data.
# Usage from PR #432: powershell -NoProfile -ExecutionPolicy Bypass -File
#                      scripts/bootstrap_inspector_private_trees.ps1
[CmdletBinding()]
param(
    [string]$PrivateData = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data'
)

$ErrorActionPreference = 'Stop'
$viewer = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sourceName = 'p0-new-cohort-20261028-063011392-955fd483-PRIVATE'
$fileName = 'golf-tree-positions-source-94-PRIVATE.json'
$sourceRepo = 'https://github.com/Nate27624/Wii-AI-Golf/pull/411'
$destination = Join-Path (Join-Path $PrivateData 'derived') $fileName
$archive = Join-Path (Join-Path $PrivateData 'captures') $sourceName
$exporter = Join-Path (Split-Path -Parent $PrivateData) 'Wii-Tree-Exporter-PR411'
$diagnose = Join-Path $viewer 'scripts\diagnose_inspector_tree_loading.py'

function Assert-GitSuccess([string]$stage) {
    if ($LASTEXITCODE -ne 0) { throw "Git failure during $stage (exit $LASTEXITCODE)" }
}

if (-not (Test-Path -LiteralPath (Join-Path $viewer 'scripts\p0_memory_inspector.py') -PathType Leaf)) {
    throw "This script must be run from a PR #432 inspector checkout: $viewer"
}
if (-not (Test-Path -LiteralPath $PrivateData -PathType Container)) {
    throw "Original PRIVATE Data folder is missing: $PrivateData. Cannot reconstruct original tree coordinates without the original capture."
}
if (Test-Path -LiteralPath $destination -PathType Leaf) {
    Write-Host "PRIVATE tree JSON already exists: $destination" -ForegroundColor Green
    Write-Host 'Checking loader status (existing file is never overwritten)...'
    & py -3 -I $diagnose
    if ($LASTEXITCODE -ne 0) { throw 'Inspector diagnostic failed' }
    return
}
if (Test-Path -LiteralPath $destination) {
    throw "The expected output path exists but is not a regular file: $destination"
}
if (-not (Test-Path -LiteralPath $archive -PathType Container) -or
    -not (Test-Path -LiteralPath (Join-Path $archive 'manifest-PRIVATE.json') -PathType Leaf)) {
    Write-Host "Original source archive not found at: $archive" -ForegroundColor Yellow
    $capRoot = Join-Path $PrivateData 'captures'
    if (Test-Path -LiteralPath $capRoot -PathType Container) {
        Write-Host 'Available private capture directory NAMES (not their contents):'
        Get-ChildItem -LiteralPath $capRoot -Directory |
            Select-Object -ExpandProperty Name | Select-Object -First 20
    }
    throw "No verified original capture: cannot generate the exact 94 tree coordinates. Original research exporter is at $sourceRepo."
}

# The exporter derives Data root as the sibling of its checkout. Ensure it
# resolves to precisely the operator's original private root, not a new clone
# path that points at another Data folder.
$root = (Resolve-Path -LiteralPath $PrivateData).Path
if ([System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $exporter) 'Wii-AI-Golf-Data')) -ne
    [System.IO.Path]::GetFullPath($root)) {
    throw 'Exporter placement would point to the wrong private Data root'
}
if (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $PrivateData) '.git')) {
    throw 'Private Data would be inside a Git repository; refused. Do not commit original RAM or vectors.'
}

Write-Host 'Retrieving the separately reviewed, source-verified tree exporter in PR #411...' -ForegroundColor Cyan
& git -C $viewer fetch origin refs/pull/411/head
Assert-GitSuccess 'fetch PR #411'
$treeCommit = (& git -C $viewer rev-parse FETCH_HEAD).Trim()
Assert-GitSuccess 'resolve PR #411'
if ($treeCommit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid PR #411 commit SHA' }

if (Test-Path -LiteralPath $exporter) {
    & git -C $exporter rev-parse --is-inside-work-tree *> $null
    Assert-GitSuccess 'verify existing exporter worktree'
    $changes = @(& git -C $exporter status --porcelain)
    Assert-GitSuccess 'check exporter worktree'
    if ($changes.Count -gt 0) { throw "Exporter worktree has local modifications; not changing it: $exporter" }
    & git -C $exporter switch --detach $treeCommit
    Assert-GitSuccess 'update exporter'
} else {
    & git -C $viewer worktree add --detach $exporter $treeCommit
    Assert-GitSuccess 'create private exporter worktree'
}

$script = Join-Path $exporter 'scripts\p0_tree_position_export_private.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "Original verified source exporter missing at PR #411 head: $script"
}

Write-Host 'Regenerating from original SHA/scene/PPC/94-tree gates (no live Dolphin needed)...' -ForegroundColor Cyan
& py -3 -I $script --archive $archive
if ($LASTEXITCODE -ne 0) {
    throw 'Original tree exporter ABSTAINED: source verification failed, or source archive changed. No fabricated positions were written.'
}
if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
    throw "Exporter did not produce expected PRIVATE JSON at $destination"
}
Write-Host "Original PRIVATE tree JSON generated: $destination" -ForegroundColor Green

Write-Host 'Inspector validation and saved-selection diagnostics:' -ForegroundColor Cyan
& py -3 -I $diagnose
if ($LASTEXITCODE -ne 0) { throw 'Inspector tree diagnostic failed' }
Write-Host 'Restart the inspector. The tree JSON should now auto-load; rendering still requires a source-qualified sample.' -ForegroundColor Green
