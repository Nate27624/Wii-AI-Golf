#requires -Version 5.1
<#
.SYNOPSIS
  Offline, sanitized P0 field-status documentation from the S000 registry.
.DESCRIPTION
  Does not read RAM or private JSON, run Dolphin, change registry or publish.
  Outputs append-only Markdown, CSV and JSON in the ignored private Data root.
  A candidate/ACK/human visual report is never promoted to physics/training.
#>
[CmdletBinding()]
param(
    [string]$RegistryPath,
    [string]$DataRoot,
    [string]$ReportId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
    $RegistryPath = Join-Path $repo 'research\memory-variables\registry.json'
}
if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    $DataRoot = Join-Path (Split-Path -Parent $repo) 'Wii-AI-Golf-Data'
}
if ([string]::IsNullOrWhiteSpace($ReportId)) {
    $ReportId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' +
        [Guid]::NewGuid().ToString('N').Substring(0, 8)
}
if ($ReportId -cnotmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,47}$') {
    throw 'Invalid sanitized report ID'
}
if (-not (Test-Path -LiteralPath $RegistryPath -PathType Leaf)) {
    throw 'Registry file missing; obtain reviewed registry branch first'
}
if ((Split-Path -Leaf $DataRoot) -cne 'Wii-AI-Golf-Data') {
    throw 'Output must be in an isolated Wii-AI-Golf-Data root'
}
if (Test-Path -LiteralPath $DataRoot) {
    $rootItem = Get-Item -LiteralPath $DataRoot -Force
    if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Private Data root cannot be a symbolic link or junction'
    }
} else {
    New-Item -ItemType Directory -Path $DataRoot -ErrorAction Stop | Out-Null
}

try {
    $registry = Get-Content -LiteralPath $RegistryPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw 'Unreadable or invalid JSON registry'
}
if ($null -eq $registry -or $registry.schema_version -ne 1 -or
    $registry.kind -cne 'wii-golf-memory-variable-registry') {
    throw 'Unsupported memory registry schema'
}
$variables = @($registry.variables)
if ($variables.Count -eq 0 -or $variables.Count -gt 1000) {
    throw 'Registry record count outside safe range'
}

$validStatus = @('unresolved','source_candidate','snapshot_correlated',
                 'runtime_verified','rejected')
$validKind = @('unresolved','pointer_chain','pointer_chain_hypothesis')
$seen = @{}
$records = [System.Collections.Generic.List[object]]::new()

