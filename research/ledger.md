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
