#Requires -Version 5.1
<#
.SYNOPSIS
  OFFLINE ONLY: privately stage operator-exported Wii Sports Golf MEM1/MEM2.
.DESCRIPTION
  Prepare -> Stage one manually exported pair per label -> Finalize.
  Never runs Dolphin, reads a game process, presses A, or establishes guest frames.
  Requires separate, independently reviewed G0 clearance before Stage/Finalize.
  Private session, original banks, notes and hashed manifest MUST NOT be committed.
.EXAMPLE
  .\scripts\p0_stage_private_capture.ps1 -Action Prepare -PrivateRoot 'C:\WiiGolfPrivate' -SessionId 'GOLF-20261030-01'
.EXAMPLE
  .\scripts\p0_stage_private_capture.ps1 -Action Stage -PrivateRoot 'C:\WiiGolfPrivate' -SessionId 'GOLF-20261030-01' -Phase B0 -Mem1Path 'C:\WiiExports\mem1.bin' -Mem2Path 'C:\WiiExports\mem2.bin' -DolphinExe 'C:\ApprovedDolphin\Dolphin.exe' -ExpectedDolphinSha256 '<independently-approved-64-hex-sha256>' -G0Status Cleared -G0EvidenceToken 'B1CrashReviewed-01' -RevisionEvidenceToken 'RSPE01Rev1Checked-01' -ExportMethod ManualPausedExport -PairSamePauseAttested -Observation 'Baseline; phase is operator-labelled only.'
.EXAMPLE
  .\scripts\p0_stage_private_capture.ps1 -Action Finalize -PrivateRoot 'C:\WiiGolfPrivate' -SessionId 'GOLF-20261030-01'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Prepare','Stage','Finalize')][string]$Action,
    [Parameter(Mandatory=$true)][string]$PrivateRoot,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$')][string]$SessionId,
    [ValidateSet('B0','A0','C0','F0','S0')][string]$Phase,
    [string]$Mem1Path,
    [string]$Mem2Path,
    [string]$DolphinExe,
    [string]$ExpectedDolphinSha256,
    [ValidateSet('Blocked','Cleared')][string]$G0Status='Blocked',
    [string]$G0EvidenceToken,
    [ValidateSet('RSPE01')][string]$GameId='RSPE01',
    [ValidateSet(1)][int]$GameRevision=1,
    [string]$RevisionEvidenceToken,
    [ValidateSet('ManualPausedExport','ManualMemoryViewer')][string]$ExportMethod='ManualPausedExport',
    [switch]$PairSamePauseAttested,
    [string]$Observation='',
    [string]$Uncertainty='Operator-labelled phase, not a verified guest frame or physical contact.',
    [string]$PythonCommand='py'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$MEM1_SIZE = 24 * 1024 * 1024
$MEM2_SIZE = 64 * 1024 * 1024
$manifestName = 'p0-capture-manifest-PRIVATE.json'
$metaName = 'p0-session-PRIVATE.json'

function Assert-LocalPrivate([string]$Path, [bool]$MustExist) {
    if (-not [IO.Path]::IsPathRooted($Path) -or $Path.StartsWith('\\')) { throw 'PRIVATE_PATH_REQUIRED' }
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -match '(?i)(^|[\\/])(?:OneDrive[^\\/]*|Dropbox|Google Drive|iCloudDrive|Syncthing)([\\/]|$)') {
        throw 'SYNCED_PATH_FORBIDDEN'
    }
    $root = [IO.Path]::GetPathRoot($full)
    $drive = New-Object IO.DriveInfo($root)
    if ($drive.DriveType -ne [IO.DriveType]::Fixed) { throw 'NONLOCAL_DRIVE' }
    $cursor = $full
    while ($cursor) {
        if ([IO.File]::Exists($cursor) -or [IO.Directory]::Exists($cursor)) {
            $attr = [IO.File]::GetAttributes($cursor)
            if (($attr -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'LINK_FORBIDDEN' }
        }
        if ([IO.Directory]::Exists((Join-Path $cursor '.git')) -or [IO.File]::Exists((Join-Path $cursor '.git'))) {
            throw 'GIT_CHECKOUT_FORBIDDEN'
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if (-not $parent -or $parent -eq $cursor) { break }
        $cursor = $parent
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $full)) { throw 'PATH_MISSING' }
    return $full
}

function Write-PrivateNew([string]$Path, [object]$Object) {
    $stream = New-Object IO.FileStream($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $writer = New-Object IO.StreamWriter($stream, (New-Object Text.UTF8Encoding($false)))
        try {
            $writer.WriteLine(($Object | ConvertTo-Json -Depth 6))
            $writer.Flush()
            $stream.Flush($true)
        } finally { $writer.Dispose() }
    } finally { $stream.Dispose() }
}

