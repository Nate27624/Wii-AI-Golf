#requires -Version 5.1
<#
Offline inspection of seven operator-labeled Wii Sports RAM export checkpoints.
One standalone PS5.1 script. NEVER boots Dolphin, swings, writes to raw inputs,
or uploads bytes, paths, digests, candidate coordinates or game images.
Expected raw naming: 1.1.raw / 1.2.raw ... 7.1.raw / 7.2.raw.
Bank identity is determined from EXACT lengths, NEVER guessed from .1 or .2.
If naming is different: inventory reports that before any analysis.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$DumpDirectory,
    [ValidateSet('Inventory','Analyze')][string]$Mode = 'Analyze'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-RealFile($item) {
    if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw 'Symlinked or non-file raw input refused.'
    }
}
function Assert-Rev1Header([string]$path) {
    $fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $buf=New-Object byte[] 8
        if ($fs.Read($buf,0,8) -ne 8) { throw 'Incomplete MEM1 game header.' }
        $expected=[byte[]]@(82,83,80,69,48,49,0,1)
        for ($n=0;$n -lt 8;$n++) {
            if ($buf[$n] -ne $expected[$n]) { throw 'Wrong RSPE01 Rev1 native MEM1 header; refusing comparisons.' }
        }
    } finally { $fs.Dispose() }
}
function PrivateHash([string]$path) {
    $fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $sha=[Security.Cryptography.SHA256]::Create()
        try { return [BitConverter]::ToString($sha.ComputeHash($fs)).Replace('-','').ToLowerInvariant() }
        finally { $sha.Dispose() }
    } finally { $fs.Dispose() }
}

# The compiled analyzer uses bounded 1 MiB buffers even for 64 MiB banks.
# Bank-relative changed page indices stay ONLY in a local PRIVATE JSON report.
$source = @'
using System;
using System.IO;
using System.Collections.Generic;
public sealed class GolfPageDiff {
  public long ChangedBytes;
  public int ChangedPages;
  public long ComparedBytes;
  public int[] ChangedPageIndices;
  public static GolfPageDiff Compare(string left, string right) {
    const int pageSize = 4096, chunk = 1024 * 1024;
    using (var a = File.Open(left, FileMode.Open, FileAccess.Read, FileShare.Read))
    using (var b = File.Open(right, FileMode.Open, FileAccess.Read, FileShare.Read)) {
      if (a.Length != b.Length) throw new InvalidDataException("BANK_SIZE_CHANGED");
      int[] pageDiff = new int[checked((int)((a.Length+pageSize-1)/pageSize))];
      byte[] x = new byte[chunk], y = new byte[chunk];
      long pos = 0, bad = 0;
      while (pos < a.Length) {
        int target = (int)Math.Min((long)chunk, a.Length-pos);
        int nx = 0, ny = 0;
        while (nx < target) {
          int n = a.Read(x,nx,target-nx);
          if (n <= 0) throw new EndOfStreamException("BANK_A_TRUNCATED");
          nx += n;
        }
        while (ny < target) {
          int n = b.Read(y,ny,target-ny);
          if (n <= 0) throw new EndOfStreamException("BANK_B_TRUNCATED");
          ny += n;
        }
        for (int i=0;i<target;i++) {
          if (x[i]!=y[i]) { bad++; pageDiff[checked((int)((pos+i)/pageSize))]++; }
        }
        pos+=target;
      }
      var pages=new List<int>();
      for (int j=0;j<pageDiff.Length;j++) if(pageDiff[j]>0) pages.Add(j);
      return new GolfPageDiff {
        ChangedBytes=bad, ChangedPages=pages.Count,
        ComparedBytes=a.Length, ChangedPageIndices=pages.ToArray()
      };
    }
  }
}
'@
if (-not ('GolfPageDiff' -as [type])) {
    Add-Type -TypeDefinition $source -ErrorAction Stop | Out-Null
}

