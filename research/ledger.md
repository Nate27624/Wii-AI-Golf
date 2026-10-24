# Research ledger

Last updated: 2026-10-24. Distinguish verified repository tests from external game claims. Append failed studies; never erase them.

## Confirmed by synthetic tests

- ShotEnvironment contract, ToyGolfEnvironment, RandomPolicy and EliteSearchPolicy run locally.
- Eight unit tests passed with Python 3 and source on PYTHONPATH.
- A synthetic elite-search policy improves average training-scenario distance; no improvement on the real game has been demonstrated.

## Unknown / unverified

- Wii Sports challenge region/revision, shot configuration list, exact medal scoring units/threshold.
- Dolphin controller swing automation, repeatable real resets and real measured reward.
- Whether a simple two-parameter shot action is sufficient.

## Hypotheses, not results

- Calibrated controller actions may permit cheaper system identification than pixel-only RL.
- Configuration-specific optimization might succeed on seen situations but not generalize.
- Contextual model-based methods may use emulator attempts more efficiently than online deep RL.

## Coordination

| Date | Role | Action | Evidence |
| --- | --- | --- | --- |
| 2026-10-24 | coordinator | Initial scaffold, contracts, synthetic baselines and issue queue | foundation commit/PR |

New evidence records: date, study_id, source (synthetic/emulator/human), agent version, train/eval IDs, attempts, seeds, metrics, uncertainty, artifact links and PR.


## 2026-10-24 — Worker 1 (integrator) — S001 research / mock transport

