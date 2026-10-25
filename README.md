# Wii AI Golf

## New: one shared Research Lab (S000–S005)

**Instead of chasing agent-specific scripts, launch the Windows app:**

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/golf.py lab gui
~~~

Or run `py scripts/golf.py lab list`, `lab plan EXPERIMENT_ID`, `lab run EXPERIMENT_ID`, `lab history` and `lab reports` from a terminal. The Lab catalogs S001 control, S002 read-only evaluation, pending S003 modeling, S004 synthetic learning and pending S005 generalization behind **one reviewed experiment registry**. A live run needs explicit `--live` and performs the **canonical single fresh Dolphin/Slot2/A–A+B–A startup**, with human authorization. Execution metadata and offline logs are local, human observations remain distinct from verified scores, and raw RAM is never uploaded.

**Latest observed shot:** the unprimed outcome-collector trial under generated bridge V2 failed to strike with adequate strength; the Lab does **not** label its profile reliable yet. We are standardizing experiments before further uncontrolled A-timing changes.

See [Research Lab user guide](docs/research-lab.md), the registry `research/experiments.json`, and [agent contract](AGENTS.md). Older `scripts/*.py` commands remain supported for their domain owners.


**Reproducible AI control and learning for Wii Sports Golf — Hitting the Green.**

One research pipeline: **emulator control → observed outcomes → swing calibration → optimization → held-out evaluation**. Different agents own different modules, but they share one study plan, one controller protocol, one local evidence directory and one public CLI.

## Current evidence (2026-10-24)

**Working:** Python starts Felk Dolphin with Emulated Wii Remote 1, no Nunchuk, a registered pre-start checkpoint, and the verified A → wait → A+B → wait → A intro. One human-observed forward swing is logged with **89/89 dispatched frames**, **ball visibly moved = yes**, **on green = no**, and a visual meter estimate of **about 75%**.

**Not yet established:** calibrated game power percentage, automatic landing-distance/score extraction, repeated-shot precision, 100 unattended scored trials, or a trained policy that improves Wii Sports performance. The 75% is a visual gauge estimate, *not a machine-verified power measurement*. Synthetic examples never count as Wii Sports outcomes.

## One interface

From the canonical Windows checkout, use Python 3.10+. **No editable install is required** for the source-local CLI.

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py scripts/golf.py --help
py scripts/golf.py doctor
~~~

### Everyday commands

| Goal | Command | Dolphin effect |
| --- | --- | --- |
| Check local setup | `py scripts/golf.py doctor` | Read-only |
| Boot to first ball | `py scripts/golf.py play --slot 2` | **Fresh full intro** |
| Guarded swing (longer A pre-hold, experimental) | `py scripts/golf.py swing --slot 2` | **Fresh intro + human confirmation** |
| Test A release timing | `py scripts/golf.py swing --slot 2 --follow-through-frames 45` | Fresh intro + one guarded shot |
| List named checkpoints | `py scripts/golf.py state list` | Read-only |
| View study plan | `py scripts/golf.py research studies` | Read-only |
| Summarize local swing logs | `py scripts/golf.py research evidence` | Read-only |
| Run unit tests | `py scripts/golf.py test` | Offline |
| Try synthetic demo | `py scripts/golf.py demo` | Offline, **not Wii Sports** |

**Close Dolphin before `play` or `swing`.** Both use `launch_golf.py → launch_hitting_green.py → menu_sequence.py`, not copied or guessed intro delays. The game image and local controller preferences are remembered from your verified setup. Slot 2 must map to `green-pre-start` in the ignored local savestate catalog; no commands create or overwrite state bytes. The actual swing requires visual confirmation and post-shot human labeling.

Advanced experiments: `py scripts/golf.py experiment --script probe_swing.py --send-live -- --preset forward --send-live-swing`. The existing coordinator wrapper launches just one session and attaches its approved child without booting a second Dolphin.

See **[the CLI guide](docs/cli.md)** for command reference, flags and safety.

## Repository map

