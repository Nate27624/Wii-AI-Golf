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
