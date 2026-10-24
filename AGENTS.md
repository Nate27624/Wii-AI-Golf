# AI agent coordination protocol

## Mission and trust model

Coordinate separate AI coding/research sessions to develop a scientifically reproducible agent for Wii Sports Golf's Hitting the Green. **Roles are logical responsibilities, not persistent autonomous processes.** No agent should claim a run happened unless logs show it.

Every session MUST read README, this document, research/ledger.md, research/queue.jsonl, open GitHub Issues/PRs and relevant tests before changing code.

## Roles and ownership

| Agent role | Scope | Primary ownership |
| --- | --- | --- |
| integrator | Dolphin automation, reproducible reset, Wii Remote input playback, outcome capture | emulator adapter, docs/hardware.md |
| modeling | Input calibration, control response, surrogate/physics models | models module, calibration experiments |
| learning | Random/search baselines, contextual policies, RL (when justified) | agents module, learning modules |
| evaluation | Score extraction verification, splits, held-out tests, provenance, replay and metrics | evaluation, research/results |
| coordinator | Interface compatibility, task priority, integration review, shared research ledger | AGENTS.md, documentation and cross-role PRs |

## Collaboration rules

1. Choose an open, non-overlapping GitHub issue. **Claim it in an issue comment**, recording your agent/session, code paths and intended test; do not assume another session sees your chat.
2. Work on a dedicated branch named `agent/<role>/<slug>` from up-to-date main. No direct feature commits to main, no overwriting concurrent branches, no forced shared branch updates.
3. Restrict edits to claimed paths. Protocol schema changes need coordinator review and compatibility tests.
4. Before a PR, run `python -m unittest discover -s tests -v`; add targeted tests and state explicit commands/results.
5. PR body contains hypothesis, exact scope, issue, experiments, positive and negative findings, sample budget, evaluation split, limitations and reproducibility instructions.
6. Integrate through PR after tests and review. If another PR changed a shared file, update your branch and resolve conflict deliberately.
7. Append findings to research/ledger.md and proposal records to research/queue.jsonl; don't erase failures or mark studies complete without associated artifact links.

## Required startup for real Hitting the Green runs (2026-10-24)

**User-confirmed working baseline:** On the target Wii Sports USA Rev 1 setup, a live operator saw the first-shot screen reached with the existing `green-pre-start` savestate and the A → wait → A+B → release → A menu sequence. PR #22 standardized the slower default timing with a small margin: requested-frame counts **120, 30, 315, 60, 135, 45, 300**. These are *RPC requests*, not accurate wall-clock/video frame timing; no automatic screen-state verifier exists yet.

**Rule for all future real-game golf launch/training scripts:** use the canonical `scripts/launch_hitting_green.py` flow or call its shared `wii_ai_golf.menu_sequence.planned_menu_phases` / `execute_menu_phases` logic after loading the same named `green-pre-start` checkpoint through `StateCatalog` + `StateManager`. Do **not** issue a bare `savestate_session start green-first-shot` and treat it as readiness; do not duplicate hardcoded menu delays in training code. `scripts/launch_golf.py` must delegate to the canonical intro rather than stop after savestate load. To add a new action collection loop, use this startup as the reproducible S001 baseline before any first-ball swing.

- Use `green-pre-start` by **name** in `research/savestates.local.json`; do not hardcode a slot, overwrite existing savestate bytes, or copy a game image into Git.
- Fresh boot: Felk Dolphin, **Emulated Wii Remote 1 / Extension None**, single `mcp_bridge_swing.py` patched without a separate startup-slot hook. Restart before fresh launch if another bridge occupies port 55355.
- Running emulator: `py scripts/launch_hitting_green.py --attach-running --send-live` restores the named checkpoint and runs the intro. Fresh boot: `py scripts/launch_golf.py` (first run prompts for game image, stores locally), or `launch_hitting_green.py --dolphin ... --game ... --bridge ... --send-live`.
- Actual swing execution is a **separate** phase and requires explicit opt-in (`--swing`, ideally with a human-ready-screen confirmation until screen detection exists). Controller ACK alone is not proof of recognized shot, successful menu navigation or score.
- Low-level `savestate_session.py`, `probe_wiimote.py`, `probe_atomic_trace.py` and custom scenario resets remain permitted as **explicit diagnostics**, not the normal first-shot golf launcher. Alternate saved-at-ball states require their own documented scenario contract and proof of readiness.
- Add a regression test whenever launch behavior changes, verifying that the canonical intro is invoked before an optional swing. Keep the user-confirmed timing baseline available as a default; proposed recalibration must preserve a runnable known-good profile.

