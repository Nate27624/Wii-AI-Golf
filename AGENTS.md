# AI agent coordination protocol

## ACTIVE OPERATOR RULES — 2026-10-27 (READ FIRST; SUPERSEDES GUI-ERA TEXT)

**Operator-only interface: Windows PowerShell, CLI-only, copy/paste-ready.** Before proposing ANY local action, read [operator PowerShell contract](docs/operator-powershell-contract.md) and [repository map](docs/repository-map.md). These current instructions govern every agent S000–S005 and supersede older GUI/Git Bash/manual Dolphin startup examples below. Historical sections are retained as evidence, not active operator runbooks.

- **MANDATORY automatic GitHub result publication and findings handoff:** Any operator-run test or research command that generates results MUST automatically publish the **approved sanitized result summary** to the existing `research/observations` GitHub branch **in the same command**, using the reviewed `scripts/research_cli.py` publisher/allowlist. No manual `git add`, GitHub upload, copying files, pasting raw output, PAT creation, or separate post-run command for the operator. This auto-publication is for **sanitized results only**; raw MEM1/MEM2, PRIVATE JSON, ROM, savestates, pointers, traces, generated bridges and local/private paths NEVER leave `Wii-AI-Golf-Data`.
- **Missing uploader is a development blocker, not an excuse:** If a study's operator command lacks reviewed auto-publish integration, agents MUST first add a **narrow tested adapter to the canonical publisher** under S000/S002 privacy review, or clearly report that automatic upload is NOT YET IMPLEMENTED and do not claim its outputs will reach GitHub. No custom secondary publisher and no bypass of the allowlist. The explicit operator `--no-upload` or privacy/safety failure overrides the default; never post unsafe data merely to comply.
- **Every important positive OR negative finding must be recorded:** For a validated or consequential hypothesis result, missed strike, candidate-variable change, calibration, contradicted assumption, blocker, regression, or P0 gate decision, post a concise dated **FINDING** on its owning GitHub issue/PR with study/run ID, source classification, commit/bridge/profile/trace identity where safe, sanitized observation URL or failure state, controls, limitations, confidence, and follow-up owner. Append the evidence-qualified conclusion to `research/ledger.md` via the owner's normal reviewed PR/integration path (do not race edits on main); link the exact issue and sanitized record. Do **not** promote source-only or human-only observations to physical XYZ, swing power, verified score or training eligibility.
- **Upload failure is visible and preserved:** Save a sanitized local record before pushing; on auth, offline, concurrent-push, schema or privacy failure report `NOT UPLOADED` with a safe error and stop/abstain rather than inventing success or asking the operator to manually upload RAW files. The agent tracks the blocker in the GitHub issue if GitHub is reachable. Verified GitHub publication requires an observed successful publisher return/link; a terminal success or local saved JSON is not proof of upload.
- **NEVER tell the operator to open, click, load, configure or manually run Dolphin or a Lab GUI.** The operator pastes one complete PowerShell block from any working directory and returns terminal output. If no local action is needed, say so; if the capability is absent/unmerged, implement a reviewed CLI adapter or identify the blocker instead of issuing hand-operated steps.
- **PowerShell block contract:** `$ErrorActionPreference = 'Stop'`; set `$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'`; `Set-Location -LiteralPath $repo`; use exact currently merged existing scripts/flags and local private sibling path; include failure guards (`$LASTEXITCODE`) and expected *sanitized* console fields. Commands should not depend on unreviewed branch files or assume Dolphin/bridge was already launched.
- **Reuse S001's validated commands and 89-sample source-frozen swing.** Canonical fresh-game startup, named checkpoint, Emulated Wii Remote and A/A+B/A menu are owned by existing code; do not duplicate or re-time without owner-reviewed controlled trial. The operator's previously validated **45-frame A** method must not be silently substituted with a different mechanism simply because it also uses 45. Distinguish menu final-A 45 request frames, separate A-only prime 45 requests, V1 observed-frame A-lead 45, and trace-neutral 45; they are NOT equivalent. Preserve the exact historical approved implementation, bridge protocol and trace hash for a given study.
- **One canonical controller stack; no competing implementations.** For result-sharing use the maintained `scripts/research_cli.py` after merged safety gates; broader `scripts/golf.py` is a source-local wrapper for doctor/state/other existing commands. Live startup is delegated to `run_golf_experiment.py -> launch_golf.py -> launch_hitting_green.py -> menu_sequence.py`, not a bare `probe_swing.py --attach-running` or a separate Dolphin invocation.
- **No unsafe live instruction just because a PR is green.** Check actual main vs draft, safe clean Felk exe/User + physical named savestate, S001/S000 acknowledgement, source gates, one explicit live human consent and unchanged trial waveform. A synthetic PASS, 89/89 bridge dispatch, a human-observed hit and a verified score are separate statuses. No auto-run or unattended shots.
- **Branch/evidence discipline unchanged:** no raw MEM1/MEM2/ROM/savestate/PRIVATE JSON, pointers or generated bridge in Git; no destructive Git commands. Claim GitHub issue paths, respect PR ownership; require cross-owner review before shared CLI/rule changes.

