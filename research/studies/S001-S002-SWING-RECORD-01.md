# S001-S002 SWING-RECORD-01 — selected-player field discovery during one human-observed swing

**STATUS: DRAFT / NOT LIVE APPROVED.** Target game: Wii Sports RSPE01 US Rev1, golf scene ID5/sport2, Hitting the Green mode4. This is an independent stacked pilot on S001 #166, NOT another RAM scanner or permission to train. S001 owns bridge integration and launch, S002 owns source/fields, S000 privacy, S003 labels/model. One operator-requested swing-specific training/data-collection trial is the goal after review, **NOT** immediate model fitting. Do not run live commands before owner signoff, full Windows tests and clean Dolphin source compatibility.

## Why and what changed

The user's B0–B3 no-shot snapshots showed source-selected inline golfer record 17 aim-associated words (relative +0x03C..+0x04C; +0x094..+0x0C0), but NO club speed, power, contact or ball flight. S001 #166's initial V2 watched swing was visually **no-hit**, with 50 stationary vector samples and incomplete drain; later fixes refuse incomplete runs. The code in this study **extends that one watcher only**: sample all 51 u32 words in its existing, source-selected 0xCC-byte PlayerManager record at each sampled callback, as extra `selected_player_record_words_PRIVATE`. This is an untyped *discovery window*, not verified swing/club state. Source-selected owner/scene/mode/slot/ball/start gates, default interval4/duration256/max80 samples, before-dispatch scheduler tick, existing 5ms overhead auto-disarm and zero new controller operations are preserved. Some record words are runtime pointers; full array is PRIVATE only. If >5ms, STOP and reduce watchlist in S001 review; don't enlarge limit or quietly alter controller timing.

A new offline `scripts/analyze_selected_player_swing_words_private.py` validates complete/stable private watcher run and ranks source-relative u32 offsets by phase versus idle/A-only controls. Sampled fixed trace index 0–11 neutral A, 12–26 backswing, 27–46 forward, 47–76 follow, 77–88 A released. Missing motion phases are explicit and cannot produce positive labels. The change scorer strips numeric u32/pointers from stdout; only relative offsets and boolean difference flags can be seen. It makes **zero** physics/type/training claims. Calls are pre-dispatch tick labels, not same guest frame game-applied events. Existing #166 private report stays the only raw capture file; no new publisher.

The canonical S001 `post_boot_action_args` now recognizes this single watched recorder as an authorized post-boot consumer, injecting `--attach-running` internally in **`run_golf_experiment.py`** after the complete fresh boot and A/A+B/A menu sequence. Users cannot pass `--attach-running` themselves. This change is a **shared S001 interface** and needs owner's explicit review and regression tests before merge.

## One-time OFFLINE Windows prep — safe to run now, DOES NOT TOUCH DOLPHIN

~~~powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Swing-Record-Study'
$branch = 'agent/research/swing-selected-record-watch-20261027'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $work)) {
    git -C $repo worktree add --detach $work "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree create failed' }
} else {
    if (@(git -C $work status --porcelain).Count -gt 0) { throw 'Dirty worktree; preserve' }
    if ((git -C $work rev-parse HEAD).Trim() -ne
        (git -C $repo rev-parse "origin/$branch").Trim()) {
        throw 'Existing worktree differs from remote; preserve, no force reset'
    }
}
Set-Location $work
py -m unittest discover -s tests -p "test_selected_player_swing_words_private.py" -v
if ($LASTEXITCODE -ne 0) { throw 'Private ranker test failure: STOP' }
py -m unittest discover -s tests -p "test_swing_record_boot_handoff.py" -v
if ($LASTEXITCODE -ne 0) { throw 'Fresh-boot regression: STOP' }
py -m unittest discover -s tests -p "test_ball_watch_*.py" -v
if ($LASTEXITCODE -ne 0) { throw 'Existing watched bridge regression: STOP' }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Full Windows test failure: STOP' }
py scripts/record_selected_ball_swing_private.py
~~~

Expected final dry-run: `live_input_sent=false`, no Dolphin launch. If preflight tests fail, report test names rather than modifying an active bridge.

## AFTER S001/S002/S000 review + real no-watch contact baseline ONLY — future LIVE run

The user already recovered `tools/FelkDolphin-Clean`, isolated from the old Qt-crash-prone installation. Its legacy bridge successfully responded to read-only ping, but **that does not validate Swing V2 #166** and clean User might not have the registered named checkpoint/Emulated Wii Remote profile. Validate all before trying to drive it. The audited watched bridge MUST be generated as a *new* file from an existing reviewed Swing V2 bridge; NEVER overwrite `mcp_bridge_swing.py`, an old bridge, or the cleaned Dolphin installation. The text below is **not authorized to execute yet**:

~~~powershell
# PRECONDITION: S001 review/CI + clean User+savestate+controller+known-good hit confirmed.
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Swing-Record-Study'
$originalV2 = Join-Path $root 'tools\mcp_bridge_swing.py'
$newBridge = Join-Path $root 'tools\mcp_bridge_selected_record_watch.py'
$cleanExe = Join-Path $root 'tools\FelkDolphin-Clean\Dolphin.exe'
$cleanUser = Join-Path $root 'tools\FelkDolphin-Clean\User'
$catalog = Join-Path $repo 'research\savestates.local.json'
$config = Join-Path $repo 'research\launch.local.json'
if (-not (Test-Path $config)) { throw 'Main checkout launch.local.json is absent; STOP' }
if (-not (Test-Path $cleanExe) -or -not (Test-Path $cleanUser) -or
    -not (Test-Path $catalog) -or -not (Test-Path $originalV2)) {
    throw 'Missing required reviewed clean runtime, source bridge or profile'
}
# Purely offline source fingerprint check; does not launch Dolphin or use RPC.
py "$repo\scripts\audit_local_swing_bridge.py" --bridge $originalV2
if ($LASTEXITCODE -ne 0) { throw 'Source bridge audit failed; STOP' }
if (Test-Path $newBridge) { throw 'Never overwrite existing watched bridge' }
py "$work\scripts\prepare_ball_watch_bridge.py" --source $originalV2 --output $newBridge
if ($LASTEXITCODE -ne 0) { throw 'Bridge preparation refused; STOP' }

# MUST first close any running Dolphin: complete fresh first-ball launch via S001.
# DRY RUN: no emulator, no game input.
py "$work\scripts\run_golf_experiment.py" --dolphin $cleanExe --dolphin-user $cleanUser --bridge $newBridge --catalog $catalog --config $config --script record_selected_ball_swing_private.py -- --send-live-swing
if ($LASTEXITCODE -ne 0) { throw 'Dispatcher dry-run failed; STOP' }

# LIVE after owner authorization, one human-approved shot only, fixed trace:
py "$work\scripts\run_golf_experiment.py" --send-live --dolphin $cleanExe --dolphin-user $cleanUser --bridge $newBridge --catalog $catalog --script record_selected_ball_swing_private.py -- --send-live-swing
if ($LASTEXITCODE -ne 0) { throw 'Swing watch failed; preserve report and STOP' }
~~~

The S001 fresh boot MUST use the MAIN checkout's existing ignored launch.local.json and savestates.local.json. A detached research worktree does not automatically inherit either. The catalog's named `green-pre-start` slot is only a label; the CLEAN portable User must contain the corresponding actual savestate bytes, and boot/ready screen must be human confirmed before typing `SWING`. Never point at the old crash-prone Felk process or run a separate Dolphin simultaneously. An RPC success is not a hit.

### Offline report analysis (ONLY after successful owner-approved watched session)

The watched recorder prints a safe summary and stores a new `*-PRIVATE.json` inside `$root\Wii-AI-Golf-Data\captures`. **Never publish/share the actual numeric private JSON in public Git.** Pass the path of this *new* file exactly (do not use old B0–B3 JSON):

~~~powershell
$report = (Read-Host 'New selected-ball-frame-watch-...-PRIVATE.json exact path').Trim('"')
py "$work\scripts\analyze_selected_player_swing_words_private.py" --private-report $report
if ($LASTEXITCODE -ne 0) { throw 'Selected record phase analysis refused; no training' }
~~~

The new change ranker deliberately does NOT treat one apparent swing-specific word as actual swing strength. S002 must trace candidate PPC write/read PCs, prove selected actor ownership while swinging, and compare independent no-shot/A-only/miss/contact controls across distinct boots before field promotion. Both monitored and unmonitored conditions must produce reliable human-observed ball contact without changing A and waveform. No contact -> valid negative sample only, do NOT claim impact/power or use for training.

## Acceptance criteria

1. Offline Python tests and full Windows regression pass at exact branch head; S001 approves touched `ball_watch_patch.py`, `post_boot.py` and frame timing, S002 confirms selected record semantics, S000 approves privacy and output. No automatic merge.
2. Clean Dolphin V2 bridge and canonical first-ball startup are demonstrated; pre-instrumentation comparison with historical V1 shows stable ball contact and no interference.
3. End-to-end live capture produces `state=complete`, all trace motion phases observed, source owner/slot/hole/start stable, max read <=5000us each, canonical 89-sample SHA unchanged and independent visible contact observation. If no visible ball displacement, report **miss/no contact**, not scored success.
4. 51 candidate source-aligned fields ranked against idle and A-held; changes are strictly hypotheses. S003 model remains blocked until impact/strength and outcome labels are independently verified.

**No new live game/shot/capture was executed by the author of this draft.** This is a proposed on-branch S001 enhancement, not a sanctioned user-facing production collector yet.
