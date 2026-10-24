# Reusable savestate checkpoints for Wii AI Golf

**Status:** implemented and unit-test scenarios written; on-device restore not yet verified. This is integrator-owned work for [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2).

## Purpose
Keep different training scenarios reproducible without navigating Wii Sports menus for every trial. Dolphin owns the actual savestate bytes; `research/savestates.local.json` contains only user-defined human-readable labels, slot numbers and notes. The registry is **local machine metadata**, not a portable copy of a savestate. Do not assume states transfer across game revisions, region, Dolphin builds, Wii system configurations or controllers.

## Initial setup: first shot

1. Run Felk Dolphin, configure **Wii Remote 1 -> Emulated Wii Remote** (not Real/Hybrid), navigate to Hitting the Green first tee. Keep the game running/unpaused.
2. Load exactly one bridge script (`mcp_bridge.py` or `mcp_bridge_atomic.py`), verify `py scripts/probe_dolphin_bridge.py --read-only-live`.
3. Register a reusable checkpoint name. The registry is created locally in the repo directory:

```powershell
py scripts/savestate_checkpoint.py register golf_first_shot --slot 3 --note "Hitting the Green, first ball before swing"
```

4. At the tee, capture **your own** current state into the registered slot (overwrites slot 3):

```powershell
py scripts/savestate_checkpoint.py save golf_first_shot --confirm-overwrite
```

5. Before every new shot, request a reload of that state:

```powershell
py scripts/savestate_checkpoint.py load golf_first_shot
```

6. Visually verify that Nueron, the ball and wind/aim reset as expected. The bridge acknowledges RPC dispatch, not successful in-game restore or deterministic physics; record a screenshot/video before relying on it.

## Automatic first-shot restoration when loading the bridge

Regenerate the patched bridge with an explicit **opt-in** startup slot:

```powershell
$tools = "D:\Projects\Wii Golf AI\tools"
py scripts/patch_felk_bridge.py --source "$tools\mcp_bridge.py" --output "$tools\mcp_bridge_atomic.py" --startup-slot 3
```

Close every Dolphin instance, restart Felk Dolphin, **launch Wii Sports before loading the bridge**, then load only `mcp_bridge_atomic.py` under View -> Scripting. The patched bridge requests `savestate.load_from_slot(3)` **once after its first emulated frame**. It logs `[wii-ai] startup savestate slot 3 load requested` or `LOAD FAILED`; inspect the Scripting log and confirm on screen. A failed restore does not retry, preventing runaway reload loops.

The `--startup-slot` option is not mandatory. Without it, the normal patched bridge starts without loading a saved state.

`--startup-slot` is resolved when generating the bridge, not dynamically from the registry. To change the active named checkpoint, look up its slot using `py scripts/savestate_checkpoint.py list`, regenerate with the desired slot, and relaunch. You may also use the `load` command between individual trials without restarting.

## Multiple future scenarios

```powershell
py scripts/savestate_checkpoint.py register golf_putting --slot 4 --note "Putting challenge"
py scripts/savestate_checkpoint.py register golf_driver --slot 5 --note "Driver start"
py scripts/savestate_checkpoint.py list
py scripts/savestate_checkpoint.py save golf_putting --confirm-overwrite
py scripts/savestate_checkpoint.py load golf_driver
```

Slots allowed: 0..255; registry detects name/slot collisions, requires confirmation before overwriting local emulator slot contents, and never removes a prior state automatically. Do not change savestate while an atomic trace is active. Start another run from a restored checkpoint only after input playback is complete, and verify the game restored correctly.

## Controller validation, separate from state restoration

User's first live `probe_atomic_trace.py` completed 15/15 dispatch frames but **nothing moved on screen**. This is a negative gameplay observation: dispatch != delivered Wii Remote HID input != game swing. Before tuning input, check Wii Remote 1 is **Emulated** and its A mapping responds manually, and compare against a direct bridge `controller.get_wiimote_buttons` / `set_wiimote_buttons` interaction. Felk's ClearOn::NextFrame behavior means a brief button pulse is not a guaranteed visible press.

Neither auto-startup load nor a successful savestate RPC has been tested on the user's Windows Dolphin yet. Record actual game feedback before declaring reset reproducible.