function Assert-ReadBank([string]$Path, [long]$Size) {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'MISSING_BANK' }
    $full = Assert-LocalPrivate $Path $true
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw 'BANK_NOT_FILE' }
    if ((Get-Item -LiteralPath $full).Length -ne $Size) { throw 'WRONG_BANK_SIZE' }
    return $full
}

function Assert-OperatorGates {
    if ($G0Status -ne 'Cleared' -or $G0EvidenceToken -cnotmatch '^[A-Za-z0-9_-]{8,64}$') {
        throw 'G0_STOP_NATIVE_CRASH_UNRESOLVED'
    }
    if ($GameId -ne 'RSPE01' -or $GameRevision -ne 1 -or $RevisionEvidenceToken -cnotmatch '^[A-Za-z0-9_-]{8,64}$') {
        throw 'GAME_REVISION_NOT_OPERATOR_ATTESTED'
    }
    if (-not $PairSamePauseAttested) { throw 'PAIR_SAME_PAUSE_NOT_ATTESTED' }
    if ($ExpectedDolphinSha256 -cnotmatch '^[a-fA-F0-9]{64}$') { throw 'MISSING_APPROVED_DOLPHIN_DIGEST' }
    $exe = Assert-LocalPrivate $DolphinExe $true
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf) -or
        [IO.Path]::GetFileName($exe) -ne 'Dolphin.exe') { throw 'DOLPHIN_INSTALL_IDENTITY' }
    if (-not [IO.File]::Exists((Join-Path ([IO.Path]::GetDirectoryName($exe)) 'portable.txt'))) {
        throw 'CLEAN_PORTABLE_DOLPHIN_REQUIRED'
    }
    $reader = [IO.File]::OpenRead($exe)
    try {
        if ($reader.ReadByte() -ne 77 -or $reader.ReadByte() -ne 90) { throw 'DOLPHIN_NOT_PE' }
    } finally { $reader.Dispose() }
    if (-not [string]::Equals((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash,
                              $ExpectedDolphinSha256, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'DOLPHIN_DIGEST_MISMATCH'
    }
}

function Invoke-ExistingPreflight([string]$Session, [bool]$WriteManifest) {
    $helper = Join-Path $PSScriptRoot 'p0_capture_manifest_preflight.py'
    if (-not [IO.File]::Exists($helper)) { throw 'MANAGER_PREFLIGHT_UNAVAILABLE' }
    $cmd = Get-Command $PythonCommand -ErrorAction Stop
    $args = @($helper,'--private-root',$Session,'--mode','checkpoint')
    if ($WriteManifest) { $args += '--write-private-manifest' }
    & $cmd.Source @args
    if ($LASTEXITCODE -ne 0) { throw 'MANAGER_PREFLIGHT_REFUSED' }
}

function Copy-VerifiedBank([string]$Source, [string]$Dest, [long]$ExpectedSize) {
    $original = Get-Item -LiteralPath $Source
    $before = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    $input = [IO.File]::Open($Source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $output = [IO.File]::Open($Dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $input.CopyTo($output); $output.Flush($true) }
        finally { $output.Dispose() }
    } finally { $input.Dispose() }
    $afterItem = Get-Item -LiteralPath $Source
    if ($original.Length -ne $ExpectedSize -or $afterItem.Length -ne $ExpectedSize -or
        $original.LastWriteTimeUtc.Ticks -ne $afterItem.LastWriteTimeUtc.Ticks -or
        (Get-Item -LiteralPath $Dest).Length -ne $ExpectedSize -or
        (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -ne $before -or
        (Get-FileHash -LiteralPath $Dest -Algorithm SHA256).Hash -ne $before) {
        throw 'BANK_CHANGED_DURING_COPY'
    }
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'WINDOWS_OPERATOR_ONLY' }
    $root = Assert-LocalPrivate $PrivateRoot $true
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'PRIVATE_ROOT_NOT_DIRECTORY' }
    $session = Assert-LocalPrivate (Join-Path $root $SessionId) $false
    $metaFile = Join-Path $session $metaName

    if ($Action -eq 'Prepare') {
        if (Test-Path -LiteralPath $session) { throw 'SESSION_EXISTS_REFUSE_OVERWRITE' }
        [IO.Directory]::CreateDirectory($session) | Out-Null
        try {
            Write-PrivateNew $metaFile ([ordered]@{
                kind='private-operator-capture-staging'; schema_version=1;
                game_id_declared='RSPE01'; revision_declared=1;
                export_method_declared=$ExportMethod; prepared_utc=[DateTime]::UtcNow.ToString('o');
                guest_frame_verified=$false; same_shot_verified=$false;
                training_approved=$false
            })
        } catch { [IO.Directory]::Delete($session,$false); throw }
        Write-Output 'P0 private session PREPARED. G0 remains unverified; no Dolphin action taken.'
        exit 0
    }

    $session = Assert-LocalPrivate $session $true
    if (-not (Test-Path -LiteralPath $session -PathType Container) -or
        -not [IO.File]::Exists($metaFile)) { throw 'SESSION_NOT_PREPARED' }
    $meta = Get-Content -LiteralPath $metaFile -Raw | ConvertFrom-Json
    if ($meta.kind -ne 'private-operator-capture-staging' -or $meta.game_id_declared -ne 'RSPE01' -or
        $meta.revision_declared -ne 1 -or $meta.export_method_declared -ne $ExportMethod -or
        $meta.training_approved -ne $false) { throw 'SESSION_CONTRACT_MISMATCH' }
    if ([IO.File]::Exists((Join-Path $session $manifestName))) { throw 'SESSION_ALREADY_FINALIZED' }

    # Exclusive local session lock; never uses Git, network, emulator processes or a watcher.
    $lock = [IO.File]::Open((Join-Path $session 'p0-stage.lock'),
                           [IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try {
        if ([IO.File]::Exists((Join-Path $session $manifestName))) { throw 'SESSION_ALREADY_FINALIZED' }
        if ($Action -eq 'Stage') {
            Assert-OperatorGates
            if (-not $Phase) { throw 'PHASE_REQUIRED' }
            $first = Assert-ReadBank $Mem1Path $MEM1_SIZE
            $second = Assert-ReadBank $Mem2Path $MEM2_SIZE
            if ([string]::Equals($first,$second,[StringComparison]::OrdinalIgnoreCase)) { throw 'BANKS_IDENTICAL_PATH' }
            $one = Join-Path $session ($Phase + '-MEM1.bin')
            $two = Join-Path $session ($Phase + '-MEM2.bin')
            $note = Join-Path $session ($Phase + '-observation-PRIVATE.json')
            if ((Test-Path -LiteralPath $one) -or (Test-Path -LiteralPath $two) -or
                (Test-Path -LiteralPath $note)) { throw 'PHASE_EXISTS_REFUSE_OVERWRITE' }
            if ($first -eq $one -or $second -eq $two) { throw 'INPUT_OUTPUT_COLLISION' }
            $drive = New-Object IO.DriveInfo([IO.Path]::GetPathRoot($session))
            if ($drive.AvailableFreeSpace -lt ($MEM1_SIZE + $MEM2_SIZE + 16777216)) {
                throw 'INSUFFICIENT_PRIVATE_STORAGE'
            }
            $prior = @(Get-ChildItem -LiteralPath $session -Filter '*-observation-PRIVATE.json' -File)
            if ($prior.Count -ge 5) { throw 'MAX_PHASES' }
            try {
                Copy-VerifiedBank $first $one $MEM1_SIZE
                Copy-VerifiedBank $second $two $MEM2_SIZE
                Invoke-ExistingPreflight $session $false
                Write-PrivateNew $note ([ordered]@{
                    phase=$Phase; capture_order=($prior.Count + 1);
                    human_label=(@{B0='baseline';A0='aim-only';C0='contact candidate';F0='flight candidate';S0='settled candidate'}[$Phase]);
                    observed_utc_wall_clock=[DateTime]::UtcNow.ToString('o');
                    observation=$Observation; uncertainty=$Uncertainty;
                    g0_cleared_operator_attestation=$true;
                    game_revision_operator_attestation=$true;
                    pair_same_pause_operator_attestation=$true;
                    export_method=$ExportMethod;
                    guest_frame_verified=$false; contact_verified=$false;
                    same_shot_verified=$false; training_approved=$false
                })
            } catch {
                foreach ($file in @($one,$two)) {
                    if ([IO.File]::Exists($file)) { [IO.File]::Delete($file) }
                }
                throw
            }
            Write-Output 'P0 native-size private pair STAGED; phase/observations are operator-labelled only.'
        } elseif ($Action -eq 'Finalize') {
            $notes = @(Get-ChildItem -LiteralPath $session -Filter '*-observation-PRIVATE.json' -File)
            if ($notes.Count -lt 1 -or $notes.Count -gt 5) { throw 'NO_VALID_PHASE_NOTES' }
            foreach ($item in $notes) {
                $p = $item.Name.Split('-')[0]
                if (-not [IO.File]::Exists((Join-Path $session ($p + '-MEM1.bin'))) -or
                    -not [IO.File]::Exists((Join-Path $session ($p + '-MEM2.bin')))) {
                    throw 'UNPAIRED_PHASE_NOTES'
                }
            }
            Invoke-ExistingPreflight $session $true
            Write-Output 'P0 private capture inventory FINALIZED; all identity/physics/training claims remain unverified.'
        } else { throw 'UNKNOWN_ACTION' }
    } finally { $lock.Dispose() }
} catch {
    # Never interpolate an exception: it can include private source paths, hashes, or console data.
    [Console]::Error.WriteLine('P0 private capture staging REFUSED (local prerequisite/privacy/integrity gate).')
    exit 2
}
