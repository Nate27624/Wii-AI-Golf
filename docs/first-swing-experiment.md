# S001: first visibly recognized Wii Sports golf swing

Status: experimental code awaiting live Wii Sports verification. This is NOT a trained agent or recognized swing.

## What changed

User confirmed Wii Sports now responds to Python-generated A after Wii Remote 1 was changed from Real Wii Remote to Emulated Wii Remote, Extension None. Controller connectivity is therefore confirmed. User also confirmed named savestate reset works. The old A+acceleration pulse had 15/15 dispatch acknowledgements but NO visible response.

Felk Preview 4 officially provides controller.set_wiimote_swing(remote,x,y,z,distance,speed,return_speed,angle), with distance in meters, speed in m/s and angle in radians. New generator option --enable-swing augments the pinned atomic bridge to support trace.submit_swing, which schedules A and Felk's dedicated swing state in each emulator tick. It does NOT combine set_wiimote_acceleration with set_wiimote_swing, because acceleration overrides swing. This dedicated path is still unvalidated inside Wii Sports.

## Local installation

From canonical repository:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_integration_swing*.py" -v

$tools = "D:\Projects\Wii Golf AI\tools"
py scripts/patch_felk_bridge.py --source "$tools\mcp_bridge.py" --output "$tools\mcp_bridge_swing.py" --enable-swing
~~~

Completely close Dolphin before changing bridge scripts. Start Felk Dolphin; open Wii Sports; load ONLY mcp_bridge_swing.py through View > Scripting. Wii Remote 1: Emulated Wii Remote; Extension: None. Run:

~~~powershell
py scripts/probe_dolphin_bridge.py --read-only-live
~~~

Go to Hitting the Green until the golfer is standing at the FIRST BALL (not the Start instructions screen). Avoid manually swinging. Run ONE trial:

~~~powershell
py scripts/probe_swing.py --preset forward --send-live-swing
~~~

The script will request ENTER to confirm the golfer is ready, schedule 59 frames of A+swing motion, and prompt for the actual on-screen observation: hit, club-only, menu, none or other. It appends this HUMAN observation to a local JSONL record under the sibling Wii-AI-Golf-Data/integration/swing-probes.jsonl. It does not auto upload or claim a score.

If the user has a tested savestate directly AT THE BALL (the profile green-first-shot), optionally use:

~~~powershell
py scripts/probe_swing.py --preset forward --reset-profile green-first-shot --send-live-swing
~~~

Do NOT use a pre-Start-screen profile as an automatic first-shot reset without advancing the Start menu. Unvalidated slots should never be loaded in an unattended script.

If forward has no visible effect, try --preset reverse or --preset sideways on separate reset attempts. These are exploratory directional hypotheses only. No automated parameter optimization should begin until Wii Sports visibly recognizes a ball strike.

## Evidence thresholds

- Bridge returns complete / 59 frames: only scheduled dispatch successful.
- Club visibly moves: game recognizes motion; shot still unproven.
- Ball leaves the tee: first verified AI-generated swing.
- Game score measured and human cross-checked: evaluation milestone owned by Issue #3.

Modeling Issue #4 owns physical calibration and optimization; this is Worker 1's transport diagnostic. Document negative attempts as carefully as positive ones.

Bridge source pin: dmang-dev/mcp-dolphin blob 8e70624680a365707f844b322f5b093746a1c022. Felk Preview 4 required.

## 2026-10-24: premature A release after first partial in-game response

**User's qualitative live observation:** The first dedicated Felk swing primitive experiment *almost worked*, but **A was released too early**. Treat this as **partial controller/motion recognition only**, not a verified ball strike or scored attempt.

The initial S001 forward trace kept `A=True` for 12 neutral setup + 15 backswing + 20 forward = **47 frames**, then immediately released A for 12 frames (59 total). New source-only client-side profile holds A through a configurable **neutral follow-through** before releasing. This deliberately leaves all existing swing direction/distance/speed values unchanged and varies only **A release timing** (one factor at a time):

| CLI setting | A-held samples | First A-off sample (1-based) | Total trace samples |
| --- | ---: | ---: | ---: |
| `--follow-through-frames 0` (old control) | 47 | 48 | 59 |
| `--follow-through-frames 15` | 62 | 63 | 74 |
| **`--follow-through-frames 30` (new default)** | **77** | **78** | **89** |
| `--follow-through-frames 45` | 92 | 93 | 104 |
| `--follow-through-frames 90` | 137 | 138 | 149 |

