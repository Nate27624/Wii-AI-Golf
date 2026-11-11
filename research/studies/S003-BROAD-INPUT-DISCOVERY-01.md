# S003 Broad-Input Discovery: Find a Lower-Power Shot

**DRAFT, unmerged and not verified in-game.** Operator's initial requested forward-speed 40% test still produced human-observed 101% power. Earlier B1/B2/XLOW/XM06 also yielded 101% despite various input parameter differences. Rather than fitting to those identical outputs, this new eight-arm smoke test explores structurally different inputs, including a zero-motion negative control.

## Experimental arms

| Arm | Changed requested movement, relative to the original 89-sample trace | Purpose |
|---|---|---|
| CTRL | Unchanged canonical 15-back +20-forward movement | Baseline |
| ZERO | All 35 movement samples stationary; A pattern unchanged | Negative control: no motion should not produce a genuine shot |
| BACK0 | Remove 15-frame backswing; forward unchanged | Does backwards motion matter? |
| FWD0 | Remove 20-frame forward swing; backswing unchanged | Is forward motion necessary? |
| PULSE2 | Keep only the first 2 of 20 forward movement frames | Test forward duration / impulse |
| TINY | Both moving phases request distance 0.02m, speed 0.10m/s and return speed 0.10m/s | Near-zero movement intensity |
| REVFWD | Reverse forward direction; speed and distances remain baseline | Test direction/phase |
| CTRL_R | Repeat exact baseline | Detect game/pose drift |

All retain the **45 callback-tick A-only lead + original 89-sample 77-held/12-released A topology**, the same source-pinned atomic V1 bridge, 0 angle, same initial partial-back club pose, manually wedge→iron final club, aim straight, first-ball zero-wind Hitting the Green. These are requested Felk movement inputs; neither native club angular velocity nor native accepted power is directly known. A noncontact ZERO, FWD0, or REVFWD outcome is useful information; it must not be recorded as 0% without seeing a gauge. If ZERO generates a high-power strike, investigate control acceptance / bridge replay before interpreting subsequent variables.

## Reusing the savestate in one Dolphin

Use the unchanged existing canonical first-boot wrapper, saved local research/launch.local.json and savestates.local.json, and the previously validated isolated atomic bridge. It starts ONE Dolphin and restores registered green-pre-start, then runs the existing A/A+B/A intro. The new child is not a launcher.

After each shot, it asks permission to load the **same pre-existing registered pre-start slot** (never saves/overwrites), waits for advancing emulator frames, checks atomic bridge capability and replays the existing canonical seven menu phases, all INSIDE the same Dolphin. It prompts before every individual shot for a visual first-ball check, partial-back pose, iron selected after wedge→iron switch, and consent. A savestate RPC ACK is not proof the screen is ready. Cancel with q if wrong. Negative results are retained and the sequence continues only with an explicit fresh reload permission.

Requested real-game attempt: 8 observed shots, 7 separate RELOAD-STATE prompts plus an initial RUN-EIGHT plan approval and per-shot ENTER confirmation. A completed shot appends an immutable private row at sibling Wii-AI-Golf-Data/captures/input-discovery-discover01.jsonl. Prior trials are NOT overwritten; do not resume a partially completed scenario. Recorded: exact requested trace SHA/fields, verified local bridge SHA, human club movement/contact/power including uncertainty/red/curve and whether result screen was still visible, training false. M:100ft remains censored score penalty rather than actual carry.

## Local PowerShell steps (no game path re-entry)

Close Dolphin. If the old 40%-speed four-shot batch is still prompting, cancel it with q before starting this new experiment. Keep isolated worktree clean. Run only after both Windows/Ubuntu exact-head CI checks pass.

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Dirty isolated worktree' }

git fetch origin refs/pull/435/head
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Checkout failed' }

py -3 -I -m unittest discover -s tests -p test_p0_input_discovery_sweep.py -v
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
py -3 -I scripts/p0_input_discovery_sweep.py --scenario discover01
if ($LASTEXITCODE -ne 0) { throw 'No-input payload dry run failed' }

foreach ($path in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required saved file: $path"
    }
}
$saved = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $saved.game -PathType Leaf)) {
    throw 'Existing game file path invalid'
}

$trial = @(
    '--config', $config, '--catalog', $catalog, '--bridge', $atomic,
    '--script', 'p0_input_discovery_sweep.py', '--',
    '--send-live-sweep', '--scenario', 'discover01',
    '--catalog', $catalog, '--bridge-source', $atomic
)
py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'No-input boot preflight failed' }

if ((Read-Host 'Type RUN-DISCOVERY to start one Dolphin') -eq 'RUN-DISCOVERY') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) {
        throw 'Experiment aborted/incomplete; no automatic retry'
    }
}
~~~

After launch: type RUN-EIGHT to approve the design. For each new state restore, type RELOAD-STATE only when ready. For each shot, visually confirm actual screen/club/pose and consent. For transient result enter G or M while visible; T if already transitioned; no result need not imply 0 power.

## Research decision

Success is **first contact-positive non-red/reduced gauge** relative to ~101% human baseline. Then design a small focused calibration series around whichever change produced it. If everything including ZERO yields a red strike, source-side game-consumed controller and native power instrumentation is higher priority than more guesses. Do not train a model, assert a native power percentage, or claim fixed trajectories yet. Relevant #399 power, #418 latch, #415 flight, #422 trees and #320 S000 assignments.
