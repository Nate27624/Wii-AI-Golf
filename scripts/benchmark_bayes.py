"""Equal-shot-budget offline benchmark; never runs Dolphin or claims Wii scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wii_ai_golf.agents import EliteSearchPolicy
from wii_ai_golf.bayes import BayesianSearchPolicy, RandomBestPolicy
from wii_ai_golf.evaluation import evaluate
from wii_ai_golf.toy_env import TOY_SCENARIOS, ToyGolfEnvironment


def benchmark(*, seed: int = 42, attempts_per_scenario: int = 32,
              repeats: int = 5) -> dict:
    if attempts_per_scenario < 6 or repeats < 1:
        raise ValueError("require at least six training attempts per scenario and one evaluation repeat")
    scenario_ids = tuple(TOY_SCENARIOS)
    methods = {
        "random_best": RandomBestPolicy(seed=seed),
        "elite_search": EliteSearchPolicy(seed=seed),
        "bayesian_ei_gp": BayesianSearchPolicy(seed=seed),
    }
    results = {}
    for method, policy in methods.items():
        training = ToyGolfEnvironment()
        for turn in range(attempts_per_scenario):
            for j, scenario_id in enumerate(scenario_ids):
                observation = training.reset(scenario_id, seed=seed + turn * len(scenario_ids) + j)
                action = policy.act(observation, explore=True)
                result = training.step(action)
                policy.observe(observation, action, result)
        # Freeze the policy for fresh calls. This synthetic environment is
        # deterministic, so repeats audit calls, not independent game trials.
        summary = evaluate(policy, ToyGolfEnvironment(), scenario_ids,
                           repeats=repeats, seed=seed + 100000)
        results[method] = {
            "training_attempts": attempts_per_scenario * len(scenario_ids),
            "evaluation_attempts": summary.attempts,
            "evaluation": summary.as_dict(),
            "final_actions": {
                sid: vars(policy.act(ToyGolfEnvironment().reset(sid, seed=seed), explore=False))
                for sid in scenario_ids
            },
        }
    return {
        "source": "synthetic-only invented objective; no real Wii Sports performance",
        "study_id": "S004-BO-SYNTH-01",
        "seed": seed,
        "scenario_ids": list(scenario_ids),
        "attempts_per_scenario": attempts_per_scenario,
        "evaluation_repeats": repeats,
        "evaluation_note": "frozen same-scenario synthetic evaluation; NOT unseen-scenario generalization",
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--attempts-per-scenario", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = benchmark(seed=args.seed, attempts_per_scenario=args.attempts_per_scenario,
                       repeats=args.repeats)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