**Precedence:** latest direct operator instruction > this ACTIVE section / operator PowerShell contract > current merged CLI implementation + docs/cli-only-workflow.md > historical dated sections below. If older text says GUI supported, use Bash, load Dolphin manually, or change A timing experimentally as a default, **that older instruction is superseded**. See [docs/repository-map.md](docs/repository-map.md) for actual repository/data/agent structure.

---

## Delegated self-merging

**Agents may merge their own PRs** when every gate in [merging requirements](docs/merging-requirements.md) is met and posted as a `MERGE READY` checklist. S000 is not a routine approval bottleneck; shared interface changes require acknowledgment by canonical owners and S000 before the author self-merges. Draft/conflicted/untested PRs cannot self-merge. Preserve GitHub protection rules and exact test evidence.
## Required cross-agent handoff

Read [cross-agent cooperation contract](docs/cross-agent-cooperation.md) before changing a shared interface. Every PR must identify upstream/downstream owners, concrete schemas/commands, collision paths, exact tests and evidence limitations, and the next integration owner. Publish API changes on the affected GitHub PRs/issues before consumers integrate them. S000 coordinates merge order; agent chats are not a shared queue. The operator's desktop Lab GUI is supported for selected-study game testing; Git Bash remains a supported expert workflow using the same Python runner.


## New research result publication (sanitized only)

The script-only operator workflow now includes explicit requested **automatic publishing of allowlisted SANITIZED summaries** via `scripts/research_cli.py`. Run results go to the distinct `research/observations` branch; code PRs go to `main`. This is not permission to upload raw captures, ROMs, savestates, generated bridges, local paths, configs or arbitrary logs. The operator can opt out with `--no-upload`. Agents must examine the small observation JSONs on that branch when planning new experiments. Do not create another independent application or user-facing GUI. The published `process_exit_code` is not a game score. See [docs/cli-only-workflow.md](docs/cli-only-workflow.md).

## ARCHIVED (2026-10-24): former GUI-first operator decision

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

This operator explicitly asks that the Lab GUI remain available, with the historical V1 trial in the selected experiment's Show/details pane, not detached toolbar steps. Support `py scripts/golf.py lab gui` alongside optional `scripts/golf.sh` / CLI. Both share one reviewed typed Lab runner, GitHub-synced tests, history and safety gates. The V1 action checks bridge provenance, requests approval before verified separate V1 preparation, then approval before exactly one Dolphin shot.

Lab session locks must be OS-released on crash; inspect previous JSON PID conservatively and never treat a leftover lockfile as proof a job is active. Preserve active/unknown locks, and never auto-upload private game evidence or infer an actual hit from script exit. New domain workflows must be usable from the shared Lab and use agent handoff contracts.
---


## Mission and trust model

Coordinate separate AI coding/research sessions to develop a scientifically reproducible agent for Wii Sports Golf's Hitting the Green. **Roles are logical responsibilities, not persistent autonomous processes.** No agent should claim a run happened unless logs show it.

Every session MUST read README, this document, research/ledger.md, research/queue.jsonl, open GitHub Issues/PRs and relevant tests before changing code.

