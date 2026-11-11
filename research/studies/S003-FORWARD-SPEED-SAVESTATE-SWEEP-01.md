# S003 Forward Speed Sweep: Four Shots, One Dolphin, Three Savestate Reloads

**DRAFT. Unmerged; exact-head CI and operator local consent required.** This new-only child PR is based on parent PR #433. It does not change S001 launcher, S002 collector, original bridge, existing private data, tree collision or first-contact physics.

## Interpretation

Prior firstball03: B1/B2/XLOW/XM06 all visually struck the ball and produced an estimated 101% human gauge. XLOW changed backswing requested distance only; XM06 scaled 105 requested distance/speed/return-speed fields. XM06 red=yes, left curve=yes, terminal landing unverified. This cannot prove native power saturation or accepted shot identity.

Original Wii Sports uses accelerometer input, not Wii MotionPlus angular velocity. Felk's swing API has requested distance_m, speed_m_s, return_speed_m_s and angle_rad fields. We do not yet know the club angular velocity actually consumed by the game. This test changes **requested forward speed_m_s ONLY** as a reproducible proxy; angle remains zero. Do not call results verified angular-velocity, acceleration, redline or game accepted power.

## Fixed four-shot protocol

Same original 45 bridge callback-tick A-only lead + same 89-sample waveform (77 A held, 12 released), same 15 backwards samples (0.25m, 1.2m/s, 1.2m/s return), same 20 forward distance=0.60m and return=2.0m/s, same angle=0. Human confirms partial-back initial pose, wedge manually changed to iron, straight aim, Hitting the Green first ball, zero wind and expected tee/pin for EVERY shot.

| Arm | Forward speed request, m/s | Changes vs baseline |
|---|---:|---|
| F100 | 3.50 | no field changes |
| F040 | 1.40 | 20 forward speed fields only |
| F070 | 2.45 | 20 forward speed fields only |
| F100R | 3.50 | identical baseline repeat |

**One Dolphin boot only.** Start with the repo's existing canonical run_golf_experiment.py, saved local game config and savestate catalog and original manually-reviewed isolated atomic A45 bridge. Before each subsequent shot, the S003 child asks permission, loads the already registered green-pre-start slot inside the same Dolphin process using StateManager.request_load, checks frame progress and loaded bridge capability, replays the existing seven canonical A/A+B/A menu phases, and requires new VISUAL readiness/club/pose/aim confirmation. The save request ACK and controller command counts are not proof of in-game ready state; human must confirm. Never save a new slot, overwrite a state, or start a second Dolphin process. User opts into four-shot plan with RUN-FOUR plus each shot's own Enter consent and each state reload with RELOAD-STATE. Any failed/declined gate stops further shots.

The new private JSONL ledger is at the ignored local sibling Data/captures/forward-speed-<scenario>.jsonl, one append per completed shot. Existing ledger is never overwritten/resumed. Only requested trace SHA, bridge source SHA, human contact/power/red/curve/outcome-timing and non-verified state metadata are saved. No native ROM/RAM data, no trained models. Human power comparison and timely landing are different checks. If result screen has disappeared, label T, not late M:100ft. Off-green 100ft is a censored penalty.

## Commands (do not type game image path)

The local main checkout already contains research/launch.local.json and research/savestates.local.json. Stop existing Dolphin before running. The separate bridge file is assumed at the same verified path as before. Update the isolated experiment worktree to the reviewed new PR head and test before any live action.

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Local changes; refusing replacement' }

# Replace this with the new child PR number after it opens.
git fetch origin refs/pull/CHILD_PR_NUMBER/head
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Checkout failed' }

py -3 -I -m unittest discover -s tests -p test_p0_forward_speed_sweep.py -v
if ($LASTEXITCODE -ne 0) { throw 'Offline synthetic tests failed' }
py -3 -I scripts/p0_forward_speed_sweep.py --scenario speedtrial01
if ($LASTEXITCODE -ne 0) { throw 'Serializer dry run failed' }

foreach ($p in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Missing: $p" }
}
$saved = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $saved.game -PathType Leaf)) { throw 'Saved game file missing' }

$trial = @(
    '--config', $config, '--catalog', $catalog,
    '--bridge', $atomic, '--script', 'p0_forward_speed_sweep.py',
    '--', '--send-live-sweep', '--scenario', 'speedtrial01',
    '--catalog', $catalog, '--bridge-source', $atomic
)

py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'No-input outer dry run failed' }

if ((Read-Host 'Type RUN-SWEEP to launch one Dolphin for a bounded four-shot experiment') -eq 'RUN-SWEEP') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) { throw 'Sweep incomplete; do not automatically retry' }
} else { Write-Host 'No live session started.' }
~~~

Expected progression: F100 baseline → approval/reload → F040 → approval/reload → F070 → approval/reload → F100R. Human changes wedge to iron and confirms partial-back position each time. Do not leave Dolphin paused; do not assume an in-flight trace or stale bridge connection is safe.

## After the experiment

Power differences would show a response to the *requested forward-speed field* but still require native club angular velocity/accelerometer and accepted-power validation. No differences would further strengthen the case for a redline/gauge/early-club-state limitation, without proving its mechanism. Prioritize source-guided calc state3 +0x0C→+0x10, redline comparison, actual selected-ball v0+strength, guest update ticks and rendered actor identity before training or fitting numerical power targets.

Coordination: #399 power study; #418 source latch; #415 physics/first contact; #320 S000 assignment; #422 native tree collision. training_approved=false throughout.
