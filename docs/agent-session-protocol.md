# ACTIVE mandatory agent startup and response re-baseline protocol

This is the **entrypoint for every new or resumed S000–S005 agent context**. Read this document together with root AGENTS.md before acting. New contexts are independent: do not assume any other agent chat, branch, worktree, live Dolphin process, approval or cached PR state is current. A README link or a completion claim alone does not prove the instructions were read.

## A. New agent context: required reading sequence (before advice, commands or edits)

1. Read the operator's latest request and the **ACTIVE top sections** of README.md and AGENTS.md in the actual current repo/branch. Then read **all of** docs/operator-powershell-contract.md, docs/repository-map.md and this agent-session-protocol.md. Read docs/cli-only-workflow.md and docs/merging-requirements.md before suggesting operator steps or a merge.
2. Read research/coordination.md, the relevant section of research/ledger.md and exact current study/spec/test/source code. Check open GitHub issues/PRs relevant to the workstream, especially the live owning issue, CLAIM/HANDOFF/FINDING comments, overlapping paths, upstream dependencies and review status. Research/queue.jsonl is a proposal manifest, **not** evidence a worker is running. A prior chat or old README historical heading never overrides a new operator directive.
3. Establish **current source identity**: checkout/worktree name, actual branch, git HEAD commit, clean/dirty state, currently merged main vs open draft PR, and the active script/flags/bridge/profile/trace revision when relevant. Do not reset or switch a dirty operator checkout. If remote GitHub access is unavailable, say **status unverified**; do not invent an approval, merged feature, current branch or running agent.
4. Establish **evidence identity**: last verified result vs source-only candidate vs synthetic test vs human-observed outcome; exact study/run (sanitized ID), negative controls, known fail cases and what still blocks the P0 gate. Distinguish a prior contact-positive trial from current reproducibility. A source-mapped position or 89/89 scheduled controller dispatch is not confirmed physical ball motion, velocity, game score, or training eligibility.
5. Establish **ownership** before editing: owning S000–S005 issue, active other-agent claims, collision paths, upstream/downstream PRs. Make a narrow CLAIM/HANDOFF comment; isolate unmerged work in a unique branch/worktree. Never use another agent's worktree as a canonical runtime checkout.
6. **Read-attestation** (first substantive response and PR): state briefly which current rule documents were read, the head/PR you actually checked, the study/owner and what remains unknown. **Do not claim to have read or rechecked material you have not accessed.**

A new context that cannot complete the required read or source check must refrain from new live commands and shared-file writes until it can; it can still answer from clearly labeled existing evidence.

## B. Every substantive response: RE-BASELINE before answering

The operator may switch between completely independent ChatGPT agent contexts without warning. **Never rely on the previous assistant message as proof of current state.** Prior to each substantive recommendation, code modification, proposed operator command, or claim of a successful merge/test:

- **Reconcile latest operator evidence:** the most recent pasted PowerShell output, phase labels, missed/hit observation, explicit correction and objective. Do not ask the operator to repeat facts already supplied or run another unchanged P0 scan.
- **Refresh only the relevant changing state**: current branch/commit/PR status and CI, latest owning issue comments/claims and upstream dependency that could block this next operation. Do not silently assume previously reviewed drafts landed on main. If the state has not been independently checked in the current context or current tool turn, say **not rechecked**, not 'merged' or 'approved'.
- **Re-anchor the frozen method:** exact existing canonical fresh-launch path, named checkpoint, accepted A method (menu final A / button-only A prime / observed V1 lead / neutral trace / follow-through), original 89-sample waveform/bridge and control trace, **only where relevant**. A numeric value '45' without its source method is ambiguous; never change flags/physics from intuition.
- **State the evidence gate:** what has been verified, what is only candidate/synthetic/human observation, what still blocks P0 or training, and whether an operator action is offline, dry-run or explicitly consented live.
- **Choose the smallest next useful action**, aligned with current GitHub ownership; prevent redundant work with other agents and unbounded detours. Prefer source analysis/offline tests first. One validated experiment variable at a time; stop on wrong state, partial data or human 'no hit'.
- **Check upload + finding requirements**: whether this exact merged command automatically publishes an allowlisted sanitized summary and whether a significant new result requires a FINDING issue/PR comment and evidence-qualified research/ledger.md update. Preserve local PRIVATE captures. On failure output NOT UPLOADED, never invent a URL.

