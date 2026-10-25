# ARCHIVED: desktop Research Lab GUI retired

The source code for the old GUI was removed following the operator's script-only decision. This page is historical; the active commands and GitHub publication instructions are in [cli-only-workflow.md](cli-only-workflow.md). Do not implement new GUI variants.

---

# Wii AI Golf Research Lab

**Current operator view:** select **Game tests → Historical V1 contact comparison**, then use **Prepare and run one V1 shot** inside the selected study's right-hand Show/details pane. No detached 1/2/3 toolbar. The Lab safely inspects/validates current V2 and old V1, prepares an isolated copy only with consent, then asks for ONE canonical Dolphin shot. OS process-held Windows locks release on crash and recognized dead legacy PID locks recover without manual deletion; active/unknown owners remain blocked. Git Bash continues to use this same Lab core.

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

## Test a real golf swing — everything in the UI

The historical V1 vs installed V2 experiment previously required a separate shell command to create the V1 bridge. **That is now a fully visible guided workflow** above the Lab's experiment list:

1. **1 Inspect bridges** — runs a registered, read-only S001 audit inside the Lab. You see the backup/current revision and an offline execution log. No Dolphin starts.
2. **2 Prepare historical V1** — available only when the saved before-V2 bridge is structurally safe (V1 swing, atomic trace, **no** savestate autoload). Requires your explicit confirmation, copies the backed-up bytes to a separate `tools/mcp_bridge_swing_legacy_eval.py`, never replaces the installed V2 bridge and refuses to overwrite an unrelated existing file. If backup is absent/unsafe, the UI disables this button and explains why.
3. **3 Run ONE V1 shot** — enabled only when the isolated V1 file exists and meets the expected structural gate. **Close Dolphin first.** Launches exactly one canonical fresh-boot Hitting the Green session, with **A prime 0** and **observed A lead 0** by default; confirms tee-ready and contact through the existing S002 outcome collector. A process exit is not a hit or score.

Clicking steps 1–2 runs an offline Lab job and displays the saved diagnostic output automatically; the **Offline log** button also opens the most recent offline output. Step 3 uses the existing explicitly approved live-test terminal and writes the human observation to the private S002 sanitized candidate summary. There is no automatic series of real shots.

The **Game tests** dropdown filter keeps these actions and other actual Dolphin tests together. A GitHub auto-update of the Lab source does not replace already-imported Python code inside an open GUI. When the sync status says updated, use the new **Restart Lab (updated)** button; it restarts only when no active Lab job or Git update is running. For the FIRST installation of the guided UI, close the older window, `git pull --ff-only`, and reopen `py scripts/golf.py lab gui` once. Subsequent GUI updates have an in-application restart control.

The equivalent terminal experiment IDs, for automated/mock tests and expert debugging only, are `integration.bridge-audit` (offline), `integration.prepare-v1` (offline explicit file creation), and `integration.v1-diagnostic` (live). For normal gameplay testing, prefer the visible three-step panel, not individual PowerShell commands. If the backup isn't valid, do not substitute arbitrary code or overwrite the current bridge; contact/score conclusions must wait until a safe comparison is possible.

## A clear in-window bridge inspection (UI repair)

The Lab's **Inspect bridges** button now reads local V1/V2 provenance directly in the window and immediately displays the installed bridge revision, shortened SHA-256 fingerprint, historical backup, separate V1 test copy and what to do next. It neither opens Dolphin nor starts another console, and it never relies on an offline log existing first. **No more empty “Run an offline experiment and then refresh” popup.** The bridge inspection remains read-only.

**Prepare historical V1** first asks for consent, then runs the already-reviewed `integration.prepare-v1` offline Lab action in a background worker, recording the real run and locally retained stdout/stderr. Progress, verification success, and any failure are shown inside the same Game Testing results panel. It refuses missing/unsafe/autoloaded backups and mismatched existing copies, and never replaces the installed V2 generated bridge or Dolphin savestate. The V1 shot button is enabled only when the current bridge is recognizable V2 **and** the isolated V1 copy's SHA matches the verified before-V2 backup.

Other offline study runners remain available from the catalog. The **Offline log** button now displays a clear in-window message if no completed log exists, rather than popping up an unhelpful dialog. An actual one-shot Dolphin experiment still opens an interactive console for the current collector's human readiness/contact prompts, after explicit consent. Its process exit must not be mistaken for a hit or official score.

After first receiving this UI change, close the existing window once and update the checkout; then reopen `py scripts/golf.py lab gui`. GitHub auto-sync can fetch later UI updates, but the current running Python process must use **Restart Lab (updated)** to reload newly merged code.

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

## Automatically download merged agent tests from GitHub

The Lab now **checks GitHub automatically at startup and every two minutes while the Windows app is open**. It safely fast-forwards a clean checked-out **local `main`** from the exact approved `origin` repository `Nate27624/Wii-AI-Golf`. If a GitHub agent merges a new `tests/test_*.py` file, the app discovers it and shows a **NEW** label next to that file; select it and choose **Run offline** to run the exact file's `unittest` suite. The **Agent tests** filter makes new and existing individual agent suites easy to find. The **Sync GitHub** button checks immediately. All fetched tests remain manual to execute — they do not run automatically.

~~~powershell
# Same safe GitHub synchronization without the GUI:
py scripts/golf.py lab sync
py scripts/golf.py lab list
py scripts/golf.py lab plan agent-tests.test_lab_core
py scripts/golf.py lab run agent-tests.test_lab_core
py scripts/golf.py lab history
~~~

**Preconditions and safeguards:** Auto-sync is permitted only when the local branch is `main`, `origin` exactly matches the approved GitHub URL, the working tree is clean (never stash/reset/force), and no Lab job has an active `run-session.lock` or `live-session.lock`. The updater uses `git fetch origin main`, verifies local HEAD is an ancestor of the fetched commit, and performs a **fast-forward-only** merge. It refuses divergence or a changed working tree. Lab test processes are serialized while the updater is active. If the Lab Python implementation itself changed, **restart the GUI** after the update to use the new code; newly merged test files can already be refreshed and run via fresh Python subprocesses.

Open PR branches and unmerged agent experiments are **NOT automatically downloaded or executed**. They become runnable only after a reviewed merge to main. The interface never executes code received from GitHub as a JSON command. Python tests can execute code, so install/run only tests from the repository and contributors you trust. Local machine must have `git` available and network access to GitHub. `lab sync` reports errors explicitly if offline, dirty, diverged or on an agent branch. The first install of this auto-sync functionality requires one manual `git pull --ff-only`; subsequent refreshes occur while the new Lab UI is open. Updates are not a cloud service and stop when the app closes.

### Requirement for agents

Every S001–S005 agent should commit regression tests under `tests/test_*.py` (unittest-compatible), label its study/owner in the PR, and merge through the normal reviewed PR process. A test file automatically appears as `agent-tests.test_FILENAME_STEM` after merging, **even if the agent did not edit the registry**. Owner tags inferred from filenames are organizational metadata, not permission grants. New live workflows and data exports still require a separately reviewed typed `research/experiments.json` registration and safe Lab adapter. No agent should ask the operator to run tests from divergent experimental worktrees or download arbitrary PR code for live Dolphin.
