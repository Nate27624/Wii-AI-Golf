# Offline, read-only Windows Application Error triage for a Dolphin startup crash.
# It NEVER launches Dolphin, reads RAM, alters a bridge, or includes event
# descriptions, executable paths, process IDs, report IDs or user directories.
[CmdletBinding()]
param(
    [ValidateRange(1,168)][int]$HoursBack = 24,
    [switch]$SelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-SafeBasename {
    param([string]$Value)
    # Cross-platform, no location disclosure. Do not echo paths on failure.
    $chunks = $Value -split '[\\/]'
    $name = $chunks[-1]
    if ($name -cmatch '^[A-Za-z0-9_.-]{1,120}$') {
        return $name
    }
    return "redacted"
}

function Get-EventDataValue {
    param([object]$Event, [int]$Index)
    try {
        if ($null -eq $Event.Properties -or $Index -ge $Event.Properties.Count) {
            return ""
        }
        return [string]$Event.Properties[$Index].Value
    } catch {
        return ""
    }
}

function ConvertTo-FelkCrashSummary {
    param([object[]]$InputEvents, [int]$WindowHours = 24)
    $entries = [System.Collections.Generic.List[object]]::new()
    $wer = 0
    $scanned = 0
    foreach ($entry in $InputEvents) {
        $scanned++
        if ($entry.Id -eq 1000 -and $entry.ProviderName -eq "Application Error") {
            # Standard Windows Event ID 1000 ordered EventData layout:
            # [0] application, [3] fault module, [6] exception code.
            $app = Get-SafeBasename (Get-EventDataValue $entry 0)
            if ($app -ine "Dolphin.exe") { continue }
            $module = Get-SafeBasename (Get-EventDataValue $entry 3)
            $exception = Get-EventDataValue $entry 6
            if ($exception -notmatch '^(?:0x)?[a-fA-F0-9]{8}$') {
                $exception = "unavailable"
            } else {
                $exception = "0x" + (($exception -replace '^0[xX]', '').ToUpperInvariant())
            }
            $time = "unknown"
            if ($null -ne $entry.TimeCreated) {
                $time = ([datetime]$entry.TimeCreated).ToString("yyyy-MM-ddTHH:mm:ss")
            }
            $entries.Add([ordered]@{
                local_time = $time
                event_id = 1000
                faulting_application = "Dolphin.exe"
                faulting_module_basename = $module
                exception_code = $exception
                source = "Windows Application Error"
            })
        } elseif ($entry.Id -eq 1001 -and $entry.ProviderName -eq "Windows Error Reporting") {
            # A WER event is supporting context, not proof that this particular
            # startup crashed. Never forward any raw WER details or text.
            $found = $false
            foreach ($field in $entry.Properties) {
                if (([string]$field.Value) -match '(?i)Dolphin\.exe') {
                    $found = $true
                    break
                }
            }
            if ($found) { $wer++ }
        }
    }
    $sorted = @($entries.ToArray() | Sort-Object -Property local_time -Descending |
        Select-Object -First 6)
    return [ordered]@{
        kind = "offline_felk_startup_application_error_triage"
        schema_version = 1
        query_window_hours = $WindowHours
        application_event_records_examined = $scanned
        dolphin_application_error_count = $entries.Count
        dolphin_wer_1001_count = $wer
        recent_dolphin_crashes = $sorted
        game_input_sent = $false
        emulator_or_bridge_started = $false
        local_paths_or_raw_event_bodies_included = $false
        fault_cause_established = $false
        interpretation = "Application Error events can localize a faulting module; they cannot prove whether the bridge script, Dolphin, a driver, or a game asset caused the crash."
    }
}

if ($SelfTest) {
    $properties = @(
        for ($i = 0; $i -lt 13; $i++) {
            [pscustomobject]@{ Value = "" }
        }
    )
    $properties[0].Value = 'X:\PRIVATE_LOCATION\Dolphin.exe'
    $properties[3].Value = 'C:\SECRET_DIR\VCRUNTIME140.dll'
    $properties[6].Value = 'c0000005'
    $fake = [pscustomobject]@{
        Id = 1000
        ProviderName = "Application Error"
        TimeCreated = [datetime]'2026-10-27T21:00:00'
        Properties = $properties
    }
    $otherProperties = @(
        [pscustomobject]@{ Value = "Other.exe" }
    )
    $unrelated = [pscustomobject]@{
        Id = 1000
        ProviderName = "Application Error"
        TimeCreated = [datetime]'2026-10-27T21:02:00'
        Properties = $otherProperties
    }
    $summary = ConvertTo-FelkCrashSummary -InputEvents @($fake, $unrelated)
    $json = $summary | ConvertTo-Json -Depth 7
    if ($summary.dolphin_application_error_count -ne 1 -or
        $summary.recent_dolphin_crashes[0].faulting_module_basename -ne "VCRUNTIME140.dll" -or
        $summary.recent_dolphin_crashes[0].exception_code -ne "0xC0000005" -or
        $json -match 'SECRET_DIR|PRIVATE_LOCATION|Other.exe|X:\\') {
        throw "Synthetic Windows Application Error parser/privacy check failed"
    }
    Write-Output '{"kind":"synthetic_windows_crash_triage_test","passed":true,"live_events_accessed":false,"game_launched":false}'
    exit 0
}

if ($env:OS -ne "Windows_NT" -or -not (Get-Command Get-WinEvent -ErrorAction SilentlyContinue)) {
    Write-Error "This read-only Application Error query requires a Windows PowerShell host."
    exit 1
}

try {
    $events = @(Get-WinEvent -FilterHashtable @{
        LogName = "Application"
        Id = 1000, 1001
        StartTime = (Get-Date).AddHours(-$HoursBack)
    } -ErrorAction Stop)
} catch {
    # No events or blocked event-log permissions: don't leak raw system error
    # text, which may include account names, paths or machine details.
    Write-Output ('{"kind":"offline_felk_startup_application_error_triage","query_status":"unavailable_or_no_events","game_input_sent":false,"fault_cause_established":false}')
    exit 0
}
$result = ConvertTo-FelkCrashSummary -InputEvents $events -WindowHours $HoursBack
$result | ConvertTo-Json -Depth 7
