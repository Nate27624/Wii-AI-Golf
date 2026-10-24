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