~~~text
Wii-AI-Golf/
├── scripts/
│   ├── golf.py                    # Public source-local CLI
│   ├── launch_golf.py             # Canonical Dolphin/controller/state startup
│   ├── launch_hitting_green.py    # Canonical A / A+B / A intro
│   ├── probe_swing.py             # One guarded shot and human observations
│   └── ...                        # Advanced adapters and diagnostics
├── src/wii_ai_golf/
│   ├── cli.py                     # One CLI, delegates to existing scripts
│   ├── integration/               # Felk RPC, savestates, swing/bridge
│   ├── audit/                     # Read-only RAM candidate audit
│   ├── research_catalog.py        # Read-only research/evidence summaries
│   ├── protocol.py                # Future ShotEnvironment contracts
│   ├── agents.py, evaluation.py   # Synthetic baseline code
│   └── toy_env.py                 # Synthetic physics only
├── research/
│   ├── README.md                  # Study lifecycle and evidence rules
│   ├── queue.jsonl                # S001–S005 proposals, not live jobs
│   ├── ledger.md                  # Historical evidence and limitations
│   ├── claims/                    # Agent ownership
│   └── worker*/                   # Role-specific notes
├── tests/                         # Unit/integration/CLI regression checks
├── docs/                          # Detailed workflows, design and measurements
└── AGENTS.md                      # Ownership/startup/evidence contract
~~~

The sibling `Wii-AI-Golf-Data/` holds local shot JSONL, screenshots and other artifacts. ROMs, emulator executables, savestates and personal configurations do **not** go into Git. Worktrees are for coding; the canonical runtime checkout contains the live state mappings.

## A shared research program

| Study | Role | Current gate |
| --- | --- | --- |
| **S001** | Integration/control | **First user-confirmed ball contact; next three-shot repeatability** |
| **S002** | Evaluation | Validate distance, landing and score against real game evidence |
| **S003** | Modeling | One-factor motion/power calibration after outcomes are measurable |
| **S004** | Learning | Fair, equal-attempt search; synthetic results stay synthetic |
| **S005** | Generalization | Test unseen shot layouts after S002–S004 |

`research/queue.jsonl` holds **proposals**, not a live scheduler. Actual agent work is tracked in GitHub issues and PRs, with S002/S003/S004 still owned separately. See [research workflow](research/README.md), [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md) and [milestones](docs/milestones.md).

## Contribute and test

~~~powershell
py scripts/golf.py test
py scripts/golf.py test --pattern "test_unified_cli.py"
py scripts/golf.py demo
~~~

Optional installation: `py -m pip install -e .` then `wii-golf --help` or `py -m wii_ai_golf --help`. Prefer `py scripts/golf.py` across multiple worktrees; it loads that checkout's source rather than a stale editable package.

The historical `scripts/*.py` commands remain functional for advanced users and the other agents. This is an **additive** consolidation, not a breaking rename. See [CONTRIBUTING.md](CONTRIBUTING.md).


## Current swing ordering experiment

**Observed failure (2026-10-24):** After a good full Dolphin launch and A/A+B/A menu intro, the operator reported that motion happened before A visibly engaged, **no ball contact**, even with 45 A-held neutral samples in the swing trace. Investigation found that those so-called A-only samples **still invoked Dolphin's swing API with zero motion**. That is not equivalent to button-only input.

The current command now sends **60 separate `controller.set_wiimote_buttons(A=True)` RPC requests with NO swing API calls**, then replays the **unchanged 89-frame forward trace** from the first user-confirmed hit (12 neutral samples inside trace, 15 back, 20 forward, 30 A-held follow-through, 12 release). This is a new **untested** ordering hypothesis, not another confirmed hit.

~~~powershell
# Close Dolphin entirely; then this command handles everything.
py scripts/golf.py swing --slot 2 --a-prime-frames 60

# To compare against the original swing trace WITHOUT additional button-only priming:
py scripts/golf.py swing --slot 2 --a-prime-frames 0
~~~

The standard CLI uses `--a-prime-frames 60`, `--a-setup-frames 12`, and `--follow-through-frames 30`. Both normal commands retain the canonical fresh Felk startup, Emulated Wii Remote 1/Extension None, Slot 2 restore, A/A+B/A intro and human ready-screen confirmation. See [timing experiment](docs/first-swing-experiment.md) and [CLI guide](docs/cli.md). In-game button acceptance is still human-observed, not automatically verified.
