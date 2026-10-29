# V2 Agent Continuity — one operator-facing status contract

This protocol applies to S000 manager, consolidation agents, memory researchers, runtime, modeling, training, and evaluation agents. It does **not** create a background execution service. An agent can do work in its current turn, and can resume on the next user message, but must not claim to continue autonomously between chats.

## On every meaningful agent response

End with an **OPERATOR STATUS** block containing one of three categories:

### CONTINUE — no operator action
```
OPERATOR STATUS: CONTINUE
Need from you: Nothing.
Completed: <concrete code, merge, research result or negative finding; include SHA/PR>
Next: <one bounded highest-priority action that agent will take on next CONTINUE request>
Blockers: None that require operator action.
```
User can respond: **Continue**. When the agent receives it, the agent must read the latest repo/PR/claims, resume from the most recent handoff, and actually perform the next task. Do not merely restate plans.

### ACTION REQUIRED — physical/local/private task
```
OPERATOR STATUS: ACTION REQUIRED
Need from you: <single precise requested action, why unavoidable>
Command or steps: <validated minimal read-only command, with prerequisite paths and expected sanitized output; omit when not applicable>
What to paste back: <specific small sanitized fields>
Safe to continue without action: <yes/no; if yes state alternate task>
```
Do not ask the operator to re-run original seven-phase captures or live Dolphin without a precise, unavoidable evidence gap. Never ask to upload raw memory, ROMs, secrets, savestates or user paths. Any live game action requires explicit separate operator authorization; a continuation response alone is not permission.

### DECISION REQUIRED — clarifying question only the user can answer
```
OPERATOR STATUS: DECISION REQUIRED
Question: <one crisp question>
Options: A) <...> B) <...>
Recommended default: <option and rationale>
If unanswered: <safe fallback and work that can proceed>
```
The S000 manager consolidates other agents' questions. Resolve technical questions from code, sources, tests, or discussions before escalating. Ask the human only for priorities, consent, irreconcilable tradeoffs, or access to their local evidence.

## Reusable user continuation message

```text
CONTINUE V2. Keep your existing role, instance ID and in-flight CLAIM. Fetch current main, latest [S000-manager] PRIORITY BOARD V2 on PR #320, canonical issue/PR handoffs, active overlapping claims, and merging.md. Finish or reconcile already claimed work first; then select the highest-value in-role unclaimed, unblocked task based on current evidence rather than a frozen older instruction. If an assigned task merged or was retired, do not repeat it: publish a handoff and coordinate a replacement claim. Perform substantive source/code/test/PR work now, self-merge only when all merging.md gates pass, and end with one OPERATOR STATUS: CONTINUE, ACTION REQUIRED, or DECISION REQUIRED. Never treat board suggestions as live consent or automatic ownership.
```

After responding to an ACTION REQUIRED or DECISION REQUIRED request, the user may simply say: `<answer or sanitized output>. CONTINUE V2.` The agent must incorporate the answer, record the decision in its canonical thread as appropriate, and proceed immediately.


## Adaptive INIT and CONTINUE — manager-coordinated priorities

