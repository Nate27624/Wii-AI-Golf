# S002-NARROW-WATCH-LATENCY-01 — Source-gated golfer RAM watchlist latency

**Status:** preregistered operator study, NOT yet executed. **Owners:** S002 PR #129 (read-only RAM capture), S000 PR #137 (typed offline auto-publication), S001 PR #112 (future true swing frame events). No new launcher, bridge, memory reader, publication kind or private data copy.

## Source observations and hypothesis

The operator's [sanitized golfer controls result](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T034248Z-7c597d65.json) has 20 candidate gameplay snapshots, 16 child pointer windows, max 18 emulated frames per read, and four changing aligned words. Each of the four changes at EVERY same-stage idle and aim comparison (10/10 idle; 7/7 aim). These are background-dynamic negatives, NOT a proven clock, pose or power gauge.

S002 PR #129 source-validates a two-cell US Rev1 static scene-manager candidate, game/scene identity, backlink and golf mode, and allows limiting the first-level 128-byte child windows via --child-start / --child-limit. Hypothesis: smaller child watchlists reduce non-atomic frame spans enough to warrant moving toward same-shot swing-event sampling.

## Frozen A/B/A design

All runs stay on the SAME first-ball Hitting the Green scene, ONE canonical Dolphin boot, no ball contact, no second launcher, no reset, no A-button, no controller RPC from the memory probe. Hold still during idle phases; move ONLY WASD Wii pointer in aim phases. Movement of the Wii pointer is not proof of 3D camera/club motion.

Each run: 4 idle samples / 6 aim-only samples / 4 idle samples; interval 0.25s, starting at child-index 0. Three independently prompted read-only captures:

| Run | Child windows | Requested region bytes/snapshot | Interpretation |
| --- | ---: | ---: | --- |
| A1 | 4 | 256 + 4×128 = 768 | Low-overhead baseline |
| B | 8 | 256 + 8×128 = 1,280 | Added watchlist overhead |
| A2 | 4 | 768 | Repeat A for time/order drift |

Additional identity-gating RPC reads incur overhead not counted in those byte totals. **Preliminary pass gate:** exactly 14 snapshots each, same stable game/scene object within run, and MAX frame-end minus frame-start ≤12 for EVERY snapshot. Abort and keep private partial data if any frame count exceeds 12, source mode changes, pointers relocate, an ambiguous scene appears, or the operator cancels. Importantly, 12 frames is still too coarse for many within-swing events; even passing this study is NOT authorization to infer the impact instant. S001/S002 may require ≤1–3 frame reads or an internal event hook for meaningful swing captures.

Auto-publish only a validated, small golfer-control-specificity summary (relative offsets, count denominators, false power/club-verification flags) via canonical Git-credential publisher. The local S002 golfer-RAW-PRIVATE JSONL MUST remain local. Source code PR #129 and typed pilot #137 are unmerged review worktrees: run focused plus full tests before a Dolphin session; never bypass a failed test or try an alternate publisher.

## Windows preflight, no game run yet

Run once from PowerShell. Creates two NEW isolated review worktrees without overwriting existing checkouts.

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$collector = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Watch-Collector-01"
$audit = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Watch-AutoAudit-01"
$captures = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"

if ((Test-Path $collector) -or (Test-Path $audit)) { throw "Study worktree exists; preserve it" }
git -C $repo fetch origin pull/129/head
if ($LASTEXITCODE -ne 0) { throw "S002 fetch failed" }
$collectorSha = (git -C $repo rev-parse FETCH_HEAD).Trim()
git -C $repo worktree add --detach $collector $collectorSha
if ($LASTEXITCODE -ne 0) { throw "Collector worktree failed" }

git -C $repo fetch origin pull/137/head
if ($LASTEXITCODE -ne 0) { throw "Publication pilot fetch failed" }
$auditSha = (git -C $repo rev-parse FETCH_HEAD).Trim()
git -C $repo worktree add --detach $audit $auditSha
if ($LASTEXITCODE -ne 0) { throw "Auto-audit worktree failed" }

Set-Location $collector
py -m unittest discover -s tests -p "test_capture_golfer_memory.py" -v
if ($LASTEXITCODE -ne 0) { throw "Collector targeted tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Collector full suite failed" }

