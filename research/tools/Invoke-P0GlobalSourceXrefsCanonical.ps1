# P0 S002: canonical archive guard around existing #240 source-global slot XREF.
# Read-only. No Dolphin, RPC, controller, guest writes, game capture or upload.
# Local source revisions are pinned; no shared agent branches are changed.
param(
    [string]$Archive,
    [string]$CanonicalCheckout,
    [switch]$SyntheticOnly
)

$ErrorActionPreference = 'Stop'
$XrefSourcePin = '6b926d88c7a2b69037c9b900662d0a0610124ea9'
$CanonicalPin = '89aa3a2bd3e82532c4051168a466498e7195f596'

function RequireGitSuccess([string]$message) {
    if ($LASTEXITCODE -ne 0) { throw $message }
}

$worktree = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $py) { throw 'Python unavailable. No private files read.' }

Push-Location -LiteralPath $worktree
try {
    Write-Host '=== XREF FABRICATED TESTS ==='
    # Python unittest -v normally writes progress to stderr. Do NOT combine
    # stderr with stdout via 2>&1 under PowerShell 5.1 Stop preference:
    # harmless "... ok" becomes a terminating NativeCommandError.
    & $py.Source -I -B -m unittest discover -s tests -p test_p0_global_ball_source_xrefs_private.py -v
    RequireGitSuccess 'Fabricated xref tests failed. No native read.'
    if ($SyntheticOnly) {
        Write-Host 'P0_GLOBAL_XREF_PS5_SYNTHETIC_ONLY=PASS'
        return
    }

    # This child review branch must not change ANY upstream Python scripts.
    & git -C $worktree merge-base --is-ancestor $XrefSourcePin HEAD
    RequireGitSuccess 'XREF source pin is not an ancestor. Refusing.'
    & git -C $worktree diff --quiet $XrefSourcePin HEAD -- scripts
    RequireGitSuccess 'XREF Python source differs from reviewed pin. Refusing.'
    $dirty = @(& git -C $worktree status --porcelain -- scripts)
    RequireGitSuccess 'Cannot inspect git script source status.'
    if ($dirty.Count -ne 0) { throw 'Worktree Python scripts modified/untracked. Refusing.' }

    if ([string]::IsNullOrWhiteSpace($CanonicalCheckout)) {
        throw 'Supply a separate exact pinned #231 canonical checkout. No native read.'
    }
    $canonical = (Resolve-Path -LiteralPath $CanonicalCheckout -ErrorAction Stop).Path
    $canonicalHead = (& git -C $canonical rev-parse HEAD).Trim()
    RequireGitSuccess 'Cannot inspect canonical checkout.'
    if ($canonicalHead -ne $CanonicalPin) {
        throw 'Canonical #231 checkout SHA differs from pinned original. Refusing.'
    }
    $canonScript = Join-Path $canonical 'scripts\audit_p0_seven_numbered_source_pairs_private.py'
    if (-not (Test-Path -LiteralPath $canonScript -PathType Leaf)) {
        throw 'Pinned canonical source reader absent. Refusing.'
    }
    $canonicalDirty = @(& git -C $canonical status --porcelain -- scripts)
    RequireGitSuccess 'Cannot inspect canonical Python scripts.'
    if ($canonicalDirty.Count -ne 0) { throw 'Canonical reader modified locally. Refusing.' }

    if ([string]::IsNullOrWhiteSpace($Archive)) {
        $captures = Join-Path (Split-Path -Parent $worktree) 'Wii-AI-Golf-Data\captures'
        if (-not (Test-Path -LiteralPath $captures -PathType Container)) {
            throw 'Private archived captures directory not found. No native read.'
        }
        $matches = @(
            Get-ChildItem -LiteralPath $captures -Directory -ErrorAction Stop |
            Where-Object {
                $m = Join-Path $_.FullName 'manifest-PRIVATE.json'
                if (-not (Test-Path -LiteralPath $m -PathType Leaf)) { return $false }
                try {
                    $doc = Get-Content -LiteralPath $m -Raw -Encoding UTF8 | ConvertFrom-Json
                    ($doc.kind -eq 'p0-private-numbered-capture-inventory' -and
                     $doc.capture_count -eq 7 -and
                     $doc.training_approved -eq $false)
                } catch { $false }
            }
        )
        if ($matches.Count -ne 1) {
            throw "Expected precisely one preserved seven-phase archive, found $($matches.Count). No native read."
        }
        $Archive = $matches[0].FullName
    }
    $archivePath = (Resolve-Path -LiteralPath $Archive -ErrorAction Stop).Path
    $manifest = Join-Path $archivePath 'manifest-PRIVATE.json'
    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        throw 'Original manifest absent. No native read.'
    }
    $beforeManifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash

    Write-Host '=== ORIGINAL FOURTEEN-BANK MANIFEST / SOURCE CHECK (BEFORE) ==='
    & $py.Source -I -B $canonScript --archive $archivePath | Out-Null
    RequireGitSuccess 'Canonical pre-read source/SHA check refused.'
    Write-Host 'P0_ORIGINAL_14_BANKS_BEFORE=PASS'

    Write-Host '=== R13 GLOBAL BALL SOURCE SLOT XREF / READ ONLY ==='
    $xrefScript = Join-Path $worktree 'scripts\audit_p0_global_ball_source_xrefs_private.py'
    $nativeJson = @(& $py.Source -I -B $xrefScript --dump-directory $archivePath)
    RequireGitSuccess 'Existing #240 source-global xref refused.'
    if ($nativeJson.Count -eq 0) { throw 'Source-global XREF returned no report.' }
    $report = ($nativeJson -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
    if ($report.kind -ne 'P0-SANITIZED-R13-GLOBAL-BALL-DIRECT-SOURCE-XREFS' -or
        $report.wedge_phases_source_validated -ne 3 -or
        $report.source_global_slot_identical_across_wedge -ne $true -or
        $report.source_code_identical_across_wedge -ne $true -or
        $report.source_selected_geometry_stable_across_wedge -ne $true -or
        $report.training_approved -ne $false -or
        $report.allowed_to_publish -ne $false -or
        $report.real_ball_world_xyz_verified -ne $false -or
        $null -eq $report.static_source_global_slot_xrefs) {
        throw 'XREF output source/safety contract failed. Report withheld.'
    }

    Write-Host '=== ORIGINAL FOURTEEN-BANK MANIFEST / SOURCE CHECK (AFTER) ==='
    & $py.Source -I -B $canonScript --archive $archivePath | Out-Null
    RequireGitSuccess 'Canonical post-read source/SHA check refused.'
    $afterManifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash
    if ($beforeManifestHash -ne $afterManifestHash) {
        throw 'Original archive manifest changed during inspection.'
    }

    Write-Host 'P0_ORIGINAL_14_BANKS_AFTER=PASS'
    Write-Host 'P0_GLOBAL_R13_XREF_CANONICAL_AUDIT=PASS'
    Write-Host '=== SANITIZED CODE UNIT COUNTS ONLY ==='
    $report.static_source_global_slot_xrefs | ConvertTo-Json -Depth 8
    Write-Host 'PHYSICS_XYZ_VELOCITY_RECEIVER_EXECUTION_TRAINING_UNVERIFIED'
} finally {
    Pop-Location
}