The neutral follow-through sends **A held** with zero dedicated swing motion and does **not** release the club button. These values are **not calibrated shot physics**. The trace API accepts at most 600 samples; this probe restricts follow-through to 0..180 (239 total maximum). The command prints exact A-held and release-frame counts and writes these timing values plus a hash of the full input trace to the user's local ignored JSONL evidence file.

### Next experiment from an ALREADY-RUNNING Dolphin session

Keep Wii Remote 1 on Emulated / Extension None, and advance through the validated A → A+B → A intro until Nueron is standing at the ball. No new bridge generator run is required because this change is to the client-generated trace only.

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_integration_swing_client.py" -v
py scripts/probe_swing.py --preset forward --follow-through-frames 30 --send-live-swing
~~~

Human confirms visually before the probe sends exactly one shot, then labels `hit`, `club-only`, `none`, etc. If A still releases too soon and the club visibly responds, rerun on **the same verified starting screen** with `--follow-through-frames 45` or `60`; avoid changing motion strength/direction at the same time. If the observed swing *stalls while A is held*, use shorter values (15, 0) and report exactly what happens. Never claim a successful hit from bridge ACK alone.

**Canonical intro coordination:** `scripts/launch_hitting_green.py` already calls `build_probe("forward")` for its optional single swing; it will automatically use the new follow-through default after merging this change. Another Worker 1 agent owns the active intro PR #25; do **not** duplicate menu timing logic inside `probe_swing.py`.

## Required normal startup for every swing experiment (2026-10-24 correction)

A user ran the earlier suggested `py scripts/probe_swing.py --preset forward --follow-through-frames 30 --send-live-swing` after Dolphin was no longer running and got `[WinError 10061]` because the probe previously assumed a listening bridge. This was a workflow bug: a real-game experiment must start from the known-good **Felk Dolphin + Emulated Wii Remote 1 / Extension None + named green-pre-start Slot 2 savestate + A / wait / A+B / wait / A + settle** intro, **then** send the opted-in swing.

As of the launcher change, the very same `probe_swing.py` command **automatically delegates to** `scripts/launch_golf.py --swing`, which itself invokes `launch_hitting_green.py` and the shared `wii_ai_golf.menu_sequence` implementation. No independent button delays or separate bridge setup exist in the probe. `launch_golf` next starts the actual probe in `--attach-running` mode, so the child does NOT spawn Dolphin again or reset the already ready screen.

Preferred from a completely CLOSED Dolphin session:

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_integration_swing_startup.py" -v
py -m unittest discover -s tests -p "test_integration_launcher.py" -v
py scripts/probe_swing.py --slot 2 --preset forward --follow-through-frames 30 --send-live-swing
~~~

The alias `py scripts/launch_golf.py --slot 2 --swing --follow-through-frames 30` is identical in launch semantics. Both use the locally remembered game image and controller config and the human-ready-screen confirmation; **no manual Scripting attachment or separate savestate command** is required. The intro currently requests **120, 30, 315, 60, 135, 45, 300** frames for its settled phases, inherited from the user-verified menu test (not an automatic visual game-state proof).

**Advanced exception only:** If Dolphin is ALREADY open, correctly configured, and sitting at the ball after a previously verified intro, use `py scripts/probe_swing.py --attach-running --preset forward --follow-through-frames 30 --send-live-swing`. This bypasses startup deliberately. Without `--attach-running`, the probe will try a full fresh start and refuse a second bridge on occupied port. Close the prior Dolphin instance before normal fresh startup.

The new `tests/test_integration_swing_startup.py` asserts the bare CLI makes **no FelkRPC call** and delegates to the full launcher, rejects reset/profile mixing, and propagates failure. Launcher tests assert A / A+B / A intro occurs before the `--attach-running` child, and pass follow-through parameter through unchanged. Live result must still be user-observed; this is code, not evidence of a ball strike.

## Repeatability baseline: three identical live shots before tuning strength

