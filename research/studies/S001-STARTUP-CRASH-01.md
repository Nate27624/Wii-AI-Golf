# S001-STARTUP-CRASH-01 — no-relaunch Felk crash fault triage

**Status:** operator's attempted isolated legacy V1 no-watch boot exited `3221225477 (0xC0000005)` BEFORE the bridge preflight, savestate, menu, controller or swing steps. This is a native Windows access violation; its cause is not established. DO NOT run the legacy boot again until faulting-module and script-load diagnostics are reviewed. No memory/physics/training claims from this failure.

The main workflow source `scripts/run_golf_experiment.py` exits after the fresh-boot child command fails; the lower-level `scripts/savestate_session.py::_launch` starts Felk with `[Dolphin.exe, --script, bridge, --exec, game]` then detects process exit before any responsive RPC bridge is available. It does NOT send swing or load a savestate before that point in the observed failing attempt. Native crash at startup cannot establish whether V1's 89 neutral `set_wiimote_swing` calls vs V2's 35 caused a weak shot: no sample was dispatched.

## Safe offline diagnostic — Windows Application Error 1000 / WER 1001

New script `scripts/audit_felk_startup_crash_events.ps1` uses Windows' read-only Application event log to find recent `Dolphin.exe` Application Error 1000 records. It extracts **ONLY** local crash time, faulting module's **basename**, and validated 8-hex-digit exception code; reports counts of Dolphin-related Windows Error Reporting ID 1001 records. It never reads full event messages, private paths, executable arguments, raw memory, process IDs, fault offsets, or user directories. A faulting module is a diagnostic clue, NOT attribution of the original bug.

Because PR #172 is still a draft and not present in `main`, first make a disposable **isolated read-only worktree** of the PR; never overwrite an existing worktree:

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Crash-Audit"
if (Test-Path $work) { throw "Existing worktree; preserve it" }
git -C $repo fetch origin pull/172/head
if ($LASTEXITCODE -ne 0) { throw "PR fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
~~~

From this isolated checkout (no Dolphin process needed):

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/audit_felk_startup_crash_events.ps1 -HoursBack 24
~~~

Or when PowerShell 7 is already installed:

~~~powershell
pwsh -NoProfile -File scripts/audit_felk_startup_crash_events.ps1 -HoursBack 24
~~~

If the crash occurred more than 24 hours ago, use `-HoursBack 72` (max 168). The output should contain only safe JSON including `faulting_module_basename` and `exception_code`; those two fields plus local event time can be shared with S001. **Do not paste the raw Windows Event Viewer message or Felk scripting log**: those may contain private full paths or game locations. In a later step, the operator can share a **manually redacted** one-line script error category (e.g., Python exception type, no pathname/traceback). If the tool reports no accessible events, it establishes neither a crash cause nor absence of a crash.

## Mock regression, completely independent of OS and emulator

~~~powershell
pwsh -NoProfile -File scripts/audit_felk_startup_crash_events.ps1 -SelfTest
~~~

`-SelfTest` is a synthetic in-memory Windows Event 1000 (Dolphin VCRUNTIME140.dll, 0xC0000005) plus unrelated process. It must print a pass result, and assert there is no fake private path or unrelated app text in the emitted JSON. It does not query event logs. A GitHub Actions test runs this on Windows and Ubuntu with PowerShell 7.

## How to interpret results

- Module `Dolphin.exe`: fault is reported in the emulator image, but may still be triggered by another component.
- Module `python*.dll` / `VCRUNTIME*.dll`: inspect embedded Python/runtime compatibility; still NOT proof that the legacy script caused the crash.
- GPU/driver module: consider emulator renderer/drivers; no inference that game memory or controller changes caused it.
- No 1000 result or different exception: pause and ask for the crash's local time, Windows diagnostic availability or a redacted Felk scripting exception *category*; do NOT rerun live experiments as a replacement for fault analysis.

## Next owner decision

S001 review module and repeatability of **offline** source startup load, compare exact code executed at top-level in preserved legacy V1 vs current V2, and verify the launcher isn't overlapping another Dolphin instance. Do not modify the original installed V2 bridge or backup. S000 privacy review before publication of anything beyond these bounded safe fields. Only after safe reviewed startup is understood can operator decide whether ONE explicitly approved **unwatched** V1 A45/89 baseline trial is appropriate. Even a working crash-free V1 is not itself a ball physics or power proof.

This script performs NO Dolphin launch, RPC, save-state action, controller commands, RAM reads, file modification, new log writing, background task or network access.