Relevant docs: [launch-hitting-green.md](docs/launch-hitting-green.md), [one-command-launch.md](docs/one-command-launch.md), [workspace-coordination.md](docs/workspace-coordination.md). Observed menu success was **human reported**, not frame-count/video verified by an automated detector.

## Mandatory fresh-boot command contract (user directive 2026-10-24)

**Every user-facing command that interacts with LIVE Wii Sports must independently start Felk Dolphin, launch the game, restore the appropriate existing named checkpoint, and complete the integrated startup/navigation before any new probe, swing, capture or training action.** Do NOT give users bare `py scripts/probe_swing.py`, `py scripts/start_golf_recording.py --attach-running`, `py scripts/discover_golf_motion.py`, `py scripts/probe_dolphin_bridge.py --read-only-live`, or similar commands that assume a manually running Dolphin bridge.

**Canonical standard first-shot dispatcher:** `py scripts/run_golf_experiment.py --send-live --script ACTION.py -- [action arguments]`. It first invokes `scripts/launch_golf.py` (emulated controller, fresh Felk Dolphin + legal Wii Sports image, named savestate `green-pre-start`, user-confirmed A → wait → A+B → release → A intro via `launch_hitting_green.py`), then executes ACTION.py **only if startup returned successfully**. A user-given game path is saved only in the ignored local launch config. Every future real-game action must either be runnable through this dispatcher or supply an equivalently self-contained fresh boot command *delegating* to the canonical launcher; no duplicate startup code or menu timing constants.

If the requested scenario is already saved at the ball or is a later shot, it requires an **explicit scenario-specific named savestate and skip-menu safety contract**. Never run A/A+B/A from an arbitrary at-ball state. The current first-shot dispatcher intentionally rejects those alternate checkpoints until properly integrated. Low-level attach/reset commands are internal diagnostics, **not full user-facing run instructions**. Existing Dolphin must be closed for fresh boot; do not start duplicate bridges. Offline tests, source analysis, patch generation and scenario planning do not require Dolphin; this directive applies to commands touching the live game.

See [fresh-boot-experiments.md](docs/fresh-boot-experiments.md) for exact commands and mock regression tests. Controller RPC acknowledgements, savestate load requests and successful menu dispatch are not automatic confirmation of visual readiness, ball contact or score.

## Scientific integrity gates

- Every experiment gets a unique study ID, baseline, hypothesis, seeds, train/evaluation partitions, attempt/time budget, success criterion and stop rule BEFORE training.
- Distinguish synthetic vs actual-emulator vs human observations; never transfer synthetic benchmark scores into game claims.
- Measure controller traces, Dolphin build, Wii Sports region/revision, shot configuration, result measurement source, game units, failure counts and environment settings.
- Hold out shot configurations as well as repeats/seeds where feasible. No training on a held-out score followed by calling it blind evaluation.
- Include identical shot budgets for competing methods; record expensive calibration shots too.
- Use the local machine by default. No GitHub Actions training workers or unexplained cloud costs.

## Priorities

1. Reliable game input/reset and measurement (100 logged unattended attempts).
2. Random baseline and calibrated parameter optimization.
3. Held-out scenario tests and contextual/surrogate models.
4. RL when the simulator or emulator offers demonstrably adequate throughput.
5. Video production with traceable performance plots and footage.

## Do not fabricate integration

The current DolphinBridge is a dependency-injected interface, not a working Dolphin API integration. ShotAction aim/power are placeholder normalized parameters until real motion has been calibrated. The current toy environment uses invented physics.

When blocked by legal game access, emulator control, inaccurate score units or unreliable resets, record the blocker, reproduce it and propose a test instead of pretending the code works.


## Collision prevention and handoffs

Before claiming or editing a new workstream, read [research/coordination.md](research/coordination.md), `research/claims/`, and the corresponding issue comments. Claims are recorded FIRST in an issue comment, then in a per-worker JSON file; conflicting paths require an explicit handoff. The shared ledger is a summary, not an automatic job scheduler or locking service. Keep raw findings in per-worker research folders to minimize merge conflicts.
