# Wii Sports Golf read-only data capture — S002

**Status: offline-tested only, not a decoded Wii Sports game dataset.** Owner: Issue #3 (evaluation). No recorded AI golf swings or verified memory symbol addresses yet.

## Exposed measurements and limitations

The upstream dmang-dev/mcp-dolphin bridge v0.3 provides frame.get_count, bridge.ping, controller.get_wiimote_buttons, controller.get_wiimote_pointer, controller.get_wiimote_acceleration, controller.get_wiimote_angular_velocity and memory.read_bytes. This tool calls only those read-only methods. A single snapshot spans **multiple emulator frames** and is not atomic. Acceleration unit is m/s²; angular velocity is radians/s. Returned state is not automatically a measured golf action.

Explicit memory reads are limited to **64 KiB in total per capture**, in 2 KiB chunks to fit the RPC client's 64 KiB response cap. A memory address must be supplied by the caller; no Wii Sports shot, distance, ball position, pin position, minimap, terrain, wind or score address has been established.

The upstream gui.screenshot RPC returns an entire base64 RGB framebuffer. The default RPC cap and the bridge's nonblocking socket may not handle such a large response. Therefore this tool does not call it; --screenshot-file records a local, manually captured screenshot pathname and SHA256 as evidence.

## Start with read-only metadata; no guessed memory addresses

While Dolphin runs the game unpaused, ensure that exactly one responding Felk bridge is loaded. Install the repo package first if needed.

~~~powershell
python -m pip install -e .
py scripts/capture_golf_data.py capture --label green01-before --shot-index 1 --savestate-profile green-first-shot --scene-note "pre-swing; visually confirmed"
~~~

This command saves local ignored research/game-data.local/green01-before.json. It makes **no input, save, load, memory-write or pause calls**. Frame and controller states are observable; club, score, ball and wind are not decoded. Saving to an existing file fails to protect evidence.

## Experimental RAM comparison, never assume a symbol

The address 0x80000000 below is a generic virtual-memory-base example and NOT a known golf variable. It may not contain the target and may be invalid for a given build. Keep the same ranges across paired captures:

~~~powershell
py scripts/capture_golf_data.py capture --label green01-left --range 0x80000000:4096 --scene-note "before visible manual aim adjustment"
# Manually change aim in Dolphin; this tool does not move it
py scripts/capture_golf_data.py capture --label green01-right --range 0x80000000:4096 --scene-note "after visible manual aim adjustment"
py scripts/capture_golf_data.py compare --before research/game-data.local/green01-left.json --after research/game-data.local/green01-right.json
~~~

When an actual game score is displayed, record its raw text and unit as a *human annotation*, and optionally search for matching changed aligned big-endian f32/u32/s32 values in the selected window:

~~~powershell
py scripts/capture_golf_data.py capture --label green01-score --range 0x80000000:4096 --on-screen-distance 7.25 --on-screen-unit m --shot-index 1
py scripts/capture_golf_data.py compare --before research/game-data.local/green01-left.json --after research/game-data.local/green01-score.json --target 7.25 --tolerance 0.1
~~~

**7.25 m is purely illustrative**; replace with the exact displayed value and unit. A candidate address is NOT a validated score. Scanning this tiny sample area is a feasibility probe, not a meaningful search of Wii RAM.

A real memory map will require controlled repetitions with varied observed distance/angle/wind and baseline runs with no change to eliminate volatile counters. Mapping a map image or course geometry requires separately validated coordinates/screenshots; the present tool does NOT reconstruct a map.

## Handoff to integration, evaluation and modeling

1. Worker 1, Issue #2: verify the Wii Remote Plus visual response and named first-shot savestate restore on screen. If efficient screenshot automation is needed, build a **chunked or file-backed** read-only screenshot endpoint, not full-frame JSON through the current 64 KiB client. Maintain bridge code ownership.
2. Evaluation Issue #3: capture before and after manually altered aim, on-screen result and reset **with repeat baselines**. Preserve raw human score text, displayed unit, shot index, screenshot hash, frame interval, and exact ROM/region/revision and Dolphin build. Determine 30 double-annotated actual scored outcomes only after successful recognized swings.
3. Modeling Issue #4: use known visible changes (aim left/right, club, wind, pin) to isolate candidate RAM fields; verify candidate numeric correlations on independent captures before using them as policy features.
4. Bayesian optimization PR #12: no training with unverified RAM candidates. Connect a real ShotResult only after an independently audited score reader exists.

The raw snapshot JSON stores selected RAM bytes, which might include game assets. **Do not commit or upload raw capture JSON**, game image, savestate, screenshot, or other copyrighted assets. Local game-data.local directory is gitignored. No actual screenshots or game memory were accessed in this author's environment.
