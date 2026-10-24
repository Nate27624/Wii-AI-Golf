# Reusable training savestates (Worker 1 / S001)

## Goal and limits

A named state (such as green-first-shot or hole2-windy) maps to a Felk Dolphin savestate slot. This is deliberately generic across challenges and training scenarios. The local catalog contains only names, slots and descriptive metadata, not the state bytes; the latter remain in Dolphin's save-state directory. Do not commit a game image or savestate. State compatibility depends on game image, region, Dolphin build and user profile.

Felk scripting-preview4 savestate.pyi documents slots 0..99, so we conservatively restrict them to that range. A slot may already hold irreplaceable data: choose an unused slot. Saving will overwrite that slot. Bridge RPC acknowledges requests, **not** verified disk writes or visually confirmed loads.

## Initial capture, once per training scenario

Navigate Wii Sports to the first Hitting the Green shot before swinging, with only one bridge running.

If you ALREADY made a manual savestate in Dolphin (example slot 1), just register its name, without saving:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py scripts/savestate_session.py register green-first-shot --slot 1 --description "Before first swing"
py scripts/savestate_session.py list
~~~

If you have NOT captured the first-shot screen yet, choose a genuinely unused slot (example 20), register it, then explicitly save into it:

~~~powershell
py scripts/savestate_session.py register green-first-shot --slot 20 --description "Before first swing"
py scripts/savestate_session.py capture green-first-shot --overwrite-slot
~~~

The catalog at research/savestates.local.json is gitignored. Registration only labels an existing slot; capture is destructive to the chosen slot. Verify the saved point with an actual reset before training.

## Reset to that state without menus

With Wii Sports running and a responsive bridge:

~~~powershell
py scripts/savestate_session.py reset green-first-shot
~~~

The reusable Python integration API is StateManager.request_load(profile); model/training agents can call it before every attempt. Profiles need not be golf-specific. Multiple local catalogs can be chosen by placing --catalog PATH before the subcommand.

## Option A: loading a patched bridge also requests one savestate

Generate a new source-pinned bridge by the registered **profile name**, not a hard-coded slot:

~~~powershell
$tools = "D:\Projects\Wii Golf AI\tools"
py scripts/patch_felk_bridge.py --source "$tools\mcp_bridge.py" --output "$tools\mcp_bridge_first_shot.py" --startup-profile green-first-shot
~~~

Close existing Dolphin processes. Launch your game, then load only mcp_bridge_first_shot.py in Dolphin's Scripting panel. After the first emulated frame it requests loading the registered slot ONCE. For advanced use you may alternatively specify --startup-slot 20 directly. The Scripting log will show [wii-ai-boot] requested savestate load or [wii-ai-boot] FAILED. A log line is not proof the state actually restored. This startup path is experimental and has not been user-validated.

For another profile/slot, generate a different boot bridge or call the named reset command. The base mcp_bridge_atomic.py remains available unchanged.

## Option B: automatically start Dolphin, script, game and selected named state

Close Dolphin first. Supply the actual path of your legally obtained Wii Sports disc image. The launcher runs Dolphin with --script and --exec, waits for a responsive bridge, then requests a named state load:

~~~powershell
py scripts/savestate_session.py start green-first-shot --dolphin "D:\Projects\Wii Golf AI\tools\FelkDolphin\Dolphin.exe" --bridge "D:\Projects\Wii Golf AI\tools\mcp_bridge_atomic.py" --game "D:\YOUR_GAME_FOLDER\Wii Sports.rvz"
~~~

For this option use an ordinary (non-startup-slot) bridge, not Option A's auto-loading bridge, to prevent two loads. For different games/scenarios, provide different catalogs or Dolphin user directories as appropriate; slot collisions are prevented within each catalog, not between unrelated Dolphin profiles. For exact provenance register --game-id if known.

## Controller connection before swing calibration

In Dolphin Controllers, set Wii Remote 1 to Emulated Wii Remote. At a game screen where Plus normally opens pause/options:

~~~powershell
py scripts/probe_wiimote.py --send-live-button --button Plus --frames 45
~~~

This emits 45 one-frame button requests and then releases Plus. Watch for a visible in-game reaction. Each RPC acknowledgement means the bridge received a command, NOT that Wii Sports consumed it. Reset via the named state after the test. Avoid this command during scoring/training.

## Units, provenance and scientific claims

Felk's official controller.pyi states accelerometer values are in **m/s²**, not g. The earlier live 15/15-frame trace only used 1–2 m/s²; Wii Sports showed no visible response. We have a proven bridge dispatch, NOT a confirmed golf swing. Issue #4 owns physical input calibration; Issue #3 owns score extraction; Worker 1 owns transport and savestates.

Record name/slot, game ID/region/revision, Dolphin build, bridge source SHA, trace attempt ID, screenshot or human reset verification, and score-read method for each game experiment. Never label a reset completed solely because Dolphin acknowledged a savestate API call.

Sources: Felk/dolphin scripting-preview4 python-stubs/dolphin/savestate.pyi, controller.pyi; dmang-dev/mcp-dolphin bridge/mcp_bridge.py; integrator Issue #2.
