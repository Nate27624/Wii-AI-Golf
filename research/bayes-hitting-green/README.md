# S004-BO-SYNTH-01 — Bayesian Hitting the Green handoff

**Source: synthetic-only.** Branch: `agent/learning/bayes-hitting-green-s004`. Issue: [#5](https://github.com/Nate27624/Wii-AI-Golf/issues/5).

Implemented a per-scenario Gaussian-process expected-improvement optimizer, fair random-best comparator, equal-budget benchmark and targeted tests. Optional NumPy is used for linear algebra. No changes were made to the raw Dolphin bridge, evaluation parser, `ShotAction` protocol or other worker-owned modules.

## Exploratory local verification

Run `python scripts/benchmark_bayes.py --seed 42 --attempts-per-scenario 32 --repeats 5` from the repo root after `pip install -e '.[bayes]'`.

- 8 invented toy scenarios, 256 training and 40 frozen evaluation attempts **per method**.
- Mean synthetic distances: random best **1.9570**; existing elite search **0.1966**; GP expected improvement **0.0053**.
- Seven new targeted tests passed in an isolated local harness; the full merged checkout suite was **not run** in this execution environment. Review must run `python -m unittest discover -s tests -v` on the repository checkout.
- Same-scenario deterministic toy tests; no independent held-out game performance or statistical claims.

## Dependencies for real trials

Wait for [S001](https://github.com/Nate27624/Wii-AI-Golf/issues/2) reliable recognized swings/resets, [S002](https://github.com/Nate27624/Wii-AI-Golf/issues/3) score extraction and [S003](https://github.com/Nate27624/Wii-AI-Golf/issues/4) action calibration. Then preregister an equal-budget real-game BO study before collecting data. See [design notes](../../docs/bayes-hitting-green.md).