## ARCHIVED (2026-10-24): GUI result-handling guidance

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

The operator reported that **Inspect bridges** opened a blank console and a generic missing-log popup instead of showing any V1/V2 facts. UI diagnostics must render **structured, action-specific results in the application itself**; do not bounce users between short-lived consoles, hidden `*.log` files, and generic message boxes. Read-only inexpensive inspections can run directly; write-capable preparation must use the same reviewed Lab runner and show progress/errors in-window. Continue to record local provenance while keeping raw RAM local and interactive live Dolphin inputs explicitly approved. Add tests covering missing backup, wrong revision, mismatched V1 copy and no missing-log popup.

## HISTORICAL (2026-10-24): broad golf.py CLI (see active PowerShell-only contract)

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

The project now has one **user/operator-facing entrypoint**: `py scripts/golf.py`. Use [docs/cli.md](docs/cli.md) for command reference, [research/README.md](research/README.md) for the S001–S005 research program and [docs/milestones.md](docs/milestones.md) for gates.

- **Normal game actions:** `golf play --slot 2` and `golf swing --slot 2` delegate to the existing, tested `launch_golf.py → launch_hitting_green.py → menu_sequence.py` sequence. They do not introduce independent A / A+B / A timings, new savestate writes, or concurrent Dolphin processes. When proposing commands to the user, use the unified CLI rather than separate manual script attach/reset instructions.
- **Advanced and agent code:** older `scripts/*.py` remain valid internally. If a worker adds useful operator functionality, add one narrow CLI adapter with a mocked single-launch regression; do not rename, fork or silently overwrite another worker's implementation.
- **Source portability:** direct `py scripts/golf.py` must work after `git pull` without requiring pip editable reinstall or falling back to a stale installed `wii_ai_golf` from another worktree.
- **Evidence hierarchy:** Felk RPC completion, user-observed ball contact, verified game distance/score, reproducible repeats and learned improvement are *distinct* gates. The first 89-frame forward swing had human-observed ball movement and not-on-green; don't call it a scored or optimized result. Static queue status does not represent live worker execution.
- **Compatibility boundary:** evaluation S002, modeling S003 and learning S004/S005 own their pending feature PRs. Coordinator CLI delegates to their stabilized entrypoints after those features land; do not import unmerged dependencies or claim their results verified.

## Roles and ownership

| Agent role | Scope | Primary ownership |
| --- | --- | --- |
| integrator | Dolphin automation, reproducible reset, Wii Remote input playback, outcome capture | emulator adapter, docs/hardware.md |
| modeling | Input calibration, control response, surrogate/physics models | models module, calibration experiments |
| learning | Random/search baselines, contextual policies, RL (when justified) | agents module, learning modules |
| evaluation | Score extraction verification, splits, held-out tests, provenance, replay and metrics | evaluation, research/results |
| coordinator | Interface compatibility, task priority, integration review, shared research ledger | AGENTS.md, documentation and cross-role PRs |

## Collaboration rules

1. Choose an open, non-overlapping GitHub issue. **Claim it in an issue comment**, recording your agent/session, code paths and intended test; do not assume another session sees your chat.
2. Work on a dedicated branch named `agent/<role>/<slug>` from up-to-date main. No direct feature commits to main, no overwriting concurrent branches, no forced shared branch updates.
3. Restrict edits to claimed paths. Protocol schema changes need coordinator review and compatibility tests.
4. Before a PR, run `python -m unittest discover -s tests -v`; add targeted tests and state explicit commands/results.
5. PR body contains hypothesis, exact scope, issue, experiments, positive and negative findings, sample budget, evaluation split, limitations and reproducibility instructions.
6. Integrate through PR after tests and review. If another PR changed a shared file, update your branch and resolve conflict deliberately.
7. Append findings to research/ledger.md and proposal records to research/queue.jsonl; don't erase failures or mark studies complete without associated artifact links.

## Required startup for real Hitting the Green runs (2026-10-24)

