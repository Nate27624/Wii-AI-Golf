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

**Stop conditions:** no contact, missing/uncertain visual power, source/bridge/trace changes, wrong initial pose, changed club/aim, wrong trial order or B1/B2 visual power diverging by >5 percentage points stop the **power-only** sequence. A missing or late terminal result stops **landing/trajectory validation**, but independently observed power/contact can still qualify as power-only evidence. Negative or uncertain power/contact rows remain stored and block advancing. For a pre-contact abort, use a new scenario identifier after diagnosis. Reset freshly through the canonical wrapper **before each arm**.

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

## Firstball03 B1 result and explicit club selection control

**Operator completed real B1:** `contact_human=yes`, visible power **101%** (`human_power_confidence=clear`), starting pose **partial-back**, `calibration_eligible_human_only=true`, `training_approved=false`. Operator describes it as "nearly perfectly 100." This is a **human-read gauge**, not native accepted shot power. New post-shot operator context: Hitting the Green initially offered **WEDGE**, which they **manually changed to IRON** before the B1 swing. B1's original private record has `expected_club=iron` but did **not** separately log the offered club or the manual selection; keep that row intact and preserve this as a **post-hoc operator addendum**, not a proven frame-synchronized club state.

For **B2**, repeat the **same** initial wedge→manual iron selection, keep the final active club **iron** and same *partial-back* pre-A pose, aim, first-ball scenario, bridge SHA and wind=0. The runner now prompts **before A** for the currently selected club and, under `--club-change wedge-to-iron`, confirms the manual change. Mismatch/uncertainty refuses the experimental A and motion. The new row records `selected_club_human` and `club_change_human` as **human observations**, with `selected_club_game_verified=false`. B1 is grandfathered into B2's comparison **only as human/post-hoc evidence**; it is not proof the native club was source-authenticated. New rows must agree on club procedure and starting pose. This is a consistency control, not proof that initial club pose/club geometry is fixed frame-by-frame.

**Corrected B2 local command (no game-path entry, one separately consented fresh boot):**

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Local changes; refusing worktree replacement' }
git fetch origin refs/pull/433/head
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Switch failed' }
py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed; no live shot' }
foreach ($p in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Missing file: $p" }
}
$settings = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $settings.game -PathType Leaf)) {
    throw 'Saved game file missing'
}
$trial = @(
    '--config', $config, '--catalog', $catalog, '--bridge', $atomic,
    '--script', 'p0_pose_power_trial.py', '--',
    '--send-live-swing', '--arm', 'B2',
    '--pose', 'back', '--pose-detail', 'partial-back',
    '--club-change', 'wedge-to-iron',
    '--scenario', 'firstball03', '--club', 'iron',
    '--aim-id', 'straight', '--bridge-source', $atomic, '--atomic-a45'
)
py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'Launcher dry-run failed' }
if ((Read-Host 'Type RUN-B2 to perform ONE fresh Dolphin baseline shot') -eq 'RUN-B2') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) { throw 'B2 incomplete; stop' }
} else {
    Write-Host 'No live shot requested.'
}
~~~

After B2: compare human gauge vs B1 101 (threshold ±5 points), contact and terminal observation. If comparable, propose ONE separate **XLOW** third trial, requested 0.20m backswing instead of 0.25m, with exactly the same wedge→iron procedure and starting pose. Do not automatically chain shots or interpret human power as native impulse. The game may position the club differently after manual switching; native pose and commit instrumentation remain open.

## Firstball03 B2 replication and result-screen / red-shot qualification

**Operator's live B2 output (preserve existing private row):** `arm=B2`, `contact_human=yes`, `human_power_pct=101.0`, `human_power_confidence=clear`, initial pose `partial-back`, selected club `iron`, manual change `wedge-to-iron`, reported `calibration_eligible_human_only=true`. This independently repeats B1's human **101%** gauge estimate at the same requested baseline waveform, within the preregistered five-point repeatability threshold. It does **not** prove a native accepted power scalar, fixed initial club angle, launch-speed parity, or repeatable landing.