foreach ($v in $variables) {
    if ($null -eq $v -or $v.id -isnot [string] -or
        $v.id -cnotmatch '^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$') {
        throw 'Registry has unsafe or absent logical variable ID'
    }
    if ($seen.ContainsKey($v.id)) {
        throw 'Duplicate logical variable ID'
    }
    $seen[$v.id] = $true
    if ($v.priority -cnotin @('P0','P1','P2','P3') -or
        $v.status -cnotin $validStatus -or
        $v.memory_locator.kind -cnotin $validKind) {
        throw 'Invalid variable priority/status/locator kind'
    }
    if ($v.game.game_id -cne 'RSPE01' -or
        $v.game.disc_revision -ne 1 -or
        $v.game.endianness -cne 'big') {
        throw 'Wrong game revision or endianness'
    }
    if ($null -eq $v.training -or $v.training.approved -isnot [bool] -or
        $v.training.eligible_as_input -isnot [bool] -or
        $v.training.eligible_as_label -isnot [bool]) {
        throw 'Missing explicit training flags'
    }
    if ($v.training.eligible_as_input -and $v.training.eligible_as_label) {
        throw 'Causal input and outcome label cannot be same field'
    }
    if (-not $v.training.approved -and
        ($v.training.eligible_as_input -or $v.training.eligible_as_label)) {
        throw 'Unapproved variable claimed as feature/label'
    }
    if ($v.training.approved -and
        ($v.status -cne 'runtime_verified' -or
         $v.phase_provenance -cne 'verified_frame_aligned' -or
         [string]::IsNullOrWhiteSpace([string]$v.review.reviewer) -or
         [string]::IsNullOrWhiteSpace([string]$v.review.approved_at) -or
         [string]::IsNullOrWhiteSpace([string]$v.training.validation_artifact) -or
         [string]::IsNullOrWhiteSpace([string]$v.training.dataset_contract))) {
        throw 'Training approval missing runtime/frame/reviewer provenance'
    }
    if ($v.memory_locator.kind -ceq 'unresolved' -and
        ($null -ne $v.memory_locator.expression -or
         @($v.memory_locator.steps).Count -gt 0)) {
        throw 'Unresolved variable has a fabricated resolved locator'
    }
    if ($v.owner -isnot [string] -or
        $v.owner -cnotmatch '^[A-Za-z0-9._/-]{1,32}$' -or
        $v.phase_provenance -isnot [string] -or
        $v.phase_provenance -cnotmatch '^[A-Za-z][A-Za-z0-9_]{0,119}) {
        throw 'Unsafe owner or phase provenance value'
    }
    if ($null -eq $v.evidence -or @($v.evidence.source_urls).Count -eq 0 -or
        $null -eq $v.required_controls) {
        throw 'Missing source evidence or controls'
    }

    $nextGate = switch ($v.status) {
        'unresolved'          { 'Find source-owned locator and motion contrast' }
        'source_candidate'    { 'Test source writer/receiver and control phases' }
        'snapshot_correlated' { 'Independent boot plus falsifying control' }
        'runtime_verified'    { 'Check frame, units, split and S002 training gate' }
        'rejected'            { 'Preserve negative result and do not train' }
    }
    if ($v.phase_provenance -cne 'verified_frame_aligned') {
        $nextGate += '; frame-anchored validation absent'
    }
    $records.Add([PSCustomObject][ordered]@{
        id                 = $v.id
        priority           = $v.priority
        status             = $v.status
        owner              = $v.owner
        locator_kind       = $v.memory_locator.kind
        phase_provenance   = $v.phase_provenance
        source_ref_count   = @($v.evidence.source_urls).Count
        capture_group_count = @($v.evidence.capture_groups).Count
        listed_controls    = @($v.required_controls).Count
        training_approved  = [bool]$v.training.approved
        eligible_as_input  = [bool]$v.training.eligible_as_input
        eligible_as_label  = [bool]$v.training.eligible_as_label
        next_gate          = $nextGate
    })
}

$sorted = @($records | Sort-Object -Property priority, id)
$p0 = @($sorted | Where-Object { $_.priority -ceq 'P0' })
$trainCount = @($sorted | Where-Object { $_.training_approved }).Count
$registryHash = (Get-FileHash -LiteralPath $RegistryPath -Algorithm SHA256).Hash.ToLowerInvariant()
$runRoot = Join-Path (Join-Path $DataRoot 'p0-documentation') $ReportId
if (Test-Path -LiteralPath $runRoot) {
    throw 'Report ID already exists: preserving existing evidence'
}
New-Item -Path $runRoot -ItemType Directory -ErrorAction Stop | Out-Null

$md = [System.Collections.Generic.List[string]]::new()
$md.Add('# P0 Wii Golf memory status — source-registry snapshot')
$md.Add('')
$md.Add('Source: S000 draft registry #205; RSPE01 US Rev1; no live Dolphin analysis in this report.')
$md.Add("Registry SHA256: $registryHash")
$md.Add("Variables: $($sorted.Count); P0: $($p0.Count); training-approved: $trainCount.")
$md.Add('')
$md.Add('## P0 fields and independent validation gates')
$md.Add('')
$md.Add('| Logical variable | Status | Locator type | Phase evidence | Listed controls | Training |')
$md.Add('| --- | --- | --- | --- | ---: | --- |')
foreach ($r in $p0) {
    $train = if ($r.training_approved) { 'APPROVED' } else { 'BLOCKED' }
    $md.Add("| $($r.id) | $($r.status) | $($r.locator_kind) | $($r.phase_provenance) | $($r.listed_controls) | $train |")
}
$md.Add('')
$md.Add('## Next review actions')
$md.Add('')
foreach ($r in $p0) {
    $md.Add("- $($r.id) ($($r.owner)): $($r.next_gate).")
}
$md.Add('')
$md.Add('## Strict evidence boundary')
$md.Add('')
$md.Add('- **P0 source/snapshot candidates are not physical ball XYZ, velocity, measured power or contact.**')
$md.Add('- A human-confirmed hit does not validate exact frame timing, true carry or score.')
$md.Add('- One JSON-associated ball may have been moving/downward; neither the precise JSON nor velocity direction is proven.')
$md.Add('- The existing 100-ft off-green display may be censored; never use it as physical carry.')
$md.Add('- No training on fields without S002 approval, same-shot provenance, units and independent controls.')
$md.Add('- Source records: https://github.com/Nate27624/Wii-AI-Golf/pull/205 and https://github.com/Nate27624/Wii-AI-Golf/pull/154.')
$md.Add('- Existing-shot effect negative: https://github.com/Nate27624/Wii-AI-Golf/pull/197 .')
$md.Add('- This document is generated from public catalog metadata, not actual native Wii RAM.')

