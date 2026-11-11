# Windows PowerShell 5.1. Existing ORIGINAL source-gated 14-bank archive only.
# No Dolphin/controller, shots, RAM writes, raw exports, or uploads.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ReviewedHead,
    [string]$Archive
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$actual = (& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $ReviewedHead) {
    throw 'ABSTAIN: receiver integration HEAD differs from the explicitly reviewed SHA.'
}
$canonicalPin = '89aa3a2bd3e82532c4051168a466498e7195f596'
$cfgPin = '8696a46a315499f220ee7c87580a21dc99f21462'

if (-not $Archive) {
    $captureRoot = Join-Path (Split-Path $repo -Parent) 'Wii-AI-Golf-Data\captures'
    $candidates = @(Get-ChildItem -LiteralPath $captureRoot -Directory |
        Where-Object {
            $_.Name -like 'p0-new-cohort-*-PRIVATE' -and
            (Test-Path -LiteralPath (Join-Path $_.FullName 'manifest-PRIVATE.json'))
        })
    if ($candidates.Count -ne 1) {
        throw 'ABSTAIN: archive ambiguous; pass exact original folder with -Archive.'
    }
    $Archive = $candidates[0].FullName
}
$Archive = (Resolve-Path -LiteralPath $Archive).Path
$manifest = Join-Path $Archive 'manifest-PRIVATE.json'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw 'ABSTAIN: original private manifest is missing.'
}
$meta = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($meta.kind -ne 'p0-private-numbered-capture-inventory' -or
    $meta.training_approved -ne $false -or
    $meta.human_phase_file_mapping_verified -ne $false) {
    throw 'ABSTAIN: original manifest kind/training/phase provenance unexpected.'
}
$beforeManifest = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw 'ABSTAIN: Python 3 not available.' }
$unique = Get-Date -Format 'yyyyMMddHHmmssffff'
$base = Split-Path $repo -Parent
$srcTree = Join-Path $base ('Wii-AI-Golf-P0-Canonical-Receiver-' + $unique)
$cfgTree = Join-Path $base ('Wii-AI-Golf-P0-CFG-Receiver-' + $unique)
$addedSource = $false
$addedCfg = $false

function Get-PinnedPR([string]$pr,[string]$pin,[string]$tree) {
    & git -C $repo fetch origin ("refs/pull/" + $pr + "/head")
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: pinned PR fetch failed.' }
    $fetched = (& git -C $repo rev-parse FETCH_HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $fetched -ne $pin) {
        throw 'ABSTAIN: PR head moved; review new source before execution.'
    }
    & git -C $repo worktree add --detach $tree $pin
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: could not isolate source worktree.' }
}

try {
    Write-Output '=== VERIFY SOURCE OWNER PINNED #231 ==='
    Get-PinnedPR '231' $canonicalPin $srcTree
    $addedSource = $true
    Write-Output '=== VERIFY INNER CFG OWNER PINNED #254 ==='
    Get-PinnedPR '254' $cfgPin $cfgTree
    $addedCfg = $true

    Push-Location -LiteralPath $repo
    try {
        Write-Output '=== RUN COMPLETELY FABRICATED REGRESSION TESTS ==='
        foreach ($suite in @('test_p0_outer_receiver_argument_source.py',
                            'test_p0_authenticated_receiver_chain_private.py')) {
            & $py.Source -m unittest discover -s tests -p $suite -v
            if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: integration synthetic tests failed.' }
        }
    }
    finally { Pop-Location }
    Push-Location -LiteralPath $cfgTree
    try {
        & $py.Source -m unittest discover -s tests -p 'test_p0_cache_receiver_cfg_mustdef.py' -v
        if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: inner CFG synthetic tests failed.' }
    }
    finally { Pop-Location }

    Write-Output '=== AUTHENTICATE ORIGINAL SOURCE ARCHIVE (14 BANKS) ==='
    & $py.Source -I (Join-Path $srcTree 'scripts\audit_p0_seven_numbered_source_pairs_private.py') --archive $Archive | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: canonical original 14-bank gate failed.' }

    Write-Output '=== APPLY TWO OUTER / TWO INNER SOURCE RECEIVER ANALYSES ==='
    & $py.Source -I (Join-Path $repo 'scripts\audit_p0_authenticated_receiver_chain_private.py') `
        --archive $Archive `
        --canonical-source-scripts (Join-Path $srcTree 'scripts') `
        --cfg-script (Join-Path $cfgTree 'scripts\review_p0_cache_receiver_cfg_mustdef.py')
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: source receiver analysis refused input.' }

    Write-Output '=== RECHECK ORIGINAL 14 BANKS AND MANIFEST ==='
    & $py.Source -I (Join-Path $srcTree 'scripts\audit_p0_seven_numbered_source_pairs_private.py') --archive $Archive | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: original archive changed after analysis.' }
    $afterManifest = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash
    if ($afterManifest -ne $beforeManifest) {
        throw 'ABSTAIN: source manifest changed during this run.'
    }
    Write-Output 'P0_RECEIVER_SOURCE_CHAIN=PASS (STATIC; RUNTIME OBJECT UNVERIFIED)'
}
finally {
    if ($addedCfg) { & git -C $repo worktree remove --force $cfgTree | Out-Null }
    if ($addedSource) { & git -C $repo worktree remove --force $srcTree | Out-Null }
}