**Critical post-hoc observation:** Operator says the shot was **red**, with apparent **right/left rotation or deviation** that may affect travel. Do **NOT** assert that red corresponds to a documented native threshold, spin direction or numerical side-force without original game evidence. Keep initial club pose, possible twist and ball flight different observables. Operator also says they **could not enter M:100ft before the next screen**. The shared S002 transient result collector marks any typed G/M as `terminal_screen_seen_before_transition_human=True` solely from the class **regardless of when it was typed**, so B2's eligibility flag may have overclaimed timely landing evidence. Do not silently relabel the original immutable B2 row, and do **not** use the result as observed native carry/landing or claim B1/B2 trajectory agreement. Treat off-green 100ft as censored penalty even if confirmed.

**Local pilot fix (new-only S003 path; S002 unchanged):** `eligible(row)` now means **human power repeatability only**, requiring contact yes, clear finite gauge estimate, appropriate wind/pose, but not a transient result. `outcome_eligible(row)` additionally requires both the G/M result and an **independent human answer that it was actually entered while the result screen was still visible**. Legacy rows lacking the timing answer cannot be promoted to outcome-valid. After the existing result/contact prompts, the S003 pilot asks for this timing and for red-shot appearance and qualitative left/right curve/rotation. These are human, optional/uncertain categories with no native physics semantics. Incorrect extra responses degrade to unknown rather than discarding a completed shot.

**Practical result-screen input:** The existing S002 collector already accepts a bare `M` or `G`; use that if it is reliably visible but there is not time to type a number. If the result has already transitioned, enter `T` rather than typing `M:100ft` late. Do not enter `M` after the transition just to preserve eligibility. Later answer honestly whether the class was entered while visible. For calibrated **power** comparison, the terminal label is not required; for **flight/landing accuracy**, it is.

**Next test:** Run **one** separately consented XLOW on `firstball03`, with pre-A partial-back, **manual wedge→iron**, same aim and atomic bridge SHA. XLOW changes only 15 requested backswing distances **0.25m → 0.20m**; forward stroke, speed settings, A45 and input topology remain unchanged. This is a *proposed lower-power manipulation*, not a validated percentage setting. Power reading and red/curve categories are the outcomes; make no carry/trajectory claims from timed-out terminal screens. Keep wind=0 for this Hitting the Green scenario. Stop on pose/club/bridge mismatch. After XLOW, separate native launch and contact/source observations are needed before training.

## XLOW live result: third 101% gauge; no validated landing (operator 2026-11-10)

The operator ran XLOW in the firstball03 series and reported a **visible strike** with a **clear human power-gauge impression of 101%**, starting pose partial-back, final club iron after manual wedge-to-iron selection, red shot yes, visible left/right curve or rotation unknown. The S003 report explicitly says **outcome_eligible_human_only=false** and **result_entered_while_visible_human=no**. Preserve the original private XLOW row unchanged. The previous two B1/B2 control gauge impressions were also 101% at 0.25m requested backswing; XLOW used 0.20m requested backswing on precisely 15 active slots, with the forward stroke unchanged. The 20% smaller backwards **request produced no detectable change in this human gauge estimate**, conditional on the reported scenario; it does not establish a zero change in hidden accepted power, club pose, spin or true ball distance. All real landing and native dynamics remain unverified, and red-shot semantics are not source proven.

**Research direction:** After B1/B2/XLOW all show the same human 101% gauge, another tiny backwards-distance change is low information. The next proposed test is stronger and explicitly **compound**: multiply **all 35 active samples' requested distance_m, speed_m_s and return_speed_m_s by 0.60**, while holding the 45 callback A lead, 89 sample count, A masks, aim, selected iron, manual wedge-to-iron procedure, coarse and detailed initial pose, source bridge SHA, and operator-reported Hitting the Green wind=0 fixed.

