#requires -Version 5.1
# Synthetic/offline validation: only a copied PUBLIC registry, never native RAM.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$subject = Join-Path $repo 'scripts\Export-P0MemoryDocs.ps1'
$registryPath = Join-Path $repo 'research\memory-variables\registry.json'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) (
    'p0docs-synthetic-' + [Guid]::NewGuid().ToString('N'))
$data = Join-Path $testRoot 'Wii-AI-Golf-Data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
if (-not (Test-Path -LiteralPath $subject) -or
    -not (Test-Path -LiteralPath $registryPath)) {
    throw 'Missing public code/registry dependency'
}

function Assert([bool]$condition, [string]$message) {
    if (-not $condition) { throw "SYNTHETIC TEST FAILED: $message" }
}
function Assert-Fail([scriptblock]$action, [string]$message) {
    $failed = $false
    try {
        & $action | Out-Null
    } catch {
        $failed = $true
    }
    if (-not $failed) { throw "SYNTHETIC TEST FAILED: expected rejection: $message" }
}
$source = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
$expectedCount = @($source.variables).Count
$expectedP0 = @($source.variables | Where-Object { $_.priority -eq 'P0' }).Count
Assert ($expectedCount -ge 10) 'public registry count unexpectedly small'

# Positive: read-only metadata export from the same public source schema.
& $subject -RegistryPath $registryPath -DataRoot $data -ReportId 'synthetic-good' | Out-Null
$folder = Join-Path $data 'p0-documentation\synthetic-good'
$csvFile = Join-Path $folder 'p0-variable-matrix.csv'
$mdFile = Join-Path $folder 'p0-evidence-review.md'
$jsonFile = Join-Path $folder 'p0-coverage-summary.json'
Assert (Test-Path -LiteralPath $csvFile) 'missing CSV'
Assert (Test-Path -LiteralPath $mdFile) 'missing Markdown'
Assert (Test-Path -LiteralPath $jsonFile) 'missing JSON'
$csv = @(Import-Csv -LiteralPath $csvFile)
$summary = Get-Content -LiteralPath $jsonFile -Raw -Encoding UTF8 | ConvertFrom-Json
Assert ($csv.Count -eq $expectedCount) 'one row per variable'
Assert ($summary.variable_count -eq $expectedCount) 'source count mismatch'
Assert ($summary.p0_count -eq $expectedP0) 'P0 count mismatch'
Assert ($summary.training_approved_count -eq 0) 'unexpected training promotion'
Assert ($summary.raw_ram_read -eq $false) 'cannot claim private RAM read'
Assert ($summary.allowed_to_publish -eq $false) 'publication must remain blocked'
Assert ((@($csv | Select-Object -ExpandProperty id -Unique)).Count -eq $csv.Count) 'duplicate output IDs'
Assert ((@($csv | Where-Object { $_.eligible_as_input -eq 'True' -or
                                      $_.eligible_as_label -eq 'True' })).Count -eq 0) 'premature train input/label'

$allOutput = (Get-Content -LiteralPath $mdFile -Raw -Encoding UTF8) +
             (Get-Content -LiteralPath $csvFile -Raw -Encoding UTF8) +
             (Get-Content -LiteralPath $jsonFile -Raw -Encoding UTF8)
Assert ($allOutput -notmatch '0x[89][0-9a-fA-F]{7}') 'absolute Wii RAM address leaked'
Assert ($allOutput -notmatch 'bytes_hex|RAW-PRIVATE|\\Wii-AI-Golf-Data\\') 'private payload/path surfaced'
Assert ($allOutput -notmatch '"expression"|"steps"|"root_static_address"') 'native pointer expression surfaced'
Write-Host 'PASS: 1 public-source matrix + private-only report outputs'

# Never overwrite an existing report ID.
Assert-Fail { & $subject -RegistryPath $registryPath -DataRoot $data -ReportId 'synthetic-good' } 'report immutability'
Write-Host 'PASS: existing reports preserved'

# Public registry duplicates or unsafe user-controlled strings are refused.
$duplicate = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$duplicate.variables[1].id = $duplicate.variables[0].id
$badPath = Join-Path $testRoot 'duplicate.json'
$duplicate | ConvertTo-Json -Depth 70 | Set-Content -LiteralPath $badPath -Encoding UTF8
Assert-Fail { & $subject -RegistryPath $badPath -DataRoot $data -ReportId 'dup' } 'duplicate ID'
Write-Host 'PASS: duplicate IDs rejected'

$bad = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$bad.variables[0].training.approved = $true
$badPath = Join-Path $testRoot 'train.json'
$bad | ConvertTo-Json -Depth 70 | Set-Content -LiteralPath $badPath -Encoding UTF8
Assert-Fail { & $subject -RegistryPath $badPath -DataRoot $data -ReportId 'train' } 'premature training approval'
Write-Host 'PASS: training cannot be inferred from source/snapshot data'

$bad = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$bad.variables[0].status = 'verified_100_percent'
$badPath = Join-Path $testRoot 'status.json'
$bad | ConvertTo-Json -Depth 70 | Set-Content -LiteralPath $badPath -Encoding UTF8
Assert-Fail { & $subject -RegistryPath $badPath -DataRoot $data -ReportId 'status' } 'unreviewed status'
Write-Host 'PASS: unsupported confidence claim rejected'

$bad = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$bad.variables[0].game.disc_revision = 0
$badPath = Join-Path $testRoot 'revision.json'
$bad | ConvertTo-Json -Depth 70 | Set-Content -LiteralPath $badPath -Encoding UTF8
Assert-Fail { & $subject -RegistryPath $badPath -DataRoot $data -ReportId 'revision' } 'wrong disc revision'
Write-Host 'PASS: wrong revision rejected'

Assert-Fail { & $subject -RegistryPath $registryPath -DataRoot $testRoot -ReportId 'outside' } 'wrong output root'
Assert-Fail { & $subject -RegistryPath $registryPath -DataRoot $data -ReportId '../escape' } 'unsafe report ID'
Write-Host 'PASS: private output boundary and traversal guarded'
Write-Host 'SYNTHETIC_P0_DOC_TESTS=PASS'
