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
