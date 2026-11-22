#Requires -Version 5.1
<#
Operator-initiated, read-only live TREE CONTACT candidate recorder.
Enter to start each WOOD, LEAVES, NEAR_MISS run.
Press Enter to stop; each run also auto-stops at the time limit.
Requires an ALREADY RUNNING Wii Sports USA Rev1 / Felk bridge on
localhost 55355. Does not launch Dolphin, swing, load/overwrite states
or write any Wii game memory.
Raw snapshots/videos ONLY in ignored sibling Wii-AI-Golf-Data.
#>
[CmdletBinding()]
param(
    [ValidateRange(5,180)][int]$Seconds=50,
    [ValidateRange(1,10)][double]$Hz=4,
    [ValidateRange(1,65535)][int]$Port=55355,
    [ValidateSet('wood','leaves','near_miss')]
    [string[]]$Kinds=@('wood','leaves','near_miss')
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$parent = Split-Path -Parent $repo
# The dedicated research worktree is a sibling of the ignored private Data.
$privateRoot = Join-Path $parent 'Wii-AI-Golf-Data\captures'
if (!(Test-Path -LiteralPath $privateRoot -PathType Container)) {
    throw "Private capture directory missing: $privateRoot"
}
$python = Get-Command py -ErrorAction Stop
$script = Join-Path $PSScriptRoot 'p0_tree_contact_record_private.py'
if (!(Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'Private source recorder script not installed'
}
if ($Kinds.Count -lt 1 -or $Kinds.Count -gt 3 -or
    (@($Kinds | Sort-Object -Unique)).Count -ne $Kinds.Count) {
    throw 'Choose one to three distinct trial intentions'
}
Write-Host '=== READ-ONLY WOOD / LEAVES / NEAR-MISS RECORDING ===' -ForegroundColor Cyan
Write-Host 'Prepare the running Dolphin golf shot BEFORE each ENTER.' -ForegroundColor Yellow
Write-Host 'The recorder sends NO swing, button input, savestate or game memory writes.'
Write-Host 'Please use one pre-shot checkpoint as the starting point for the 3 trials.'
Write-Host 'Raw candidate records and optional Dolphin-window video stay in Wii-AI-Golf-Data.'
& $python.Source -3 -I $script --private-root $privateRoot --seconds $Seconds --hz $Hz --port $Port --kinds @Kinds
$code = $LASTEXITCODE
if ($code -ne 0) {
    throw "Tree-contact recorder exited $code; any partial data remains PRIVATE"
}
