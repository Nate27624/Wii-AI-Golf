# One-command Dolphin launch and state restoration

Use `scripts/launch_golf.py` from the **canonical** runtime checkout `D:\Projects\Wii Golf AI\Wii-AI-Golf`. Do not execute source scripts from the sibling `Wii-AI-Golf-Data` directory.

## First run: set your Wii Sports image path once

Close Dolphin before starting. The repository already has the opt-in swing bridge generated locally at `D:\Projects\Wii Golf AI\tools\mcp_bridge_swing.py`, and a user-verified named savestate in `research/savestates.local.json`. A *game image path* has not been established in the repository, so paste your actual lawful Wii Sports .rvz/.iso filename when prompted:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/launch_golf.py
~~~

This automatically starts Felk Dolphin with `Dolphin.exe --script mcp_bridge_swing.py --exec <your_game_image>`, waits for a responsive bridge, and requests `savestate_session.py start green-first-shot` restoration via existing named StateManager. On the first run only, it prompts for the full disc-image path, then saves it in `research/launch.local.json`. Both that file and temporary file are gitignored. No ROM, savestate or private file path is uploaded to GitHub. To change games later, run `py scripts/launch_golf.py --game "D:\PATH\Wii Sports.rvz"`.

If your known-good checkpoint is the **pre-Start instructions menu** instead, choose it explicitly with `--profile green-pre-start`. The default `green-first-shot` should be an existing registered, manually verified checkpoint at the first ball. Never interpret RPC `load_requested` as independently verified screen restoration; look at Dolphin.

## Every subsequent run: one command

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/launch_golf.py
~~~

The command performs, in order:

1. Launch the **scripting-enabled Felk Dolphin** build under `tools\FelkDolphin`.
2. Attach **the swing-enabled bridge** `tools\mcp_bridge_swing.py` with Dolphin's `--script` command-line flag, launch the saved Wii Sports image with `--exec`.
3. Wait for the bridge to respond over 127.0.0.1:55355, request loading the local savestate profile `green-first-shot`.
4. Return with an explicit warning that the screen must be visually checked; state loading does **not** overwrite the saved slot.

**Optional one-command first-swing experiment:** When the checkpoint places the golfer at the ball, use:

~~~powershell
py scripts/launch_golf.py --swing
~~~

This performs the same launch/attach/reset and then runs **one** `probe_swing.py --preset forward --send-live-swing` test. It still asks for Enter just before the swing and records your on-screen observation; no unattended repetition. For alternate hypotheses, `--swing --preset reverse` or `--swing --preset sideways` are available.

## Preconditions and troubleshooting

- Fully close existing Dolphin instances before using this command; never leave two bridge scripts bound to port 55355.
- Wii Remote 1 must remain **Emulated Wii Remote** with Extension **None**. The user's prior successful scripted A test required these settings; Real Wii Remote / Nunchuk block expected inputs.
- `mcp_bridge_swing.py` must already be generated with `scripts/patch_felk_bridge.py --enable-swing`.
- `green-first-shot` is a local **name** referring to a previously verified save slot; the launcher does NOT create the slot, save over it, or generate the underlying savestate.
- If startup state load fails or times out, keep the actual savestate and try the known-good `py scripts/savestate_session.py reset green-first-shot` from an already-running game. The auto launch path still needs user live validation; do not label a startup load as working until observed.
- For a different checkpoint, pass `--profile NAME`. For a nondefault emulator/bridge, use `--dolphin PATH` / `--bridge PATH`. `--catalog PATH` selects a separate local catalog.
- One first-run game-path prompt is unavoidable without guessing which legally sourced Wii Sports game image you have. Subsequent calls are fully parameter-free.

## Validation status

Worker 1 added offline tests `tests/test_integration_launcher.py` for one-time configuration, source path validation, bridge/game/slot command composition, optional guarded swing and no swing after launch errors. Tests should run via:

~~~powershell
py -m unittest discover -s tests -p "test_integration_launcher.py" -v
~~~

This feature's GitHub commit is **code only**, not a report of a new Dolphin live run. The first user launch, screen restore, and any swing remain subject to human verification.

