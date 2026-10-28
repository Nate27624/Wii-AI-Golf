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

## 2026-10-27 pivot: finished aiming pointer attribution → swing-specific data

Actual owner-run #178 B0 source scan established a valid static source manager entry `r29←r3` and both selected-pointer `manager+0x334` direct-call paths into angle-matrix recomputation. Selected golfer B0–B3 no-shot +0x3C rotation change was −25.127°. **That hypothesis is sufficiently source-backed for this phase; do not repeat aim-only atlas scans.**

The next S001-governed experiment is ONE causal golf swing with separate idle/no-A and button-only A controls, trace neutral, commanded backswing, forward, followthrough, A-release and after-trace observation. Real in-game visible contact/miss is indispensable; a changed `0xCC` player record word alone is NOT physical velocity or power. Existing #189 51-word sampler + S001 #166 ball/source-start vector sampler remain the ONLY prepared live watch; do not introduce another bridge or memory polling owner.

### New synthetic noninterference test, cross-agent support

An additive reviewer-only file `tests/test_s001_selected_record_full_trace_parity.py` executes the **actual generated** frozen Swing V2 bridge callback with the 51-word selected record watch and no-watch control over the same 89-sample trace. It validates exact controller call ordering/arguments and 89-frame ACK, 64 bounded watched callback observations with all 51 words, no returned internal owner pointer, injected native-memory-reader failure, and **forced >5ms read-time auto-disarm** while demonstrating the fake low-level motion-dispatch remains unchanged. The latter intentionally continues a fake controller callback after watch disarm for parity; actual operator orchestration aborts when a later phase RPC fails, and this synthetic test does NOT authorize a real watched swing. Added to existing Windows/Ubuntu targeted workflow. Independent #171 reviewed the older 3-vector watch; this adds a unique regression for #189's 51-word expansion.

Independent review **draft #191** fixes a different serious *offline ranker* issue: record fields already differing in trace-neutral A-held samples must not be called swing-motion-specific, and invalid stage/index sequence must fail closed. Require S001/S002 owner review/cherry-pick of #191 before interpreting swing-specific candidate ranks. Do not bypass #191 for convenience.

### Order of operations and blocking criteria

1. **Read-only local infrastructure:** preserve the functioning clean portable FelkDolphin-Clean and original unmodified bridge; user previously validated canonical registered green-pre-start slot2, main ignored launch/savestate config, watched bridge as a *separate* new file and no-game dispatcher dry-run. Avoid repeating these already completed steps without a changed artifact.
2. **Restore an UNWATCHED contact baseline first:** independent clean V1 diagnostic via main universal CLI `py scripts/golf.py lab plan integration.v1-diagnostic --a-lead 0` (planning only), after review/consent one witnessed hit or miss with the original known-good route. An earlier weak V2 watched pilot had no visible movement and incomplete samples; zero trusted positive contact/flight examples exist. V1 vs V2 difference and clean savestate file availability still matter. This is the main live blocker. Do not run V1 through V2-only `scripts/launch_golf.py --swing`.
3. **S001 contact + instrumentation approval:** #166 owner must review callback parity and production boot/controller compatibility; test actual 51-word per-sample latency against 5ms limit on clean Felk, WITHOUT changing waveform or skipping safety gates. Synthetic clock timing is not native timing.
4. **S000 privacy and S002 source review:** keep all 51 u32 words (some runtime pointers) and raw triplets only in ignored local PRIVATE report; only relative offset boolean/count summaries may go to public PR. S003 never trains on this first unverified trace.
5. **One deliberate gated monitored attempt:** only after owner-reviewed witnessed unwatched contact and clean fresh boot. Independent observer labels hit/no hit. If visibly no hit, report MISS and preserve as negative, not a false physical shot.
6. **Displaced POST and result:** if and ONLY if visible ball moved and can be paused before reset, reuse #180 PRE/POST paired memory capture and #184/#185 optional landed SETTLED/RESULT distance tooling. The game's result screen can reset player/ball; a RESULT snapshot cannot substitute for visibly displaced POST. No new scanner needed.

**Next safe operator command:** from the MAIN checkout, `py scripts/golf.py lab plan integration.v1-diagnostic --a-lead 0` is a planning-only preview, not `lab run --live`. No live actions should be automated from this PR until source/S001/S000 review and user confirmation.
