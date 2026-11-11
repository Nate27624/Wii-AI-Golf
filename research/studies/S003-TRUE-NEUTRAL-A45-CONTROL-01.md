# S003: True Button-Only Control After Legacy ZERO Anomaly

## 2026-11-11 operator live abort: first CTRL moved club but NO ball contact

The operator executed the FIRST CTRL arm of the new isolated A45 neutral-suppressed bridge study. The bridge's 89-sample swing dispatch finished and the operator saw **club motion** but **no actual strike or shot**. At the shared result prompt the operator typed **q**, which cancels terminal labeling and stops the child BEFORE it writes a successful human trial row. This is an aborted CTRL attempt, **not** a finished two-shot comparison; ZERO was never executed. The operator did not report a new power gauge and no landing/carry was measured. The later PowerShell throw merely signals the nonzero exit code.

**Design interpretation:** Original V1 atomic bridge produced multiple 101% human-gauge strikes under identical requested nonzero waveform. In the new isolated neutral-suppressed bridge, the nominal CTRL no longer struck in this one observed local attempt. The change in neutral zero-valued setter behavior is a plausible difference, but do not declare native causality or accepted-power mapping: session, game phase, A recognition and exact guest club pose are not memory verified. Club moved != game committed shot. No power observation can be inferred from a non-contact swing.

**Prompt clarification:** If the shot never hits, entering **U** (unknown terminal) instead of **q** allows the human collector to continue; then answer **no** for visibly struck, and leave the power gauge empty/unknown. Use T only when a result actually transitioned and it was not observed; do not invent M:100ft. q intentionally CANCELS and prevents writing a completed row. Preserve any private raw capture artifacts that might already exist, and create a NEW scenario for any separately approved later attempt.

**Safety correction:** The true-neutral two-arm runner now persists a negative or mismatched first CTRL result and **stops before ZERO**, unless CTRL had contact=yes AND a clear human power impression within five points of the earlier 101%. The old script permitted proceeding to ZERO even when its new bridge's CTRL failed. There is a focused fake-RPC regression test for this fail-closed behavior; no checkpoint is overwritten and no second Dolphin is booted. The next useful investigation is the bridge/guest distinction between setter calls during initial idle/back/forward/follow-through phases, not another arbitrary movement speed scale. Compare original V1 and neutral source at the setter schedule first, then design an isolated phase-specific restore test if warranted. Avoid new live input until exact-head CI passes and operator explicitly consents.



**Status: experimental isolated V1 source patch, no live Dolphin result yet.**

## Evidence motivating this correction

The operator's prior `discover01` first two trials both produced human **101%** power and confirmed ball contact, with the second arm labeled ZERO and a red left-curving shot. The operator corrected the ambiguous `club_motion_human=yes` answer for ZERO to **unknown**; the immutable local row must NOT be silently modified. This correction is recorded as a post-hoc addendum in PR #435 and issues #399/#418.

The ZERO arm was scientifically misdescribed: in the existing isolated **V1** A45 bridge, the controller code unconditionally invokes `controller.set_wiimote_swing` for **all 89 trace frames**, including zero-valued ones. Original source path `src/wii_ai_golf/integration/swing_patch.py` at historical source commit `4171f334c4b0f334f7c1222429f37f840cf7394e` proves this. The newer V2 source introduced a neutral-frame skip precisely to avoid unexpected state effects. Thus ZERO 101% did not show that an A-only trace creates red contact or that power ignores movement.

## New true button-only comparison

Construct a **NEW isolated bridge source**, leaving previously validated `mcp_bridge_swing_atomic_a45.py` and every game/savestate file unchanged. The new patch only changes the historical swing setter site inside the existing A45 V1 bridge:

