#requires -Version 5.1
<#
Read-only P0 source-provenance HINT for an explicitly named, locally installed
Felk Dolphin executable. No emulator execution, network, memory or DLL loading.
Original public Felk preview4 commit a22afcb... generates SCM_REV_STR from
Git HEAD via CMake/ScmRevGen.cmake. Presence of an embedded string does NOT
prove exact compiled fork/source, installed runtime invocation or physics.
Emits only categorical booleans. Does not print local SHA, paths or bytes.
#>
[CmdletBinding(DefaultParameterSetName='File')]
param(
    [Parameter(Mandatory=$true,ParameterSetName='File')]
    [ValidateNotNullOrEmpty()][string]$DolphinExe,
    [Parameter(Mandatory=$true,ParameterSetName='SelfTest')]
    [switch]$SelfTest
)

$ErrorActionPreference='Stop'
$PublicPreview4Commit='a22afcb10b97c251e17e46f2982d4e37729d32a1'
$MaximumPeBytes=256MB

function Test-CanonicalPeAmd64([byte[]]$Bytes) {
    if ($null -eq $Bytes -or $Bytes.Length -lt 256) { return $false }
    if ($Bytes[0] -ne 0x4D -or $Bytes[1] -ne 0x5A) { return $false }
    $pe=[BitConverter]::ToInt32($Bytes,0x3C)
    if ($pe -lt 0x40 -or $pe -gt ($Bytes.Length-24)) { return $false }
    if ($Bytes[$pe] -ne 0x50 -or $Bytes[$pe+1] -ne 0x45 -or
        $Bytes[$pe+2] -ne 0 -or $Bytes[$pe+3] -ne 0) { return $false }
    return ([BitConverter]::ToUInt16($Bytes,$pe+4) -eq 0x8664)
}

function Get-MarkerClassification([byte[]]$Bytes, [string]$FullRevision) {
    if (-not (Test-CanonicalPeAmd64 $Bytes)) {
        throw 'Unqualified PE architecture or truncated header'
    }
    if ($FullRevision -cnotmatch '^[a-f0-9]{40}$') {
        throw 'Unqualified public source revision'
    }
    # Literal complete 40-digit revision only; not shortened strings, patterns
    # or guessed tags. Check both possible UTF16LE byte alignments.
    $asAscii=[Text.Encoding]::GetEncoding('iso-8859-1').GetString($Bytes)
    $foundAscii=$asAscii.Contains($FullRevision)
    $asUtf16Even=[Text.Encoding]::Unicode.GetString($Bytes)
    $foundUtf16=$asUtf16Even.Contains($FullRevision)
    if (-not $foundUtf16) {
        $asUtf16Odd=[Text.Encoding]::Unicode.GetString(
            $Bytes,1,$Bytes.Length-1)
        $foundUtf16=$asUtf16Odd.Contains($FullRevision)
    }
    return @{
        kind='P0-INSTALLED-FELK-PE-EMBEDDED-SCM-REV-HINT-V1'
        status='LOCAL_FILE_REVISION_HINT_CHECKED_SOURCE_UNVERIFIED'
        pe_amd64_verified=$true
        exact_public_preview4_commit_embedded_ascii=$foundAscii
        exact_public_preview4_commit_embedded_utf16le=$foundUtf16
        any_full_public_preview4_scm_revision_hint=($foundAscii -or $foundUtf16)
        public_preview4_git_commit='a22afcb10b97c251e17e46f2982d4e37729d32a1'
        absence_is_source_mismatch_proof=$false
        embedded_marker_is_authenticated_binary_source_proof=$false
        inspected_executable_is_current_process_verified=$false
        exact_source_fork_verified=$false
        python_callback_api_verified=$false
        guest_golf_physics_step_clock_verified=$false
        rendered_ball_and_xyz_velocity_impact_power_score_verified=$false
        file_path_or_hash_emitted=$false
        emulator_process_contacted=$false
        training_approved=$false
        allowed_to_publish=$false
    }
}

if ($SelfTest) {
    try {
        $fixture=New-Object byte[] 1024
        $fixture[0]=0x4D; $fixture[1]=0x5A
        [BitConverter]::GetBytes([int]0x80).CopyTo($fixture,0x3C)
        $fixture[0x80]=0x50; $fixture[0x81]=0x45
        [BitConverter]::GetBytes([UInt16]0x8664).CopyTo($fixture,0x84)
        $ascii=[Text.Encoding]::ASCII.GetBytes($PublicPreview4Commit)
        [Array]::Copy($ascii,0,$fixture,0x100,$ascii.Length)
        $yes=Get-MarkerClassification $fixture $PublicPreview4Commit
        if ($yes.pe_amd64_verified -ne $true -or
            $yes.exact_public_preview4_commit_embedded_ascii -ne $true -or
            $yes.embedded_marker_is_authenticated_binary_source_proof -ne $false) {
            throw 'Positive ASCII synthetic failed'
        }
        [Array]::Clear($fixture,0x100,$ascii.Length)
        $utf=[Text.Encoding]::Unicode.GetBytes($PublicPreview4Commit)
        [Array]::Copy($utf,0,$fixture,0x121,$utf.Length)
        $yesUtf=Get-MarkerClassification $fixture $PublicPreview4Commit
        if ($yesUtf.exact_public_preview4_commit_embedded_utf16le -ne $true -or
            $yesUtf.exact_public_preview4_commit_embedded_ascii -ne $false) {
            throw 'Positive odd-alignment UTF16 synthetic failed'
        }
        [Array]::Clear($fixture,0x121,$utf.Length)
        $no=Get-MarkerClassification $fixture $PublicPreview4Commit
        if ($no.any_full_public_preview4_scm_revision_hint -ne $false -or
            $no.absence_is_source_mismatch_proof -ne $false) {
            throw 'Negative source-hint synthetic failed'
        }
        $fixture[0]=0x00
        $failed=$false
        try { $null=Get-MarkerClassification $fixture $PublicPreview4Commit }
        catch { $failed=$true }
        if (-not $failed) { throw 'Malformed PE synthetic failed' }
        Write-Output 'P0_FELK_EMBEDDED_SCM_REV_SYNTHETIC=PASS'
        exit 0
    } catch {
        Write-Output 'P0_FELK_EMBEDDED_SCM_REV_SYNTHETIC=ABSTAIN'
        exit 2
    }
}

try {
    $item=Get-Item -LiteralPath $DolphinExe -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Attributes -band
        [IO.FileAttributes]::ReparsePoint) {
        throw 'Unqualified input file'
    }
    if ($item.Length -lt 256 -or $item.Length -gt $MaximumPeBytes) {
        throw 'Binary outside byte bounds'
    }
    $bytes=[IO.File]::ReadAllBytes($item.FullName)
    if ($bytes.Length -ne $item.Length) { throw 'Binary length changed' }
    $result=Get-MarkerClassification $bytes $PublicPreview4Commit
    $result | ConvertTo-Json -Depth 3
    exit 0
} catch {
    @{kind='P0-INSTALLED-FELK-PE-EMBEDDED-SCM-REV-HINT-V1';
      status='ABSTAIN_FILE_OR_PE_GATE';
      exact_source_fork_verified=$false;
      training_approved=$false;
      allowed_to_publish=$false} | ConvertTo-Json -Compress
    exit 2
}
