# S003 — pose-gated swing-power pilot (Hitting the Green, zero wind)

**Status:** isolated draft; one atomic shot had operator-confirmed visible contact but its numeric power was UI-truncated and is NOT a calibration reference. Operator-reported constraint: **Hitting the Green wind is always 0**. The *initial club position affects shot power*, so never compare different starting poses as if the controller waveform alone were responsible. This implementation only **observes and gates** the pose; it does **not** manipulate the club into a particular pose or prove how the game computes power.

## Scope and ownership

New-only paths in isolated branch; do not alter S001 live launch/bridge, S002 data lineage, S003 historical `research_cli` studies, #418 accepted power, #422 tree collision, or #431 visual renderer. The script delegates exactly one live attempt to existing canonical `scripts/run_golf_experiment.py` and `collect_outcome_transition.run_session`. No automated sequence of shots, no memory writes beyond the game's ordinary controller inputs, no raw RAM capture/publication, no model training. The private trial ledger lives at `../Wii-AI-Golf-Data/captures/pose-power-<scenario>.jsonl`. Do not publish it without review.

## Preregistered three-arm pilot

| Arm | Initial pose (human pre-shot) | A lead | Requested backswing | Requested forward | Aim/club |
|---|---|---:|---:|---:|---|
| B1 | same declared `back` / `center` / `forward` | 45 | 0.25m, 1.2m/s for 15 samples | 0.60m, 3.5m/s for 20 samples | fixed |
| B2 | same as B1 | 45 | 0.25m, 1.2m/s | 0.60m, 3.5m/s | fixed |
| X1 | same as B1/B2 | 45 | **0.30m**, 1.2m/s for 15 samples | 0.60m, 3.5m/s | fixed |

Each has the unchanged 89-sample A/motion pattern (12 neutral A, 15 backswing A, 20 forward A, 30 neutral A, 12 released) and the same **isolated atomic A45 V1** bridge file. The host-polled A45 lead is **forbidden** after the operator's Nov 10 observed gap; do not switch bridge between arms. `back/center/forward` is a coarse *human observation* and cannot resolve sub-bin differences in starting club angle. A45 callback ticks are NOT native guest physics frames.

Before starting, human verifies the same first-ball course/hole/pin, club, aim and zero-wind display. `--scenario`, `--club`, and `--aim-id` are human-declared provenance labels, NOT memory-verified sensors. Never use the label alone to prove conditions match. The runner refuses a wrong pose **before** A. It cannot independently verify the actual club angle.

**Stop conditions:** no contact, missing or transitioned terminal result, missing visual percentage, source/bridge/trace changes, wrong initial pose, changed club/aim, wrong trial order or B1/B2 visually estimated power diverging by >5 percentage points. Negative/ineligible terminal observations are still saved and prevent advancing under the same scenario. For any pre-contact abort, use a new scenario identifier on reattempt after diagnosis. The first-ball scenario should be reset freshly by the canonical wrapper **before each arm**.

## Offline verification — no Dolphin

From an isolated checkout containing the PR:

```powershell
py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
py -3 -I scripts/p0_pose_power_trial.py --arm B1 --pose back --scenario firstball01 --club iron --aim-id straight
```

The second command uses the **actual** `_build_v1_trace_and_digest` and `SwingTraceClient.submit` serializer with a **fake RPC**, checking 89 samples, 77/12 A mask and exactly 15 changed backswing `distance_m` fields at indices 12–26. It does not contact Dolphin. The unittest fixture itself uses synthetic stubs and must not be mistaken for live client integration. Run full `python -m unittest discover -s tests -v` plus Win/Ubuntu CI before merge.

## Nov 10 B1 attempt: aborted A lead, NO submitted motion

Operator reached first-ball ready screen and confirmed initial club pose back. A was briefly pressed while host-side frame.get_count polling attempted to sustain A. A jump of more than one emulated frame triggered **"Unobserved emulated frame gap during A lead"**. The helper released A and threw **before submission of the 89-sample swing**. No completed B1 contact, trajectory, or power observation; no successful B1 ledger record. However, the brief A pulse could affect club state, so **close Dolphin and reset from the canonical first-ball state** before testing again.

This is a known limitation of frame-expiring Felk A requests controlled by a host polling loop; do NOT weaken the gap check, increase host polling to mask it, or retry the old V1 host-polled A45 path. The corrected pilot rejects live non-atomic mode before invoking controller RPC, and checks the **actually loaded** atomic A45 capability before human prompts. All B1/B2/X1 trials must now use the exact same isolated atomic V1 bridge. Use new scenario ID **firstball02** to separate the failed prehold epoch.

