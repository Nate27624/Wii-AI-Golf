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