This is **a short baseline refresh, not a full repo audit or 10-paragraph recitation per message**. On initial or changed contexts, provide a concise 3–5-field 'Current baseline' paragraph. On a continuing response, update only fields changed by new operator evidence or GitHub activity; never suppress a material change. For trivial acknowledgments no baseline narration is needed.

### Suggested compact user-visible baseline

**Current baseline:** Source = reviewed main at actual SHA / isolated PR at actual SHA / not checked; Goal = named P0 gate; Verified = observed fact + source class; Blocker = current missing proof or owner approval; Next = ONE action or no action.

If a tool cannot verify the current SHA, say 'source not checked' rather than supplying a guessed value. Do not copy confidential game paths or raw memory into the baseline.

## C. Response and action rules that follow from the baseline

- **No manual Dolphin or GUI steps**. Give a complete self-locating Windows PowerShell code block with exact already-merged scripts, path, safe preflight and checked exit codes, or explicitly **No PowerShell action needed**. Do not ask the operator to navigate the menu, launch Dolphin manually, find a mystery path, run Bash, install a new uploader, or start two emulator instances.
- **No redundant experiments**. Check existing source, archived evidence and agent PRs before creating scripts. Reuse source-pinned A/A+B/A menu procedure, existing controller/bridge and the previously proven swing recipe; an improvement requires separate hypothesis, owner review, tests and a named experimental variant, not a silent default replacement.
- **No fake completion**. Identify PR draft vs merged, tested mocks vs real Wii Sports session, controller scheduler ACK vs visible ball strike, RAM candidate vs verified units, issue comments vs actual tested code, local result vs successful GitHub upload.
- **One action/one return path**. Whenever operator execution is actually required, say exactly which sanitized terminal fields to paste back and stop; do not demand manual post-processing, raw dumps or repeated clicks.
- **Record failures, too**. Significant negative controls, no-hit trials, regressions, disproven interpretations and blocked uploads go to an owning dated FINDING issue/PR and a reviewed ledger entry. Do not delete/overwrite earlier evidence or declare training ready from a single trial.
- **Do not promise background progress** in a stateless chat. Make a concrete commit, PR or handoff during the current task; if unfinished, label remaining work and owner, not 'I will do it later'.
- **Respect agent boundaries**. Different conversations cannot read each other's hidden state. GitHub issues, reviewed PRs, sanitized observation branch and research ledger are the durable coordination layer.

## D. Required handoff when stopping/switching contexts

When leaving substantial work, attach a short dated HANDOFF in the owning GitHub issue/PR:
- identity: owner/study, branch/head, changed files and other-agent collisions
- evidence: exact test command/results/platform, local vs GitHub sanitized result, source classification and negative findings
- current P0: verified gates, blocker, known-good frozen input/bridge/profile and any safety limits
- next safe action: one owner or executable reviewed operator PowerShell command if actually needed
- privacy: raw files remain local, public link exists or NOT UPLOADED, train/publish still gated

New agents read the handoff, but **must independently re-check current PR state** before acting. A stale handoff never authorizes live game control.

## E. Enforcement and limits

The root AGENTS.md and README.md link here. CONTRIBUTING.md and the GitHub PR template require a checked read-attestation and a 'current baseline' with actual source/PR identity. Targeted tests verify those contracts are present on both Windows and Ubuntu. These are **repository rules and review gates**, not a technical guarantee that an external agent has read the files. The agent must actually read them and truthfully state what was checked. Code review and full regression are still required for merge, and the user's explicit live opt-in remains mandatory.
