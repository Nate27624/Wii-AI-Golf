# S001 V1 unwatched baseline: clean portable launch-path correction

**Operator evidence:** `py scripts/golf.py lab plan integration.v1-diagnostic --a-lead 0` completed with `PREVIEW ONLY: no Dolphin process, RAM access, or file writes`. It named `tools/mcp_bridge_swing_legacy_eval.py`, `collect_outcome_transition.py`, `--a-prime-requests 0`, `--a-lead-frames 0`, `--observe-start-pose` and one canonical fresh game boot. This is plan validation **NOT** a real swing or contact.

## P0 discovery and patch

Before this branch, the Lab V1 plan passed `--bridge` but omitted `--dolphin` and `--dolphin-user`. The nested canonical `launch_golf.py` defaults to `tools/FelkDolphin/Dolphin.exe` (legacy Qt startup crash) rather than the already boot-tested, separately extracted portable `tools/FelkDolphin-Clean/Dolphin.exe` with isolated `User`. It also depended on implicit ignored config/catalog resolution.

Only `src/wii_ai_golf/lab/core.py` V1 diagnostic generation is changed. This plan always targets the **clean portable** executable and User and explicitly passes main-checkout ignored `launch.local.json` and `savestates.local.json`; if native files are missing the canonical launcher fails closed instead of starting old Dolphin. The existing V1 source bridge audit, A-lead 0, single guarded launch and contact prompts stay unchanged. New synthetic `tests/test_lab_v1_clean_launch_plan.py` and Windows+Ubuntu workflow check that missing clean install is NOT created during planning. **S001 must independently approve before merge or LIVE action.**

## Next read-only operator preflight on main (no launcher change, no game input)

Execute this complete block from **any** PowerShell directory. It checks the known clean installation, main local game/catalog and clean portable StateSaves inventory, then previews the nested canonical real-game command WITH EXPLICIT clean paths. It does **not** run `--send-live` and does **not** send a controller action.

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$clean = Join-Path $root 'tools\FelkDolphin-Clean'
$exe = Join-Path $clean 'Dolphin.exe'
$user = Join-Path $clean 'User'
$bridge = Join-Path $root 'tools\mcp_bridge_swing_legacy_eval.py'
$config = Join-Path $repo 'research\launch.local.json'
$catalog = Join-Path $repo 'research\savestates.local.json'
foreach ($p in @($exe, $user, $bridge, $config, $catalog)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing clean V1 prerequisite: $p" }
}
$settings = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if ($settings.schema_version -ne 1 -or -not (Test-Path -LiteralPath $settings.game -PathType Leaf)) {
    throw 'Configured game missing; do not boot old installation'
}
$states = Join-Path $user 'StateSaves'
if (-not (Test-Path -LiteralPath $states -PathType Container)) {
    throw 'Clean portable StateSaves folder missing: registered slot may have no file'
}
Get-ChildItem -LiteralPath $states -File |
    Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
Set-Location -LiteralPath $repo
py scripts/golf.py lab plan integration.v1-diagnostic --a-lead 0
if ($LASTEXITCODE -ne 0) { throw 'V1 Lab plan failed' }
py scripts/run_golf_experiment.py `
    --dolphin $exe --dolphin-user $user `
    --bridge $bridge --config $config --catalog $catalog `
    --script collect_outcome_transition.py -- `
    --send-live-swing --a-prime-requests 0 `
    --a-lead-frames 0 --observe-start-pose
if ($LASTEXITCODE -ne 0) { throw 'Explicit CLEAN V1 nested boot preview failed' }
```

### Live gate (NOT CLEARED)

A clean StateSaves directory **does not prove** the registered green-pre-start slot 2 bytes actually exist there; verify exact Wii Sports RSPE01 Rev1 slot mapping/source provenance and screen restoration separately. An isolated bridge having the V1 signature does not prove Dolphin will register A or that a ball is hit. The existing watched V2 trial missed; do not run #189 watched data acquisition yet. Before ANY baseline live run, S001 owner must approve clean User+named save, controller configuration, one-process port status, and human-attested visual contact test; preserve all private results only locally. The parent #189 51-word watcher and P0 #191 neutral-confound ranker remain draft. S000 training stays blocked and no native RAM is committed.
