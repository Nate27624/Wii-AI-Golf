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
