# Hitting the Green: Bayesian search, Part 1 (offline)

**Status:** implementation and synthetic benchmark only. Not a real Wii Sports learning result.

This first part excludes general-purpose challenges, forced clubs, trick shots, RL and vision. It optimizes one shot at a time through the existing `ShotEnvironment` interface.

## Algorithm

`BayesianSearchPolicy` fits an independent Gaussian-process model for each `scenario_id`, with an RBF kernel over **placeholder normalized parameters**: `aim` in [-1, 1] and `power` in [0, 1]. After six random warmup experiments, it proposes actions maximizing **expected improvement for minimization** over RNG-seeded global, local and boundary candidates. `observe` stores actual measured outcomes; frozen inference (`explore=False`) returns the best **observed** action.

The GP uses a noise nugget, adaptive Cholesky jitter and a bounded fitting window; all observations are retained for selecting the best played action. **No actual Wii Remote control or game scoring is provided here.** The action parameters remain uncalibrated.

`Observation.features` are not used: scenarios are handled independently by ID, so this is *not* a generalizing model. Unseen scenario IDs receive a documented untrained fallback.

## Reproduce

```sh
python -m pip install -e '.[bayes]'
python -m unittest discover -s tests -v
python scripts/benchmark_bayes.py --seed 42 --attempts-per-scenario 32 --repeats 5 --output research/bayes-hitting-green/synthetic_results.json
```

The offline benchmark uses the **invented deterministic quadratic** in `ToyGolfEnvironment`, not real Wii Sports physics. All three policies get 32 training attempts per scenario × eight toy scenarios = **256 training attempts each**. Five subsequent frozen evaluation calls per scenario = **40 evaluation attempts each**, with identical scenario IDs, seed protocol and attempt budgets.

The random comparator deploys its **best observed** training action at evaluation, rather than taking an unfair fresh random shot. Existing `EliteSearchPolicy` uses its default configuration.

**Exploratory synthetic result (seed 42, 2026-10-24):** GP expected improvement mean distance **0.0053**, elite search **0.1966**, random best **1.9570**. Distances are the invented toy score exposed by the `distance_m` API. These results are not evidence of real-game superiority, are not preregistered empirical Wii Sports research, and cannot support inferential statistics.

Frozen evaluation revisits already-trained toy configurations. Since the toy is deterministic, repeated evaluations audit calls rather than independent samples. There is **no held-out scenario generalization test** in this first part.

## Part 2 real-game prerequisites

1. Complete **S001**: prove game-recognized golf contact and repeatable savestate restoration, with an audited raw controller trace.
2. Complete **S002**: independently verify scoring units, penalties and outcome extraction. Record missed swings, missed greens and resets explicitly. Validate aggregation over ten shots.
3. Complete **S003**: calibrate mapping from normalized action parameters to real controller motion; change the protocol only through coordinator review.
4. **Before any live BO data collection**, preregister configurations, untouched evaluation states, seeds, equal training/evaluation budgets, baselines, handling of noise and failures, and stopping rules. Keep raw footage and traces.

The `act` → `ShotEnvironment.step` → `observe` loop can consume real measured `ShotResult` values once those external prerequisites exist. This patch does not assert Dolphin integration.
