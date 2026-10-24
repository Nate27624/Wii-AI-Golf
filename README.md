# Wii AI Golf — Hitting the Green

Collaborative, reproducible machine-learning research for **Wii Sports Golf: Hitting the Green**. The long-term goal is to train an agent that plays the real challenge through the Dolphin emulator.

> **Status: research scaffold, not a working Wii Sports AI.** The demo uses an invented synthetic objective. The Wii Remote input bridge, game-state reader, and actual scoring calibration are NOT yet implemented. Synthetic results are not evidence of real-game performance.

## Objectives

Build an experimentally verified loop: observe a shot → propose an action → execute a reproducible Wii Remote swing → measure the final distance → learn → evaluate on untouched shot configurations. Compare random choice, per-scenario search, system identification, model-based control, and reinforcement learning where warranted.

## Quick start (Python 3.10+)

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m wii_ai_golf.demo
```

In offline environments with setuptools already installed: `python -m pip install --no-build-isolation -e .`.

## Project map

- [AGENTS.md](AGENTS.md): role definitions, issue ownership, experiment validity, PR workflow.
- [CONTRIBUTING.md](CONTRIBUTING.md): review/checklist.
- [src/wii_ai_golf](src/wii_ai_golf): shared protocol; synthetic simulator; random and elite-search baselines; Dolphin adapter interface.
- [tests](tests): unit and learning smoke tests.
- [research/queue.jsonl](research/queue.jsonl): proposed experiments (no running job worker).
- [research/ledger.md](research/ledger.md): verified findings, unknowns and handoffs.
- [docs/architecture.md](docs/architecture.md): system boundaries and measurement contract.
- [docs/milestones.md](docs/milestones.md): work phases and acceptance gates.
- [docs/hardware.md](docs/hardware.md): local emulator setup checklist.

## Real Wii Sports launch: standardized first-shot intro

A user-tested A → wait → A+B → A sequence from the existing `green-pre-start` savestate is now the **standard startup for real Hitting the Green experiments**, not a substitute for actual swing recognition. Both `scripts/launch_golf.py` and `scripts/launch_hitting_green.py` execute the same canonical menu routine. Future training/shot scripts must reuse this intro; see [AGENTS.md](AGENTS.md#required-startup-for-real-hitting-the-green-runs-2026-10-24).

After `py -m pip install -e .`, and with Dolphin closed, run:

~~~powershell
py scripts/launch_golf.py --game "PATH_TO_YOUR_WII_SPORTS.wbfs" --profile green-pre-start
~~~

The first command stores the image path and selected **named savestate profile** in a gitignored local config. On later launches just run `py scripts/launch_golf.py`. For an opt-in, human-confirmed swing after automatically reaching the first ball, append `--swing`. To reuse an already-running Dolphin session instead of launching a second instance, run `py scripts/launch_hitting_green.py --attach-running --send-live --swing --confirm-before-swing`.

Prerequisites: single swing-enabled Felk bridge, Wii Remote 1 **Emulated** with **Extension None**, and an existing named `green-pre-start` savestate (do not recapture or overwrite it). Additional [launch instructions](docs/one-command-launch.md) and [calibrated button schedule](docs/launch-hitting-green.md). RPC dispatch counts are not verified contact or score evidence.

## Mandatory one-command **fresh launch** for every live golf experiment

Do not run live probes, recording scripts or training actions against an assumed already-running Dolphin process. Close Dolphin first; use the coordinator wrapper, which **starts Felk Dolphin, loads the existing named `green-pre-start` checkpoint, runs the user-confirmed A/A+B/A intro, then dispatches the selected action**:

~~~powershell
py scripts/run_golf_experiment.py --send-live --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --script probe_swing.py -- --preset forward --send-live-swing
~~~

After the first launch remembers the game image path locally, the `--game` argument is optional. The actual swing script asks for a human confirmation. This is intentionally a **fresh boot**, not `--attach-running`. For data capture and other action scripts, replace `probe_swing.py` and its arguments, but retain the wrapper. Offline analysis and tests do not start Dolphin.

See [fresh-boot command policy and examples](docs/fresh-boot-experiments.md) and [AGENTS.md](AGENTS.md#mandatory-fresh-boot-command-contract-user-directive-2026-10-24). Different already-at-ball checkpoints require their own explicit safe runner; do not blindly replay menu A presses there.

## First real milestone

Demonstrate **100 unattended, measured Dolphin shots** with controller input traces, successful resets, verified distance units, and failures logged. This comes **before** expensive neural network training.

Only synthetic code has been exercised here. The repository intentionally excludes ROMs, BIOS, Nintendo assets, savestates and emulator binaries. Default to local experimentation, not GPU training in GitHub Actions.


## Worker 1 integration research (safe mock first)

```bash
PYTHONPATH=src python scripts/probe_dolphin_bridge.py
# On a PC with Felk's Dolphin scripting bridge v0.2 already running:
PYTHONPATH=src python scripts/probe_dolphin_bridge.py --read-only-live
```

Read [coordination and claims](research/coordination.md) before another AI session starts work. Worker 1's [findings](docs/integrator-research.md) show why the bridge currently cannot guarantee simultaneous button and motion input; no real swing or scored run has yet been demonstrated.
