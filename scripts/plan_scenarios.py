"""Register observed Wii Sports configurations and create deterministic train/test plans.

Do not run from a second copied checkout with a different savestate catalog.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import StateCatalog, StateManager
from wii_ai_golf.integration.scenario_bank import Scenario, ScenarioBank

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "research" / "savestates.local.json"
DEFAULT_BANK = ROOT / "research" / "scenarios.local.json"


def _conditions(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key or not value or key in out:
            raise ValueError("conditions must be unique KEY=VALUE pairs")
        out[key] = value
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Observed golf scenario coverage: register, plan, and load")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                        help="same absolute named savestate catalog used by savestate_session.py")
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK,
                        help="local scenario labels, shot indices and observed variants")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    add = sub.add_parser("add", help="register an existing savestate as an observed configuration")
    add.add_argument("name")
    add.add_argument("--checkpoint", required=True)
    add.add_argument("--challenge", default="hitting-green")
    add.add_argument("--shot-index", type=int)
    add.add_argument("--variant", default="unmeasured",
                     help="observed pin/layout variant label; never invent variations")
    add.add_argument("--condition", action="append", default=[], help="KEY=VALUE (e.g. pin=left)")
    add.add_argument("--visually-verified", action="store_true",
                     help="human confirmed exact current state restores via Dolphin")
    plan = sub.add_parser("plan", help="seeded, balanced planning only; NEVER drives game")
    plan.add_argument("--rounds", type=int, default=3)
    plan.add_argument("--seed", type=int, default=42)
    plan.add_argument("--balance", choices=("shot", "scenario"), default="shot")
    plan.add_argument("--holdout-shots", default="", help="comma-separated shot indices to isolate in evaluation")
    plan.add_argument("--include-unverified", action="store_true")
    plan.add_argument("--out", type=Path, required=True, help="new JSON file in local evidence folder")
    load = sub.add_parser("load-attempt", help="request state load for a single preplanned attempt")
    load.add_argument("--plan", type=Path, required=True)
    load.add_argument("--attempt", type=int, required=True)
    load.add_argument("--port", type=int, default=55355)
    args = parser.parse_args()
    catalog = StateCatalog(args.catalog)
    bank = ScenarioBank(args.bank, catalog)
    if args.command == "list":
        print(json.dumps({"catalog": str(args.catalog), "bank": str(args.bank),
                          "scenarios": [asdict(s) for s in bank.scenarios.values()]}, indent=2))
    elif args.command == "add":
        s = Scenario(args.name, args.checkpoint, args.challenge, args.shot_index,
                     args.variant, _conditions(args.condition), args.visually_verified)
        bank.add(s)
        bank.save()
        print(json.dumps({"registered": asdict(s), "bank": str(args.bank)}, indent=2))
    elif args.command == "plan":
        holdout = frozenset(int(x) for x in args.holdout_shots.split(",") if x.strip()) if args.holdout_shots else frozenset()
        result = bank.plan(rounds=args.rounds, seed=args.seed, balance=args.balance,
                           holdout_shots=holdout, verified_only=not args.include_unverified)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        print(json.dumps({"saved": str(args.out), "seed": result["seed"],
                          "train_count": result["train_count"], "holdout_count": result["holdout_count"],
                          "observed_shots": result["seen_hitting_green_shots"],
                          "missing_shots": result["missing_hitting_green_shots"]}, indent=2))
    else:
        payload = json.loads(args.plan.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("unsupported plan format")
        row = next((x for x in payload["attempts"] if x["attempt"] == args.attempt), None)
        if row is None:
            raise ValueError("attempt not present in plan")
        registered = bank.scenarios[row["scenario"]]
        if registered.checkpoint != row["checkpoint"]:
            raise ValueError("plan no longer matches registered scenario")
        profile = catalog.get(registered.checkpoint)
        if profile.slot != row["slot"]:
            raise ValueError("savestate slot changed since plan generation")
        with FelkRPC(port=args.port) as rpc:
            result = StateManager(rpc).request_load(profile)
        print(json.dumps({"attempt": args.attempt, "scenario": registered.name, **result}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
        print(f"scenario plan error: {exc}", file=sys.stderr)
        sys.exit(1)
