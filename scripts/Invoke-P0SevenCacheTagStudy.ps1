# Offline-only operator wrapper for PR #242 seven-phase cache tag study.
# Never launches Dolphin or issues RAM/controller writes. Python performs full
# canonical 14-bank manifest SHA check before AND after native read.
param(
    [Parameter(Mandatory=$false)]
    [string]$Archive
)

$ErrorActionPreference = 'Stop'

& {
    $here = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    $captures = Join-Path (Split-Path -Parent $here) 'Wii-AI-Golf-Data\captures'
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -eq $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if ($null -eq $py) { throw 'Python launcher not available. No native RAM read attempted.' }

    if ([string]::IsNullOrWhiteSpace($Archive)) {
        if (-not (Test-Path -LiteralPath $captures -PathType Container)) {
            throw 'Ignored sibling private captures root unavailable. No RAM read attempted.'
        }
        $matching = @(
            Get-ChildItem -LiteralPath $captures -Directory -ErrorAction Stop |
            Where-Object {
                $manifest = Join-Path $_.FullName 'manifest-PRIVATE.json'
                if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { return $false }
                try {
                    $doc = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 |
                        ConvertFrom-Json -ErrorAction Stop
                    ($doc.kind -eq 'p0-private-numbered-capture-inventory' -and
                     $doc.capture_count -eq 7 -and
                     $doc.training_approved -eq $false)
                } catch { $false }
            }
        )
        if ($matching.Count -ne 1) {
            throw "Expected exactly one original private seven-pair archive; found $($matching.Count). No RAM read attempted. Supply -Archive explicitly if needed."
        }
        $Archive = $matching[0].FullName
    }

    Push-Location -LiteralPath $here
    try {
        Write-Host '=== P0 #242: FABRICATED SYNTHETIC TESTS ==='
        & $py.Source -I -B -m unittest discover -s tests -p test_p0_seven_cache_update_tags_private.py -v 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Synthetic test failure. Native RAM will not be read.' }

        Write-Host '=== P0 #242: READ-ONLY CANONICAL SEVEN-PAIR TAG AUDIT ==='
        $json = @(& $py.Source -I -B scripts/audit_p0_seven_cache_update_tags_private.py --archive $Archive)
        if ($LASTEXITCODE -ne 0) { throw 'Native P0 audit abstained. Do not interpret any tag values.' }
        if ($json.Count -eq 0) { throw 'Audit returned no data; abstaining.' }

        $report = ($json -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
        if ($report.kind -ne 'P0-SEVEN-CACHE-CONDITIONAL-TAG-EQUALITY-CONTROLS' -or
            $report.archive_14_banks_sha_gated -ne $true -or
            $report.seven_phase_source_roster_gated -ne $true -or
            $report.training_approved -ne $false -or
            $report.allowed_to_publish -ne $false -or
            @($report.within_shot_edges).Count -ne 4) {
            throw 'Unexpected report shape or gate. Do not interpret.'
        }

        Write-Host 'P0_CACHE_TAG_REAL_SOURCE_AUDIT=PASS'
        Write-Host '=== SANITIZED ONLY: copy the JSON below (never private raw files) ==='
        $report | ConvertTo-Json -Depth 10
    }
    finally {
        Pop-Location
    }
}