$csv = Join-Path $runRoot 'p0-variable-matrix.csv'
$markdown = Join-Path $runRoot 'p0-evidence-review.md'
$json = Join-Path $runRoot 'p0-coverage-summary.json'
$sorted | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
[IO.File]::WriteAllLines($markdown, $md.ToArray(), [Text.UTF8Encoding]::new($false))
$summary = [ordered]@{
    schema_version            = 1
    kind                      = 'p0-memory-documentation-offline'
    game_id                   = 'RSPE01'
    disc_revision             = 1
    registry_sha256           = $registryHash
    source_pr                 = 205
    variable_count            = $sorted.Count
    p0_count                  = $p0.Count
    training_approved_count   = $trainCount
    status_counts             = @{}
    p0_status_counts          = @{}
    runtime_shot_observation  = $false
    physical_ball_xyz_verified = $false
    physical_velocity_verified = $false
    ball_contact_memory_verified = $false
    official_score_memory_verified = $false
    raw_ram_read              = $false
    allowed_to_publish       = $false
}
foreach ($status in $validStatus) {
    $summary.status_counts[$status] = @($sorted | Where-Object { $_.status -ceq $status }).Count
    $summary.p0_status_counts[$status] = @($p0 | Where-Object { $_.status -ceq $status }).Count
}
($summary | ConvertTo-Json -Depth 8) |
    Set-Content -LiteralPath $json -Encoding UTF8

Write-Output "P0_REPORT_ID=$ReportId"
Write-Output "REGISTRY_VARIABLES=$($sorted.Count)"
Write-Output "P0_VARIABLES=$($p0.Count)"
Write-Output "TRAINING_APPROVED=$trainCount"
Write-Output 'MODE=OFFLINE_DOCUMENTATION_ONLY'
Write-Output 'RAW_RAM_READ=False'
Write-Output 'GITHUB_OBSERVATION=NOT_UPLOADED (new adapter requires S000/S002 approval)'
) {
        throw 'Unsafe owner or phase provenance value'
    }
    if ($null -eq $v.evidence -or @($v.evidence.source_urls).Count -eq 0 -or
        $null -eq $v.required_controls) {
        throw 'Missing source evidence or controls'
    }

    $nextGate = switch ($v.status) {
        'unresolved'          { 'Find source-owned locator and motion contrast' }
        'source_candidate'    { 'Test source writer/receiver and control phases' }
        'snapshot_correlated' { 'Independent boot plus falsifying control' }
        'runtime_verified'    { 'Check frame, units, split and S002 training gate' }
        'rejected'            { 'Preserve negative result and do not train' }
    }
    if ($v.phase_provenance -cne 'verified_frame_aligned') {
        $nextGate += '; frame-anchored validation absent'
    }
    $records.Add([PSCustomObject][ordered]@{
        id                 = $v.id
        priority           = $v.priority
        status             = $v.status
        owner              = $v.owner
        locator_kind       = $v.memory_locator.kind
        phase_provenance   = $v.phase_provenance
        source_ref_count   = @($v.evidence.source_urls).Count
        capture_group_count = @($v.evidence.capture_groups).Count
        listed_controls    = @($v.required_controls).Count
        training_approved  = [bool]$v.training.approved
        eligible_as_input  = [bool]$v.training.eligible_as_input
        eligible_as_label  = [bool]$v.training.eligible_as_label
        next_gate          = $nextGate
    })
}

$sorted = @($records | Sort-Object -Property priority, id)
$p0 = @($sorted | Where-Object { $_.priority -ceq 'P0' })
$trainCount = @($sorted | Where-Object { $_.training_approved }).Count
$registryHash = (Get-FileHash -LiteralPath $RegistryPath -Algorithm SHA256).Hash.ToLowerInvariant()
$runRoot = Join-Path (Join-Path $DataRoot 'p0-documentation') $ReportId
if (Test-Path -LiteralPath $runRoot) {
    throw 'Report ID already exists: preserving existing evidence'
}
New-Item -Path $runRoot -ItemType Directory -ErrorAction Stop | Out-Null

