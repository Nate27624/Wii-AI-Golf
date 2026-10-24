# S001 canonical intro handoff (2026-10-24)

Scope: Issue #2; claim comment [6381974863](https://github.com/Nate27624/Wii-AI-Golf/issues/2#issuecomment-6381974863). This work standardizes a user-observed successful full-menu intro across the existing one-command launcher.

## Confirmed by user (live Wii Sports; not emulator-telemetry proof)

The **first A** worked but the original fast sequence failed later. The user next ran an A/A+B/A test with input-request counts `120, 30, 300, 60, 120, 45, 300` and reported that it was **perfect** and reached the swing screen. User explicitly asked to add ~0.25 seconds to the delays. PR #22 (already merged before this task) changed only the two pauses to `315` and `135` requested frames, respectively; this extra padding is not separately tested.

## Integration change

Previously, `scripts/launch_golf.py` used `savestate_session.py start` and defaulted to `green-first-shot`, which silently skipped menu navigation. It now invokes `scripts/launch_hitting_green.py --profile green-pre-start --send-live` as a subprocess. This imports the authoritative `wii_ai_golf.menu_sequence.planned_menu_phases` and `execute_menu_phases`, reuses existing registered named state, and leaves the separate `probe_swing.py` opt-in. Existing `--game` one-time local config and Dolphin controller emulation setup remain in place.

The code refuses to automatically run the intro on another existing checkpoint profile, because menu inputs could accidentally swing/advance if the golfer were already at the ball. Other checkpoint/specialist probes remain available, but must be documented as advanced scenarios and are not the standard first-shot entry point. Agent policy in `AGENTS.md` is now explicit for future training scripts.

## Validation and risks

- Added regression tests in `tests/test_integration_launcher.py` verifying delegation, default named checkpoint, prevention of saved legacy shortcut, and that swing only starts after successful launcher subprocess.
- **New tests have not been executed against the user's repository** from this GitHub-only session; no direct access to Felk Dolphin or game image.
- Local test command: `py -m unittest discover -s tests -v`.
- Manual acceptance: `py scripts/launch_golf.py --game "YOUR_GAME.wbfs" --profile green-pre-start` with Dolphin closed; verify ready screen, only then `py scripts/launch_golf.py --swing` on next fresh start, or use `launch_hitting_green.py --attach-running --send-live --swing --confirm-before-swing`.
- Important: serial RPC one-frame requests do not guarantee physical time, game state, ball contact or scoring. Check camera/screen for success; record failed navigation trials too.

Path and source rules: `Wii-AI-Golf` is canonical runtime checkout, `Wii-AI-Golf-Data` stores local evidence, and the gitignored state catalog is the one source of named-to-slot mappings.

## Next priority

Implement an actual ready-to-swing screen/state detector in evaluation/bridge work, then measure shot impact and score. Any further menu timing tuning should preserve the 2026-10-24 baseline until repeated trials justify a new default.
