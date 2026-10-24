# Wii AI Golf — Hitting the Green

Collaborative, reproducible machine-learning research for **Wii Sports Golf: Hitting the Green**, using the Dolphin emulator once its control interface is validated.

> **Current status:** framework scaffold, not a working Wii Sports agent. The synthetic demo uses invented physics and must not be interpreted as real-game performance. The Wii Remote input bridge and real-game reward extraction remain unimplemented.

## Objective

Build the complete loop: observe a shot → select an action → execute a controlled Wii Remote swing → measure the result → learn → test on held-out configurations. Compare random action selection, elite search, surrogate/model-based optimization, and RL where justified by data and throughput.

## Start

Requires Python 3.10+:

\`\`\`bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m wii_ai_golf.demo
\`\`\`

If offline build isolation blocks installing dependencies, use \`python -m pip install --no-build-isolation -e .\` with setuptools already installed.

## Structure

- **AGENTS.md** — collaboration rules for multiple AI sessions, role ownership, coordination, review.
- **src/wii_ai_golf/** — shared interfaces, synthetic example, optimization baselines, emulator adapter interface.
- **tests/** — local tests with no game/ROM needed.
- **research/queue.jsonl** — proposed studies (not a running execution queue).
- **research/ledger.md** — sourced findings, uncertainties, handoffs.
- **docs/** — architecture, hardware checklist, and milestones.

## Next milestone

Before GPU-intensive training, complete **100 unattended measured shots on Dolphin** with real input traces, verified score units and tracked failed attempts. Keep train and blind evaluation data separate.

The repository does not contain or distribute Nintendo game files, ROMs, BIOS, savestates, or emulator binaries. Training should run locally by default, rather than as GitHub Actions jobs.

Start by reading [AGENTS.md](AGENTS.md) and [docs/milestones.md](docs/milestones.md).