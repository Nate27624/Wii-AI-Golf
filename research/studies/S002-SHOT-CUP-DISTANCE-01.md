# S002-SHOT-CUP-DISTANCE-01 — single hit, landed memory, result distance

**Study state: prepared, not yet executed.** User explicitly requested one real controlled swing and post-result distance study. The scripts **never control Dolphin or deliver any swing**; the operator chooses when to capture. This branch is stacked on #180 (PRE/POST source contract), which stacks on #163/#160. Geometry uses #182 source pin/cup/ball relationships, #183 conditional goal caches. S001 #166 owns the optional future live frame sampler and waveforms; S000 #154 owns claim promotion. No raw memory or private manifest in GitHub.

## What this can answer

- PRE: native game state while the selected ball is visibly at rest, before club motion.
- POST: native state after **exactly one observed ball-moving shot**, when the ball visibly rests at its landing point and is still displaced (no ball/hole reset yet). This is the key comparison for ball candidate `PlayerManager selected record+0x88→Ball+0x4C` and record+0x54.
- RESULT: OPTIONAL separate native snapshot after the game displays the score/distance result, even if the game has moved to a result screen. Operator can enter the exact UI-displayed distance (feet, yards or meters) privately. The shot outcome shown by the game is a separately attested measurement, not proven equivalent to the physics ball-to-cup distance.
- The analyzer reads source `FieldManager+0x54` CUP, `+0x44` PIN, `+0x50` START with each source map object's `+0x4C→+0x30` translation. If the optional RESULT screen still exposes a valid source-selected ball and the same owner/cup, it also reports **RESULT ball-to-cup candidate distance** and a **reset-to-start boolean**. A post-result source value does NOT replace the earlier landed POST memory and is not automatically the displayed UI distance. It computes PRE and POST candidate **ball-to-cup horizontal distance using float components [0,2]**, POST 3D ball-to-cup, POST candidate ball-to-pin and PRE-to-POST displacement, in **UNVERIFIED game-coordinate units**. It retains the UI's entered distance/unit and an exploratory one-shot ratio UI-units/game-unit; it does not claim yard conversion, true physical XYZ, flight path, velocity, impact, club pose, or power.
- This is NOT a same-guest-frame flight trajectory. Success is first a visually supported POST displacement with static source CUP and START and stable selected owner/hole. The spectator GUI and pause labels are operator-attested.

## Essential trap: the result screen may reset the ball

If the game resets the ball, switches holes, or moves the selected actor before you pause POST, do not call the late scene POST or set `--shot-observed`. PRE→RESULT-only data are insufficient to verify moving ball memory. You can still transcribe the UI distance manually and keep your screenshot privately, then collaborate with S001 to configure the existing in-frame watcher for a repeat approved shot. Do not re-create the B0–B3 controls; they already passed.

## Preflight and AUTO-ENTER Hitting the Green — canonical repository launcher

**Correction after operator feedback:** do **NOT** manually open a bare `Dolphin.exe` or walk the menus. The MAIN REPOSITORY already contains `scripts/launch_golf.py`: it loads the named `green-pre-start` save and runs the calibrated **A → A+B → A** into Hitting the Green. This study provides a thin `scripts/launch_golf_shot_study.py` adapter which delegates to that **main-checkout** canonical launcher rather than maintaining another menu sequence or shipping unreviewed controller waveform. It uses the separate known clean FelkDolphin-Clean portable installation and the bridge previously booted successfully on it; **NO `--swing`** is sent. If the clean portable User does not actually contain the registered savestate bytes, source-safe failure is expected; a JSON catalog entry is merely a name/slot mapping, not a transferred save. Never assume the menu succeeded without visual confirmation.

Use a NEW PowerShell terminal. This is a fully repo-scripted startup, but it needs an existing Wii Sports path (`$repo\research\launch.local.json`) and registered named checkpoint (`$repo\research\savestates.local.json`) from the MAIN checkout. Do not use the isolated worktree's missing ignored config.

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$branch = 'agent/research/shot-cup-distance-cohort-20261027'
$work = "$root\Wii-AI-Golf-Shot-Cup-Study"
$clean = "$root\tools\FelkDolphin-Clean"
$session = "$root\Wii-AI-Golf-Data\captures\SHOT-$(Get-Date -Format yyyyMMdd-HHmmss)-PRIVATE"
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (-not (Test-Path $work)) {
  git -C $repo worktree add --detach $work "origin/$branch"
  if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
} else {
  $upstream = git -C $repo rev-parse "origin/$branch"
  $installed = git -C $work rev-parse HEAD
  if ($upstream -ne $installed) { throw 'Existing shot study worktree is stale; inspect it rather than force resetting' }
}
py -m unittest discover -s "$work\tests" -p 'test_golf_shot_cup_distance_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Shot study tests failed; stop' }
py -m unittest discover -s "$work\tests" -p 'test_launch_golf_shot_study.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Auto-intro tests failed; stop' }
New-Item -ItemType Directory -Path $session -ErrorAction Stop | Out-Null