**User-confirmed working baseline:** On the target Wii Sports USA Rev 1 setup, a live operator saw the first-shot screen reached with the existing `green-pre-start` savestate and the A → wait → A+B → release → A menu sequence. PR #22 standardized the slower default timing with a small margin: requested-frame counts **120, 30, 315, 60, 135, 45, 300**. These are *RPC requests*, not accurate wall-clock/video frame timing; no automatic screen-state verifier exists yet.

**Rule for all future real-game golf launch/training scripts:** use the canonical `scripts/launch_hitting_green.py` flow or call its shared `wii_ai_golf.menu_sequence.planned_menu_phases` / `execute_menu_phases` logic after loading the same named `green-pre-start` checkpoint through `StateCatalog` + `StateManager`. Do **not** issue a bare `savestate_session start green-first-shot` and treat it as readiness; do not duplicate hardcoded menu delays in training code. `scripts/launch_golf.py` must delegate to the canonical intro rather than stop after savestate load. To add a new action collection loop, use this startup as the reproducible S001 baseline before any first-ball swing.

- Use `green-pre-start` by **name** in `research/savestates.local.json`; do not hardcode a slot, overwrite existing savestate bytes, or copy a game image into Git.
- Fresh boot: Felk Dolphin, **Emulated Wii Remote 1 / Extension None**, single `mcp_bridge_swing.py` patched without a separate startup-slot hook. Restart before fresh launch if another bridge occupies port 55355.
- Running emulator: `py scripts/launch_hitting_green.py --attach-running --send-live` restores the named checkpoint and runs the intro. Fresh boot: `py scripts/launch_golf.py` (first run prompts for game image, stores locally), or `launch_hitting_green.py --dolphin ... --game ... --bridge ... --send-live`.
- Actual swing execution is a **separate** phase and requires explicit opt-in (`--swing`, ideally with a human-ready-screen confirmation until screen detection exists). Controller ACK alone is not proof of recognized shot, successful menu navigation or score.
- **Canonical experiment entrypoints:** `py scripts/launch_golf.py --slot 2 --swing --follow-through-frames 30` and `py scripts/probe_swing.py --slot 2 --preset forward --follow-through-frames 30 --send-live-swing` both run the **entire** Dolphin + Emulated Wii Remote + named savestate + verified A / A+B / A intro before a guarded swing. The bare `probe_swing.py` must delegate to `launch_golf.py` automatically and must **never** assume a bridge already exists (previous bare call produced Windows 10061). `--attach-running` is reserved for an explicitly already-running, ready-to-swing Dolphin; the launcher uses it only for its own swing child to avoid recursion. **Do not recommend bare-bridge probe commands for normal training/evaluation runs.**
- Low-level `savestate_session.py`, `probe_wiimote.py`, `probe_atomic_trace.py` and custom scenario resets remain permitted as **explicit diagnostics**, not the normal first-shot golf launcher. Alternate saved-at-ball states require their own documented scenario contract and proof of readiness.
- Add a regression test whenever launch behavior changes, verifying that the canonical intro is invoked before an optional swing. Keep the user-confirmed timing baseline available as a default; proposed recalibration must preserve a runnable known-good profile.

Relevant docs: [launch-hitting-green.md](docs/launch-hitting-green.md), [one-command-launch.md](docs/one-command-launch.md), [workspace-coordination.md](docs/workspace-coordination.md). Observed menu success was **human reported**, not frame-count/video verified by an automated detector.

## Mandatory fresh-boot command contract (user directive 2026-10-24)

**Every user-facing command that interacts with LIVE Wii Sports must independently start Felk Dolphin, launch the game, restore the appropriate existing named checkpoint, and complete the integrated startup/navigation before any new probe, swing, capture or training action.** Do NOT give users bare `py scripts/probe_swing.py`, `py scripts/start_golf_recording.py --attach-running`, `py scripts/discover_golf_motion.py`, `py scripts/probe_dolphin_bridge.py --read-only-live`, or similar commands that assume a manually running Dolphin bridge.

