# Offline P0 inventory of the installed Dolphin executable.
# Does NOT launch Dolphin, read a process, inspect memory, access the network,
# register callbacks, infer physics-frame time, or authorize any shot.
# PowerShell 5.1+; run -SelfTest without an installed Dolphin executable.
[CmdletBinding()]
param(
    [string]$DolphinExe,
    [switch]$SelfTest,
    [switch]$CheckPublicPreview4Revision
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-P0Abstain([string]$Reason) {
    return [ordered]@{
        kind = 'P0-INSTALLED-DOLPHIN-BINARY-IDENTITY-V1'
        status = 'ABSTAIN'
        abstain_reason = $Reason
        binary_pe_header_verified = $false
        binary_sha256 = $null
        binary_machine = $null
        binary_version = $null
        binary_product_name = $null
        exact_installed_source_fork_verified = $false
        public_api_callback_set_verified = $false
        game_simulation_step_callback_verified = $false
        physical_xyz_velocity_impact_power_score_verified = $false
        emulator_process_contacted = $false
        game_memory_read = $false
        network_contacted = $false
        training_approved = $false
        allowed_to_publish = $false
    }
}

function Get-P0SafeMetadata([object]$Value, [int]$Max = 100) {
    if ($null -eq $Value) { return $null }
    $v = [string]$Value
    if ($v.Length -lt 1 -or $v.Length -gt $Max) { return $null }
    if ($v -cnotmatch '^[A-Za-z0-9 ._+()\-]+$') { return $null }
    return $v
}


# Public Felk/dolphin scripting-preview4 tag, verified against GitHub's tag
# reference and immutable SCM source. Presence of a literal in PE bytes is
# only a candidate VERSION STRING, never an authenticated source/build match.
$P0_PUBLIC_PREVIEW4_REV = 'a22afcb10b97c251e17e46f2982d4e37729d32a1'

function Find-P0Preview4LiteralInFile([string]$FilePath) {
    # Read in bounded 64 KiB chunks and retain 79 bytes across boundaries:
    # UTF16-LE representation of a 40-character revision is 80 bytes.
    # No PE execution, network, memory-mapped process, raw bytes in output.
    $latin1 = [System.Text.Encoding]::GetEncoding(28591)
    $asciiNeedle = $P0_PUBLIC_PREVIEW4_REV
    $wideNeedle = $latin1.GetString(
        [System.Text.Encoding]::Unicode.GetBytes($P0_PUBLIC_PREVIEW4_REV)
    )
    $reader = $null
    try {
        $reader = [System.IO.File]::Open(
            $FilePath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $buffer = New-Object byte[] 65536
        $tail = New-Object byte[] 0
        while (($n = $reader.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $window = New-Object byte[] ($tail.Length + $n)
            if ($tail.Length -gt 0) {
                [System.Buffer]::BlockCopy($tail, 0, $window, 0, $tail.Length)
            }
            [System.Buffer]::BlockCopy($buffer, 0, $window, $tail.Length, $n)
            $text = $latin1.GetString($window)
            if ($text.IndexOf($asciiNeedle, [System.StringComparison]::Ordinal) -ge 0) {
                return 'ASCII'
            }
            if ($text.IndexOf($wideNeedle, [System.StringComparison]::Ordinal) -ge 0) {
                return 'UTF16LE'
            }
            $keep = [Math]::Min(79, $window.Length)
            $tail = New-Object byte[] $keep
            [System.Buffer]::BlockCopy($window, $window.Length - $keep, $tail, 0, $keep)
        }
        return 'NONE'
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
    }
}

function Add-P0Preview4LiteralEvidence([object]$Identity, [string]$FilePath) {
    # A deliberate opt-in ONLY after the existing file/PE/SHA check succeeds.
    # The returned revision is public; never print snippets, paths or exe bytes.
    $Identity['embedded_public_preview4_revision_encoding'] = $null
    $Identity['embedded_public_preview4_revision_present'] = $null
    $Identity['embedded_revision_string_proves_source_build'] = $false
    $Identity['embedded_revision_string_proves_running_process'] = $false
    if ($Identity.status -ne 'LOCAL_BINARY_IDENTIFIED_SOURCE_UNVERIFIED') {
        return $Identity
    }
    try {
        $before = Get-Item -LiteralPath $FilePath -Force -ErrorAction Stop
        $len = [long]$before.Length
        $ticks = $before.LastWriteTimeUtc.Ticks
        $encoding = Find-P0Preview4LiteralInFile $before.FullName
        $after = Get-Item -LiteralPath $FilePath -Force -ErrorAction Stop
        if ([long]$after.Length -ne $len -or $after.LastWriteTimeUtc.Ticks -ne $ticks) {
            $Identity['embedded_revision_evidence_abstain_reason'] = 'FILE_CHANGED_DURING_SCAN'
            return $Identity
        }
        $Identity['embedded_public_preview4_revision_present'] = ($encoding -ne 'NONE')
        if ($encoding -ne 'NONE') {
            $Identity['embedded_public_preview4_revision_encoding'] = $encoding
        }
    } catch {
        $Identity['embedded_revision_evidence_abstain_reason'] = 'READ_FAILED'
    }
    return $Identity
}

function Get-P0BinaryIdentity([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return (New-P0Abstain 'EXPLICIT_EXE_PATH_REQUIRED')
    }
    $item = $null
    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    } catch {
        return (New-P0Abstain 'EXE_NOT_FOUND')
    }
    # A reparse point could redirect our read to an unrelated binary.
    if ($item.PSIsContainer -or $item.Extension -ine '.exe' -or
        (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
        return (New-P0Abstain 'UNQUALIFIED_EXE_PATH')
    }
    $len = [long]$item.Length
    if ($len -lt 256 -or $len -gt 536870912) {
        return (New-P0Abstain 'UNQUALIFIED_EXE_SIZE')
    }
    $result = New-P0Abstain 'UNVERIFIED_BINARY'
    $reader = $null
    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $item.FullName,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $reader = [System.IO.BinaryReader]::new($stream)
        if ($reader.ReadByte() -ne 0x4D -or $reader.ReadByte() -ne 0x5A) {
            return (New-P0Abstain 'NOT_MZ_EXECUTABLE')
        }
        [void]$stream.Seek(0x3C, [System.IO.SeekOrigin]::Begin)
        $peOffset = $reader.ReadInt32()
        if ($peOffset -lt 64 -or [long]$peOffset -gt $len - 6) {
            return (New-P0Abstain 'INVALID_PE_OFFSET')
        }
        [void]$stream.Seek($peOffset, [System.IO.SeekOrigin]::Begin)
        if ($reader.ReadUInt32() -ne 0x00004550) {
            return (New-P0Abstain 'INVALID_PE_SIGNATURE')
        }
        $machine = $reader.ReadUInt16()
        $machineLabel = switch ($machine) {
            0x8664 { 'AMD64'; break }
            0x014c { 'I386'; break }
            0xAA64 { 'ARM64'; break }
            default { $null }
        }
        if ($null -eq $machineLabel) {
            return (New-P0Abstain 'UNSUPPORTED_PE_MACHINE')
        }
        $result.binary_pe_header_verified = $true
        $result.binary_machine = $machineLabel
    } catch {
        return (New-P0Abstain 'PE_READ_FAILED')
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        elseif ($null -ne $stream) { $stream.Dispose() }
    }

    # The file is inspected by digest, never executed. A hash identifies bytes,
    # but cannot authenticate fork provenance or supported callback signatures.
    try {
        $start = Get-Item -LiteralPath $item.FullName -ErrorAction Stop
        $stamp = $start.LastWriteTimeUtc.Ticks
        $size = [long]$start.Length
        $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
        $end = Get-Item -LiteralPath $item.FullName -ErrorAction Stop
        if ([long]$end.Length -ne $size -or $end.LastWriteTimeUtc.Ticks -ne $stamp -or $hash -cnotmatch '^[0-9A-F]{64}$') {
            return (New-P0Abstain 'BINARY_CHANGED_DURING_READ')
        }
        $result.binary_sha256 = $hash.ToLowerInvariant()
        $ver = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($item.FullName)
        $result.binary_version = Get-P0SafeMetadata $ver.FileVersion 64
        $result.binary_product_name = Get-P0SafeMetadata $ver.ProductName 100
        $result.abstain_reason = $null
        $result.status = 'LOCAL_BINARY_IDENTIFIED_SOURCE_UNVERIFIED'
    } catch {
        return (New-P0Abstain 'HASH_OR_VERSION_READ_FAILED')
    }
    return $result
}

function Invoke-P0SyntheticSelfTest {
    # Generated dummy PE headers validate the local parser only.
    # Test artifacts are NOT evidence about installed Dolphin or Felk.
    $root = Join-Path ([System.IO.Path]::GetTempPath()) (
        'p0-synthetic-' + [Guid]::NewGuid().ToString('N')
    )
    [void](New-Item -ItemType Directory -Path $root -Force)
    try {
        $exe = Join-Path $root 'synthetic.exe'
        $bytes = New-Object byte[] 512
        $bytes[0] = 0x4D
        $bytes[1] = 0x5A
        $bytes[0x3C] = 0x80
        $bytes[0x80] = 0x50
        $bytes[0x81] = 0x45
        $bytes[0x84] = 0x64
        $bytes[0x85] = 0x86
        [System.IO.File]::WriteAllBytes($exe, $bytes)

        $positive = Get-P0BinaryIdentity $exe
        if ($positive.status -ne 'LOCAL_BINARY_IDENTIFIED_SOURCE_UNVERIFIED' -or $positive.binary_machine -ne 'AMD64' -or $positive.binary_sha256.Length -ne 64 -or $positive.game_simulation_step_callback_verified -or $positive.allowed_to_publish) {
            throw 'Positive synthetic PE/header control failed'
        }
        $invalid = Join-Path $root 'invalid.exe'
        [System.IO.File]::WriteAllBytes($invalid, (New-Object byte[] 512))
        $negative = Get-P0BinaryIdentity $invalid
        if ($negative.abstain_reason -ne 'NOT_MZ_EXECUTABLE' -or $negative.binary_sha256 -ne $null) {
            throw 'Invalid header was not rejected'
        }
        $missing = Get-P0BinaryIdentity (Join-Path $root 'absent.exe')
        if ($missing.abstain_reason -ne 'EXE_NOT_FOUND') {
            throw 'Missing executable was not rejected'
        }
        $bytes[0x80] = 0x00
        [System.IO.File]::WriteAllBytes($exe, $bytes)
        $badSig = Get-P0BinaryIdentity $exe
        if ($badSig.abstain_reason -ne 'INVALID_PE_SIGNATURE') {
            throw 'Bad PE signature was not rejected'
        }
        $bytes[0x80] = 0x50
        $bytes[0x84] = 0x00
        $bytes[0x85] = 0x00
        [System.IO.File]::WriteAllBytes($exe, $bytes)
        $badMachine = Get-P0BinaryIdentity $exe
        if ($badMachine.abstain_reason -ne 'UNSUPPORTED_PE_MACHINE') {
            throw 'Bad PE machine was not rejected'
        }
        $missingArg = Get-P0BinaryIdentity ''
        if ($missingArg.abstain_reason -ne 'EXPLICIT_EXE_PATH_REQUIRED') {
            throw 'Missing required path must abstain'
        }
        # No emulation: test the stream-boundary witness against fabricated bytes.
        $candidate = Join-Path $root 'revision-fixture.bin'
        $bytes = New-Object byte[] 70000
        $needle = [System.Text.Encoding]::ASCII.GetBytes($P0_PUBLIC_PREVIEW4_REV)
        [System.Buffer]::BlockCopy($needle, 0, $bytes, 65530, $needle.Length)
        [System.IO.File]::WriteAllBytes($candidate, $bytes)
        if ((Find-P0Preview4LiteralInFile $candidate) -ne 'ASCII') {
            throw 'Split-chunk ASCII revision witness missed'
        }
        $bytes = New-Object byte[] 70000
        $wide = [System.Text.Encoding]::Unicode.GetBytes($P0_PUBLIC_PREVIEW4_REV)
        [System.Buffer]::BlockCopy($wide, 0, $bytes, 65530, $wide.Length)
        [System.IO.File]::WriteAllBytes($candidate, $bytes)
        if ((Find-P0Preview4LiteralInFile $candidate) -ne 'UTF16LE') {
            throw 'Split-chunk UTF16LE revision witness missed'
        }
        [System.IO.File]::WriteAllBytes($candidate, (New-Object byte[] 70000))
        if ((Find-P0Preview4LiteralInFile $candidate) -ne 'NONE') {
            throw 'No-revision control failed'
        }
        Write-Output 'P0_OFFLINE_INSTALLED_BINARY_PROBE_SYNTHETIC_TESTS=PASS'
    } finally {
        Remove-Item -LiteralPath $root -Force -Recurse -ErrorAction SilentlyContinue
    }
}

if ($SelfTest) {
    Invoke-P0SyntheticSelfTest
    exit 0
} else {
    $result = Get-P0BinaryIdentity $DolphinExe
    if ($CheckPublicPreview4Revision) {
        $result = Add-P0Preview4LiteralEvidence $result $DolphinExe
    }
    $result | ConvertTo-Json -Depth 5
    if ($result.status -ne 'LOCAL_BINARY_IDENTIFIED_SOURCE_UNVERIFIED') {
        exit 2
    }
}
