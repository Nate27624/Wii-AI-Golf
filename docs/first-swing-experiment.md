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
