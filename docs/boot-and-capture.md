# Standard Wii Sports evaluation startup: ONE savestate restore and A → A+B → A

This is the **recommended** entry point for new ball-position, score and swing research runs. Use `scripts/start_golf_recording.py` from the evaluation checkout. It **does not implement its own menu timings**; it invokes the integrator-owned, current canonical `scripts/launch_hitting_green.py` to load the existing named pre-start savestate and send the already user-validated A → delay → A+B → delay → A sequence. Once the launcher finishes and releases all buttons, the evaluator starts `scripts/discover_golf_motion.py` on its existing read-only capture path.

**Do not combine this with `launch_golf.py` or an auto-restoring startup bridge.** `launch_golf.py` restores a named checkpoint but does *not* advance the pre-start menu; a startup-autoloading bridge can cause an unintended second restore. The preferred source of truth is the canonical checkout at `D:\Projects\Wii Golf AI\Wii-AI-Golf`, holding the only named savestate catalog at `research/savestates.local.json`, and the integrator's `launch_hitting_green.py`. Sibling `Wii-AI-Golf-Data` is a separate evaluation code worktree during PR development but uses the canonical catalog. A completed merge can run from the canonical checkout itself.

## Existing running Dolphin: pre-start reset + exact intro + automatic capture

**This command WILL reset the running Dolphin state**, so save any gameplay work first. Dolphin must have one healthy scripting bridge listening at 127.0.0.1:55355.

~~~powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data'
$env:PYTHONPATH = (Resolve-Path '.\src').Path
py scripts/start_golf_recording.py --attach-running --seconds 30 --scan-profile fast
~~~

It loads the **registered `green-pre-start` checkpoint**, not `green-first-shot`. It does not save/overwrite any savestate. The integrator's default button request durations are **120 / 30 / 315 / 60 / 135 / 45 / 300** (state settle, A, wait, A+B, release, A, game settle). Those values remain owned by the integration agent and are not duplicated or adjustable in this wrapper. The requested frame counts approximate timing; actual menu navigation should still be visually verified.

After the menu settles, the wrapper starts recording automatically. **Swing manually** while the scanner is running. The collector will not send a swing or a second savestate load. Ctrl+C stops the scanner early and should preserve its local JSONL and upload its compact summary.

## Fresh Dolphin: launch game, restore and navigate, then capture

**Fully close Dolphin first.** The command uses the existing swing bridge (`tools\mcp_bridge_swing.py`) and Felk Dolphin (`tools\FelkDolphin\Dolphin.exe`) as defaults. No new bridge is patched or launched simultaneously.

~~~powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data'
$env:PYTHONPATH = (Resolve-Path '.\src').Path
py scripts/start_golf_recording.py --fresh --game 'G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs' --seconds 30 --scan-profile fast
~~~

Wii Remote 1 must be **Emulated Wii Remote**, extension **None**, before launch. For read-only counter/score scans, pass `--scan-profile broad`. Use `--no-upload` to retain all results locally. Raw emulator RAM hex is *always* local even if the compact report is uploaded.

## Design and error handling

- Requires the existing `green-pre-start` profile in the canonical `research/savestates.local.json` (verify with `py scripts/savestate_session.py list` **from the canonical repo**). If the correct pre-start checkpoint has a different registered name, use `--savestate-profile NAME`. Do not use a first-ball checkpoint for the A/A+B/A intro.
- Attach mode refuses to run if the bridge is not listening. Fresh mode refuses to run when a bridge already owns the port.
- The wrapper calls the canonical launcher as a subprocess, using that checkout's exact `src` path. The scanner runs as a **second, sequential subprocess**, using the evaluation checkout's `src` path. This prevents earlier cross-worktree import failures.
- If the canonical launcher fails or the named profile is missing, it never starts the scanner or duplicates the button sequence. It never sends `--swing`, and the scanner only reads.
- This verifies ordering and RPC dispatch, **not that the game consumed a menu press or that a swing struck the ball**. The user's observation of a slightly moving club indicates the bridge may be influencing motion, but it does not prove a scored swing.
- The integrator agent owns `launch_hitting_green.py`, `menu_sequence.py` and button timing. The evaluator owns only the orchestration wrapper and data capture. Do not copy those implementations between workers.

Run its offline tests with:

~~~powershell
py -m unittest discover -s tests -p 'test_start_golf_recording.py' -v
~~~

See `docs/launch-hitting-green.md` for the authoritative integrator-owned menu sequence and limitations.
