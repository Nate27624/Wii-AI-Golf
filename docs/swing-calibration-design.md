# S003: Wii Sports Golf swing design and calibration

**2026-10-24 status:** Offline model/control hypothesis ONLY. No AI-generated ball strike, landing distance, or trained real-game policy demonstrated. [Modeling Issue #4](https://github.com/Nate27624/Wii-AI-Golf/issues/4). Depends on integrator [PR #16](https://github.com/Nate27624/Wii-AI-Golf/pull/16), evaluation [PR #14](https://github.com/Nate27624/Wii-AI-Golf/pull/14).

## Control semantics and hypotheses

Felk Preview4's official controller stub documents `set_wiimote_swing(port,x,y,z,distance,speed,return_speed,angle)`: distances in meters, speeds in m/s and angle in radians. It is overridden by `set_wiimote_acceleration` and angular-velocity overrides. Integrator PR #16 adds an **opt-in** atomic A-button + dedicated swing trace scheduler. Its recognition in Wii Sports remains UNVERIFIED. Wii Sports' official manual says hold A while swinging and warns that an overly forceful swing can hook/slice. Earlier A+acceleration samples (1–2 m/s² in the Felk API) did NOT visibly move the club. These observations are not proof that stronger swings or the dedicated helper will work.

One proposed 59-frame waveform:
1. Ready: hold A and zero swing for 12 frames.
2. Backswing: hold A, opposite signed axis, 0.25 m, 35% of nominal speed, 15 frames.
3. Downswing: hold A, chosen signed axis, 0.6 m and 3.5 m/s, 20 frames.
4. Finish: release A and zero swing for 12 frames.

All timings, axes, speed values and angle effects are exploratory. Repeating a helper's state each frame might not simulate a physical natural swing; investigate Felk's implementation if none register. Profiles validate the integrator PR #16 bounds (direction components <= 1, travel <= 1.5 m, speeds <= 8 m/s, |angle| <= pi, total <= 600 frames). Fingerprints are SHA-256 over generated frame arrays. Dispatch acknowledgement alone does not prove a strike.

## Gates and predeclared study budget

**Gate 0: visible contact.** First merge/test integrator PR #16 and run **one** guided `scripts/probe_swing.py --preset forward --send-live-swing` at the actual first ball. Confirm game reaction visually, then use S003's 12 offline-planned recognition trials only if needed: each of six *signed* X/Y/Z directions repeated twice in randomized order on one verified at-ball checkpoint. Record: `hit/club-only/menu/none/other`. Stop after 12 with zero real hits and debug transport/controller interpretation. Never silently run all trials on an instruction screen or unverified savestate.

**Gate 1: controllable response.** Only after a reproducible hit and reset, register **two distinct observed and visually verified at-ball scenes**. Select one axis that produced an actual strike. Within each scenario keep club/aim/wind conditions fixed as feasible and sweep one parameter at a time:

| Factor | Levels | Attempts, both scenarios |
| --- | --- | ---: |
| Speed (m/s) | 1.2, 2.0, 2.8, 3.5, 4.3, 5.0; 3 repeats | 36 |
| Forward travel (m) | 0.3, 0.6, 0.9; 3 repeats | 18 |
| Downswing duration (frames) | 12, 20, 28; 3 repeats | 18 |
| Angle (radians) | -0.25, -0.125, 0, +0.125, +0.25; 3 repeats | 30 |
| Default reference replays | 10 per scenario | 20 |

Total: **12 recognition + 122 response = 134 exploratory attempts**. Reserve 20 *separate, frozen, truly held-out observed-scenario* trials and 46 attempts for failures/replication, **cap 200**. Never call training results unbiased evaluation. Stop on unrepeatable savestate restoration, controller errors, or invalid outcomes. A 100-shot unattended measured loop with >95% valid outcomes remains the repository's reliability milestone.

**Gate 2: feedback and optimization.** Capture every trace hash/frame payload, save-state/scenario ID, version/region, A timing, club, aim, wind, verified ball contact label, displayed raw error + UI units, measurement method/confidence, converted error only when audited, and failure/reset state. Fit simple empirical speed/power/error curves with uncertainty and compare with random/fixed swing baselines at equal budgets. Introduce Bayesian search only after repeatable real measurement. Optimize D-pad aim **separately** from swing speed and angle. Avoid equating the toy `ShotAction(power)` with m/s.

## Current spatial readout is NOT the ball trajectory

Evaluation has plausible version-gated RSPE01 Rev1 candidate pin/cup/start translations (pin/cup align in X/Z). They are **unverified game-coordinate units**, do not establish a meters scale, and are *not dynamic ball coordinates or scored landing distance*. The ~1 Hz read-only monitor can miss entire ball flight. More state/score reverse engineering belongs to evaluation #3, while bridge actuation belongs to integrator #2.

## Offline commands (never send game input)

Run from the canonical `D:\Projects\Wii Golf AI\Wii-AI-Golf` checkout **after merging S003**:

```powershell
py -m unittest discover -s tests -p "test_modeling*.py" -v
py scripts/design_swing_sweep.py --stage recognition --scenario VERIFIED-FIRST-BALL --seed 42 --out "..\Wii-AI-Golf-Data\plans\s003-recognition.json"
py scripts/design_swing_sweep.py --stage recognition --scenario VERIFIED-FIRST-BALL --show-trace 1
```

The label `VERIFIED-FIRST-BALL` is a placeholder for an actual registered, visually verified *at-ball* checkpoint. Do **not** swing from the current `green-pre-start` if it still requires advancing the Start menu.

Only after one hit-producing axis, two observed distinct at-ball scenarios, and score/readout verification:

```powershell
py scripts/design_swing_sweep.py --stage calibration --scenario ACTUAL-SCENE-1 --scenario ACTUAL-SCENE-2 --confirmed-axis 'y+' --seed 42 --out "..\Wii-AI-Golf-Data\plans\s003-calibration.json"
```

Here `y+` is **an example, NOT a known working direction**. The scripts generate only reproducible manifests with empty outcomes. For integrator PR #16 compatibility, convert a generated trace row to `SwingSample(hold_a=bool(row[0]), direction=tuple(row[1:4]), distance_m=row[4], speed_m_s=row[5], return_speed_m_s=row[6], angle_rad=row[7])` before passing to `SwingTraceClient.run`. Unattended real execution is outside modeling scope; coordinate on Issue #2.

## Sources and tests

- Official Wii Sports manual: https://csassets.nintendo.com/noaext/image/private/t_KA_PDF/Wii_Wii_Sports?_a=DATAg1AAZAA0
- Felk Preview4 controller API: https://github.com/Felk/dolphin/blob/scripting-preview4/python-stubs/dolphin/controller.pyi
- [Integrator PR #16](https://github.com/Nate27624/Wii-AI-Golf/pull/16)
- [Evaluation PR #14](https://github.com/Nate27624/Wii-AI-Golf/pull/14)

Focused offline tests passed in a source-equivalent local mirror; full repository suite and live Windows Dolphin testing were not available to this modeling session.
