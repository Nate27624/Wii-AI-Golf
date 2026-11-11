# S001-FELK-STARTUP-CRASH-01 — isolate legacy bridge startup access violation

**Status:** diagnostic-only. No Dolphin process, ROM, savestate load, controller input, bridge runtime execution, or shot performed by this tool. S001 owns startup/bridge/controller; S002 owns ball source; S000 owns public evidence approval. Do **not** merge as permission for live replay.

## Why the ball-motion study is blocked

Owner reported: an earlier selected-ball watched Swing V2 trial rendered a weak club swing with **no human-observed ball movement**, and 50/50 selected-ball samples remained static (partial watch). A later attempt to fresh-launch **an isolated legacy V1 bridge** terminated the Dolphin process before the bridge port preflight with Windows return code `3221225477` = `0xC0000005`, an access-violation code. `scripts/savestate_session.py::_launch` starts `Dolphin.exe --script LEGACY --exec GAME`, then waits for RPC; the process exited **before** any savestate load request, menu A/A+B/A input, A45 priming or 89-frame motion trace. It would be scientifically invalid to label this as a failed *legacy swing*. An access violation does not establish whether a Python script, its embedded interpreter, a graphics driver, the game executable or the emulator itself caused the exception.

Next work should be a *local evidence classification*, not another uncontrolled run. The operator already has the private old/current bridge files and preserved ball B0–B3 checkpoints, so no memory re-collection or reinstall is needed.

## Implemented separate, non-overlapping diagnostic

`scripts/triage_felk_startup_crash_offline.py` accepts the existing local Swing V2 and prepared legacy V1 Python files **without executing them**, validates existing repo source markers (atomic+Swing V1/V2, no autoload), parses each AST including top-level `await` support, and counts changed module-level import/assignment/expression/control nodes. Python syntax and marker checks are necessary, not sufficient for the embedded Felk ABI. It optionally reads a SINGLE exported Windows `Application Error` event (ID1000) XML and maps its private `ModuleName` to one category: Dolphin executable, Python runtime, Windows runtime, graphics stack or other/unknown. Event `ExceptionCode=c0000005` is checked against the observed process exit code. It optionally accepts a local .txt Scripting log and emits only presence flags for traceback/script-load-error/access-violation patterns. It prints ONLY bounded nonidentifying booleans/counts; it never outputs bridge bytes, code, local paths, Windows computer/user names, specific module basenames, event times, hashes, private memory or controller data. The original files remain unmodified. The actual raw Event XML is private and must never be committed.

## Windows operator commands — NO Dolphin launch

Use a NEW PowerShell window. Do not close or touch any already-running Dolphin process. `Get-WinEvent` may require appropriate Windows event read permissions; if no matching recent event exists, the source-only classification still works.

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Felk-Crash-Offline"
$branch = 'agent/research/felk-startup-crash-offline-triage-20261027'
$case = "$root\Wii-AI-Golf-Data\felk-crash-evidence-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Path $case -ErrorAction Stop | Out-Null
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path $work) { throw 'Existing offline crash worktree: inspect instead of replacing it' }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Worktree setup failed' }
py -m unittest discover -s "$work\tests" -p test_felk_startup_crash_offline.py -v
if ($LASTEXITCODE -ne 0) { throw 'Focused diagnostic tests failed' }

# READ-ONLY Windows Application log lookup for the last 2 days; do not launch Dolphin.
$errEvent = Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000;StartTime=(Get-Date).AddDays(-2)} -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match '(?i)Dolphin\.exe' } |
  Sort-Object TimeCreated -Descending | Select-Object -First 1
$argsForTriage = @(
  '--current-bridge', "$root\tools\mcp_bridge_swing.py",
  '--legacy-bridge', "$root\tools\mcp_bridge_swing_legacy_eval.py"
)
if ($errEvent) {
  $localEvent = Join-Path $case 'Dolphin-Event1000-PRIVATE.xml'
  $errEvent.ToXml() | Set-Content -LiteralPath $localEvent -Encoding UTF8
  $argsForTriage += @('--event-xml', $localEvent)
} else {
  Write-Host 'No matching Application Error event found; source-only audit will still run.'
}
py "$work\scripts\triage_felk_startup_crash_offline.py" @argsForTriage
if ($LASTEXITCODE -ne 0) { throw 'Local offline crash triage refused inputs' }
```

Optional: pass `--scripting-log PATH_TO_PRIVATE_SCRIPTING_LOG.txt` if that file truly exists; don't guess a path or copy the log to the repo. Windows event storage and logs may contain private device paths and identifiers. The script deliberately omits those from stdout.

## Evidence interpretation / next S001 action

- `event_is_dolphin_app_error_1000=true` and `event_exception_code_matches_exit_code=true`: corroborates the **reported native startup access-violation category**. It does NOT prove legacy bridge caused the crash.
- `faulting_module_bucket=python_runtime`: inspect Felk's embedded interpreter startup and bridge import/async load, plus unhandled script exception logs, but no unsupported claim of root cause.
- `faulting_module_bucket=graphics_stack` or `dolphin_executable`: inspect startup graphics/plugin/emulator environment and isolate without game or controller; still not root cause proof.
- `faulting_module_bucket=windows_runtime|other_module|unknown`: do not infer script source causation; gather Felk Scripting log and exact crash event privately.
- `module_level_executable_structure_differs=true`: examine which top-level bridge expressions/imports changed in PRIVATE source and whether they execute before RPC setup, while treating function body changes as an independent unchecked variable.
- `module_level_executable_structure_differs=false`: doesn't imply equal startup behavior. A changed function body, dynamic imports, native extension or emulator/environment can still crash.
- `event_is_dolphin_app_error_1000=false`: probable event mismatch, not evidence that Dolphin did not crash; compare exact crash time privately before inferring.

### Training and movement gates

Operator's four paired B0-B3 no-shot controls **passed**: selected slot0/hole stable, selected ball/record/source-start vec3 bitwise stable across idle, visibly changed WASD aim and release; complete banks changed. That supports a stationary position candidate, NOT dynamic world XYZ.

Next S001 step after startup root cause investigated: one **no-watch** successfully visible ball-contact baseline through the canonical safe bridge, with unchanged input 45A+89 frozen waveform and explicit operator confirmation. Compare installed V2, any legacy bridge only if its native boot is deemed safe; never force an unreviewed legacy retry. Next S002 step: reuse #166 sole in-frame watcher on the **same known-good** runtime setup and validate actual ball-vector displacement while source-start is fixed. Match trace provenance; #165 strict temporal gate abstains on callback ticks. Do not collect another broad RAM scan; do not authorize training or label velocity/impact/power until independent same-frame evidence exists.

Cross-agent: #166 owns single live sampler; #171 owns synthetic waveform parity; #170 fixes unrelated CI fixture failures; #160/#163 own selected source; #154 controls evidence ledger. This PR provides only new offline triage and fabricated tests (no edits to owner bridge/launcher files).