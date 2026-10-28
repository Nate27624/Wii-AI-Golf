# Operator contract: PowerShell-only, reuse-validated-methods (ACTIVE)

**Last operator decision:** 2026-10-27. **Applies to every agent S000–S005, all study/runbook answers, and all user-visible commands.** This is the authoritative current operator-delivery contract. Newer direct operator instructions override it; this document overrides archived GUI, Git Bash, manual-attach, and legacy ad hoc launch recipes elsewhere in the repository. It does not by itself authorize a live experiment or a merge.

## Required context-switch baseline

**Every new or resumed agent context must first READ** root AGENTS.md, ACTIVE README, [mandatory session protocol](agent-session-protocol.md), this contract, [repository map](repository-map.md), [research coordination](../research/coordination.md), the relevant owner issue/PR and source/tests. The first substantive response truthfully identifies what was checked. **Every substantive response must RE-BASELINE** against the newest pasted PowerShell output and relevant current GitHub branch/HEAD/CI/ownership/evidence before advising; provide a concise Current baseline of source | P0 goal | verified-vs-candidate evidence | blocker/owner | next one action. If a document or remote state was not checked, state NOT CHECKED. Do not assume separate agent contexts share memory, approved methods, physical Dolphin state or live consent. Avoid a full historical reread for trivial replies; only refresh changing relevant facts. Record a dated HANDOFF in the owning GitHub issue/PR before context switch. Full details: [agent session protocol](agent-session-protocol.md).

## Non-negotiable output rules

1. **Give Windows PowerShell, never manual Dolphin steps.** NEVER tell the operator to open/load/configure Dolphin manually, choose any GUI menu, or run a substitute shell workflow. Every action the operator must perform is a single **copy/paste-ready** PowerShell code block. Never say only "open Dolphin", "click File > Open", "load a state", "press A", "start an RPC server", "use the GUI", "run these Git Bash commands" or "manually connect the bridge." Do not provide a Unix/Git Bash command as the operator's action. The operator pastes PowerShell and returns terminal output.
2. **Always navigate automatically.** PowerShell block begins with $ErrorActionPreference = 'Stop', declares the known canonical repo root as D:\Projects\Wii Golf AI\Wii-AI-Golf, then Set-Location -LiteralPath $repo. Hardcoded *verified* local private Data root is a sibling directory D:\Projects\Wii Golf AI\Wii-AI-Golf-Data. Do not ask the operator to discover paths already known from the study.
3. **Fully self-contained commands.** Include actual existing script names, argument values, preflight, error checks on $LASTEXITCODE and a clear expected output/stop rule. Do not provide pseudo-code, placeholder paths, bash-style line continuations, or a command from an unmerged branch while implying it is on main. If a feature is only in a PR, give either an explicit safe reviewed worktree read-only command or say it is not runnable from main yet.
4. **Make scripts do the work.** If the required capability exists, use its current documented interface. If absent, own a small code change with tests/PR; do not make the operator perform manual Dolphin actions, hunt for a script, manually calculate RAM offsets, or substitute an unapproved one-off procedure.
5. **One smallest useful step and stop.** Default to one logical operation per block, then request the operator to paste the *sanitized* terminal result. Avoid dumping 100 commands, telling them to repeatedly fiddle with the GUI, or scheduling long blind retries. Each result should state whether it was executed, which mode (offline/dry-run/live), and whether raw data stayed local.
6. **Preserve operator state.** Never recommend git reset --hard, git clean -fd, force push, stash/checkout over dirty changes, overwriting savestates/ROMs/bridges or deleting local Data to bypass a guard. Respect concurrently running agents; use a unique isolated worktree for unmerged offline research, then return to the canonical directory. Avoid automatic code updates unless the reviewed script's existing safe sync has been verified and the operator requested that command.
7. **Do not leak raw evidence.** Native MEM1/MEM2, ROM, savestate, private pointer/word arrays, screenshots with secrets, generated bridge sources, game configuration and raw PRIVATE JSON remain in ignored local storage. Console snippets shared to agents and GitHub issue comments should contain allowlisted counts, relative field offsets, pass/fail flags, human observations and caveats, not raw private memory. Sanitized automatic GitHub results via existing publisher only.

## Automatic GitHub publication and durable research findings (MANDATORY)