**Canonical standard first-shot dispatcher:** `py scripts/run_golf_experiment.py --send-live --script ACTION.py -- [action arguments]`. It first invokes `scripts/launch_golf.py` (emulated controller, fresh Felk Dolphin + legal Wii Sports image, named savestate `green-pre-start`, user-confirmed A → wait → A+B → release → A intro via `launch_hitting_green.py`), then executes ACTION.py **only if startup returned successfully**. A user-given game path is saved only in the ignored local launch config. Every future real-game action must either be runnable through this dispatcher or supply an equivalently self-contained fresh boot command *delegating* to the canonical launcher; no duplicate startup code or menu timing constants.

If the requested scenario is already saved at the ball or is a later shot, it requires an **explicit scenario-specific named savestate and skip-menu safety contract**. Never run A/A+B/A from an arbitrary at-ball state. The current first-shot dispatcher intentionally rejects those alternate checkpoints until properly integrated. Low-level attach/reset commands are internal diagnostics, **not full user-facing run instructions**. Existing Dolphin must be closed for fresh boot; do not start duplicate bridges. Offline tests, source analysis, patch generation and scenario planning do not require Dolphin; this directive applies to commands touching the live game.

See [fresh-boot-experiments.md](docs/fresh-boot-experiments.md) for exact commands and mock regression tests. Controller RPC acknowledgements, savestate load requests and successful menu dispatch are not automatic confirmation of visual readiness, ball contact or score.

## Scientific integrity gates

- Every experiment gets a unique study ID, baseline, hypothesis, seeds, train/evaluation partitions, attempt/time budget, success criterion and stop rule BEFORE training.
- Distinguish synthetic vs actual-emulator vs human observations; never transfer synthetic benchmark scores into game claims.
- Measure controller traces, Dolphin build, Wii Sports region/revision, shot configuration, result measurement source, game units, failure counts and environment settings.
- Hold out shot configurations as well as repeats/seeds where feasible. No training on a held-out score followed by calling it blind evaluation.
- Include identical shot budgets for competing methods; record expensive calibration shots too.
- Use the local machine by default. No GitHub Actions training workers or unexplained cloud costs.

## Priorities

1. Reliable game input/reset and measurement (100 logged unattended attempts).
2. Random baseline and calibrated parameter optimization.
3. Held-out scenario tests and contextual/surrogate models.
4. RL when the simulator or emulator offers demonstrably adequate throughput.
5. Video production with traceable performance plots and footage.

## Do not fabricate integration

The current DolphinBridge is a dependency-injected interface, not a working Dolphin API integration. ShotAction aim/power are placeholder normalized parameters until real motion has been calibrated. The current toy environment uses invented physics.

When blocked by legal game access, emulator control, inaccurate score units or unreliable resets, record the blocker, reproduce it and propose a test instead of pretending the code works.


## Collision prevention and handoffs

Before claiming or editing a new workstream, read [research/coordination.md](research/coordination.md), `research/claims/`, and the corresponding issue comments. Claims are recorded FIRST in an issue comment, then in a per-worker JSON file; conflicting paths require an explicit handoff. The shared ledger is a summary, not an automatic job scheduler or locking service. Keep raw findings in per-worker research folders to minimize merge conflicts.

## ARCHIVED GUI-era integration path (historical; current CLI-only contract takes precedence)

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

The project now includes one source-local **`py scripts/golf.py lab ...`** experiment registry/runner and **`py scripts/golf.py lab gui`** Windows app. [docs/research-lab.md](docs/research-lab.md) defines the user/operator workflow and [research/experiments.json](research/experiments.json) is the reviewed catalog.

