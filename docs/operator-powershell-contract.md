# Operator contract: PowerShell-only, reuse-validated-methods (ACTIVE)

**Last operator decision:** 2026-10-27. **Applies to every agent S000–S005, all study/runbook answers, and all user-visible commands.** This is the authoritative current operator-delivery contract. Newer direct operator instructions override it; this document overrides archived GUI, Git Bash, manual-attach, and legacy ad hoc launch recipes elsewhere in the repository. It does not by itself authorize a live experiment or a merge.

## Non-negotiable output rules

1. **Give Windows PowerShell, never manual Dolphin steps.** NEVER tell the operator to open/load/configure Dolphin manually, choose any GUI menu, or run a substitute shell workflow. Every action the operator must perform is a single **copy/paste-ready** PowerShell code block. Never say only "open Dolphin", "click File > Open", "load a state", "press A", "start an RPC server", "use the GUI", "run these Git Bash commands" or "manually connect the bridge." Do not provide a Unix/Git Bash command as the operator's action. The operator pastes PowerShell and returns terminal output.
2. **Always navigate automatically.** PowerShell block begins with $ErrorActionPreference = 'Stop', declares the known canonical repo root as D:\Projects\Wii Golf AI\Wii-AI-Golf, then Set-Location -LiteralPath $repo. Hardcoded *verified* local private Data root is a sibling directory D:\Projects\Wii Golf AI\Wii-AI-Golf-Data. Do not ask the operator to discover paths already known from the study.
3. **Fully self-contained commands.** Include actual existing script names, argument values, preflight, error checks on $LASTEXITCODE and a clear expected output/stop rule. Do not provide pseudo-code, placeholder paths, bash-style line continuations, or a command from an unmerged branch while implying it is on main. If a feature is only in a PR, give either an explicit safe reviewed worktree read-only command or say it is not runnable from main yet.
4. **Make scripts do the work.** If the required capability exists, use its current documented interface. If absent, own a small code change with tests/PR; do not make the operator perform manual Dolphin actions, hunt for a script, manually calculate RAM offsets, or substitute an unapproved one-off procedure.
5. **One smallest useful step and stop.** Default to one logical operation per block, then request the operator to paste the *sanitized* terminal result. Avoid dumping 100 commands, telling them to repeatedly fiddle with the GUI, or scheduling long blind retries. Each result should state whether it was executed, which mode (offline/dry-run/live), and whether raw data stayed local.
6. **Preserve operator state.** Never recommend git reset --hard, git clean -fd, force push, stash/checkout over dirty changes, overwriting savestates/ROMs/bridges or deleting local Data to bypass a guard. Respect concurrently running agents; use a unique isolated worktree for unmerged offline research, then return to the canonical directory. Avoid automatic code updates unless the reviewed script's existing safe sync has been verified and the operator requested that command.
7. **Do not leak raw evidence.** Native MEM1/MEM2, ROM, savestate, private pointer/word arrays, screenshots with secrets, generated bridge sources, game configuration and raw PRIVATE JSON remain in ignored local storage. Console snippets shared to agents and GitHub issue comments should contain allowlisted counts, relative field offsets, pass/fail flags, human observations and caveats, not raw private memory. Sanitized automatic GitHub results via existing publisher only.

## Existing working methods are preferred over experimentation

**S001 owns the one canonical live implementation.** Never generate an alternative Dolphin launcher, menu macro, controller driver, waveform, reset shortcut or ad hoc attach-running protocol. Existing scripts are designed to work together:

- **Maintained research operator interface:** scripts/research_cli.py; offline sync/test and explicitly authorized V1 one-shot result collection, with allowlisted GitHub publication. The broader source-local scripts/golf.py CLI delegates to the same implementation domains for doctor, state inspection, tests, play/swing and research. These are **entrypoints into existing components, not two competing emulator implementations**. Consult README and docs/cli-only-workflow.md for the currently merged command; prefer the existing research_cli.py for research result collection.
- **Single startup owner:** scripts/run_golf_experiment.py -> scripts/launch_golf.py -> scripts/launch_hitting_green.py -> wii_ai_golf.menu_sequence. Existing named green-pre-start catalog/checkpoint, Emulated Wii Remote 1 / Extension None, and the human-confirmed A -> A+B -> A menu progression. Never hardcode another menu sequence or tell the operator to load a savestate manually.
- **Frozen baseline swing:** existing source-pinned trace and source-selected Felk bridge method, including the original **89-sample forward waveform** (12 neutral, 15 back, 20 forward, 30 follow-through, 12 release). Preserve trace SHA/digest, A state, controller protocol version, release timing and all phase boundaries unless a distinct S001/S000-reviewed intervention explicitly changes one dimension. A completed RPC/89/89 acknowledgement alone is not game-accepted contact or a score.
- **The number 45 has MULTIPLE DIFFERENT meanings.** Do not confuse (a) the **45 requested-frame final A press** inside the validated *menu intro*, (b) **45 separate button-only A-prime requests** before the swing (where specified), (c) **45 observed-frame A-lead** in the isolated V1 diagnostic, or (d) **45 A-held neutral trace samples** (historically shown not to be equivalent to a genuine A-only hold). These are different APIs and experiments. Likewise a 45-frame follow-through is an independent release-timing variation. **Never "improve" or replace the operator's established 45-frame A procedure by picking another 45 flag.** Identify exactly which pre-existing implementation/flag was already validated in the current study and keep it unchanged. Record the trace hash (SHA256 digest), bridge revision, and exact approved 45-frame flag. These potentially identical counts are **NOT equivalent** inputs. If semantics truly cannot be established from evidence, stop at read-only preflight rather than invent a live command.
- **Use tested frozen known-good routines first**, not novel V1/V2 swaps, new A/A+B combinations, button-hold variants or fresh launcher scripts. Prior contact and repeated contact are distinct evidence gates; never call an experimental A-prime a new known-good just because dispatch completes.
- **No unsafe live actions:** The reviewed #195 safe-clean-Dolphin CLI guard is a draft until merged: if main lacks the explicit clean portable executable/User/config/catalog preflight, do not suggest that a main-branch V1 run necessarily uses the fixed setup. Code review/full Windows tests, true clean named savestate presence, and separate live human authorization come first.

## Required answer layout to operator

**What I found:** one or two factual sentences, referencing source branch/PR/commit if relevant.

**What to run:** one fenced PowerShell block with no omitted setup. For a pure GitHub/code change that does not require local action, say **No PowerShell action needed** rather than inventing a script.

**What to paste back:** the specific short sanitized console fields/summary requested. If the code is draft or prerequisites failed, do not give a dangerous live launch command disguised as a test.

**What is verified / not verified:** separate code tests, actual Dolphin launch, visible ball contact, frame provenance, ball XYZ, power, distance and training authorization. A human-observed hit/miss is explicitly labeled as human observation.

## Reference PowerShell shapes

Safe read-only repo status, from any current directory:

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
Set-Location -LiteralPath $repo
git status --short
if ($LASTEXITCODE -ne 0) { throw 'Git status failed' }
py scripts/golf.py doctor
if ($LASTEXITCODE -ne 0) { throw 'Read-only doctor failed' }
~~~

Run a previously merged offline test only:

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
Set-Location -LiteralPath $repo
py -m unittest discover -s tests -p 'test_research_cli.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Offline regression failed; do not launch Dolphin' }
~~~

For future live-game requests, construct a **separately reviewed** single PowerShell block around the *currently merged* canonical CLI, confirm Dolphin is closed and the exact clean executable/User plus named savestate actually exist, preserve validated swing parameters, require the existing human SWING/Enter opt-in, and stop after exactly one attempt. Do **not** turn this policy's example into authorization to run a live swing.

## Enforcement and ownership

- S000 owns this operator interface, top-level rules and documentation. S001 owns Dolphin/controller/trace/menu implementations; S002 owns private memory capture/outcome evidence; S003 calibration, S004 search, S005 held-out validation.
- Before changing a shared module: read active GitHub issue claims and overlapping PRs, claim scope, obtain S000/affected owner acknowledgment, run focused + full Windows regression, preserve raw-private boundaries, and submit draft PR. A docs rule does not override the repository's merging-requirements.md or GitHub protection.
- New agent on a resumed conversation MUST read AGENTS.md, this document, docs/repository-map.md and docs/cli-only-workflow.md **before** telling the operator to do anything.
- A response that says only "open/run Dolphin" or repeats a manual GUI workflow is noncompliant. Correct it into a complete PowerShell instruction using the canonical code; if no approved path is available, implement/test a narrow adapter instead.

Historical 2026-10-24 GUI and mixed-runbook text is preserved only as research history. It is not permission to revert this 2026-10-27 operator decision.