# Fresh launch only. Do not start another Dolphin or kill a working session.
$running = @(Get-CimInstance Win32_Process -Filter "Name='Dolphin.exe'")
if ($running.Count -gt 0) {
  $running | Select-Object ExecutablePath
  throw 'Dolphin already open. Close it normally for fresh canonical startup, or use the explicitly attached intro in the advanced workflow.'
}
# Offline preflight of MAIN local game profile and clean portable user.
py "$work\scripts\launch_golf_shot_study.py" --dry-run
if ($LASTEXITCODE -ne 0) { throw 'Auto-intro preflight failed; repair the named profile/game/config first' }

# This DOES launch the clean Dolphin, restore green-pre-start, send A/A+B/A.
# It DOES NOT swing, capture RAM, alter the game image, or create a savestate.
py "$work\scripts\launch_golf_shot_study.py"
if ($LASTEXITCODE -ne 0) { throw 'Canonical Hitting Green intro did not complete. Do NOT claim PRE' }
Write-Host 'Visually verify Golf > Training > Hitting the Green at first stationary ball.'
```

**If Dolphin is already open:** do not run a second instance. Once you have confirmed that it is specifically the clean portable FelkDolphin-Clean process running Wii Sports with the correct bridge, the existing canonical `scripts/launch_hitting_green.py --attach-running --send-live --profile green-pre-start` can load the saved profile and dispatch the intro **in that existing process**. This is intentional state reset and button input, not a read-only probe; use only when you actually intend to restart the green training mode. The study's simple launch above deliberately fails if a bridge is already using its port.

**Known setup caveat:** official clean Preview4 boot and read-only RPC were observed with the legacy bridge, but an old configured game path/savestate in the original emulator is NOT evidence that the clean isolated `User` contains that savestate. The wrapper intentionally validates MAIN local config and clean controller config, and reports `live_savestate_bytes_independently_verified=false`. If it cannot load the named checkpoint, preserve the clean install, inspect saved state files and named catalog rather than randomly entering menus or copying old emulator state behind the user's back.

### Find native Export/Dump folder AFTER first PRE export

Once Golf mode4 first ball is visibly stationary and ready: GUI Emulation→Pause; View→Memory; Export→Dump MRAM; then Export→Dump ExRAM; keep GUI PAUSED. In a PowerShell window, locate the clean portable export directory (the source name may differ between Felk forks):

```powershell
$export1 = Get-ChildItem "$root\tools\FelkDolphin-Clean\User" -Filter 'mem1.raw' -Recurse -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $export1) { throw 'No clean Dolphin mem1.raw; ensure you exported MRAM through Memory panel' }
$dump = $export1.Directory.FullName
if (-not (Test-Path "$dump\mem2.raw")) { throw 'Export ExRAM in same GUI pause' }
Get-Item "$dump\mem1.raw","$dump\mem2.raw" | Select-Object Name,Length,LastWriteTime
```

**PRE capture** (run ONLY AFTER that same paused MRAM/ExRAM pair was freshly exported):

```powershell
py "$work\scripts\preserve_golf_shot_distance_checkpoint_private.py" --private-root $session --mem1-source "$dump\mem1.raw" --mem2-source "$dump\mem2.raw" --checkpoint PRE --paused-confirmed
if ($LASTEXITCODE -ne 0) { throw 'PRE preservation failed' }
```

**SHOT / POST capture:** In Dolphin manually unpause. Perform **ONE** human-controlled intentional shot using the already working controller. Verify the golf ball visibly moves. When it stops at a new location and is **still visibly displaced before any reset/hole transition**, GUI Pause immediately; export **Dump MRAM then Dump ExRAM** while still paused. If you could not catch it before reset, STOP; do not claim POST. If successful, run:

```powershell
py "$work\scripts\preserve_golf_shot_distance_checkpoint_private.py" --private-root $session --mem1-source "$dump\mem1.raw" --mem2-source "$dump\mem2.raw" --checkpoint POST --paused-confirmed --shot-observed --same-process-confirmed --same-hole-confirmed
if ($LASTEXITCODE -ne 0) { throw 'POST preservation failed' }
```

**Optional RESULT capture:** In Dolphin resume, wait for final distance/score text, pause while result UI visible and again export **MRAM then ExRAM**. If the game shows numeric distance, transcribe the displayed value and EXACT unit as printed, not as inferred. For example if UI says 8.7 ft:

```powershell
py "$work\scripts\preserve_golf_shot_distance_checkpoint_private.py" --private-root $session --mem1-source "$dump\mem1.raw" --mem2-source "$dump\mem2.raw" --checkpoint RESULT --paused-confirmed --result-visible --displayed-distance 8.7 --ui-unit ft
if ($LASTEXITCODE -ne 0) { throw 'RESULT preservation failed' }
```

If the result is nonnumeric or no distance is displayed, omit `--displayed-distance` and `--ui-unit` but still use `--result-visible`. An optional screenshot can be saved locally to the same ignored private session without automatic OCR or public upload. Do not use a value guessed from shot strength, trajectory or the user's memory of an earlier trial.

### Offline PRE/POST motion and hole-distance analysis

```powershell
py "$work\scripts\audit_selected_ball_prepost_shot_private.py" --private-root $session
if ($LASTEXITCODE -ne 0) { throw 'PRE/POST source-motion audit refused: investigate; no training' }
py "$work\scripts\audit_golf_shot_cup_distance_private.py" --private-root $session
if ($LASTEXITCODE -ne 0) { throw 'Distance audit refused; preserve raw capture and send redacted error' }
```

The first command reports source candidate displacement counts and unchanged START control; the second reports computed candidate distances to PIN/CUP in **unverified game units**, possible UI observation, and an exploratory scaling ratio (do not assume it proves yards/feet). Both are read-only and retain all `training_allowed=false`, `allowed_to_publish=false` semantics. Share only the sanitized console JSON directly in chat for interpretation; do NOT upload raw `.bin`, private `.json` manifests, screenshots, or output to a public GitHub repo.

## Post-capture agent responsibilities

- **S001 #166**: preserve working clean Felk bridge and waveform, no watcher injection on FIRST post-landing study. If POST cannot be paused before game auto-resets, design source-selected in-frame snapshot trigger for later explicit opt-in; callback tick is not necessarily CPU frame.
- **S002 #180/#160/#163**: PRE/POST scene, stable owner/slot/hole, nested ball vs record +0x54 change, stable START and CUP, whether source caches +0xCC/+0xF0/+0xFC follow or lag. If owner pointer changes, do not claim physical motion.
- **S002 #182/#183**: PIN/CUP distinct transformations and goal fallback, whether UI metric is horizontal cup distance, pin distance, or a gameplay-specific score threshold. The UI may use feet/yard units, round or use a projection.
- **S000 #154**: stage outcomes as `source_coordinate_ball_distance_candidate` only; do not promote to world XYZ, physical game units, shot/contact, verified velocity, power, model training until repeated verified held-out shots and S001 guest-timing evidence.
- **S003 #125**: no power regression on one shot. Later repeat with different measured power and at least two distinct targets/hole distances with controls and comparable static geometry; never infer strength from result-score alone.

## Expected failure / stop rules

- PRE not at first ball in mode4: stop; restart this fresh session rather than relabel an old B0 dump.
- Shot does not move ball: save your PRE but STOP, do not claim POST.
- Game resets ball before GUI pause: the capture is not valid POST displacement; STOP and ask S001 for same-session bounded watcher plan.
- Existing clean portable lacks profile/savestate: navigate manually, no force-copy from broken build.
- Result screen changes scene or owner: RESULT is still useful for UI transcribed numeric display but NOT same-scene source physics; separate result status will show `result_golf_source_chain_still_valid=false`.
- PRE/POST selected source owner/slot/hole or START/PIN/CUP changed: no valid candidate distance comparison; save original images but do not replace missing evidence with a guess.
- Two GUIs exported >5 minutes apart within a pause, size/mmtime reversed or stale: keeper refuses; re-export both without changing the game, same pause.
- `0` valid UI distance or target hole-in-one: record exact display; scaling ratio is omitted when computed planar game distance is zero.

**No machine learning/training output is created by any script in this study.**