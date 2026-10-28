#Requires -Version 5.1
<#
.SYNOPSIS
  Offline, source-relative P0 memory field change matrix on preserved B0-B3 native Wii RAM.
.DESCRIPTION
  Reads only existing, hash-validated private 24 MiB MEM1 and 64 MiB MEM2
  checkpoints. Emits NO raw RAM values, memory addresses, paths or hashes.
  B0-B3 operator labels are NOT independently verified shot phases or frame times.
  Does not launch Dolphin, call RPC, write files or upload evidence.
#>
[CmdletBinding()]
param(
    [string]$PrivateRoot = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-study-20261027-212633',
    [string]$DataRoot = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-P0([bool]$Condition, [string]$Reason) {
    if (-not $Condition) { throw "P0 source-field audit rejected: $Reason" }
}
function Test-P0MemoryRange([uint64]$Address, [int]$Length, [string]$Bank) {
    if ($Length -le 0 -or (($Address % 4) -ne 0)) { return $false }
    if ($Bank -eq 'MEM1') { return ($Address -ge 0x80000000L -and ($Address + $Length) -le 0x81800000L) }
    if ($Bank -eq 'MEM2') { return ($Address -ge 0x90000000L -and ($Address + $Length) -le 0x94000000L) }
    return $false
}
function Read-P0Bytes([hashtable]$Banks, [uint64]$Address, [int]$Count) {
    $which = if (Test-P0MemoryRange $Address $Count 'MEM1') { 'MEM1' } elseif (Test-P0MemoryRange $Address $Count 'MEM2') { 'MEM2' } else { '' }
    Assert-P0 ($which.Length -gt 0) 'read crossed native RAM bank or is unaligned'
    $base = if ($which -eq 'MEM1') { [uint64]0x80000000L } else { [uint64]0x90000000L }
    $file = [System.IO.FileStream]$Banks[$which]
    [void]$file.Seek([int64]($Address - $base), [System.IO.SeekOrigin]::Begin)
    $bytes = New-Object byte[] $Count
    $read = $file.Read($bytes, 0, $Count)
    Assert-P0 ($read -eq $Count) 'truncated native bank read'
    return ,$bytes
}
function Read-P0U32([hashtable]$Banks, [uint64]$Address) {
    [byte[]]$v = Read-P0Bytes $Banks $Address 4
    return [uint32](([uint64]$v[0] -shl 24) -bor ([uint64]$v[1] -shl 16) -bor ([uint64]$v[2] -shl 8) -bor [uint64]$v[3])
}
function Read-P0Words([hashtable]$Banks, [uint64]$Address, [int]$Count) {
    Assert-P0 ($Count -ge 1 -and $Count -le 4) 'unexpected field component count'
    $out = @()
    for ($i = 0; $i -lt $Count; $i++) { $out += [uint32](Read-P0U32 $Banks ($Address + 4 * $i)) }
    return ,([uint32[]]$out)
}
function Assert-P0FloatWords([uint32[]]$Words) {
    foreach ($word in $Words) {
        $f = [BitConverter]::ToSingle([BitConverter]::GetBytes($word), 0)
        Assert-P0 (-not [float]::IsNaN($f) -and -not [float]::IsInfinity($f) -and [Math]::Abs([double]$f) -le 100000.0) 'non-finite/out-of-range candidate floating word'
    }
}
function Test-P0ExistingRealDirectory([string]$Path) {
    Assert-P0 (Test-Path -LiteralPath $Path -PathType Container) 'private directory not found'
    $item = Get-Item -LiteralPath $Path -Force
    Assert-P0 (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'linked private directory rejected'
    return $item.FullName.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
}
function Get-P0Snapshot([hashtable]$Banks) {
    [byte[]]$disc = Read-P0Bytes $Banks ([uint64]0x80000000L) 8
    Assert-P0 ([Text.Encoding]::ASCII.GetString($disc, 0, 6) -ceq 'RSPE01' -and $disc[7] -eq 1) 'wrong disc ID/revision'
    $sceneMgr = Read-P0U32 $Banks ([uint64]0x804BF4D8L)
    Assert-P0 ((Test-P0MemoryRange $sceneMgr 0x20 'MEM1') -and (Read-P0U32 $Banks ([uint64]0x804BF4DCL)) -eq 0) 'invalid scene manager static gate'
    $scene = Read-P0U32 $Banks ($sceneMgr + 0x0C)
    Assert-P0 (Test-P0MemoryRange $scene 0xA0 'MEM2') 'scene object outside MEM2'
    Assert-P0 ((Read-P0U32 $Banks ($sceneMgr + 0x18)) -eq 5 -and (Read-P0U32 $Banks ($scene + 0x1C)) -eq 5 -and (Read-P0U32 $Banks ($scene + 0x20)) -eq $sceneMgr -and (Read-P0U32 $Banks ($scene + 0x54)) -eq 2) 'not source-gated Golf scene 5 / sport 2'
    $config = Read-P0U32 $Banks ([uint64]0x804BF8C4L)
    Assert-P0 (Test-P0MemoryRange $config 0x9C 'MEM2') 'missing Golf config'
    Assert-P0 ((Read-P0U32 $Banks ($config + 0x94)) -eq 4) 'not Hitting-the-Green mode 4'
    $hole = Read-P0U32 $Banks ($config + 0x98)
    Assert-P0 ($hole -lt 9) 'hole index out of expected bounds'
    $field = Read-P0U32 $Banks ([uint64]0x804BF868L)
    Assert-P0 (Test-P0MemoryRange $field 0xA8 'MEM2') 'missing Golf field manager'
    $pm = Read-P0U32 $Banks ([uint64]0x804BF8D0L)
    Assert-P0 (Test-P0MemoryRange $pm 0x340 'MEM2') 'missing PlayerManager candidate'
    $selected = Read-P0U32 $Banks ($pm + 0x334)
    $indices = @(0..3 | Where-Object { $selected -eq ($pm + 4 + ($_ * 0xCC)) })
    Assert-P0 ($indices.Count -eq 1) 'selected pointer is not a unique 0xCC record'
    $record = [uint64]$selected
    Assert-P0 (Test-P0MemoryRange $record 0xCC 'MEM2') 'selected player record out of range'
    $ball = Read-P0U32 $Banks ($record + 0x88)
    Assert-P0 (Test-P0MemoryRange $ball 0x1AC 'MEM2') 'selected ball-related object outside MEM2'
    # +0x4C is the source-followed translation pointer; it must point to mapped MEM2.
    $ballTrans = Read-P0U32 $Banks ($ball + 0x4C)
    Assert-P0 (Test-P0MemoryRange $ballTrans 12 'MEM2') 'ball-related translation pointer invalid'
    $start = Read-P0U32 $Banks ($field + 0x50)
    Assert-P0 (Test-P0MemoryRange $start 0x50 'MEM2') 'current start object missing'
    $startTrans = Read-P0U32 $Banks ($start + 0x4C)
    Assert-P0 (Test-P0MemoryRange $startTrans 12 'MEM2') 'current start translation invalid'
    Assert-P0 ((Read-P0U32 $Banks ($start + 0x48)) -eq $start + 0x0C -and $startTrans -eq $start + 0x30) 'start object selfref gates failed'
    Assert-P0 ($ballTrans -eq $ball + 0x30) 'selected ball-related translation selfref mismatch'

    $words = [ordered]@{}
    $words['golf.player.selected_record.initial_position_candidate'] = Read-P0Words $Banks ($record + 0x54) 3
    $words['golf.player.selected_record.start_copy_candidate'] = Read-P0Words $Banks ($record + 0x60) 3
    $words['golf.ball_object.current_translation_candidate'] = Read-P0Words $Banks $ballTrans 3
    $words['golf.ball_object.initialized_cache_cc'] = Read-P0Words $Banks ($ball + 0xCC) 3
    $words['golf.ball_object.conditional_cache_f0'] = Read-P0Words $Banks ($ball + 0xF0) 3
    $words['golf.ball_object.conditional_cache_fc'] = Read-P0Words $Banks ($ball + 0xFC) 3
    $words['golf.player.selected_record.aim_rotation'] = Read-P0Words $Banks ($record + 0x3C) 1
    $words['golf.player.selected_record.aim_transform_matrix_candidate'] = Read-P0Words $Banks ($record + 0x40) 4
    $words['golf.tee_start.map_translation_xyz'] = Read-P0Words $Banks $startTrans 3
    $pin = Read-P0U32 $Banks ($field + 0x44)
    Assert-P0 (Test-P0MemoryRange $pin 0x50 'MEM2') 'current pin object missing'
    Assert-P0 ((Read-P0U32 $Banks ($pin + 0x4C)) -eq $pin + 0x30) 'pin translation selfref invalid'
    $words['golf.pin.map_translation_xyz'] = Read-P0Words $Banks ($pin + 0x30) 3
    $cup = Read-P0U32 $Banks ($field + 0x54)
    Assert-P0 (Test-P0MemoryRange $cup 0x3C 'MEM2') 'cup object missing'
    # Cup inherited Base offset is a *hypothesis*, independently falsifiable.
    $words['golf.cup.map_translation_xyz'] = Read-P0Words $Banks ($cup + 0x30) 3
    foreach ($name in $words.Keys) { Assert-P0FloatWords ([uint32[]]$words[$name]) }
    return [pscustomobject]@{
        Identity = @([uint64]$sceneMgr, [uint64]$scene, [uint64]$config, [uint64]$field, [uint64]$pm, [uint64]$record, [uint64]$ball, [uint64]$ballTrans, [uint64]$start, [uint64]$startTrans, [uint64]$pin, [uint64]$cup, [uint64]$hole, [uint64]$indices[0])
        Words = $words
    }
}
function Get-P0ComponentDifference([uint32[]]$Left, [uint32[]]$Right) {
    Assert-P0 ($Left.Count -eq $Right.Count) 'field component lengths inconsistent'
    $changed = 0
    for ($j = 0; $j -lt $Left.Count; $j++) { if ($Left[$j] -ne $Right[$j]) { $changed++ } }
    return $changed
}

try {
    $privateBase = Test-P0ExistingRealDirectory $DataRoot
    Assert-P0 ([IO.Path]::GetFileName($privateBase) -ceq 'Wii-AI-Golf-Data') 'DataRoot must be named Wii-AI-Golf-Data'
    $session = Test-P0ExistingRealDirectory $PrivateRoot
    Assert-P0 ($session.StartsWith($privateBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) 'session must be below private Data root'
    $manifestPath = Join-Path $session 'checkpoint-manifest-PRIVATE.json'
    Assert-P0 (Test-Path -LiteralPath $manifestPath -PathType Leaf) 'missing private checkpoint manifest'
    $manifestFile = Get-Item -LiteralPath $manifestPath -Force
    Assert-P0 ((($manifestFile.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) -and $manifestFile.Length -le 1048576) 'unsafe manifest'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-P0 ($manifest.schema_version -eq 1 -and $manifest.kind -ceq 'local-private-golf-paired-checkpoints') 'unsupported manifest schema'
    $phaseLabels = @('idle_baseline', 'idle_delayed', 'wasd_aim_only', 'idle_after_aim')
    $phases = @('B0','B1','B2','B3')
    $snapshots = @()
    $hashes = @()
    for ($phaseIndex = 0; $phaseIndex -lt $phases.Count; $phaseIndex++) {
        $phase = $phases[$phaseIndex]
        $entry = $manifest.checkpoints.$phase
        Assert-P0 ($null -ne $entry -and $entry.phase_operator_label -ceq $phaseLabels[$phaseIndex] -and $entry.operator_reports_gui_paused -eq $true -and $entry.scene_source_chain_gated -eq $true -and $entry.native_sizes_valid -eq $true -and $entry.observed_game_mode -eq 4) 'incomplete/mislabeled checkpoint provenance'
        $paths = @{}
        $hash = @{}
        foreach ($bank in @('MEM1','MEM2')) {
            $path = Join-Path $session "$phase-$bank.bin"
            Assert-P0 (Test-Path -LiteralPath $path -PathType Leaf) 'missing B0-B3 bank'
            $file = Get-Item -LiteralPath $path -Force
            $length = if ($bank -eq 'MEM1') { 25165824L } else { 67108864L }
            Assert-P0 (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0 -and $file.Length -eq $length) 'unsafe or wrong-sized native bank'
            $digest = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
            Assert-P0 (-not [string]::IsNullOrWhiteSpace($entry.sha256.$bank) -and $digest -ieq $entry.sha256.$bank) 'preserved bank SHA mismatch'
            $hash[$bank] = $digest
            $paths[$bank] = $path
        }
        $streams = @{}
        try {
            foreach ($bank in @('MEM1','MEM2')) {
                $streams[$bank] = [System.IO.File]::Open($paths[$bank], [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
            }
            $snapshots += Get-P0Snapshot $streams
            $hashes += $hash
        } finally {
            foreach ($stream in $streams.Values) { if ($null -ne $stream) { $stream.Dispose() } }
        }
    }
    # Comparisons are meaningful only while selected source objects/slot/hole stay identical.
    for ($i = 1; $i -lt 4; $i++) {
        Assert-P0 ((Get-P0ComponentDifference ([uint64[]]$snapshots[0].Identity) ([uint64[]]$snapshots[$i].Identity)) -eq 0) 'game object identity/selected slot/hole changed; refuse cross-phase comparison'
    }
    $matrix = @()
    foreach ($key in $snapshots[0].Words.Keys) {
        $dims = @((0..2) | ForEach-Object {
            $index = $_
            Get-P0ComponentDifference ([uint32[]]$snapshots[$index].Words[$key]) ([uint32[]]$snapshots[($index + 1)].Words[$key])
        })
        $matrix += [ordered]@{
            registry_id = $key
            changed_components_B0_B1 = [int]$dims[0]
            changed_components_B1_B2 = [int]$dims[1]
            changed_components_B2_B3 = [int]$dims[2]
            source_candidate_not_physics_verified = $true
        }
    }
    $fixed = @('golf.tee_start.map_translation_xyz','golf.pin.map_translation_xyz','golf.cup.map_translation_xyz')
    $fixedStable = @($matrix | Where-Object { $fixed -contains $_.registry_id -and ($_.changed_components_B0_B1 + $_.changed_components_B1_B2 + $_.changed_components_B2_B3) -eq 0 }).Count -eq 3
    $bankDistinct = @()
    for ($i = 0; $i -lt 3; $i++) {
        $bankDistinct += [ordered]@{
            transition = "$($phases[$i])_$($phases[$i+1])"
            MEM1_different = ($hashes[$i].MEM1 -ne $hashes[$i+1].MEM1)
            MEM2_different = ($hashes[$i].MEM2 -ne $hashes[$i+1].MEM2)
        }
    }
    $result = [ordered]@{
        kind = 'P0-SOURCE-FIELD-MATRIX-OFFLINE-SANITIZED-LOCAL'
        schema_version = 1
        game_id = 'RSPE01'
        disc_revision = 1
        declared_mode = 4
        captured_labels = $phases
        capture_provenance = 'operator_labels_only_not_verified_frame_or_shot_phase'
        hash_checks_all_passed = $true
        selected_owner_slot_hole_stable = $true
        fixed_scene_geometry_candidate_unchanged = [bool]$fixedStable
        bank_diff_flags = $bankDistinct
        field_comparisons = $matrix
        actual_ball_world_xyz_verified = $false
        ball_velocity_verified = $false
        ball_contact_verified = $false
        same_shot_frame_join_verified = $false
        training_approved = $false
        github_upload = 'NOT_UPLOADED_unreviewed_private_source_analysis'
    }
    $result | ConvertTo-Json -Depth 7
} catch {
    # Never echo the .NET exception or a private path, raw value, address or hash.
    [Console]::Error.WriteLine('P0 SOURCE FIELD MATRIX: ABORTED. Private inputs rejected; no memory values or paths emitted.')
    exit 2
}