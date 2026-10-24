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
- **Validation:** eight new isolated Python unit tests pass locally (savestate catalog/RPC and boot hook). No user-operated savestate load/capture or new button probe yet. Startup auto-load is currently an **untested experimental hypothesis**, and acknowledgement does not establish successful restore.
- **Docs:** `docs/savestate-workflow.md`; Issue #2 claim/handoff. Evaluation #3 owns score extraction; modeling #4 owns physical swing calibration.

- **Adaptability update:** source-pinned patch generator now supports `--startup-profile NAME` resolved via local catalog, as well as `--startup-slot`. This avoids embedding first-shot-specific code in reusable integration and preserves multi-scenario training support.
