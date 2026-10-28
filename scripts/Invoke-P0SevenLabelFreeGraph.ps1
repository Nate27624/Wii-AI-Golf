# PowerShell 5.1-compatible, offline source-selected seven-capture graph.
# No Dolphin, input, RAM writes, additional shots or network downloads.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Archive
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$manifest = Join-Path $Archive 'manifest-PRIVATE.json'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw 'ABSTAIN: Expected original canonical seven-capture private manifest.'
}
$metadata = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($metadata.kind -ne 'p0-private-numbered-capture-inventory') {
    throw 'ABSTAIN: Manifest is not canonical p0-new-cohort format; do not rewrite original labels or hashes.'
}
$python = Get-Command 'py' -ErrorAction SilentlyContinue
if ($null -eq $python) { $python = Get-Command 'python' -ErrorAction SilentlyContinue }
if ($null -eq $python) {
    throw 'Python launcher not found: install Python 3 or run in configured project environment.'
}

Push-Location -LiteralPath $repo
try {
    Write-Output '=== SYNTHETIC LABEL-FREE GRAPH TESTS (NO GAME BANKS) ==='
    & $python.Source -m unittest discover -s tests -p test_p0_seven_label_free_graph_private.py -v
    if ($LASTEXITCODE -ne 0) { throw 'ABSTAIN: synthetic regression tests failed.' }

    Write-Output '=== ORIGINAL SEVEN CAPTURES: SHA AND REV1 SOURCE GATED ==='
    & $python.Source -I scripts/audit_p0_seven_label_free_graph_private.py --archive $Archive
    if ($LASTEXITCODE -ne 0) {
        throw 'ABSTAIN: original archive SHA/scene/owner/context gate failed.'
    }
    Write-Output '=== LABEL-FREE AUDIT FINISHED; NO PHASE OR TRAINING APPROVAL ==='
}
finally { Pop-Location }
