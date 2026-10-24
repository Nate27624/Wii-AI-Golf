# Standard Wii Sports data-recording startup — automatic fresh-or-attach

**All live S002 evaluation entry points now default to the FULL integration launch.**
There is a single source of truth for the savestate and menu timing:
the canonical checkout's `scripts/launch_hitting_green.py` + `menu_sequence.py`.

## Every run — one command

Close Dolphin first if it is open without a working Felk bridge. Run from the S002 evaluation worktree:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"
$env:PYTHONPATH = (Resolve-Path ".\src").Path
$game = "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs"

py scripts/start_golf_recording.py --game $game --seconds 30 --scan-profile fast
~~~

The script now automatically:

1. Checks port 55355 for a responsive bridge. If one is listening, reuse that Dolphin. If not, start the normal Felk Dolphin + swing-enabled bridge. If a Dolphin window is already running **without** a listening bridge, fail safely rather than launching a competing instance; close Dolphin and rerun.
2. For a fresh launch, call the canonical integration helper to set **Wii Remote 1: Emulated / Extension None**, preserving its original config backup and any saved Dolphin user folder.
3. Restore the existing named pre-start checkpoint `green-pre-start` from the **canonical** `research/savestates.local.json`. Never save, register or overwrite savestates. A first-ball checkpoint is NOT suitable for the menu sequence.
4. Dispatch integrator-owned **A → wait → A+B → release → A**, with the tested request lengths **120 / 30 / 315 / 60 / 135 / 45 / 300**. This sequence is NOT copied into the S002 evaluation scripts. Actual screen arrival still needs visual verification; RPC ACK alone is not enough.
5. Automatically start a READ-ONLY memory scan. The bridge remains running; no extra reset or button press is sent by the scanner. The scanner receives an internal explicit `--startup skip` to avoid a second launch. **Swing manually** during capture, and Ctrl+C to stop early and preserve/auto-publish a compact report.

Once the game path has been recorded by the canonical `launch_golf.py` in ignored `research/launch.local.json`, `--game` may be omitted. Explicit `--startup fresh` insists on a fresh launch; `--startup attach` insists on a listening bridge. The historic `--attach-running` wrapper flag remains accepted but now means automatic fresh-or-attach, fixing previous ConnectionRefusedError when Dolphin wasn't running.

## Every live capture script uses the SAME startup

The default `--startup auto` behavior applies to:

- `scripts/start_golf_recording.py` — startup once, then launches the motion scanner
- `scripts/discover_golf_motion.py` — direct candidate ball/score scan
- `scripts/monitor_hitting_green.py` — continuous map position monitor
- `scripts/collect_hitting_green.py` — manually scored before/after trials
- `scripts/probe_golf_spatial.py` — version-gated pin/cup/tee vectors
- `scripts/probe_golf_symbols.py` — struct pointer and mode probe
- `scripts/capture_golf_data.py capture` — live state capture

Their read-only subcommands do not write emulator memory. `scripts/capture_golf_data.py compare` is **offline** and never starts Dolphin.

**Only for an already-verified in-progress session**, explicitly add `--startup skip` to a live capture command to avoid rewinding progress. This is particularly important when collecting an `after` capture after a `before` capture. Omitting this flag intentionally resets to the registered pre-start checkpoint every run.

## Local verification

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"
$env:PYTHONPATH = (Resolve-Path ".\src").Path
py -m unittest discover -s tests -p "test_start_golf_recording.py" -v
py -m unittest discover -s tests -v
~~~

The new tests mock Dolphin, Git subprocesses and controller preparation; they must not alter the user's emulator. Runtime UI navigation, port availability, and real ball contact still need a live test.

**No automatic swing yet:** The user saw the club move slightly, but a ball strike or score has not been verified. Data collection must not misclassify RPC motion as successful shot contact.

This workflow only changes S002 evaluation scripts. Worker #2 continues to own the canonical launch, controller configuration, savestate registration and menu timing. Do not create another start sequence or boot from an autorestore bridge script.

## Physical Wii Remote data collection (`--controller-mode physical`)

All live S002 capture scripts now accept `--controller-mode physical` or `--controller-mode emulated` (default). **Physical** does not rewrite Wii Remote 1 to Emulated, does not load/reset the named savestate, and does not send automated menu presses. Instead, you manually start Dolphin with Wii Remote 1 set to **Real Wii Remote**, pair the controller, have the Felk read-only bridge available at port 55355, navigate to the first ball and swing. Example:

~~~powershell
py scripts/discover_golf_motion.py --controller-mode physical --seconds 30 --profile fast
~~~

The wrapper also accepts `--controller-mode physical`. If physical mode is requested and there is no listening bridge, it fails safely with instructions to start Dolphin manually rather than launch the emulated controller startup. This is intentional: the integrator's `launch_hitting_green.py` always emits virtual button inputs, so reusing it in physical mode would mix controller input sources.

**Emulated** mode continues the exact automatic canonical full launch, prestart savestate and A/A+B/A menu sequence. In either mode, the motion scanner itself is read-only. For live data with the physical remote, no automatic intro is implied; the player must navigate.

## Physical Wii Remote: bridge refused / zero captured samples

The user ran **115 passing offline tests**, but `--controller-mode physical --startup skip` emitted 5 `ConnectionRefusedError` messages and 0 captures: the bridge was NOT running. This is not a decoder failure. Prior startup code returned success from physical skip without checking the port; now physical skip and attach **verify the Felk bridge before beginning a capture**.

To start a fresh Felk instance without ever modifying the real Wii Remote settings or sending virtual A/B:

~~~powershell
# Close Dolphin first. It must NOT already be running.
py scripts/discover_golf_motion.py --controller-mode physical --startup fresh --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --seconds 30 --profile fast
~~~

This launches Dolphin with `--script mcp_bridge_swing.py --exec <game>` but does **not** alter `WiimoteNew.ini`, does **not** load the prestart checkpoint, and does **not** navigate menus. Pair the physical Wii Remote in Dolphin's Controllers interface and enter Hitting the Green before/while observing. This experiment starts capturing as soon as the bridge responds, so results may initially contain non-training menu scenes.

If the game is already at a swing-ready screen with the bridge running, use:

~~~powershell
py scripts/discover_golf_motion.py --controller-mode physical --startup skip --seconds 30 --profile fast
~~~

If a normal Dolphin window is open *without* a bridge, close it before the fresh launch (the script refuses duplicate instances). **Avoid `--controller-mode emulated` if you want to retain real Wiimote 1**: that mode invokes the controller setup helper and virtual menu sequence. Automated A/A+B/A navigation currently requires emulated mode; physical mode intentionally leaves buttons under real Wii Remote control.

The physical bridge preflight and fresh launch have mocked regression tests, but a real Windows / physical Wiimote run is still required.
