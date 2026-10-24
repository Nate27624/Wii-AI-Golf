# Canonical one-command Wii Sports golf launch and calibrated intro

Use `scripts/launch_golf.py` from the **canonical** checkout `D:\Projects\Wii Golf AI\Wii-AI-Golf`. Do not execute scripts from the sibling `Wii-AI-Golf-Data` evidence directory.

**Verified observation (2026-10-24):** User confirmed that restoring the existing `green-pre-start` checkpoint and pressing **A → wait → A+B → release → A** with slower waits successfully reached the ready-to-swing screen. An additional 15 one-frame RPC requests have since been added to each inter-button wait. That padding has not yet been retested live. No autonomous score parsing, shot contact or frame-exact duration is implied.

## Fresh launcher: set the game path and checkpoint once

Close Dolphin before a fresh launch. Configure Wii Remote 1 as **Emulated Wii Remote** with **Extension None**. With the original Felk bridge available locally, `tools\mcp_bridge_swing.py` must be generated with `scripts/patch_felk_bridge.py --enable-swing` and **without** `--startup-profile` (the launcher handles the checkpoint load).

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py -m pip install -e .
py scripts/savestate_session.py list
py scripts/launch_golf.py --game "FULL_PATH_TO_YOUR_WII_SPORTS.wbfs" --profile green-pre-start
~~~

Your game path and checkpoint name are stored only in `research/launch.local.json` (gitignored). The launcher does not create, capture or overwrite a Dolphin savestate. It resolves `green-pre-start` through `research/savestates.local.json` (gitignored), so no numeric slot is hardcoded. If you previously saved `green-first-shot` as your preferred launcher profile, explicitly pass `--profile green-pre-start` once to update that preference. `--slot` is accepted **only** when it points to the named `green-pre-start` checkpoint; the standard full-menu launcher intentionally refuses other saved-at-ball checkpoints.

On subsequent fresh starts:

~~~powershell
py scripts/launch_golf.py
~~~

To do one *human-confirmed* experimental swing after intro:

~~~powershell
py scripts/launch_golf.py --swing --preset forward
~~~

The first command delegates to `launch_hitting_green.py --send-live`, which starts Felk Dolphin with `--script` and `--exec`, loads the checkpoint, checks bridge progress, then executes the **central** menu timing sequence. With `--swing`, the main launcher calls `probe_swing.py` *after* the intro subprocess finishes; the probe still prompts before one swing and logs the user's observation. No input trace is proof of a real Wii Sports hit.

## Already-running Dolphin: single reset and intro

To reuse a responsive swing bridge in a game that is **already running**:

~~~powershell
py scripts/launch_hitting_green.py --attach-running --send-live --swing --confirm-before-swing
~~~

This does not start another Dolphin; it restores the named pre-start checkpoint and navigates the intro, then requests confirmation before one optional forward swing. Remove `--swing --confirm-before-swing` for menu navigation only. For a fresh launch using this lower-level CLI, provide `--dolphin`, `--game`, `--bridge` and `--send-live` explicitly.

## Calibrated default schedule

| Phase | Controller | One-frame input requests |
| --- | --- | ---: |
| Wait after checkpoint | None | 120 |
| First press | A | 30 |
| Wait for menu | None | 315 |
| Second press | A+B | 60 |
| Release between buttons | None | 135 |
| Third press | A | 45 |
| Wait for ready screen | None | 300 |

The prior **120 / 30 / 300 / 60 / 120 / 45 / 300** schedule was user-confirmed successful. The extra +15 requests per inter-button pause approximate a quarter second at 60 FPS but are not guaranteed video frames/wall-clock intervals. The live sequence still needs on-screen inspection until an automated menu-state detector is verified.

The timing defaults live in `wii_ai_golf.menu_sequence.planned_menu_phases` and the arguments on `scripts/launch_hitting_green.py`. Other golf scripts must not create their own timing constants or use bare `savestate_session.py start` as the standard gameplay entry point. See [AGENTS.md](../AGENTS.md#required-startup-for-real-hitting-the-green-runs-2026-10-24).

## Advanced scenarios and diagnostics

Low-level capture/load/probe scripts remain available for intentional research diagnostics and later-shot scenarios. They are **not** a substitute for the standard Hitting the Green intro. A checkpoint already standing at a ball (such as `green-first-shot`) may not tolerate A/A+B/A; do not use it as a normal pre-menu profile. Different captured scenarios require explicit proof of screen readiness and a separate experiment description.

Failure cases: a second bridge on port 55355; Dolphin paused or using Real Wii Remote; outdated `mcp_bridge_swing.py`; missing named `green-pre-start` registration; game region incompatible with saved state; startup bridge configured to load a second slot. No ROM or private savestate bytes belong in Git.

## Tests

~~~powershell
py -m unittest discover -s tests -p "test_integration_launcher.py" -v
py -m unittest discover -s tests -p "test_menu_sequence.py" -v
py -m unittest discover -s tests -v
~~~

The tests use mocked IO and controller RPCs. User visually confirmed menu navigation in the earlier run, but actual emulator launch, screen verification, recognized swing, scoring and safety after repeated restarts still need measured evidence.