$md = [System.Collections.Generic.List[string]]::new()
$md.Add('# P0 Wii Golf memory status — source-registry snapshot')
$md.Add('')
$md.Add('Source: S000 draft registry #205; RSPE01 US Rev1; no live Dolphin analysis in this report.')
$md.Add("Registry SHA256: $registryHash")
$md.Add("Variables: $($sorted.Count); P0: $($p0.Count); training-approved: $trainCount.")
$md.Add('')
$md.Add('## P0 fields and independent validation gates')
$md.Add('')
$md.Add('| Logical variable | Status | Locator type | Phase evidence | Listed controls | Training |')
$md.Add('| --- | --- | --- | --- | ---: | --- |')
foreach ($r in $p0) {
    $train = if ($r.training_approved) { 'APPROVED' } else { 'BLOCKED' }
    $md.Add("| $($r.id) | $($r.status) | $($r.locator_kind) | $($r.phase_provenance) | $($r.listed_controls) | $train |")
}
$md.Add('')
$md.Add('## Next review actions')
$md.Add('')
foreach ($r in $p0) {
    $md.Add("- $($r.id) ($($r.owner)): $($r.next_gate).")
}
$md.Add('')
$md.Add('## Strict evidence boundary')
$md.Add('')
$md.Add('- **P0 source/snapshot candidates are not physical ball XYZ, velocity, measured power or contact.**')
$md.Add('- A human-confirmed hit does not validate exact frame timing, true carry or score.')
$md.Add('- One JSON-associated ball may have been moving/downward; neither the precise JSON nor velocity direction is proven.')
$md.Add('- The existing 100-ft off-green display may be censored; never use it as physical carry.')
$md.Add('- No training on fields without S002 approval, same-shot provenance, units and independent controls.')
$md.Add('- Source records: https://github.com/Nate27624/Wii-AI-Golf/pull/205 and https://github.com/Nate27624/Wii-AI-Golf/pull/154.')
$md.Add('- Existing-shot effect negative: https://github.com/Nate27624/Wii-AI-Golf/pull/197 .')
$md.Add('- This document is generated from public catalog metadata, not actual native Wii RAM.')

$csv = Join-Path $runRoot 'p0-variable-matrix.csv'
$markdown = Join-Path $runRoot 'p0-evidence-review.md'
$json = Join-Path $runRoot 'p0-coverage-summary.json'
$sorted | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
[IO.File]::WriteAllLines($markdown, $md.ToArray(), [Text.UTF8Encoding]::new($false))
$summary = [ordered]@{
    schema_version            = 1
    kind                      = 'p0-memory-documentation-offline'
    game_id                   = 'RSPE01'
    disc_revision             = 1
    registry_sha256           = $registryHash
    source_pr                 = 205
    variable_count            = $sorted.Count
    p0_count                  = $p0.Count
    training_approved_count   = $trainCount
    status_counts             = @{}
    p0_status_counts          = @{}
    runtime_shot_observation  = $false
    physical_ball_xyz_verified = $false
    physical_velocity_verified = $false
    ball_contact_memory_verified = $false
    official_score_memory_verified = $false
    raw_ram_read              = $false
    allowed_to_publish       = $false
}
foreach ($status in $validStatus) {
    $summary.status_counts[$status] = @($sorted | Where-Object { $_.status -ceq $status }).Count
    $summary.p0_status_counts[$status] = @($p0 | Where-Object { $_.status -ceq $status }).Count
}
($summary | ConvertTo-Json -Depth 8) |
    Set-Content -LiteralPath $json -Encoding UTF8

Write-Output "P0_REPORT_ID=$ReportId"
Write-Output "REGISTRY_VARIABLES=$($sorted.Count)"
Write-Output "P0_VARIABLES=$($p0.Count)"
Write-Output "TRAINING_APPROVED=$trainCount"
Write-Output 'MODE=OFFLINE_DOCUMENTATION_ONLY'
Write-Output 'RAW_RAM_READ=False'
Write-Output 'GITHUB_OBSERVATION=NOT_UPLOADED (new adapter requires S000/S002 approval)'
