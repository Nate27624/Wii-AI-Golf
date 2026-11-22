# Restore/generate the 94-tree PRIVATE JSON from the original source-qualified
# seven-phase capture. Never invent coordinates or commit private game data.
# Usage from PR #432: powershell -NoProfile -ExecutionPolicy Bypass -File
#                      scripts/bootstrap_inspector_private_trees.ps1
[CmdletBinding()]
param(
    [string]$PrivateData = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data',
    [switch]$SelfTest
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
$register = Join-Path $viewer 'scripts\register_inspector_private_tree.py'

function Test-InGitCheckout([string]$FileOrDirectory) {
    # The inspector loader rejects all ancestor Git checkouts, not just
    # the immediate private Data directory. Match that rule before registration.
    $cursor = (Resolve-Path -LiteralPath $FileOrDirectory).Path
    if (Test-Path -LiteralPath $cursor -PathType Leaf) {
        $cursor = Split-Path -Parent $cursor
    }
    while ($cursor) {
        if (Test-Path -LiteralPath (Join-Path $cursor '.git')) { return $true }
        $parent = Split-Path -Parent $cursor
        if (-not $parent -or $parent -eq $cursor) { break }
        $cursor = $parent
    }
    return $false
}

function Get-InspectorTreePath([string]$source) {
    # A previous source exporter could create a valid JSON inside a Git
    # checkout's ignored Data/derived. That does NOT satisfy the strict
    # inspector's outside-Git rule. Preserve the original and copy it out.
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing PRIVATE source tree JSON: $source"
    }
    $sourceItem = Get-Item -LiteralPath $source -Force
    if ($sourceItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Linked PRIVATE tree JSON refused'
    }
    if ($sourceItem.Length -lt 1 -or $sourceItem.Length -gt 65536) {
        throw 'PRIVATE tree JSON outside safe 64 KiB bound'
    }
    if (-not (Test-InGitCheckout $source)) { return $source }

    # Known original layout:
    #   D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\derived\... (inside .git)
    # Correct private sibling:
    #   D:\Projects\Wii-AI-Golf-Data\derived\... (outside .git)
    $projectParent = Split-Path -Parent $PrivateData
    $projectRoot = Split-Path -Parent $projectParent
    if (-not $projectRoot) { throw 'Unable to choose a private sibling outside Git' }
    $targetRoot = Join-Path $projectRoot 'Wii-AI-Golf-Data'
    $targetDir = Join-Path $targetRoot 'derived'
    if (-not (Test-Path -LiteralPath $targetRoot)) {
        New-Item -ItemType Directory -Path $targetRoot -ErrorAction Stop | Out-Null
    }
    if (-not (Test-Path -LiteralPath $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -ErrorAction Stop | Out-Null
    }
    foreach ($dir in @($targetRoot, $targetDir)) {
        $item = Get-Item -LiteralPath $dir -Force
        if (-not $item.PSIsContainer -or
            ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Private tree destination directory is linked or invalid: $dir"
        }
    }
    if (Test-InGitCheckout $targetDir) {
        throw "Private tree destination is still inside Git: $targetDir"
    }

    $target = Join-Path $targetDir $fileName
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
            throw "PRIVATE tree destination exists but is not a file: $target"
        }
        $targetItem = Get-Item -LiteralPath $target -Force
        if ($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw 'Existing PRIVATE destination is linked'
        }
        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        if ($sourceHash -ne $targetHash) {
            throw "PRIVATE tree JSON at safe destination differs. Refusing overwrite: $target"
        }
        Write-Host "Matching PRIVATE tree JSON already outside Git: $target" -ForegroundColor Green
    } else {
        # Never overwrite; preserves both original research artifact and any
        # previously generated private file. No JSON contents go to stdout/Git.
        [System.IO.File]::Copy($source, $target, $false)
        Write-Host "Copied PRIVATE tree JSON outside Git: $target" -ForegroundColor Green
    }
    return $target
}

function Register-TreeJson {
    $safeTreePath = Get-InspectorTreePath $destination
    & py -3 -I $register --file $safeTreePath
    if ($LASTEXITCODE -ne 0) { throw 'Failed to validate/save the source-94 JSON path into inspector settings' }
    & py -3 -I $diagnose
    if ($LASTEXITCODE -ne 0) { throw 'Inspector diagnostic failed' }
}

function Assert-GitSuccess([string]$stage) {
    if ($LASTEXITCODE -ne 0) { throw "Git failure during $stage (exit $LASTEXITCODE)" }
}

if ($SelfTest) {
    # Offline synthetic Windows regression: copy a private-named file from
    # ignored data INSIDE a Git checkout to a safe sibling without overwrite.
    # Never reads game data and never launches Dolphin.
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
        'wii-tree-bootstrap-' + [System.IO.Path]::GetRandomFileName())
    try {
        $project = Join-Path $tempRoot 'Wii Golf AI'
        $PrivateData = Join-Path $project 'Wii-AI-Golf-Data'
        $derived = Join-Path $PrivateData 'derived'
        New-Item -ItemType Directory -Path $derived -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $project '.git') -Force | Out-Null
        $original = Join-Path $derived $fileName
        [System.IO.File]::WriteAllText($original, '{"synthetic":true}')
        if (-not (Test-InGitCheckout $original)) {
            throw 'BOOTSTRAP_SELFTEST_FAIL: git ancestor was not detected'
        }
        $outside = Get-InspectorTreePath $original
        if (-not (Test-Path -LiteralPath $outside -PathType Leaf) -or
            (Test-InGitCheckout $outside) -or
            $outside -eq $original -or
            (Get-FileHash -LiteralPath $outside -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash) {
            throw 'BOOTSTRAP_SELFTEST_FAIL: safe copy/hash/outside-git validation failed'
        }
        if ((Get-InspectorTreePath $original) -ne $outside) {
            throw 'BOOTSTRAP_SELFTEST_FAIL: duplicate copy was not idempotent'
        }
        [System.IO.File]::WriteAllText($outside, '{"different":true}')
        $refused = $false
        try {
            $null = Get-InspectorTreePath $original
        } catch {
            $refused = $_.Exception.Message -like '*Refusing overwrite*'
        }
        if (-not $refused) {
            throw 'BOOTSTRAP_SELFTEST_FAIL: conflicting private JSON would overwrite existing'
        }
        Write-Host 'BOOTSTRAP_PRIVATE_JSON_OUTSIDE_GIT_SYNTHETIC_PASS' -ForegroundColor Green
        return
    } finally {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $viewer 'scripts\p0_memory_inspector.py') -PathType Leaf)) {
    throw "This script must be run from a PR #432 inspector checkout: $viewer"
}
if (-not (Test-Path -LiteralPath $PrivateData -PathType Container)) {
    throw "Original PRIVATE Data folder is missing: $PrivateData. Cannot reconstruct original tree coordinates without the original capture."
}
if (Test-Path -LiteralPath $destination -PathType Leaf) {
    Write-Host "PRIVATE tree JSON already exists: $destination" -ForegroundColor Green
    Write-Host 'Validating and registering existing file (never overwritten)...'
    Register-TreeJson
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

Write-Host 'Validating/remembering the source JSON for automatic startup:' -ForegroundColor Cyan
Register-TreeJson
Write-Host 'Restart the inspector. The tree JSON should now auto-load; rendering still requires a source-qualified sample.' -ForegroundColor Green
