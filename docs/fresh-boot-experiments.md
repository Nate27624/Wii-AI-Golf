# Mandatory fresh Dolphin boot for every real-game experiment command

**User requirement, 2026-10-24:** Every live golf probe, capture or learning run must begin with the integrator's validated setup, not assume an existing bridge. A complete command must: (1) configure Emulated Wii Remote 1 / Extension None; (2) start Felk Dolphin with the existing swing bridge and Wii Sports image; (3) restore the **existing named** local `green-pre-start` savestate; (4) send the centralized A / wait / A+B / release / A intro, with the proven slower timings; (5) only after the boot succeeds, run the requested measurement or test.

The entry point below delegates to the already merged `scripts/launch_golf.py` -> `scripts/launch_hitting_green.py`, using the shared menu sequence module. It does not implement its own timing, bridge setup or savestate slot selection.

## First complete command: probe one experimental swing

**Close Dolphin first.** From PowerShell:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only

py scripts/run_golf_experiment.py `
  --send-live `
  --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" `
  --script probe_swing.py -- --preset forward --send-live-swing
~~~

This boots the emulator, restores the registered `green-pre-start` savestate, runs the full intro and then starts `probe_swing.py`. **The dispatcher now automatically supplies `--attach-running` to its internal swing-probe child after successful startup**, because Worker 1 recently made bare `probe_swing.py` self-launching. Do **not** supply `--attach-running` in the user command: the wrapper deliberately rejects it at its outer boundary and inserts it only after the already verified boot.

The swing probe still asks you to confirm that the game is ready before sending one motion trace. The script prints a game-visible result prompt afterward; button acknowledgements alone are not hit evidence. Earlier attempts that ended in `Felk bridge port is already occupied` at this handoff **never sent a swing**; do not interpret them as insufficient power.

After the first run, the ignored `research/launch.local.json` retains the game path, so later complete commands can omit `--game`:

~~~powershell
py scripts/run_golf_experiment.py --send-live --script probe_swing.py -- --preset reverse --send-live-swing
~~~

## Fresh boot, then a read-only bridge check

~~~powershell
py scripts/run_golf_experiment.py `
  --send-live `
  --script probe_dolphin_bridge.py -- --read-only-live
~~~

This *still* launches Dolphin, restores the named checkpoint, navigates the menu and only then executes the read-only check. Do not hand out `--read-only-live` alone as a standard game command.

## Fresh boot, then memory recording when evaluation PR #14 is integrated

Do not call `start_golf_recording.py` from this wrapper, because it separately boots/restores Dolphin. Instead call its scanner/collector after the canonical boot:

~~~powershell
py scripts/run_golf_experiment.py `
  --send-live `
  --script discover_golf_motion.py -- --seconds 30 --profile fast --no-upload
~~~

This example works after `discover_golf_motion.py` has been merged into the canonical code repo, NOT while it exists only in an agent worktree. Keep local raw memory data in the private sibling `Wii-AI-Golf-Data` folder; candidate summaries can be shared only according to the evaluation agent's policy. If studying a different scenario/shot, use a separately specified saved-at-ball checkpoint procedure; **never** send the A/A+B/A menu intro from a checkpoint already at the ball.

## Safety and tests

- The dispatcher refuses a second launch script, configuration/capture utility, **user-provided** `--reset-profile`, `--attach-running`, `--fresh`, and commands outside the canonical `scripts/` directory. Its **internal** post-boot `probe_swing.py` child does receive `--attach-running`, so no second Dolphin startup is attempted. It refuses other named profiles in this first-shot workflow, to avoid pressing A into arbitrary saved game screens.
- If the canonical boot fails, the action **is never started**. An existing Dolphin bridge intentionally triggers a failure rather than creating a second emulator. Close Dolphin before executing every standalone live command.
- `--send-live` is required for writes. Omit it to print the exact boot and action command without launching Dolphin.
- This only enforces the rule for experiments run **through this dispatcher**. Low-level scripts are still available for debugging and intentional alternate-scenario work; do not present their bare invocations as complete user-facing gameplay commands.
- Menu navigation was confirmed by user observation with `120/30/300/60/120/45/300` requested-frame durations; defaults now add +15 pause requests twice. Requested frames are not guaranteed emulation video frames or real-time 250 ms delays. Automatic screen recognition and ball/score feedback are not yet validated.
- Fresh boot applies to **real game actions**, not `unittest`, local report analysis, or bridge generation. These offline scripts should **not** start Dolphin.

To validate the wrapper without Dolphin:

~~~powershell
py -I scripts/run_golf_experiment.py --help
py -m unittest discover -s tests -p "test_golf_experiment_boot.py" -v
py -m unittest discover -s tests -v
~~~

One game-independent mock test suite covers action ordering, boot failure, validation, and dry run. These tests do not verify a real Wii Sports shot; real results require user observation and a genuine score reader.

## Future agent implementation contract

For any NEW live-game script added in `scripts/` that consumes an existing bridge, provide its user command through `scripts/run_golf_experiment.py --send-live --script NEW_SCRIPT.py -- [args]`. It should not spawn Dolphin, load savestates or repeat the menu sequence itself. If the script already owns its own startup, migrate it to a *separate action-only helper* and dispatch that action with this wrapper. If it needs a specialized scenario, coordinate that contract rather than silently reusing `green-pre-start`. The canonical launcher and intro remain the single source of truth.
