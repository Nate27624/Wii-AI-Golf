# Launch Wii Sports and automatically navigate the Hitting the Green pre-start menu

**Status:** Mock-tested menu schedule; real Dolphin/Wii Sports navigation must be visually verified. This is an opt-in integration experiment, not an automatic score reader or calibrated golfer.

## Existing checkpoints only

The launcher reads the *canonical*, gitignored `research/savestates.local.json` catalog and defaults to the previously user-tested `green-pre-start` profile. It never saves, registers or overwrites a slot. Its `--dolphin`, `--game`, `--bridge` inputs identify the local Felk executable, user's legally acquired Wii Sports image, and the **existing** swing-enabled bridge.

Generate the bridge **without** `--startup-profile` or `--startup-slot`; the launcher loads the named state exactly once through `StateManager.request_load`, after verifying bridge readiness. An auto-loading startup bridge could cause a second uncoordinated restore. Configure Wii Remote 1 as **Emulated Wii Remote** with **Extension None**, and prevent Dolphin from pausing when it loses focus.

Build only if needed:

~~~powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
git pull --ff-only
py -m pip install -e .
py scripts/savestate_session.py list

$tools = 'D:\Projects\Wii Golf AI\tools'
py scripts/patch_felk_bridge.py --source "$tools\mcp_bridge.py" --output "$tools\mcp_bridge_swing.py" --enable-swing
~~~

Do **not** run the patched bridge simultaneously with the original bridge. Close Dolphin before a fresh launch.

## Dry-run: print exact button plan, no game changes

~~~powershell
py scripts/launch_hitting_green.py
~~~

It checks the existing savestate name and prints the phase schedule. If your actual working pre-start profile has a different name, pass `--profile EXISTING_NAME` after checking `savestate_session.py list`.

## One-command launch, restore and menu navigation

First use actual local paths for Felk Dolphin and a legally obtained Wii Sports image (the game path below is a placeholder):

~~~powershell
$tools = 'D:\Projects\Wii Golf AI\tools'
$game = 'D:\PATH\TO\YOUR\Wii Sports.rvz'
py scripts/launch_hitting_green.py --dolphin "$tools\FelkDolphin\Dolphin.exe" --game "$game" --bridge "$tools\mcp_bridge_swing.py" --send-live
~~~

The command launches Dolphin via the existing `scripts/savestate_session.py` start function, restores the previously registered slot, confirms that Felk's frame counter advances, sends the pre-start menu inputs, and **stops** without firing a shot. It refuses to launch another Dolphin if the bridge port is already in use.

If Felk Dolphin is **already running** and the correct bridge is healthy:

~~~powershell
py scripts/launch_hitting_green.py --attach-running --send-live
~~~

That still **resets** the existing named state before sending A / A+B / A.

## Default requested-frame timeline

| Phase | A | B | Requests |
| --- | --- | --- | ---: |
| Allow restored game to settle | Off | Off | 90 |
| First A press | On | Off | 12 |
| Release and wait | Off | Off | 75 |
| A+B simultaneously | On | On | 15 |
| Release for a fresh A edge | Off | Off | 8 |
| Final A press | On | Off | 12 |
| Wait for game transition | Off | Off | 120 |

These counts are **RPC input requests**, not guaranteed exact video frames. Felk processes one-frame button overrides on its emulation coroutine. Holding a button is approximated by repeating the same RPC and waiting for each acknowledgement. Network/host jitter can leave gaps. The sequence cannot prove which menu screen the game reached; watch Dolphin and adjust values based on observation.

To change durations, use `--startup-frames`, `--first-a-frames`, `--wait-frames`, `--ab-frames`, `--gap-frames`, `--last-a-frames`, `--settle-frames` (each 1..600). `--remote` selects 0..3.

## Optionally execute one *experimental* swing

Add `--swing --confirm-before-swing` to the launch or attach command. After the navigation sequence, the script prompts for Enter only when the first ball is actually ready. It then reuses the existing **forward** 59-request swing primitive. Without `--confirm-before-swing`, `--swing` fires automatically after the requested settling frames; this is explicitly opt-in and may hit a menu if the sequence was mistimed. Acknowledged controller dispatch does not prove ball contact or a score.

## Offline tests and acceptance

~~~powershell
py -m unittest discover -s tests -p 'test_menu_sequence.py' -v
py -m unittest discover -s tests -v
~~~

Acceptance for live usage: verify named restore, visually confirm A then A+B then A navigation, confirm ready golfer (rather than a different screen), and only then attempt swing. Record negative observations and any necessary timing changes on Issue #2. Do not train on synthetic controller ACKs.

Coordination: [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2) (integrator) and [Issue #4](https://github.com/Nate27624/Wii-AI-Golf/issues/4) (physical calibration).
