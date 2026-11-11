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

Each has the unchanged 89-sample A/motion pattern (12 neutral A, 15 backswing A, 20 forward A, 30 neutral A, 12 released) and the same **isolated V1 legacy** or same **isolated atomic A45 V1** bridge file; do not switch bridge between arms. `back/center/forward` is a coarse *human observation* and cannot resolve sub-bin differences in starting club angle. A45 callback ticks are NOT native guest physics frames.

Before starting, human verifies the same first-ball course/hole/pin, club, aim and zero-wind display. `--scenario`, `--club`, and `--aim-id` are human-declared provenance labels, NOT memory-verified sensors. Never use the label alone to prove conditions match. The runner refuses a wrong pose **before** A. It cannot independently verify the actual club angle.

**Stop conditions:** no contact, missing or transitioned terminal result, missing visual percentage, source/bridge/trace changes, wrong initial pose, changed club/aim, wrong trial order or B1/B2 visually estimated power diverging by >5 percentage points. Negative/ineligible terminal observations are still saved and prevent advancing under the same scenario. For any pre-contact abort, use a new scenario identifier on reattempt after diagnosis. The first-ball scenario should be reset freshly by the canonical wrapper **before each arm**.

## Offline verification — no Dolphin

From an isolated checkout containing the PR:

```powershell
py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
py -3 -I scripts/p0_pose_power_trial.py --arm B1 --pose back --scenario firstball01 --club iron --aim-id straight
```

The second command uses the **actual** `_build_v1_trace_and_digest` and `SwingTraceClient.submit` serializer with a **fake RPC**, checking 89 samples, 77/12 A mask and exactly 15 changed backswing `distance_m` fields at indices 12–26. It does not contact Dolphin. The unittest fixture itself uses synthetic stubs and must not be mistaken for live client integration. Run full `python -m unittest discover -s tests -v` plus Win/Ubuntu CI before merge.

## Local one-shot operator protocol — never run unattended

1. Confirm a **stable, clean, user-reviewed local bridge** and existing `green-pre-start` savestate; close previously running Dolphin. Legacy V1 and atomic A45 V1 are **not interchangeable**. Choose the same bridge for all three arms.
2. Set the bridge path once. Example for the existing isolated legacy V1 bridge (replace if your inspected local file is different):

```powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$bridge = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_legacy_eval.py'
Set-Location -LiteralPath $repo
```

3. **Dry-run the outer launcher**: no `--send-live` on outer command. This prints the boot and action commands without controlling Dolphin.

```powershell
py -3 -I scripts/run_golf_experiment.py --bridge $bridge --script p0_pose_power_trial.py -- --send-live-swing --arm B1 --pose back --scenario firstball01 --club iron --aim-id straight --bridge-source $bridge
```

4. Once source SHA and the required fresh-boot/scene/power-observation gates have been reviewed, run **one explicitly authorized baseline** by adding `--send-live` to the outer wrapper. It will boot via the canonical intro, then ask twice for explicit human confirmation and ask for initial club pose BEFORE A:

```powershell
py -3 -I scripts/run_golf_experiment.py --send-live --bridge $bridge --script p0_pose_power_trial.py -- --send-live-swing --arm B1 --pose back --scenario firstball01 --club iron --aim-id straight --bridge-source $bridge
```

For B2, change only `--arm B1` to `--arm B2` on a **separately consented fresh first-ball session**. Only if both baseline records qualify, consider `--arm X1`. **Do not execute the entire three-arm series automatically**, do not try to reset the game in the child, and stop on any launch/bridge/savestate mismatch. If using a previously verified **isolated atomic A45** bridge, both outer `$bridge` and child `--bridge-source` must point to that file and child must add `--atomic-a45`; new atomic bridge preparation or modification is outside this PR.

5. Compare the human power-meter estimates **only within the same club/aim/starting-pose stratum**. Record power as *human visual*, not native accepted swing percent. `100ft` off-green is a **censored penalty**, never a carry measurement. Do not fit power vs distance from these outcomes.

## Next scientific step

To measure the effect of **initial club position itself**, first obtain a repeatable and source-qualified way to set or measure the game-owned club pose (or angle). Then run **separate pose strata** with identical requested waveform and independent repeated baselines. A `back` vs `center` difference here is not a controlled pose manipulation until its actual geometry and transition timing are established. To map desired powers like 25/50/75/100%, validate the game-accepted scalar against the native launch vector and collect repeated, uncensored observations.

Collision/terrain/tree events end any airborne-only validation; PR #422 must establish original tree geometry and response. Do not create fake cylinders/spheres as verified native hitboxes. Links: #399 control preregistration, #418 source-power latch, #415 flight equation ledger, #422 collision. `training_approved=false`; `game_power_verified=false`; `guest_physics_frame_verified=false`.