## Choose and remember a specific savestate slot (fix for Slot 1 vs Slot 2)

After a user-observed launcher restored Slot 1 instead of the intended Slot 2, the launcher now supports selecting a **registered** local slot exactly once:

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
py scripts/savestate_session.py list
py scripts/launch_golf.py --slot 2
~~~

It looks up Slot 2 in the existing gitignored `research/savestates.local.json` catalog, prints the resolved profile name, slot number and description, and stores that **name** in the local gitignored `research/launch.local.json`. It fails before launching if Slot 2 is not registered; it does not register an unknown slot or overwrite game data. Later `py scripts/launch_golf.py` (or `--swing`) uses that selected profile without requiring `--slot 2` each time. Alternatively `--profile green-pre-start` persists the named choice.

**Important:** In earlier user setup Slot 2 was `green-pre-start`, at the **instructions screen**, whereas Slot 1 `green-first-shot` was for the ball. The local catalog is private, so verify with `list` before assuming this has not changed. A successful Slot 2 restore may still require manually pressing Start before sending a swing; `--swing` prompts for human confirmation, and you must not press Enter until standing at the first ball. For experiments we ultimately want a newly verified `green-first-shot` profile saved at the ball, not a menu checkpoint.


## New: enforce Emulated Wii Remote 1 on every launch

A real Windows run exposed an additional launcher bug: Dolphin started with **Real Wii Remote** selected after the Python bridge was attached, silently blocking scripted A and motion inputs.

The launcher now requires the **existing Dolphin user configuration** `Config/WiimoteNew.ini` before starting a new game. It carefully changes only `[Wiimote1] Source = 1` (Emulated Wii Remote) and `Extension = None`, preserving all other keyboard mappings, Wii Remote ports, comments and unrelated Dolphin preferences. A first-change snapshot `WiimoteNew.ini.wii-ai-golf.original.bak` is kept beside the original file and not overwritten on subsequent launches. Controller preflight refuses to run when a previous bridge is still listening on port 55355.

From your canonical runtime checkout, close Dolphin completely, then:

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_integration_controller_config.py" -v
py -m unittest discover -s tests -p "test_integration_launcher.py" -v
py scripts/launch_golf.py --slot 2
~~~

The CLI prints:

- `Selected checkpoint: NAME (Dolphin slot 2)`
- `Controller ready BEFORE boot: Emulated Wii Remote (1) | Extension: None`
- Actual on-disk `WiimoteNew.ini` path, whether it was changed and the original backup path.

It then launches Dolphin, attaches `tools/mcp_bridge_swing.py` and requests a named state restore. On later starts, `py scripts/launch_golf.py --swing` uses the remembered profile and config. **Do not press Enter for the swing while on a pre-Start instructions menu.**

Dolphin can use a portable `User` directory beside the executable, Windows `%APPDATA%/Dolphin Emulator`, a legacy Documents user directory or an override. The launcher picks an existing, unambiguous settings file; it never invents or creates a new user directory (which could make checkpoints appear to vanish).

If it fails with "Could not locate" or "Multiple Dolphin user configurations":

1. Open the specific Felk Dolphin you use, click **File > Open User Folder**, note the absolute folder path, then close Dolphin.
2. Run `py scripts/launch_golf.py --dolphin-user "C:\\PATH\\TO\\YOUR\\DOLPHIN\\USER" --slot 2`.
3. It remembers that directory in ignored `research/launch.local.json`. Future runs require no path argument.

If you want Dolphin to use real controllers again outside the research project, restore the backed up `WiimoteNew.ini` **while Dolphin is closed** or switch back through the GUI; the launcher will switch to Emulated Wii Remote again on the next AI session.

### Verification limits

The source setting is supported by Dolphin's `WiimoteSettings.cpp`, `Wiimote.h` and `CommonPaths.h`. This implementation has focused offline tests but **needs a user-observed restart** to establish that the Felk fork uses the selected config and the game does not override it with a per-game INI. If the Dolphin Controllers UI still says Real Wii Remote after launch, send the printed selected config path and we will investigate game-specific settings / user-folder discrepancy; do not collect swings. The launcher does not delete game data, savestates, or any files unrelated to the controller INI.