- Every worker that proposes a new operator-visible test must register a stable `S000–S005`-owned ID with a **reviewed typed kind** (not a free-form shell command), evidence classification and test coverage. If a PR has not landed, keep its entry **planned**, not runnable.
- S001 exclusively owns swing/bridge primitive revisions. S002 owns outcome/RAM probes, S003 motion modeling, S004 learning, S005 held-out generalization. Coordinator owns the CLI/GUI/registry. Coordinate overlapping changes on GitHub issues, not by changing another worker's live script.
- Lab live runs require `--live`, preserve the canonical **fresh Dolphin / named existing green-pre-start state / A→A+B→A intro**, prompt the human and record every attempt, including missed shots. A Lab live lock prevents overlapping Lab sessions but does not kill or manage independently started legacy processes.
- Distinguish **script exit**, **Felk bridge ACK**, **user-observed ball strike**, **verified game score** and **generalization performance**. The latest S002 unprimed V2 human-reported shot **failed due to insufficient strike strength** and must remain a negative observation; prior 2.1-ft green and 100-ft miss hits are non-equivalent input conditions.
- Save metadata in local `Wii-AI-Golf-Data/lab`, not GitHub; never upload RAW-PRIVATE RAM. All offline commands may be planned without any Dolphin connection, and only approved live commands can launch it. No unattended batches until measured scoring and safe control gates are passed.

## ARCHIVED GUI-era diagnostics (do not instruct operator to use UI)

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

The operator explicitly rejected separate shell instructions for the historical V1 swing comparison. The **single Windows Lab** now exposes a persistent **Game Testing** panel with registered `integration.bridge-audit` (read-only offline), `integration.prepare-v1` (consented isolated historical backup creation) and `integration.v1-diagnostic` (consented one-shot real Dolphin). All three use the SAME typed runner, history and logs. S001 owns original bridge provenance/backup logic; S002 owns observed outcome capture. S000/UI agents must not ask users to run `scripts/audit_local_swing_bridge.py` or inspect individual bridge-copy paths for routine trials; the UI itself provides the workflow and clear inability reasons.

All new agent-proposed gameplay tests must include UI-visible prerequisite checks and preparation actions, or be explicitly tagged as unavailable. No "run this hidden Python script before your UI test" dependency is acceptable. Never silently alter installed V2 bridge, reuse autoloading legacy scripts, claim successful ball contact based on process exit, or start another Dolphin without user approval. The recent V2 unprimed outcome trial remains a human-reported insufficient-strength **failure**.

## ARCHIVED (2026-10-24): former Lab test delivery

> **Historical only:** old GUI/Bash/manual-launch language in this section is NOT an active operator instruction; use PowerShell-only `docs/operator-powershell-contract.md`.

**Operator request:** AI agents must use the same local Lab. GitHub-committed tests from agents should arrive in the Lab automatically when merged. A contributor's **`tests/test_*.py`** file is discovered on the user's clean `main` checkout after the app's **automatic safe GitHub sync** (startup, every 120 seconds, or **Sync GitHub** button) and appears as selectable `agent-tests.test_...` **OFFLINE** test. There is no need to write another operator-facing `py scripts/test_one_off.py` command, and no need to edit the static experiment catalog for every new regression file.

S001–S005 agent handoff requirements:
1. Include focused unittest-compatible `tests/test_*.py` regression tests in each agent PR; prefix tests consistently (`test_integration_...` → S001, `test_outcome_...` → S002, `test_model_...` → S003, `test_learning_...` → S004, `test_generalization_...` → S005). These are **inferred labels**, not trusted authorization.
2. Merge reviewed PRs to trusted **`origin/main`**; merely committing an agent branch/PR **does not** make code eligible for local auto-execution. Do not instruct the user to run arbitrary shell scripts or auto-checkout PR heads. The GUI **fetches/pulls code only**; the user selects when to run a test, and no live Dolphin tests run automatically.
3. For a new real-game experiment or special offline data operation, coordinate with S000 on issue #51 and contribute a typed **Lab** adapter plus registry entry. Existing S001/S002 actions remain stable; never bypass canonical fresh-boot/startup and human swing authorization.
4. After a merge, publish experiment ID(s), outcome caveats, expected local test outputs, any proprietary data requirements and safe reproduction instructions in the shared issue/PR rather than scattering separate PowerShell instructions.
5. The Lab updater **rejects** dirty local trees, unapproved Git remotes, non-main branches, divergent histories, and concurrent Lab jobs. Never suggest `git reset --hard`, `git stash`, ignoring the guard, or overwriting the user's local savestates as a workaround.

Docs: [docs/research-lab.md](docs/research-lab.md). Coordinator ownership: GitHub sync and registry; domain agents own their scripts/tests.
