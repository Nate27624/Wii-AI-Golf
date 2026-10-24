"""End-to-end pipeline smoke test. Uses SYNTHETIC physics only."""
from __future__ import annotations

import json

from .agents import EliteSearchPolicy, RandomPolicy
from .evaluation import evaluate, train_elite_search
from .toy_env import TOY_SCENARIOS, ToyGolfEnvironment


def main() -> None:
    train_ids = tuple(TOY_SCENARIOS)[:6]
    holdout_ids = tuple(TOY_SCENARIOS)[6:]
    baseline = evaluate(RandomPolicy(42), ToyGolfEnvironment(), train_ids, repeats=10)
    learner = EliteSearchPolicy(seed=42)
    train_elite_search(learner, ToyGolfEnvironment(), train_ids, iterations=1_200, seed=42)
    train_eval = evaluate(learner, ToyGolfEnvironment(), train_ids, repeats=10)
    holdout = evaluate(learner, ToyGolfEnvironment(), holdout_ids, repeats=10)
    print(json.dumps({
        "WARNING": "SYNTHETIC environment; not a Wii Sports result",
        "seed": 42,
        "training_attempts": 1200,
        "baseline_seen_scenarios": baseline.as_dict(),
        "optimized_seen_scenarios": train_eval.as_dict(),
        "unseen_scenarios_no_retraining": holdout.as_dict(),
        "notes": "EliteSearchPolicy memorizes scenario IDs; holdout results measure failure to generalize",
    }, indent=2))


if __name__ == "__main__":
    main()
