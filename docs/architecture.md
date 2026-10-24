# System architecture

```text
                         Study / scenario manifest
                                     |
                                     v
                        ShotEnvironment Protocol
                        reset(id, seed) -> Observation
                        step(ShotAction) -> ShotResult
                              /               \
                  ToyGolfEnvironment      DolphinEnvironment
                  (synthetic only)               |
                                             DolphinBridge
                                             - deterministic attempt setup
                                             - Wii Remote motion event trace
                                             - capture actual final score
                              \               /
                                 Policy
                        Random / Elite Search / Future RL
                                     |
                        Training and evaluation metrics
```

The normalized ShotAction(aim, power) is a **provisional abstraction**, not a verified representation of Wii Remote swing control. Do not assume a valid mapping until calibrated on the target game.

Observation: numeric features plus a scenario identifier, with a documented extraction method for every feature. ShotResult: real final distance in meters and holed-out status, only after score units and parsing have been verified on game footage. Real implementations must also log unconverted raw score for auditing.

## Real-game data logging requirement

Append one record per attempt: study_id, run_id, scenario_id, seed, emulator version, game region/revision, observation/feature schema, action, controller trace hash, on-screen raw score + unit, converted score + unit, measurement method, confidence, duration, error/reset status and source (emulator/human). Preserve raw evidence outside Git, with safe artifact hashes.

## Research comparisons

1. Random exploration and fixed heuristics establish an honest baseline.
2. Parameter sweeps and elite search test controllability and optimize *seen* situations.
3. Response-surface modeling and Bayesian optimization test sample efficiency.
4. Contextual model-based policies target generalization to *unseen* situations.
5. RL can be attempted after automatic resets/rewards and shot throughput are sufficiently reliable.

## Experimental gates

100 unattended shots with >95% complete valid outcomes, verified raw score units, and repeatable action-to-result effects precede any claim of real-game learning. A ten-shot run is composed of ten ShotEnvironment attempts; per-shot means alone do not prove a medal threshold.