## Nov 10 completed atomic B1: exploratory contact, invalid numeric power

The operator completed a firstball02 B1 swing with the existing atomic A45 V1 bridge, and visually confirmed ball contact plus M:100ft OFF-GREEN (a **censored score penalty**, never carry). Human initially entered 120 for displayed swing power; the shared S002 collector rejected values above 100, so the operator entered 100 to complete the trial. The operator later stated that power **might be above 100 but was uncertain** and that the club was **partially**, not fully, drawn back.

**Evidence decision:** Preserve the original firstball02 private JSONL unchanged; its value 100 was a form-limited fallback, NOT a reliable native or human measured 100%. **Do not reuse firstball02 as a B2/X1 calibration baseline.** Its coarse back label did not distinguish partial from full backswing. Successful dispatch and visual contact did not establish native accepted power, launch velocity, or physical distance. Record this interpretation on #399 and #433. Start new firstball03 series.

### Corrected measurement and action design

- Predeclared starting club pose detail now required: partial-back or full-back when coarse pose=back, and center/forward otherwise. Before sending A, user must affirm exact declared detailed category. It is only a HUMAN visual category, not a verified club angle.
- Power prompt now accepts 120, 120?, >100, 100+, and blank. A clear number is still a **human visual estimate**, not native accepted power. Questionable values and lower bounds are persisted for analysis but **do not qualify as a numeric baseline**. Bound 500 only protects against input typos and is not a claim about game maximum.
- B1 and B2 continue exact same 45 bridge-callback A lead + 89 input samples. Same reported pre-A detailed pose, club, aim, source SHA, and scenario. Only after two repeatable qualified baselines can one third contrast be attempted: XLOW reduces the **15 backswing requested distances from 0.25 m to 0.20 m**, while X1 raises them to 0.30 m. Neither requested value guarantees any particular swing power, since emulator dynamics and club pose matter.
- Do not automatically run B2/XLOW/X1. We recommend first exploring XLOW because the initial shot may have been above 100, and re-evaluating after a repeatable control.
- The club reaching only partially back **during** the atomic action is not necessarily the same as the **initial pre-A** club pose. Establish that distinction with synchronized frame/video or native club state measurements. The new prompt only gates the latter.

### Operator's local one-shot protocol (new firstball03; no ROM path entry)

Close Dolphin between trials. Reuse main checkout's gitignored launch.local.json and savestates.local.json. The already prepared distinct mcp_bridge_swing_atomic_a45.py source must be the same original-reviewed bridge. Do not regenerate/overwrite or use the legacy host-polled bridge.

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'

Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Worktree has local changes' }
git fetch origin refs/pull/433/head
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }

py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }

foreach ($item in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $item -PathType Leaf)) { throw "Missing: $item" }
}
$saved = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $saved.game -PathType Leaf)) {
    throw 'Saved game file was not found'
}

$trial = @(
    '--config', $config, '--catalog', $catalog, '--bridge', $atomic,
    '--script', 'p0_pose_power_trial.py', '--',
    '--send-live-swing', '--arm', 'B1',
    '--pose', 'back', '--pose-detail', 'partial-back',
    '--scenario', 'firstball03',
    '--club', 'iron', '--aim-id', 'straight',
    '--bridge-source', $atomic, '--atomic-a45'
)
py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'Outer launcher dry run failed' }

if ((Read-Host 'Type RUN-B1 for ONE live, consented firstball03 trial') -eq 'RUN-B1') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) { throw 'B1 not qualified, stop here' }
} else {
    Write-Host 'No live shot requested.'
}
~~~

If user sees >100 but cannot read an exact number, enter >100 or 100+; if approximate 120, enter 120?; do NOT replace an over-100 reading with 100. If initial pose differs, cancel with q before A. An incomplete/unqualified B1 cannot advance to B2. No scripting of multiple automatic live shots is permitted. Off-green 100ft remains a censored penalty.

## Next scientific step

To measure the effect of **initial club position itself**, first obtain a repeatable and source-qualified way to set or measure the game-owned club pose (or angle). Then run **separate pose strata** with identical requested waveform and independent repeated baselines. A `back` vs `center` difference here is not a controlled pose manipulation until its actual geometry and transition timing are established. To map desired powers like 25/50/75/100%, validate the game-accepted scalar against the native launch vector and collect repeated, uncensored observations.

Collision/terrain/tree events end any airborne-only validation; PR #422 must establish original tree geometry and response. Do not create fake cylinders/spheres as verified native hitboxes. Links: #399 control preregistration, #418 source-power latch, #415 flight equation ledger, #422 collision. `training_approved=false`; `game_power_verified=false`; `guest_physics_frame_verified=false`.
