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
CONTINUE V2. Read current main, docs/v2-navigation.md, docs/v2-agent-continuity.md, merging.md, and your canonical CLAIM/HANDOFF thread. Keep your existing role/instance and scope. Resolve routine engineering choices yourself; do substantive source/code/test/PR work now. Do not ask for approval on routine merges that meet merging.md. At the end, output exactly one OPERATOR STATUS block: CONTINUE, ACTION REQUIRED, or DECISION REQUIRED. If action or decision is required, make it specific and state whether you can proceed independently on another task.
```

After responding to an ACTION REQUIRED or DECISION REQUIRED request, the user may simply say: `<answer or sanitized output>. CONTINUE V2.` The agent must incorporate the answer, record the decision in its canonical thread as appropriate, and proceed immediately.

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