$directory = (Resolve-Path -LiteralPath $DumpDirectory -ErrorAction Stop).ProviderPath
$dirInfo = Get-Item -LiteralPath $directory -Force
if (-not $dirInfo.PSIsContainer -or (($dirInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
    throw 'DumpDirectory must be a real private directory (not a link).'
}
$sets = @{}
foreach ($i in 1..7) { $sets[$i] = @{ MEM1=$null; MEM2=$null } }
$unmatched = 0
$invalidSize = 0
$raws = @(Get-ChildItem -LiteralPath $directory -File -Filter '*.raw' -Force)
foreach ($item in $raws) {
    Assert-RealFile $item
    $matched = [regex]::Match($item.Name, '^([1-7])\.([12])\.raw
    $bank = if ($item.Length -eq 25165824) { 'MEM1' }
            elseif ($item.Length -eq 67108864) { 'MEM2' }
            else { $null }
    if (-not $bank) { $invalidSize++; continue }
    if ($null -ne $sets[$phase][$bank]) { throw 'Duplicate native bank for the same operator phase.' }
    $sets[$phase][$bank] = $item.FullName
}

$inventory = foreach ($i in 1..7) {
    [pscustomobject]@{
        Phase=$i
        MEM1_24MiB=[bool]($sets[$i]['MEM1'])
        MEM2_64MiB=[bool]($sets[$i]['MEM2'])
        CompletePair=[bool]($sets[$i]['MEM1'] -and $sets[$i]['MEM2'])
    }
}
Write-Host 'SEVEN-SNAPSHOT INVENTORY (human labels only; files remain PRIVATE)'
$inventory | Format-Table -AutoSize | Out-Host
Write-Host ("Unmatched .raw names: {0}; matched names with wrong sizes: {1}" -f $unmatched,$invalidSize)
if ($Mode -eq 'Inventory') { return }

$comparisons=@(
    [pscustomobject]@{Pair='D1_to_D2_airborne_to_stopped';A=1;B=2},
    [pscustomobject]@{Pair='W5_to_W6_near_apex_to_descending';A=5;B=6},
    [pscustomobject]@{Pair='W6_to_W7_descending_to_flag_result';A=6;B=7},
    [pscustomobject]@{Pair='W5_to_W7_near_apex_to_flag_result';A=5;B=7}
)
$eligible=@($comparisons | Where-Object {
    $sets[$_.A]['MEM1'] -and $sets[$_.A]['MEM2'] -and
    $sets[$_.B]['MEM1'] -and $sets[$_.B]['MEM2']
})
if ($eligible.Count -eq 0) {
    Write-Warning 'NO WITHIN-SHOT NATIVE PAIRS READY. No RAM compared. Confirm actual file names, MEM1/MEM2 lengths, and phase mapping; do not rename originals.'
    Write-Host 'Suggested expected shape: 1.1.raw + 1.2.raw (one 24MiB bank and one 64MiB bank); likewise for each observation.'
    return
}
$uniquePhases=@($eligible | ForEach-Object { $_.A; $_.B } | Sort-Object -Unique)
$metadata=@{}
foreach ($phase in $uniquePhases) {
    $m1=$sets[$phase]['MEM1']; $m2=$sets[$phase]['MEM2']
    Assert-Rev1Header $m1
    foreach ($p in @($m1,$m2)) {
        $file=Get-Item -LiteralPath $p -Force
        Assert-RealFile $file
    }
    # Digests retained in PRIVATE report solely for provenance, never stdout.
    $metadata[[string]$phase]=@{
        phase=$phase; human_label_only=$true; same_guest_frame_verified=$false
        mem1_sha256=PrivateHash $m1; mem2_sha256=PrivateHash $m2
        mem1_bytes=25165824; mem2_bytes=67108864
    }
}
$results=@()
foreach ($pair in $eligible) {
    $bankDeltas=@{}
    foreach ($bank in @('MEM1','MEM2')) {
        $d=[GolfPageDiff]::Compare($sets[$pair.A][$bank],$sets[$pair.B][$bank])
        $bankDeltas[$bank]=@{
            changed_bytes=[long]$d.ChangedBytes
            changed_4096_byte_pages=[int]$d.ChangedPages
            total_compared_bytes=[long]$d.ComparedBytes
            changed_page_indices_private=@($d.ChangedPageIndices)
        }
    }
    $results+=@{
        comparison=$pair.Pair; from_phase=$pair.A; to_phase=$pair.B
        mem1=$bankDeltas['MEM1']; mem2=$bankDeltas['MEM2']
        same_shot_operator_reported=$true
        source_gated_ball_identity_verified=$false
        actual_physical_motion_verified=$false
    }
    Write-Host ("{0}: MEM1 changed {1} pages; MEM2 changed {2} pages (4096 B/page)" -f
        $pair.Pair,$bankDeltas['MEM1'].changed_4096_byte_pages,
        $bankDeltas['MEM2'].changed_4096_byte_pages)
}
# Require bytewise stability of all source banks across the diff pass.
# Dolphin could be writing a dump file while this audit runs; never report
# a completed contrast if any input changed between the two digest passes.
foreach ($phase in $uniquePhases) {
    $key=[string]$phase
    foreach ($bank in @('MEM1','MEM2')) {
        $original = if ($bank -eq 'MEM1') { $metadata[$key].mem1_sha256 }
                    else { $metadata[$key].mem2_sha256 }
        if ((PrivateHash $sets[$phase][$bank]) -ne $original) {
            throw 'A PRIVATE raw memory bank changed while auditing; report not written.'
        }
    }
}
$private = Join-Path $directory ("P0-SEVEN-AUDIT-" + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
    '-' + [guid]::NewGuid().ToString('N').Substring(0,10) + '-PRIVATE')
[void](New-Item -ItemType Directory -Path $private -ErrorAction Stop)
$report=@{
    kind='local-seven-human-labeled-golf-native-bank-delta'
    schema_version=1; created_utc=[DateTime]::UtcNow.ToString('o')
    human_observation_study='S002-SEVEN-HUMAN-DUMPS-01'
    labels=@{
        '1'='driver_midair_power_rising'; '2'='same_driver_ball_stopped'
        '3'='putter_extended_back_a_released'; '4'='driver_medium_back_a_held'
        '5'='wedge_near_apex_camera_change'; '6'='same_wedge_descending'
        '7'='same_wedge_flag_impact_nice_on_15p2ft_ui'
    }
    inventory=@($inventory); unmatched_raw_names_count=$unmatched
    invalid_size_count=$invalidSize; per_phase_native_sha256_private=$metadata
    comparisons=@($results)
    all_bank_pairs_same_guest_frame_verified=$false
    p0_ball_world_xyz_verified=$false; p0_ball_velocity_verified=$false
    p0_power_verified=$false; official_score_memory_verified=$false
    pin_and_camera_confounds_unresolved=$true
    approved_for_model_training=$false; allowed_to_publish=$false
}
$path=Join-Path $private 'report-RAW-PRIVATE.json'
$json=$report | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText($path,$json,[Text.UTF8Encoding]::new($false))
Write-Host ("PRIVATE REPORT WRITTEN; within-shot comparisons completed: {0}; no raw RAM uploaded." -f $results.Count)
Write-Host "No same-guest-frame, ball XYZ, power, score or training claim has been established."
, [Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if (-not $matched.Success) {
        $unmatched++
        continue
    }
    $phase = [int]$matched.Groups[1].Value
    $bank = if ($item.Length -eq 25165824) { 'MEM1' }
            elseif ($item.Length -eq 67108864) { 'MEM2' }
            else { $null }
    if (-not $bank) { $invalidSize++; continue }
    if ($null -ne $sets[$phase][$bank]) { throw 'Duplicate native bank for the same operator phase.' }
    $sets[$phase][$bank] = $item.FullName
}

$inventory = foreach ($i in 1..7) {
    [pscustomobject]@{
        Phase=$i
        MEM1_24MiB=[bool]($sets[$i]['MEM1'])
        MEM2_64MiB=[bool]($sets[$i]['MEM2'])
        CompletePair=[bool]($sets[$i]['MEM1'] -and $sets[$i]['MEM2'])
    }
}
Write-Host 'SEVEN-SNAPSHOT INVENTORY (human labels only; files remain PRIVATE)'
$inventory | Format-Table -AutoSize | Out-Host
Write-Host ("Unmatched .raw names: {0}; matched names with wrong sizes: {1}" -f $unmatched,$invalidSize)
if ($Mode -eq 'Inventory') { return }

$comparisons=@(
    [pscustomobject]@{Pair='D1_to_D2_airborne_to_stopped';A=1;B=2},
    [pscustomobject]@{Pair='W5_to_W6_near_apex_to_descending';A=5;B=6},
    [pscustomobject]@{Pair='W6_to_W7_descending_to_flag_result';A=6;B=7},
    [pscustomobject]@{Pair='W5_to_W7_near_apex_to_flag_result';A=5;B=7}
)
$eligible=@($comparisons | Where-Object {
    $sets[$_.A]['MEM1'] -and $sets[$_.A]['MEM2'] -and
    $sets[$_.B]['MEM1'] -and $sets[$_.B]['MEM2']
})
if ($eligible.Count -eq 0) {
    Write-Warning 'NO WITHIN-SHOT NATIVE PAIRS READY. No RAM compared. Confirm actual file names, MEM1/MEM2 lengths, and phase mapping; do not rename originals.'
    Write-Host 'Suggested expected shape: 1.1.raw + 1.2.raw (one 24MiB bank and one 64MiB bank); likewise for each observation.'
    return
}
$uniquePhases=@($eligible | ForEach-Object { $_.A; $_.B } | Sort-Object -Unique)
$metadata=@{}
foreach ($phase in $uniquePhases) {
    $m1=$sets[$phase]['MEM1']; $m2=$sets[$phase]['MEM2']
    Assert-Rev1Header $m1
    foreach ($p in @($m1,$m2)) {
        $file=Get-Item -LiteralPath $p -Force
        Assert-RealFile $file
    }
    # Digests retained in PRIVATE report solely for provenance, never stdout.
    $metadata[[string]$phase]=@{
        phase=$phase; human_label_only=$true; same_guest_frame_verified=$false
        mem1_sha256=PrivateHash $m1; mem2_sha256=PrivateHash $m2
        mem1_bytes=25165824; mem2_bytes=67108864
    }
}
$results=@()
foreach ($pair in $eligible) {
    $bankDeltas=@{}
    foreach ($bank in @('MEM1','MEM2')) {
        $d=[GolfPageDiff]::Compare($sets[$pair.A][$bank],$sets[$pair.B][$bank])
        $bankDeltas[$bank]=@{
            changed_bytes=[long]$d.ChangedBytes
            changed_4096_byte_pages=[int]$d.ChangedPages
            total_compared_bytes=[long]$d.ComparedBytes
            changed_page_indices_private=@($d.ChangedPageIndices)
        }
    }
    $results+=@{
        comparison=$pair.Pair; from_phase=$pair.A; to_phase=$pair.B
        mem1=$bankDeltas['MEM1']; mem2=$bankDeltas['MEM2']
        same_shot_operator_reported=$true
        source_gated_ball_identity_verified=$false
        actual_physical_motion_verified=$false
    }
    Write-Host ("{0}: MEM1 changed {1} pages; MEM2 changed {2} pages (4096 B/page)" -f
        $pair.Pair,$bankDeltas['MEM1'].changed_4096_byte_pages,
        $bankDeltas['MEM2'].changed_4096_byte_pages)
}
$private = Join-Path $directory ("P0-SEVEN-AUDIT-" + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') +
    '-' + [guid]::NewGuid().ToString('N').Substring(0,10) + '-PRIVATE')
[void](New-Item -ItemType Directory -Path $private -ErrorAction Stop)
$report=@{
    kind='local-seven-human-labeled-golf-native-bank-delta'
    schema_version=1; created_utc=[DateTime]::UtcNow.ToString('o')
    human_observation_study='S002-SEVEN-HUMAN-DUMPS-01'
    labels=@{
        '1'='driver_midair_power_rising'; '2'='same_driver_ball_stopped'
        '3'='putter_extended_back_a_released'; '4'='driver_medium_back_a_held'
        '5'='wedge_near_apex_camera_change'; '6'='same_wedge_descending'
        '7'='same_wedge_flag_impact_nice_on_15p2ft_ui'
    }
    inventory=@($inventory); unmatched_raw_names_count=$unmatched
    invalid_size_count=$invalidSize; per_phase_native_sha256_private=$metadata
    comparisons=@($results)
    all_bank_pairs_same_guest_frame_verified=$false
    p0_ball_world_xyz_verified=$false; p0_ball_velocity_verified=$false
    p0_power_verified=$false; official_score_memory_verified=$false
    pin_and_camera_confounds_unresolved=$true
    approved_for_model_training=$false; allowed_to_publish=$false
}
$path=Join-Path $private 'report-RAW-PRIVATE.json'
$json=$report | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText($path,$json,[Text.UTF8Encoding]::new($false))
Write-Host ("PRIVATE REPORT WRITTEN; within-shot comparisons completed: {0}; no raw RAM uploaded." -f $results.Count)
Write-Host "No same-guest-frame, ball XYZ, power, score or training claim has been established."