**Source of live task recommendations:** the newest authenticated
`[S000-manager] PRIORITY BOARD V2` GitHub comment on
[canonical coordination PR #320](https://github.com/Nate27624/Wii-AI-Golf/pull/320).
It contains a validated, versioned JSON task board pinning the `main` SHA,
role, priority, readiness, canonical issue/PR and a bounded objective.
It is *advisory*: actual availability depends on checking the current
CLAIM/HANDOFF on that owner thread, current PR state, changed-file overlaps,
head/CI, and blockers. A board pinned to older main is stale; never
interpret it as automatic assignment or completed tests.

Use the same **existing** role/instance ID for continuation. For a brand-new
agent, the operator can choose a new role after inspecting S000's latest
unclaimed work; a new distinct ID must be verified against GitHub claims.
No script reserves IDs or starts new ChatGPT conversations. The roles S000–S005
remain governed by the charter, regardless of priority order.

**New ChatGPT conversation — dynamic initiation message:**

```text
INIT V2. Read latest main, AGENTS.md, docs/v2-navigation.md, docs/v2-agent-charter.md, docs/v2-agent-continuity.md and merging.md. Read the newest [S000-manager] PRIORITY BOARD V2 on coordination PR #320, then inspect live CLAIM/HANDOFF comments and current open PR overlaps. Recommend the highest-value UNCLAIMED and UNBLOCKED role-appropriate task according to S000 coordination; select a unique S00N-instance ID not already claimed. Post [INSTANCE] CLAIM on its EXISTING canonical issue/PR, preserving prior research and role ownership. Begin one bounded substantive source/code/test or evidence-preserving consolidation action immediately. Do not create duplicate implementations or research-only PRs. Follow exact-head Windows/Ubuntu CI and root merging.md; self-merge objective-qualified PRs, without requesting a manager approval ritual. No automatic live Dolphin actions, private captures, publication or training promotion. End with one OPERATOR STATUS.
```

**Same-chat dynamic continuation:** use the updated `CONTINUE V2` message above.
Check fresh manager recommendations **after** completing the existing claim;
never abandon in-flight ownership just because a priority number changed.

Optional local, **read-only** helper (requires already authenticated `gh`
CLI for live reads; if missing, use the GitHub connector in ChatGPT):

```powershell
python scripts/agent_init.py --mode suggest --live
python scripts/agent_init.py --mode init --role S002 --instance S002-memory-c --live
python scripts/agent_init.py --mode continue --role S002 --instance S002-memory-c --live
```

The helper reads `main` and the latest board using **GET** only, validates
task types, and prints ranked candidates for the selected role. It **cannot**
inspect every overlapping claim or prove task availability: the agent must
do that directly through GitHub before any CLAIM or edit. When authentication,
network, schema or board freshness is uncertain, it explicitly abstains or
warns and does not invent an assignment. Offline tests can pass a sanitized
board via `--board-file`; such output is *not* live-verified.

**S000 manager duty:** after major merges, evidence changes or parent PR
closures, post a new board on #320 with a fresh main SHA, exact owner threads,
a small number of highest-impact in-role tasks and explicit `ready_offline`,
`review_only`, or `blocked` statuses. Do not mass-edit repo files for each
board update; record changes as GitHub comments. Stale, blocked or claimed
tasks are not instructions to create duplicate PRs.

## Internal handoff for durable continuity

Each completed task should leave a source-backed GitHub `[INSTANCE] HANDOFF` comment containing branch/head SHA, completed changes, exact tests/CI, active owner, unresolved uncertainty, and next falsifiable step. Use GitHub as cross-chat durable state; never rely only on hidden chat context. Source evidence may be private; publish only sanitized conclusions.

The manager should periodically check agent `QUESTION` and `BLOCKED` comments and decide whether to answer directly or relay a user-facing question. Posting a comment is not a background notification or a guarantee another agent saw it.

## Discipline

- Maximum one operator-facing question per response unless a genuinely unavoidable grouped decision is needed.
- No filler, no "wait", no claim of background work or monitoring without an actual scheduled automation.
- Continue on safe nonconflicting work when a local/live action is blocked.
- Strictly distinguish completed results from proposed next tasks.
- Fail closed on missing identity, source provenance, outcome censoring, renderer identity, or memory frame evidence.
- Do not treat `CONTINUE` as live-shot permission, PR merge policy override, or training approval.


## When an agent chat reaches its context limit: SUCCESSION

The operator already maintains V2 initiation/continuation prompts. **Do not replace those
prompts or create a parallel onboarding architecture.** This protocol adds a durable
*handoff record* and a *successor identity* to the existing process.

1. The operator says `HANDOFF V2` or gives their existing handoff prompt to the
   outgoing agent. This is a request to prepare a successor, **not** authorization
   to launch a new chat, transfer secrets, merge code, or execute Dolphin.
2. The outgoing agent rechecks current `main`, its canonical owner issue/PR,
   latest CLAIM/HANDOFF, open overlapping PRs and actual CI. Complete or
   safely stop in-progress work; do not leave an unwritten worktree change
   or represent an unmerged branch as main.
3. Post `[OUTGOING-INSTANCE] SUCCESSION HANDOFF` on the **existing canonical
   GitHub issue/PR**, containing: role and instance, proposed *new distinct*
   instance ID of the same role, permalink to this handoff, latest verified
   `main` SHA, owned files/branch and exact head, completed/remaining work,
   current claims/dependencies, tests truly run and their exact SHAs/CI,
   privacy/evidence limitations, blockers, and **one next falsifiable task**.
   Never post raw private evidence or credentials.
4. The outgoing agent returns the exact posted SUCCESSION HANDOFF comment URL
   and **one complete, standalone, ready-to-paste successor-chat prompt**.
   The operator creates the next ChatGPT conversation and pastes that prompt.
   The operator may still use their existing V2 initiation prompt; the
   successor handoff generator does not replace or edit their other prompts.
   A GitHub comment cannot create a new chat or notify an agent by itself.
5. The successor reads latest `main`, this protocol, the charter and merge
   policy, the exact handoff URL and live overlaps, then runs
   `scripts/agent_init.py` with the **new** instance ID. It posts
   `[NEW-INSTANCE] CLAIM` on the **same canonical thread**, linking the
   predecessor's handoff. The old instance ceases changing those files;
   overlapping claims require reconciliation before new edits.
6. S000 resolves cross-agent overlaps and routes questions, without acting
   as a discretionary merge gate. The successor preserves the **same role
   responsibilities**, but must not silently assume that the outgoing
   agent's chat context, access, user consent, current branch or test
   results transfer automatically.

A read-only template helper is available locally:

```powershell
python scripts/agent_handoff.py --role S002 --instance S002-memory-a --successor S002-memory-b --thread https://github.com/Nate27624/Wii-AI-Golf/issues/121
```

It prints **a structured GitHub comment template** and a **complete new-chat prompt**
marked with copy boundaries. Fill all template placeholders with verified facts and
post the handoff through the usual GitHub tools. If the handoff comment has
already been posted, run the same command with
`--handoff-url https://github.com/Nate27624/Wii-AI-Golf/issues/121#issuecomment-123456`
(replace the number with the real comment ID) to embed the exact permalink.
A link's syntax is checked offline, **not** its existence or ownership; verify
those directly in GitHub first. Copy the content only between `NEW CHAT PROMPT`
and `END NEW CHAT PROMPT` into the newly opened chat. The helper **does not**
post comments, contact GitHub, create new agents, or run experiments. An
agent without local repository access can produce the same structured
record directly in its canonical GitHub thread.

Distinguish **`CONTINUE V2`** (resume the *same* agent/chat identity) from
**`HANDOFF V2`** (end an outgoing chat, prepare a *new* instance). Do not
reuse the outgoing ID for a different concurrently active chat, and do
not invent a globally reserved identity: GitHub claims are the coordination
source of truth.
