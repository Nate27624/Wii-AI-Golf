# Read-only local Windows Application Error 1000 discriminator for Clean B1.
# NEVER launches Dolphin, reads process RAM, accesses ROM, reads crash dumps,
# or prints Event XML, machine paths, process IDs or report identifiers.
[CmdletBinding()]
param(
    [string]$IncidentUtc = '2026-10-29T01:38:02Z',
    [ValidateRange(1,30)][int]$WindowMinutes = 8,
    [switch]$SelfTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertFrom-P0Event1000Xml {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$EventXml,
        [Parameter(Mandatory)][datetimeoffset]$ReferenceUtc,
        [Parameter(Mandatory)][int]$WindowMinutes
    )
    try {
        [xml]$doc = $EventXml
        $evt = $doc.DocumentElement
        if ($null -eq $evt -or $evt.LocalName -ne 'Event') { return $null }
        $system = $evt.SelectSingleNode("*[local-name()='System']")
        $provider = $system.SelectSingleNode("*[local-name()='Provider']")
        $id = $system.SelectSingleNode("*[local-name()='EventID']")
        $clock = $system.SelectSingleNode("*[local-name()='TimeCreated']")
        if ($null -eq $provider -or $null -eq $id -or $null -eq $clock) { return $null }
        if ($provider.Attributes['Name'].Value -cne 'Application Error' -or
            $id.InnerText.Trim() -ne '1000') { return $null }
        $timeString = $clock.Attributes['SystemTime'].Value
        $stamp = [datetimeoffset]::Parse(
            $timeString, [cultureinfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime()
        $delta = [math]::Abs(($stamp - $ReferenceUtc.ToUniversalTime()).TotalSeconds)
        if ($delta -gt ($WindowMinutes * 60)) { return $null }

        $fields = @{}
        $data = $evt.SelectNodes("*[local-name()='EventData']/*[local-name()='Data']")
        foreach ($node in $data) {
            $attr = $node.Attributes['Name']
            if ($null -eq $attr -or [string]::IsNullOrWhiteSpace($attr.Value) -or
                $fields.ContainsKey($attr.Value)) { return $null }
            $fields[$attr.Value] = [string]$node.InnerText
        }
        foreach ($required in @('AppName','ModuleName','ExceptionCode','FaultingOffset')) {
            if (-not $fields.ContainsKey($required)) { return $null }
        }
        if ($fields['AppName'].Trim() -cne 'Dolphin.exe') { return $null }
        $exception = $fields['ExceptionCode'].Trim()
        if ($exception -notmatch '^(?:0x)?[cC]0000005$') { return $null }
        $offset = $fields['FaultingOffset'].Trim()
        if ($offset -notmatch '^(?:0[xX])?([0-9a-fA-F]{1,16})$') { return $null }
        $safeOffset = '0x' + $Matches[1].ToUpperInvariant()
        # Path.GetFileName is platform-sensitive about backslashes; sanitize both.
        $module = @($fields['ModuleName'].Trim() -split '[\\/]')[-1]
        if ($module -cnotmatch '^[A-Za-z0-9_.+-]{1,100}$') { return $null }
        return [pscustomobject]@{
            event_utc = $stamp.ToString('yyyy-MM-ddTHH:mm:ssZ', [cultureinfo]::InvariantCulture)
            module_basename = $module
            fault_offset = $safeOffset
            exception = '0xC0000005'
            seconds_from_incident = [int][math]::Round($delta)
        }
    }
    catch {
        # This is an untrusted EventXML parser; never leak the raw exception.
        return $null
    }
}

function Invoke-P0SelfTest {
    $eventXml = @'
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><Provider Name="Application Error"/><EventID>1000</EventID><TimeCreated SystemTime="2026-10-29T01:38:03Z"/></System><EventData><Data Name="AppName">Dolphin.exe</Data><Data Name="ModuleName">C:\Private\Qt6Widgets.dll</Data><Data Name="ExceptionCode">c0000005</Data><Data Name="FaultingOffset">000000000000BEEF</Data><Data Name="AppPath">C:\Sensitive\DoNotShow.exe</Data></EventData></Event>
'@
    $anchor = [datetimeoffset]::Parse('2026-10-29T01:38:02Z')
    $good = ConvertFrom-P0Event1000Xml -EventXml $eventXml -ReferenceUtc $anchor -WindowMinutes 8
    if ($null -eq $good -or $good.module_basename -cne 'Qt6Widgets.dll' -or
        $good.fault_offset -cne '0x000000000000BEEF' -or
        $good.seconds_from_incident -ne 1) {
        throw 'P0 synthetic Event1000 positive case failed'
    }
    $cases = @(
        $eventXml.Replace('Application Error', 'Other Source'),
        $eventXml.Replace('Dolphin.exe', 'NotDolphin.exe'),
        $eventXml.Replace('c0000005', 'c0000006'),
        $eventXml.Replace('2026-10-29T01:38:03Z', '2026-10-27T01:38:03Z'),
        $eventXml.Replace('Name="FaultingOffset"', 'Name="Irrelevant"'),
        $eventXml.Replace('000000000000BEEF', '..\private'),
        '<bad xml',
        $eventXml.Replace('Qt6Widgets.dll', 'Sensitive?name.dll')
    )
    foreach ($case in $cases) {
        $bad = ConvertFrom-P0Event1000Xml -EventXml $case -ReferenceUtc $anchor -WindowMinutes 8
        if ($null -ne $bad) { throw 'P0 synthetic Event1000 negative case failed' }
    }
    $output = [ordered]@{ status = 'SELFTEST_PASS'; positive = 1; negative = $cases.Count;
        event_log_accessed = $false; dolphin_launched = $false }
    Write-Output ($output | ConvertTo-Json -Compress -Depth 3)
}

if ($SelfTest) {
    try { Invoke-P0SelfTest; exit 0 }
    catch { Write-Output '{"status":"SELFTEST_FAILED"}'; exit 9 }
}

try {
    $incident = [datetimeoffset]::Parse(
        $IncidentUtc, [cultureinfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime()
    if ($IncidentUtc -notmatch '(?:Z|[+-][0-9]{2}:[0-9]{2})$') {
        throw 'Explicit UTC or offset required'
    }
    # Windows FilterHashtable expects machine-local time in StartTime/EndTime.
    $startLocal = $incident.AddMinutes(-$WindowMinutes).LocalDateTime
    $endLocal = $incident.AddMinutes($WindowMinutes).LocalDateTime
    $events = @(Get-WinEvent -FilterHashtable @{
        LogName = 'Application'; Id = 1000
        StartTime = $startLocal; EndTime = $endLocal
    } -MaxEvents 256 -ErrorAction Stop)
    if ($events.Count -ge 256) {
        Write-Output '{"status":"ABSTAIN_TOO_MANY_EVENTS"}'; exit 4
    }
    $valid = @()
    foreach ($entry in $events) {
        $result = ConvertFrom-P0Event1000Xml -EventXml $entry.ToXml() -ReferenceUtc $incident -WindowMinutes $WindowMinutes
        if ($null -ne $result) { $valid += $result }
    }
    if ($valid.Count -eq 0) {
        Write-Output '{"status":"ABSTAIN_NO_MATCH"}'; exit 3
    }
    if ($valid.Count -ne 1) {
        Write-Output '{"status":"ABSTAIN_AMBIGUOUS_MULTIPLE_MATCHES"}'; exit 4
    }
    $out = [ordered]@{
        status = 'ONE_MATCH_REQUIRES_PRIVATE_BUILD_CONFIRMATION'
        event_utc = $valid[0].event_utc
        module_basename = $valid[0].module_basename
        fault_offset = $valid[0].fault_offset
        exception = $valid[0].exception
        seconds_from_incident = $valid[0].seconds_from_incident
        native_crash_cause_verified = $false
        dolphin_launched = $false
        real_shot_authorized = $false
    }
    Write-Output ($out | ConvertTo-Json -Compress -Depth 3)
    exit 0
}
catch {
    # Do not print Windows account, private installation paths, Event XML or errors.
    Write-Output '{"status":"ABSTAIN_EVENT_LOG_UNAVAILABLE_OR_INVALID_INPUT"}'
    exit 5
}