User has confirmed one complete in-game swing from the canonical fresh-launch Slot 2 + A/A+B/A intro with forward preset, 30 additional A-held follow-through frames (89 total). User uploaded a cropped power-meter photo, visually around three-quarters filled but **no ground-truth in-game power percentage or landing outcome**.

**Preregistered next experiment:** Perform **3 independent fresh-boot shots** using **exactly the same 89-frame forward trace**; no tuning between them. Hypothesis: this input reproducibly causes visible ball contact and approximately consistent visual power; failure if any trial only moves the club, starts at the wrong screen, or returns an RPC error. Operator closes Dolphin between attempts and uses:

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py scripts/launch_golf.py --slot 2 --swing --preset forward --follow-through-frames 30
~~~

After each shot, the swing probe now asks optional human observations **ball visibly moved?**, **landed on the green?**, **on-screen displayed distance and its unit**, and **estimated meter fill 0..100**. Press Enter to leave any item unknown; never guess a distance or translate the meter fill into a game power percentage. Each trial appends timing and observations to the existing local `Wii-AI-Golf-Data/integration/swing-probes.jsonl`. `game_score` stays `null` because the evaluation agent has not established score units. The human answers are tagged `human-reported-not-verified`. Do not upload game binaries, states or screenshots to source control.

**Decision after 3 repeats:** Only when all 3 runs show ball contact and consistent on-screen observations, run a **one-factor** calibration sweep with S003's candidate profiles (speed or distance, not both), using S002's validated real-game result capture. Don't send a 20+ random sweep based only on bridge ACKs. If repeated shots differ or fail, fix/measure scene readiness first. A strong swing does not necessarily mean a green hit or good target distance.

## 2026-10-24: A-press ordering observed late relative to motion

**New user observation:** After the unified `golf swing --slot 2` correctly booted Dolphin and ran the canonical A / A+B / A menu sequence, the observer reported that club/swing motion visually occurred **before the game's A interaction**. The previous 89-frame trace had only **12 neutral samples with A held** before 15 backswing + 20 forward motion. Since Felk bridge ACKs reflect command dispatch rather than the frame at which Wii Sports accepts controller state, the actual in-game A/motion ordering is **not independently measured**.

**Isolate one factor: A-only setup duration.** The swing probe now supports `--a-setup-frames N`, a contiguous A-held, ZERO-motion prep phase before the first backswing sample. Default **45** (instead of 12), bounded **1..180**. No changes to A / A+B / A intro, 15 backswing samples, 20 forward samples, motion speed/distance/axes, 30 A-held follow-through, or 12 released samples.

| Trial | A-held neutral setup | First backswing sample (1-based) | A first released | Total trace | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| Exact earlier 89-frame baseline | `--a-setup-frames 12` | 13 | 78 | 89 | Replays prior command / known human hit evidence |
| New delay hypothesis | `--a-setup-frames 45` | 46 | 111 | 122 | Allows A to settle before any motion; **NOT yet validated in-game** |
| Longer controlled follow-up | `--a-setup-frames 60` | 61 | 126 | 137 | If 45 still looks premature; no simultaneous motion changes |

**Safest user-facing entrypoint, from CLOSED Dolphin:**

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py scripts/golf.py test --pattern "test_integration_swing_client.py"
py scripts/golf.py test --pattern "test_unified_cli.py"
py scripts/golf.py swing --slot 2 --preset forward --a-setup-frames 45 --follow-through-frames 30
~~~

This invokes Felk launch, Emulated Wii Remote 1/Extension None, named Slot 2 `green-pre-start`, user-proven A / A+B / A menu intro, then a **single guarded swing**. The probe prints both A setup and first-motion sample. The JSONL trial now includes `a_setup_frames` and `first_motion_sample_1_based` to avoid comparing unlike traces. At the Enter prompt confirm the golfer is actually ready. Human should note whether A is visibly active **before** the club moves and whether the ball moved. If the motion still precedes A, report that and retain the record as a failed ordering hypothesis; do not call it a hit from RPC completeness alone. For apples-to-apples replay of first successful swing, use `--a-setup-frames 12`.

**Warning:** The API still calls `set_wiimote_swing` with zero motion during the A setup; this is a scheduling/latency hypothesis, not a proof of Wii Sports' internal input-consumption order. If pre-hold alone fails, next work is an in-bridge button-first readiness barrier / readback, **not** arbitrary power changes.