Set-Location $audit
py -m unittest discover -s tests -p "test_golfer_phase_specificity.py" -v
if ($LASTEXITCODE -ne 0) { throw "Audit targeted tests failed" }
py -m unittest discover -s tests -p "test_public_observation.py" -v
if ($LASTEXITCODE -ne 0) { throw "Privacy tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Audit full suite failed" }
~~~

A prior full-suite lab lock message mismatch is under PR #131; if encountered, STOP and return test output for correction rather than suppressing it.

## One canonical startup and three read-only captures

Close Dolphin before the one fresh main-checkout startup:

~~~powershell
Set-Location $repo
py scripts/launch_golf.py
if ($LASTEXITCODE -ne 0) { throw "Canonical launcher failed" }
# Visually verify ready first-ball golf, then LEAVE Dolphin running.
~~~

Then run all 3 *explicitly prompted* memory captures plus automatic sanitized analysis. No new Dolphin launches. Each S002 capture prompts three times; allow one complete A/B/A study before exiting.

~~~powershell
$previous = @(Get-ChildItem $captures -Filter "golfer-*-RAW-PRIVATE.jsonl" | ForEach-Object { $_.FullName })
$counts = @(4, 8, 4)
for ($i = 0; $i -lt $counts.Count; $i++) {
    $n = $counts[$i]
    Write-Host "STUDY S002-NARROW-WATCH-LATENCY-01 run $($i+1)/3, children=$n"
    Set-Location $collector
    $captureArgs = @("--read-only", "--child-start", "0", "--child-limit", "$n", "--phase", "idle:4", "--phase", "aim_only:6", "--phase", "idle:4", "--interval", "0.25", "--max-frame-span", "12")
    py scripts/capture_golfer_memory.py @captureArgs
    if ($LASTEXITCODE -ne 0) { throw "Memory capture failed latency or scene identity gate; stop" }
    $files = @(Get-ChildItem $captures -Filter "golfer-*-RAW-PRIVATE.jsonl")
    $new = @($files | Where-Object { $previous -notcontains $_.FullName })
    if ($new.Count -ne 1) { throw "Cannot uniquely match new RAW with this capture; stop" }
    if (@(Get-Content $new[0].FullName).Count -ne 14) { throw "Incomplete capture, stop" }
    Set-Location $audit
    $auditOutput = @(py scripts/audit_golfer_phase_specificity.py --input "$($new[0].FullName)" 2>&1)
    $auditOutput | ForEach-Object { Write-Host "$_" }
    if ($LASTEXITCODE -ne 0) { throw "Sanitized audit failed; stop" }
    $published = @($auditOutput | Where-Object {
        "$_" -match "^GitHub sanitized observation: https://github.com/Nate27624/Wii-AI-Golf/tree/research/observations"
    })
    if ($published.Count -ne 1) { throw "GitHub automatic upload did not confirm; stop" }
    $previous = @($files | ForEach-Object { $_.FullName })
}
~~~

The PowerShell wrapper explicitly checks for exactly one confirmed "GitHub sanitized observation:" output after EACH run. Because the currently experimental audit CLI catches publication failure and may return process exit 0, the study stops even when the auditor process succeeded but the Git upload did not. Report the local sanitized report/upload failure if this happens. Never paste/publish private raw files or runtime addresses.

## Prespecified result interpretation

On GitHub, S000/S002 compare the three typed records by chronological run IDs: max sample span for A1/B/A2, candidate_child_regions expected 4/8/4, within-stage idle and aim comparisons, and whether the previously continuous-changing main+0x074 stays background-dynamic. We specifically **do not** call static-under-aim regions irrelevant to *swing*.

Passing max 12 frames is only a **latency feasibility** signal; before a real swing-power experiment, S001/S002 must implement SAME-shot input-command/event and game-RAM frame brackets in a single authoritative RPC stream, check instrumentation does not disrupt the previously working 45-frame A lead, and collect at least 3 distinct independently human-observed power values. Off-green 100.0ft is censored challenge penalty, not carry. No fitting a power predictor before those gates.

If 4-child A1 is already too slow, abort B and improve the sampler rather than taking more ordinary shots. If B fails but A passes, report the threshold and favor the 4-child watchlist. If A1/A2 disagree, investigate emulator sampling contention or scene drift. The A/B/A design is a diagnostic, NOT independent statistical replication. New static offset additions and public schema changes require separate S002/S000 owner review.
