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