- Claim: [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2#issuecomment-6380103711); scope tracked in `research/claims/worker-1.json` and ownership protocol in `research/coordination.md`.
- **Primary-source finding:** `mcp-dolphin` v0.2 added accelerometer/pointer methods; its bridge accepts one RPC command at a time from Felk's scripting loop. See `docs/integrator-research.md` for exact code and sources.
- **Blocking risk:** Hitting the Green holds A during a swing; sequential independent A/button and accelerometer RPC calls are not provably atomic. Need an in-emulator per-frame scheduler or an alternative validated path before repeatable shots.
- **Local tests:** original 8 plus 13 integrator tests = 21 passing; mock socket and trace only. No live Dolphin, game observations, medal tests or scored attempts performed.
- **Handoff:** `research/worker1/README.md`; next step is read-only Felk preflight, followed by A+acceleration delivery verification and 30-shot experiment.

## 2026-10-24 — Worker 1 S001 continued: experimental atomic scheduler

- New source-pinned patch design for mcp-dolphin upstream `bridge/mcp_bridge.py` v0.3.0 / blob `8e70624680a365707f844b322f5b093746a1c022` (upstream MIT); no vendored game or bridge source.
- Adds `trace.submit`, `trace.status`, `trace.abort`; patch installs same-frame button+accelerometer calls in Felk's emulation coroutine. Supports 1–600 sample sequences with strict inputs, completion counts, explicit abort and A release.
- New offline tests for atomic sequencing and client control pass. Full suite now **30/30 passing**, 0 live emulator attempts, 0 Wii Sports swings measured. This is an unvalidated integration hypothesis, not working gameplay.
- See `docs/felk-atomic-scheduler.md` for install steps, source pin, experiments and limitations.

## 2026-10-24 — Worker 1 S001: first successful user-operated live Dolphin bridge preflight

- **Evidence/source:** user-provided PowerShell output from Windows host (`D:\Projects\Wii Golf AI\Wii-AI-Golf`), running Felk Dolphin with Wii Sports loaded. `Test-NetConnection 127.0.0.1 -Port 55355` returned `TcpTestSucceeded : True`.
- **Observed probe:** `py scripts/probe_dolphin_bridge.py --read-only-live` returned `source=live-bridge-read-only`, `bridge_version=0.3.0`, `initial_frame=2354`, `second_frame=2355`, and `frame_progressed=true`. This was executed by the user, not the Worker 1 sandbox; raw CLI output provided in conversation.
- **Validated claim:** the local Python script can communicate with the Felk bridge over loopback while the emulator advances frames. Earlier bridge-connection failure (`WinError 10061`) is resolved for the read-only probe.
- **Not validated:** controller injection, patched atomic trace, game recognition of a swing, real scoring/extraction, deterministic resets, or unattended trials. **0 demonstrated AI golf shots** so far.
- **Next experiment:** generate separately named pinned atomic bridge via `scripts/patch_felk_bridge.py`, restart Dolphin with only that bridge loaded, run read-only preflight and then explicitly authorized `scripts/probe_atomic_trace.py --send-live-trace`. Do not mark S001 complete until game sees an actual shot; preserve both success/failure evidence.

## 2026-10-24 — Worker 1 S001: first reported live atomic trace dispatch

- **Source:** user-executed Windows PowerShell CLI transcript, not replayed in Worker 1 sandbox. After loading the experimental source-pinned `mcp_bridge_atomic.py`, user ran `py scripts/probe_atomic_trace.py --send-live-trace`.
- **Observed response:** `source=experimental-patched-emulator`; result `state=complete`, `id=1`, `start_frame=3455`, `completion_dispatch_frame=3470`, `total_frames=15`, `applied_frames=15`. Bridge acknowledges 15 sequential dispatch frames, ending one frame after last sample as designed.
- **Meaning:** real Dolphin bridge command accepted; in-bridge scheduled calls to set Wii Remote A and acceleration were reported completed. Does **not** independently verify Wii Sports consumed controller values or that a club swing/shot occurred.
- **Still unobserved:** on-screen movement/contact, score/distance, reset determinism, trials, optimization. **Confirmed golf swings remain 0 until user supplies gameplay observation.**
- **Next:** ask the human observer whether Nueron moved/swang/struck the ball during the 15-frame trace, then design the minimal calibrated input experiment. Preserve clear separation between transport success and game behavior.

## 2026-10-24 — Worker 1 S001: no visible golf response; reusable savestate/reset tooling staged

- **Negative real-game observation:** user reports *nothing happened on screen* after the bridge acknowledged 15/15 experimental A+acceleration frame dispatches (frames 3455–3470). Controller connection to the game is **not proven**; no ball strike and no score.
- **Independent verified source:** Felk scripting-preview4 `controller.pyi` specifies accelerometer units **m/s²**. Earlier 1–2-unit test was incorrectly described as g and was too weak to be a conclusive swing test. Button recognition and motion calibration now priorities.
- **New integration tooling:** local named StateCatalog + StateManager (save/load by named slot, 0..99 from Felk `savestate.pyi`), capture/register/reset/start CLI, optional one-shot `--startup-slot` in pinned atomic bridge, and `Plus` visual controller check. Scope is reusable for future game screens and training states, not tied to first golf shot.
- **Validation:** ten new isolated Python unit tests pass locally (savestate catalog/RPC and boot hook). No user-operated savestate load/capture or new button probe yet. Startup auto-load is currently an **untested experimental hypothesis**, and acknowledgement does not establish successful restore.
- **Docs:** `docs/savestate-workflow.md`; Issue #2 claim/handoff. Evaluation #3 owns score extraction; modeling #4 owns physical swing calibration.

- **Adaptability update:** source-pinned patch generator now supports `--startup-profile NAME` resolved via local catalog, as well as `--startup-slot`. This avoids embedding first-shot-specific code in reusable integration and preserves multi-scenario training support.


## 2026-10-24 — Worker 1 S001: verified reset; scenario-coverage and workspace coordination

- **User-operated result:** `py scripts/savestate_session.py reset green-first-shot` worked from `D:\Projects\Wii Golf AI\Wii-AI-Golf`. The identically named command from `Wii-AI-Golf-Data` failed with `unknown savestate profile` due to distinct local catalog paths; no evidence that the emulator savestate itself was lost. User reports successful restore, but objective frame-by-frame equality and deterministic RNG reset have not been audited.
- **Research lead:** publicly available 2007 Wii Sports Training FAQ reports **ten fixed shooting locations with changing pin location** during Hitting the Green; not validated on user's Wii Sports build. Source: https://gamefaqs.gamespot.com/wii/933010-wii-sports/faqs/45923 . We do **not** know the complete set of possible pin/configuration combinations or how to generate them programmatically.
- **Implementation:** new integrator-owned observed `ScenarioBank` references local named `StateCatalog` checkpoint slots. Includes challenge/shot index/variant/conditions/visual-verification metadata, collision validation, round-robin seeded balanced scheduling, holdout by entire shot-index groups, and manifest of missing shot indices. `scripts/plan_scenarios.py` can register/list observed scenes, write an immutable-by-default JSON schedule, or request replay of one preplanned attempt. This is **offline planning + reset request**, not gameplay randomization or actual scoring.
- **Coordination fix:** canonical runtime checkout and checkpoint registry are `Wii-AI-Golf`; sibling `Wii-AI-Golf-Data` contains raw outputs only. Agent-specific Git branches/worktrees remain valid for coding; no copied second runtime catalog. See `docs/workspace-coordination.md`. Worker 1 notified evaluation #3, modeling #4 and learning #5 in GitHub comments before code changes.
- **Validation:** 4 focused scenario-bank tests passed in local source-equivalent mirror; 14/14 integration tests passed in that partial mirror. Full checkout suite, new scenario CLI on Windows, random config collection and on-screen automatic iteration **not yet tested**. No new scored Wii Sports attempts or recognized swings.

## 2026-10-24 — Worker 1 S001: emulated Wii Remote now controls Wii Sports; dedicated swing probe staged

- **Positive game observation (human):** Wii Sports responded to Python-generated A after Wii Remote 1 switched from Real Wii Remote to **Emulated Wii Remote**, Extension **None**. Earlier Real Wii Remote state and unexpected Nunchuk extension had masked input; neither the Python package nor TCP transport was the culprit. User said configuration now "works flawlessly". Do not infer swing control from button success.
- **Other user-confirmed functionality:** named Python-driven savestate restoration succeeds at a tested slot, making repeatable attempts feasible. Exact local slot is not public and must not be hardcoded in repository.
- **New hypothesis:** Felk Preview4's documented `controller.set_wiimote_swing` may produce recognized golf motion where the earlier 1-2 m/s² acceleration test did not. This is **not yet tested in the user's emulator**.
- **Implementation:** opt-in `--enable-swing` on existing source-pinned bridge patch generator, `trace.submit_swing` single-frame A+swing scheduling with conservative per-sample limits and error release, typed SwingTraceClient, `scripts/probe_swing.py` human-confirmed one-shot probe with optional named reset and local JSONL human observation, focused offline tests and `docs/first-swing-experiment.md`.
- **Experiment metadata:** Study S001, one profile per operator-confirmed attempt (start with forward, only then reverse/sideways if needed); baseline no recognized movement during original weak acceleration trace; game-visible contact is success gate; stop before blind parameter optimization. **0 new live swing trials in this PR; no ball-hit proof.**
- **Verification status:** tests committed but full integrated suite was not executed in the GitHub-only development environment. User should run the commands in docs and provide genuine output and visible observation.

## 2026-10-24 — S001 canonical Hitting the Green intro: user-observed success

- **Human-observed live game finding:** The user reported that the slower `green-pre-start` restore plus controller sequence **A → 300 neutral requests → A+B → 120 neutral requests → A** successfully navigated to the ready-to-swing scene (with corresponding startup/hold/final settle phases `120/30/300/60/120/45/300`). Earlier faster defaults failed to complete A+B and final A. The user asked for a further ~0.25-second margin; PR #22 merged `120/30/315/60/135/45/300` requested-frame defaults. This padding was **not separately verified on game footage**. RPC requests are not guaranteed exact frames or wall time.
- **Code integration fix:** The older `scripts/launch_golf.py` started Dolphin and restored `green-first-shot` without running the proven menu. The standard launcher now delegates to `scripts/launch_hitting_green.py`, selects the named `green-pre-start` profile by default, rejects incompatible default-profile shortcuts, and performs the intro before an optional separately confirmed swing. New tests guard the route and profile selection. `AGENTS.md`, README and one-command docs mandate shared intro logic for future gameplay/training scripts; specialized low-level savestate probes remain explicit diagnostics.
- **Verification limits:** Integration-specific regression tests were added but **not run against the user's Windows checkout during this GitHub connector session**. No automatic menu detector, recognized shot, ball impact or measured game score has been demonstrated in this follow-up. Run `py -m unittest discover -s tests -v` locally and visually confirm first-ball readiness. Claim: [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2#issuecomment-6381974863).

## 2026-10-24 — Coordinator S001: fresh boot required for every real-game experiment command

- **User directive:** Every real-game probe, capture or learning action must begin by starting Felk Dolphin, restoring the appropriate existing savestate and performing the other agent's successfully demonstrated startup sequence. Do not assume a live RPC listener and do not hand out bare `--attach-running` commands as standalone recipes.
- **Implementation (mock only):** new `scripts/run_golf_experiment.py` dispatcher delegates startup to `scripts/launch_golf.py`, which itself invokes `scripts/launch_hitting_green.py` and the shared A → wait → A+B → release → A intro from `green-pre-start`. On startup failure it does not execute the requested action. Refuses duplicate boot commands, second savestate resets and arbitrary external action paths; allows new action-only scripts in canonical `scripts/`.
- **Boundary:** default workflow is first-shot `green-pre-start`; distinct already-at-ball/checkpoint scenes require a separately verified scenario runner without menu reentry. Offline tests/configuration remain offline.
- **Tests/evidence:** 9 mocked regression cases added in `tests/test_golf_experiment_boot.py` but not executed against user's Windows checkout from GitHub-only session. User-confirmed slower menu navigation still stands as prior observation; no live swing, ball contact or game score measured here. Claim in [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2#issuecomment-6382121079).