- An all-zero motion sample: schedule A button only; **DO NOT call** `set_wiimote_swing`.
- A nonzero motion sample: call the SAME original swing primitive with the SAME parameters.
- The callback atomic A45 lead, 89 trace slots, 77-held/12-released A mask, source A/selection paths and frame-gap guards stay unchanged.
- Install read-only `trace.a45_neutral_capabilities`; the child requires its exact response **on the actually loaded bridge before any experimental A**. Original `trace.atomic_a45_capabilities` is also checked every shot.

In **one Dolphin process**, only two shots with a saved-state reload between:
1. **CTRL**: 35 nonzero motion samples, plus A-only prelude and neutral frame A; new bridge.
2. **ZERO**: 0 `set_wiimote_swing` calls across all 89 trace frames, but identical **A button timing**; same new bridge, same first-ball/wedge-to-iron/partial-back/aim/wind setup.

Each shot still requires visual first-ball scene and per-shot operator consent. Before shot 2 separately approve reloading the registered `green-pre-start` checkpoint; the canonical A / A+B / A intro is replayed. No savestate save/overwrite or second Dolphin launch. Record operator-observed contact, human gauge, red/curve, result-timing, and default `club_motion_human=unknown` (do not ask an ambiguous animation question). A result is not native accepted power or proven A/club motion; off-green 100ft is a censored penalty. Immutable private ledger `neutral-button-only-neutral01.jsonl` uses a new scenario, not `discover01` or `firstball03`. The earlier incomplete discovery batch should remain archived, not resumed. All training flags false.

If ZERO **does not** visibly strike, prior 101% with zero-valued V1 swing calls was probably related to setter behavior, but *not yet proven as mechanism*. If ZERO **does** strike, investigate A-only effects, stale controller state, game input consumption and native power latch; do not infer accelerometer/rotational-speed equivalence. Either way stop guessing and use native game-state instrumentation as needed.

## Local runbook — no ROM path entry

Close Dolphin and cancel any old script. The existing saved game config/catalog remain in main checkout. Run after exact-head Windows and Ubuntu focused + full offline CI pass.

~~~powershell
$ErrorActionPreference = 'Stop'

$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
$neutral = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45_neutral.py'

Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Local changes; refusing checkout' }
git fetch origin refs/pull/435/head
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Checkout failed' }

py -3 -I -m unittest discover -s tests -p test_p0_true_neutral_control.py -v
if ($LASTEXITCODE -ne 0) { throw 'Neutral bridge tests failed' }

foreach ($path in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required saved file missing: $path"
    }
}
$saved = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $saved.game -PathType Leaf)) {
    throw 'Previously saved Wii Sports game image no longer exists'
}

# Builds a separate V1 atomic A45 neutral-suppressed file.
# Never overwrites the historical atomic source.
py -3 -I scripts/prepare_a45_neutral_bridge.py --source $atomic --output $neutral
if ($LASTEXITCODE -ne 0) { throw 'Neutral bridge preparation failed' }

py -3 -I scripts/p0_input_discovery_sweep.py --true-neutral-control --scenario neutral01
if ($LASTEXITCODE -ne 0) { throw 'Two-arm payload dry-run failed' }

$trial = @(
    '--config', $config, '--catalog', $catalog,
    '--bridge', $neutral,
    '--script', 'p0_input_discovery_sweep.py', '--',
    '--send-live-sweep',
    '--true-neutral-control',
    '--scenario', 'neutral01',
    '--catalog', $catalog,
    '--bridge-source', $neutral
)

py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'Outer no-input preflight failed' }

if ((Read-Host 'Type RUN-NEUTRAL to start ONE Dolphin for TWO separate shots') -eq 'RUN-NEUTRAL') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) { throw 'Diagnostic stopped; no automatic retry' }
} else {
    Write-Host 'No live input dispatched.'
}
~~~

The child then asks for RUN-TWO, one-shot ENTER permission per trial, and RELOAD-STATE before ZERO. Reconfirm the actual first-ball/iron/partial-back/aim/wind conditions after reload. Output is append-only local private; do not rerun against the same neutral01 ledger if stopped. No live test performed by CI.
