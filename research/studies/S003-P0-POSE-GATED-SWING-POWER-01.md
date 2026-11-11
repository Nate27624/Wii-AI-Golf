# S003 — pose-gated swing-power pilot (Hitting the Green, zero wind)

**Status:** isolated draft code, no real game result. Operator-reported constraint: **Hitting the Green wind is always 0**. The *initial club position affects shot power*, so never compare different starting poses as if the controller waveform alone were responsible. This implementation only **observes and gates** the pose; it does **not** manipulate the club into a particular pose or prove how the game computes power.

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

## One-shot operator protocol — atomic A45, never unattended

1. Close existing Dolphin. Reuse the saved original game path and registered checkpoint from the main checkout (not the new worktree); no game path copy/paste. Prepare a **distinct** isolated atomic bridge without overwriting the historical legacy V1:

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$legacy = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_legacy_eval.py'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
foreach ($item in @($config, $catalog, $legacy)) {
    if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
        throw "Missing required file: $item"
    }
}
$settings = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $settings.game -PathType Leaf)) {
    throw 'Saved game path is invalid'
}
Set-Location -LiteralPath $repo
py -3 -I scripts/prepare_atomic_a45_bridge.py --source $legacy --output $atomic
if ($LASTEXITCODE -ne 0) { throw 'Atomic bridge preparation failed; no shot' }
~~~

2. Run tests and the outer **dry-run** with the new scenario; no buttons or game input are sent by these:

~~~powershell
py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed; no shot' }
py -3 -I scripts/run_golf_experiment.py --config $config --catalog $catalog --bridge $atomic --script p0_pose_power_trial.py -- --send-live-swing --arm B1 --pose back --scenario firstball02 --club iron --aim-id straight --bridge-source $atomic --atomic-a45
if ($LASTEXITCODE -ne 0) { throw 'Outer dry-run failed; no shot' }
~~~

3. After confirming these outputs and the prepared source's identity, run **ONE** separately consented B1 from fresh saved first-ball state:

~~~powershell
py -3 -I scripts/run_golf_experiment.py --send-live --config $config --catalog $catalog --bridge $atomic --script p0_pose_power_trial.py -- --send-live-swing --arm B1 --pose back --scenario firstball02 --club iron --aim-id straight --bridge-source $atomic --atomic-a45
if ($LASTEXITCODE -ne 0) { throw 'B1 did not complete; do not run B2' }
~~~

The child checks runtime atomic capability **before any A or motion**, confirms initial pose before A, and requests human consent. Stop with q if club/scene/aim/pin differ. A callback receipt is NOT evidence that the game accepted A/contact, and human-visible percent is NOT a source-verified power scalar. The first-ball condition and wind=0 remain operator-established, not memory-qualified.

4. Only if B1 yields a qualifying observed shot, proceed later to a separately consented B2 and then X1 on fresh first-ball starts, changing only --arm and retaining the same firstball02 scenario, pose, club, aim, and **same atomic bridge SHA**. Off-green 100ft is a censored penalty, not measured carry; no training.

## Next scientific step

To measure the effect of **initial club position itself**, first obtain a repeatable and source-qualified way to set or measure the game-owned club pose (or angle). Then run **separate pose strata** with identical requested waveform and independent repeated baselines. A `back` vs `center` difference here is not a controlled pose manipulation until its actual geometry and transition timing are established. To map desired powers like 25/50/75/100%, validate the game-accepted scalar against the native launch vector and collect repeated, uncensored observations.

Collision/terrain/tree events end any airborne-only validation; PR #422 must establish original tree geometry and response. Do not create fake cylinders/spheres as verified native hitboxes. Links: #399 control preregistration, #418 source-power latch, #415 flight equation ledger, #422 collision. `training_approved=false`; `game_power_verified=false`; `guest_physics_frame_verified=false`.
