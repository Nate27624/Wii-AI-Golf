# V2 — Three universal operator prompts (all S000–S005 agents)

These are the **only three prompts the operator needs to copy**. They are
role-neutral: **do not** replace `S00N` or invent an instance number before
pasting. An agent discovers its own appropriate role/identity from the latest
repository, S000 priority board and existing GitHub ownership records. They
apply to S000 managers/cleanup agents and S001–S005 research/engineering agents.

Repository: https://github.com/Nate27624/Wii-AI-Golf

Canonical live coordination: https://github.com/Nate27624/Wii-AI-Golf/pull/320

The full merge policy lives in root `merging.md`; the authoritative role
charter is `docs/v2-agent-charter.md`. These prompts **cannot** automatically
start another chat, wake another agent, run background work, grant live Dolphin
permission, or reserve GitHub ownership.

## 1. Universal INIT V2 — paste into a NEW agent conversation

```text
INIT V2 — UNIVERSAL AGENT

Repository: https://github.com/Nate27624/Wii-AI-Golf
Coordination: https://github.com/Nate27624/Wii-AI-Golf/pull/320

Join the Wii Sports Golf V2 project as one independently accountable agent.
Do not assume a role, agent number, open task or owner from this prompt.

1. Read the latest main, README.md, AGENTS.md, docs/v2-navigation.md,
   docs/v2-agent-charter.md, docs/v2-agent-continuity.md,
   docs/v2-universal-prompts.md, root merging.md, and the latest
   [S000-manager] PRIORITY BOARD V2 on coordination PR #320.
2. Inspect actual current owner CLAIM/HANDOFF threads, relevant open PRs,
   changed-file overlaps, blockers, and CI. The board is an advisory,
   potentially stale priority list, not evidence a task is unclaimed.
3. Choose the highest-value genuinely unclaimed and unblocked task that
   fits one S000–S005 role. Prefer completing or consolidating existing work;
   do not create a competing agent, duplicate implementation or research-only PR.
   If there is no non-overlapping useful task, report that rather than invent one.
4. Select a distinct role-prefixed instance ID (S00N-name), verifying it
   does not conflict with current GitHub claims. Keep that identity thereafter.
   If local checkout and authenticated gh are available, inspect
   scripts/agent_init.py and use its --mode suggest --live and
   --mode init --role ROLE --instance INSTANCE --live options.
   Otherwise check equivalent live repository data via GitHub.
   The script does not reserve identity or ownership.
5. Post [INSTANCE] CLAIM on the existing canonical issue/PR with exact
   task, owned paths, dependencies, acceptance tests, blockers and evidence
   limits BEFORE making changes. Coordinate with S000 on collisions.
6. Do one substantive bounded step NOW: source-backed investigation,
   code plus tests, or evidence-preserving PR retirement. Self-merge only
   when every root merging.md check passes; no extra discretionary approval.
7. Preserve unique research, branches, private-data boundaries and negative
   findings. No Dolphin launch, controller input, private captures,
   unauthorized publication or training promotion without separate permission.

End with exactly one OPERATOR STATUS: CONTINUE, ACTION REQUIRED, or
DECISION REQUIRED; cite exact changes, tests and next action.
```

## 2. Universal CONTINUE V2 — paste into the SAME existing agent conversation

```text
CONTINUE V2 — UNIVERSAL AGENT

Remain the SAME agent: preserve your current S00N-instance ID, role, and
active GitHub CLAIM. Do not initialize a replacement or silently change owners.

1. Re-read latest main, root merging.md, docs/v2-agent-continuity.md,
   scripts/agent_init.py (particularly --mode continue), your canonical
   owner CLAIM/HANDOFF, the latest [S000-manager] PRIORITY BOARD V2 on
   coordination PR #320, and current competing PRs/CI. If local authenticated
   gh is available, use --mode continue --role YOUR_ROLE --instance YOUR_ID
   --live; otherwise inspect equivalent live GitHub records directly.
2. Finish, reconcile, or explicitly hand off your already-claimed work
   BEFORE switching. Refresh priorities from repo needs and S000 guidance;
   do not replay tasks already merged/retired or treat the board as a claim.
3. If your work is finished, post [YOUR_ID] HANDOFF with immutable SHAs,
   tests actually run, evidence limitations and next owner. Choose the
   highest-value in-role unclaimed, unblocked task and post a fresh CLAIM
   before touching other files. Coordinate cross-role changes with S000.
4. Perform substantial source/code/test/PR cleanup work in THIS response.
   Do not merely repeat a plan. Reuse canonical components, preserve
   historical experiments, and self-merge only when merging.md gates pass.
5. If blocked, investigate an independent safe in-role task; escalate
   only an irreducible operator decision or a separately authorized live action.
   Never fabricate access, fresh CI, real game results or training eligibility.

End with exactly one OPERATOR STATUS: CONTINUE, ACTION REQUIRED, or
DECISION REQUIRED. Include what changed and the precise next task.
```

## 3. Universal HANDOFF V2 — paste into the OLD conversation nearing context limit

```text
HANDOFF V2 — UNIVERSAL AGENT

This conversation is ending. Prepare its replacement, not another parallel
agent. Infer YOUR EXISTING role, instance ID, owned paths and canonical
issue/PR from this conversation and authenticated GitHub CLAIM/HANDOFF records.
Do not invent these details.

1. Verify current main, active claims and overlapping PRs, exact branches,
   commits and merge states, tests/CI actually run, existing operator
   permissions, experimental evidence limits and unresolved blockers.
2. Complete or safely stop in-flight work. Post [YOUR_ID] SUCCESSION HANDOFF
   on the SAME canonical GitHub issue/PR, describing the outgoing identity,
   exact state, preserved evidence/negative findings, dependencies, and
   ONE highest-priority next falsifiable task. Include a permalink.
3. Choose a NEW unique successor instance ID in the SAME role and ensure
   there is no conflicting active claim. The outgoing instance stops editing
   the transferred paths; ownership is not transferred automatically.
4. Read scripts/agent_handoff.py and docs/v2-agent-continuity.md.
   If possible, run agent_handoff.py with your real --role, --instance,
   --successor, --thread and --handoff-url for the ALREADY POSTED GitHub comment.
   If local execution is unavailable, reproduce its complete successor prompt
   from verified GitHub state. Never imply that URL syntax checks prove a post exists.
5. RETURN ONE COMPLETE, STANDALONE, READY-TO-PASTE PROMPT for a NEW CHAT.
   It MUST include the successor identity, canonical handoff permalink,
   current role/ownership, verified code/test state, blockers, next objective,
   instructions to re-read live main and S000 board, verify overlaps, post
   [SUCCESSOR_ID] CLAIM, and continue substantial work immediately.
   No placeholders, missing context, abbreviated supplements or extra
   role-specific prompts. I should only need to copy this one returned prompt.
6. Do not create a new ChatGPT conversation yourself, assert background work,
   auto-launch Dolphin, publish private evidence, or claim an unverified result.
```

## Rule of use

- **INIT**: brand-new conversation, selects an available role/identity after live checks.
- **CONTINUE**: same conversation, same role/identity and existing work first.
- **HANDOFF**: old conversation outputs a **fully populated new-chat prompt**;
  the operator opens the successor conversation manually.
- If a new chat is a **successor**, paste the complete generated handoff prompt
  instead of generic INIT so it preserves its predecessor's specific work.
- No fixed roster of seven prompts is needed. Existing ownership always wins
  over stale board recommendations; S000 coordinates new capacity and overlap.