**New one-shot arm XM06:** Backswing requested distance 0.25→0.15m, speed 1.2→0.72m/s, return 1.2→0.72m/s over 15 samples; forward distance 0.60→0.36m, speed 3.5→2.1m/s, return 2.0→1.2m/s over 20 samples. The exact serializer verifies **105 individual requested numeric field differences**. This is a **movement-intensity sensitivity test**, NOT a pure speed, pure position, pure club-angle or 60%-power controller. If it still visibly returns 101%, prioritize native power-latch and initial club trajectory verification before accumulating more guessed scaling runs. If it lowers the human gauge, follow with fresh controls and independently isolated factors in a separately owned study. The existing shared S002 collector accepts motion_scale=0.6 and the in-bridge atomic A45 unchanged; no shared generator/renderer/tree collision files are modified.

### XM06 local protocol (single fresh first-ball session; never unattended)

Use the existing saved game config, savestate catalog and isolated atomic A45 bridge. Close Dolphin before starting. This uses the SAME firstball03 private ledger; you must keep the B1/B2/XLOW entries unmodified. Execute **only** after exact-head Windows/Ubuntu focused, actual serializer, and full offline CI all pass.

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Pose-Pilot'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$config = Join-Path $main 'research\launch.local.json'
$catalog = Join-Path $main 'research\savestates.local.json'
$atomic = 'D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_atomic_a45.py'
Set-Location -LiteralPath $repo

if (git status --porcelain) { throw 'Worktree contains uncommitted changes' }
git fetch origin refs/pull/433/head
if ($LASTEXITCODE -ne 0) { throw 'PR fetch failed' }
git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Worktree update failed' }

py -3 -I -m unittest discover -s tests -p test_p0_pose_power_trial.py -v
if ($LASTEXITCODE -ne 0) { throw 'Focused offline tests failed' }

foreach ($item in @($config, $catalog, $atomic)) {
    if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
        throw "Missing required file: $item"
    }
}
$saved = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $saved.game -PathType Leaf)) {
    throw 'Saved Wii Sports game file not found'
}

$trial = @(
    '--config', $config, '--catalog', $catalog, '--bridge', $atomic,
    '--script', 'p0_pose_power_trial.py', '--',
    '--send-live-swing',
    '--arm', 'XM06',
    '--pose', 'back', '--pose-detail', 'partial-back',
    '--club-change', 'wedge-to-iron',
    '--scenario', 'firstball03', '--club', 'iron',
    '--aim-id', 'straight', '--bridge-source', $atomic,
    '--atomic-a45'
)

py -3 -I scripts/run_golf_experiment.py @trial
if ($LASTEXITCODE -ne 0) { throw 'No-input launcher dry-run failed' }

if ((Read-Host 'Type RUN-XM06 to consent to ONE fresh live shot') -eq 'RUN-XM06') {
    py -3 -I scripts/run_golf_experiment.py --send-live @trial
    if ($LASTEXITCODE -ne 0) { throw 'XM06 failed/ineligible; STOP' }
} else {
    Write-Host 'No game action requested.'
}
~~~

Before A, confirm an iron is selected, manually changed from wedge, with the club partially back, with the same aim. If any detail differs, cancel with q. On fast terminal screen, type bare M or G **while actually visible**, or T if already transitioned; never fabricate M:100ft after the screen changes. Record the gauge number and red/curve human observations with uncertainty. Human 101%, red yes, or a hit alone are NOT game-accepted power or native trajectory verification.

## Next scientific step

To measure the effect of **initial club position itself**, first obtain a repeatable and source-qualified way to set or measure the game-owned club pose (or angle). Then run **separate pose strata** with identical requested waveform and independent repeated baselines. A `back` vs `center` difference here is not a controlled pose manipulation until its actual geometry and transition timing are established. To map desired powers like 25/50/75/100%, validate the game-accepted scalar against the native launch vector and collect repeated, uncensored observations.

Collision/terrain/tree events end any airborne-only validation; PR #422 must establish original tree geometry and response. Do not create fake cylinders/spheres as verified native hitboxes. Links: #399 control preregistration, #418 source-power latch, #415 flight equation ledger, #422 collision. `training_approved=false`; `game_power_verified=false`; `guest_physics_frame_verified=false`.
