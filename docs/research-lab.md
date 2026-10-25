# Wii AI Golf Research Lab

**One local application for S000 coordination, S001 integration, S002 evaluation, S003 modeling, S004 learning and S005 generalization.** All experiments have registered ownership, execution mode, stable IDs, canonical commands, and local records. A process exit is *not* a game score.

## Launch the Windows desktop application

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py scripts/golf.py lab gui
~~~

Or use `py scripts/golf_lab.py`. Both load the current checkout through built-in Tkinter; no browser server, third-party packages, or GitHub Actions required.

The interface lists all studies with **OFFLINE / LIVE / PLANNED** classifications. Select a study to see its purpose, input options and exact-command preview. Offline tests, guarded ONE-shot Dolphin actions, recent process execution history and sanitized human-observed results are available in one window. Every live run opens an interactive console for the required tee-ready, consent and observation prompts.

**PLANNED entries cannot run** until the corresponding agent's reviewed work is merged. Do not assume pending S003/S005 studies work merely because they are catalogued.

## Same functions via one CLI

~~~powershell
py scripts/golf.py lab list
py scripts/golf.py lab show evaluation.capture
py scripts/golf.py lab plan evaluation.capture
py scripts/golf.py lab run core.tests
py scripts/golf.py lab run evaluation.tests
py scripts/golf.py lab history
py scripts/golf.py lab reports
~~~

`list`, `show`, `plan`, `history`, `reports` and GUI Preview **never start Dolphin**. A planned command prints the exact subprocess. A live run requires both an explicit `run` and `--live`.

### One guarded real shot

Only when the user approves one experiment, with Dolphin fully closed:

~~~powershell
py scripts/golf.py lab plan evaluation.capture
py scripts/golf.py lab run evaluation.capture --live
~~~

S002's action-only collector is launched through coordinator `run_golf_experiment.py`, which does fresh Felk Dolphin startup, restores the existing `green-pre-start` checkpoint, runs the known A / A+B / A intro, and asks the operator to confirm tee readiness and authorize the shot. It uses **0 separate A prime requests** and fast 3 pre/2 post/3 settled RAM observations. **The latest user report is a FAILED low-strength/non-strike shot even under the unprimed V2 bridge.** Neither this nor S001's separate swing diagnostic is a proven reliable policy. Do not treat the exit code as ball contact.

`integration.swing` is a separately tagged S001 diagnostic with its own configurable A prime and follow-through, not a drop-in equivalent to the S002 workflow.

### Offline audits and comparisons

~~~powershell
py scripts/golf.py lab run evaluation.compare --input "FIRST-candidates.json" --second-input "SECOND-candidates.json"
py scripts/golf.py lab run evaluation.audit --input "motion-summary.json"
py scripts/golf.py lab run evaluation.recover --input "LOCAL-outcome-RAW-PRIVATE.jsonl" --contact yes --green no --distance "100ft"
~~~

The last command only processes a **local** private file and saves a sanitized result; **never upload RAW-PRIVATE memory**. The Lab never accepts arbitrary commands or scripts from its registry.

## What is saved locally

- `Wii-AI-Golf-Data/lab/runs/RUNID.json` — study/agent ID, complete command, UTC start/end, Git revision, generated bridge SHA, process status and exit code; the generic `game_outcome` remains **not_observed_or_verified**
- `Wii-AI-Golf-Data/lab/runs/RUNID.log` — offline unittest/audit output for local inspection
- `Wii-AI-Golf-Data/lab/live-session.lock` — prevents simultaneous **Lab-started** live sessions; it does not cover legacy scripts launched separately
- `Wii-AI-Golf-Data/captures/outcome-*-candidates.json` — **sanitized human-labeled** S002 result summaries indexed by `lab reports`; never confused with a verified game-memory score

The generated bridge's on-disk SHA is not proof of which script an existing running Dolphin loaded. A successful process is not a successful golf shot. When a live process crashes leaving a lockfile, first verify no Dolphin/Lab job is running before manually removing it. No Lab action saves or overwrites a Dolphin savestate.

## Agent contribution contract

Each reviewed entry in `research/experiments.json` has a stable ID, `owner` S000–S005, title, description, `mode` offline/live/planned and a vetted `kind`. The core runner implements **fixed, typed executors**; manifests cannot specify arbitrary shell commands. Agents own their domain scripts and add a narrow tested adapter when work is ready. Active PRs are not silently imported, and entries that have not landed remain `planned`.

Future experiments must maintain the full first-shot Dolphin startup contract; a scenario already saved at the ball requires a separate explicit reset policy. Synthetic research stays labeled synthetic. Raw RAM, ROMs, binaries, savestates and credentials remain private/local. The desktop app is not an automatic training or background scheduling system.

## Local validation

~~~powershell
py scripts/golf.py test --pattern "test_lab_core.py"
py scripts/golf.py test --pattern "test_lab_reports.py"
py scripts/golf.py test --pattern "test_unified_cli.py"
py scripts/golf.py lab list
py scripts/golf.py lab plan evaluation.capture
py scripts/golf.py lab gui
~~~

Tests use fake subprocesses; real Windows GUI/Dolphin behavior must be verified on the operator's machine. Legacy scripts are retained as internal/advanced utilities.

## S002 local trace integration (proposed PR)

The study registry adds **evaluation.trace** as a runnable **OFFLINE** job in Golf Lab. The GUI's existing Input path and Output path fields pass through the typed runner; it cannot start Dolphin or claim ball identification. Capture studies **evaluation.landmarks** and **evaluation.minimap** are visible as **PLANNED** and blocked until their physical-controller/manual-ready workflows have an approved one-boot adapter. No duplicate game launcher or arbitrary script execution is introduced.

~~~powershell
py scripts/golf.py lab gui
py scripts/golf.py lab plan evaluation.trace --input "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf-Data\\captures\\focused-object-xyz-20261025T000301Z-bfd74bbd.jsonl"
py scripts/golf.py lab run evaluation.trace --input "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf-Data\\captures\\focused-object-xyz-20261025T000301Z-bfd74bbd.jsonl" --out "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf-Data\\captures\\two-swing-lab-summary.json"
py -m unittest discover -s tests -p "test_lab_s002_trace.py" -v
~~~

This study analyzes **unverified XYZ candidate motion**, not real ball flight. Raw local JSONL remains on the PC; summary counts and timing can be viewed through the Lab's offline run logs.

## Synchronize agent-uploaded tests

The desktop Lab now has **Sync reviewed**. It checks the canonical GitHub origin and fast-forwards **only a clean local `main` branch** from `origin/main`. It declines detached branches, dirty working trees, and noncanonical origins. **Restart the application** after syncing so Python imports and the experiment registry reflect updated source. Other agents' commits are available through this path **only after their PRs are reviewed and merged into main**. Draft feature branches and arbitrary manifests are never automatically executed. The UI continues to offer `core.tests` for all merged regression tests, including S002 after merge.

S002 `evaluation.trace` is runnable through the UI now on this integration branch, with the path to its local JSONL capture entered in **Input path**. The `evaluation.landmarks` and `evaluation.minimap` rows remain **PLANNED**, not runnable: these are live physical-controller workflows and must first be adapted to the Lab's single-startup contract and its live-session lock. Do not interpret the Sync button as installing those unmerged live runners.