**User's active standing instruction (2026-10-27): Operator experiment/test output must be automatically uploaded to GitHub, and important findings must be recorded.** This does NOT authorize uploading private/raw evidence or unattended live actions.

### Default successful command lifecycle

1. The operator executes **one approved self-locating PowerShell block** invoking a **currently merged and vetted CLI**. Offline diagnostics, experiment control and result collection must use the existing source methods.
2. The reviewed collector stores raw/full observations **locally** under the ignored sibling Wii-AI-Golf-Data, produces a small **explicitly allowlisted SANITIZED** result record (study ID, unique run ID, UTC, source class, code/bridge hash when safe, inputs/protocol identity, short bounded metrics, human outcome, failure flags and validity gates).
3. That **same invocation** calls the current trusted GitHub result publisher (scripts/research_cli.py and its existing publish_summary contract) and publishes **only** the allowlisted record to the separate research/observations branch. The operator must not have to run git add/commit/push, create a new token, open GitHub, paste a raw log or run a second upload command. Use the existing verified remote, clean/safe sync, no force push, no arbitrary branch creation and no new independent publisher.
4. On a confirmed successful publish, print UPLOADED (or the existing publisher's unambiguous 'GitHub observation published:') plus the GitHub location and safe run/study identifier. **Do not claim upload until the publisher actually returns success.** The local result must still be preserved.
5. The agent reads the sanitized GitHub observation, judges whether a result is material, and records significant findings in its **owning GitHub issue/PR immediately**, followed by an evidence-qualified research/ledger.md entry through a reviewed owner PR/merge. Include positive, negative and falsifying evidence, not just successes. Link the sanitized record, owner, controls, limitations and next P0 action. Never rely solely on a chat response for a durable discovery.

### Mandatory limitations and failure behavior

- **Do not upload raw output or pretend it is sanitized.** Native MEM1/MEM2, RAW-PRIVATE JSON/JSONL, unrestricted stdout/stderr, game ROM/image, savestate, Dolphin User config, raw controller traces, per-sample words/pointers, personal information, credentials and private paths stay ignored/local. The S000/S002 allowlist decides what can be published; a private numeric vector does not become public because the user asks for automatic uploads.
- The **currently merged** scripts/research_cli.py already auto-publishes its test and v1 sanitized summaries by default, unless operator explicitly passes --no-upload. This DOES NOT imply unrelated scripts/*.py offline probes or unmerged PRs already upload. An agent must inspect the exact command path and prove auto-publish with synthetic tests before recommending it. If not integrated, build an owner-reviewed narrow adapter into that one publisher **first**, then provide a valid PowerShell command.
- If publication is rejected (privacy/schema), remote/auth fails, or concurrent push conflicts, **retain the local sanitized record**, report NOT UPLOADED with a short nonsecret reason and relevant retry/owner blocker, and do not ask the operator to manually upload raw files. The result's scientific evidence may still exist privately but is not a publicly linked successful GitHub observation.
- --no-upload is a deliberate user privacy override. Auto-publication policy never overrides an explicit operator opt-out, the publisher's trust restrictions, branch protection or S000/S002 review.
- A synthetic CI pass on a PR is already available in GitHub and may be linked as code validation; it is NOT a real Dolphin/game-result observation. Do not generate a fake live shot record to meet this rule.
- **Important finding definition:** newly supported/falsified P0 variable, confirmed/unconfirmed contact, observed failure mode, changed source interpretation, calibration or unit discovery, acceptance gate changes and significant regressions. Each record must distinguish source-derived, offline-native snapshot, live bridge ACK, human-observed motion, independently validated physical outcome and synthetic-only proof.

### Minimum research handoff fields

For a material result, post a dated **FINDING** in the GitHub issue/PR: **study/run ID**, code revision/owner, experiment/control and trace source, observed positive/negative outcome, whether raw remains private, sanitized observation link or NOT UPLOADED blocker, what is verified versus hypothetical, impact on P0 gates, and named next owner. The reviewed ledger entry should summarize this finding and reference the same evidence. Do not mark an uncertain RAM offset as a training-ready feature just because an agent wrote it in GitHub.

**Never provide an operator command that is advertised as auto-uploading unless its existing reviewed implementation actually does so.** The correct response to a missing adapter is a code change/test or explicit limitation, never manual upload instructions.

---

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
