# Three universal V2 operator prompts — manager-directed assignments

**Exactly three copy/paste prompts for every S000–S005 agent.** The operator
does not choose a role-specific template. S000 owns the assignment roster on
[coordination PR #320](https://github.com/Nate27624/Wii-AI-Golf/pull/320);
the priority board is an unassigned candidate queue, not a task reservation.
The detailed lifecycle, matching roster schema and oversight rules live in
[continuity](v2-agent-continuity.md). Work is CLI-first; no automatic chat,
background job, Dolphin launch, private capture, publication or training approval.
Use the real current role and unique S00N-name identity; a same-chat CONTINUE
never silently changes identity.

## 1. Universal INIT V2 — new conversation

```text
INIT V2 — UNIVERSAL AGENT

Repository: https://github.com/Nate27624/Wii-AI-Golf
Coordination: https://github.com/Nate27624/Wii-AI-Golf/pull/320

Join Wii Sports Golf V2 as an independently accountable agent, but DO NOT
independently choose a task or implement files from the priority board.

1. Read latest main, AGENTS.md, docs/v2-navigation.md, charter,
   docs/v2-agent-continuity.md, root merging.md, scripts/agent_init.py,
   the latest S000 priority board AND latest [S000-manager] ASSIGNMENT
   ROSTER V2 comment on PR #320. Verify single manager and real CLAIMs.
   BOOTSTRAP EXCEPTION: if you are the UNIQUE already operator-authorized
   S000 Manager with a verified manager CLAIM but NO assignment roster yet,
   publish the FIRST complete roster yourself. Never wait to assign yourself
   before creating that first roster. S000 cleanup/support is NOT the manager.
2. If the operator supplied a verified successor handoff, keep its SAME role
   and the distinct successor ID and task until the manager transfers the
   roster entry. Otherwise check whether S000 has already assigned you
   an exclusive role/instance/task. Do NOT invent a S00N-name or choose
   an attractive P0 that other agents can also see.
3. If no unique matching manager assignment exists, post a bounded
   ASSIGNMENT REQUEST on #320 (or report what identity/role needs assignment)
   and PARK without unowned code edits. Check open PRs, changed-file
   overlap and old claims before accepting any roster entry.
4. Once assigned, post [YOUR_INSTANCE] CLAIM on the canonical issue/PR,
   referencing the exact manager roster comment, owned paths, dependency,
   acceptance criteria and evidence limits. One task, one canonical code owner.
5. Start substantive bounded source/test/cleanup work ONLY in assigned scope.
   Self-merge objective-qualified code under root merging.md and exact-head
   Windows/Ubuntu CI; S000 coordination is NOT discretionary merge approval.
6. Never infer live Dolphin consent, physical ball XYZ, score or trainability
   from synthetic/offline evidence, and preserve historical unique findings.

At the end of your response, give one OPERATOR STATUS with explicit
Role: S00N — descriptive role, Agent ID: S00N-name, Assignment with
status/permalink, Completed, Next, Blockers, and OVERSIGHT ESCALATION:
REQUIRED or NOT REQUIRED. If waiting for assignment, say PARKED.
```

## 2. Universal CONTINUE V2 — SAME existing agent conversation

```text
CONTINUE V2 — UNIVERSAL AGENT

Remain the SAME agent: keep your existing role, exact instance ID and active
CLAIM. Do not silently take a new role or adopt another agent's files.

1. Read latest main, root merging.md, docs/v2-agent-continuity.md,
   scripts/agent_init.py --mode continue, your canonical CLAIM/HANDOFF,
   open PRs and CI, latest S000 board and latest ASSIGNMENT ROSTER V2 on
   PR #320. Check whether your assignment still matches that roster.
2. Finish or reconcile your existing verified claim first. For any older
   claim predating roster adoption, ask S000 to enter/confirm its ownership;
   do not use the stale candidate board to acquire competing files.
3. If current work is complete, post a factual HANDOFF with exact SHA,
   tests/CI and evidence limits. Do NOT independently select the next P0.
   Request a NEW named manager assignment and PARK until allocated.
4. Implement one substantive next action within your assigned paths.
   Resolve normal technical details autonomously; if blocked, provide
   source-backed findings and let S000 decide whether to reassign scope.
   Never merge competing implementations. Self-merge only under merging.md.
5. Do not claim unattended progress, new live Dolphin permission, native
   game evidence, or training approval.

End with exactly one OPERATOR STATUS: CONTINUE, ACTION REQUIRED or
DECISION REQUIRED. ALWAYS include:
Role: S00N — descriptive role
Agent ID: your EXACT current S00N-name
Assignment: manager-issued task ID/state and roster permalink (or PARKED)
Completed: exact commit/PR/tests or negative source finding
Next: one assigned task or assignment request
Blockers: any genuine operator or dependency blocker
OVERSIGHT ESCALATION: REQUIRED or NOT REQUIRED

For S000 manager: include the seven-agent roster status and significant
merge count since independent review; explicitly escalate unresolved owner
collisions, two-cycle P0 stalls, architecture/eligibility conflicts, unsafe
merges, or every five significant merges. Ordinary verified merges follow
merging.md without an extra AI approval ritual.
```

## 3. Universal HANDOFF V2 — OLD chat near context limit

```text
HANDOFF V2 — UNIVERSAL AGENT

Your conversation is ending. Do not start or impersonate a parallel agent.
Identify and preserve YOUR verified role, instance ID and assignment.

1. Recheck latest main, root merging.md, role, active issue/PR CLAIM,
   current manager ASSIGNMENT ROSTER V2 on PR #320, branches, actual CI,
   evidence bounds, blockers and the complete unfinished assignment.
2. Complete or safely stop edits. Post [YOUR_INSTANCE] SUCCESSION HANDOFF
   on your existing canonical issue/PR, including exact SHAs, owned paths,
   tests, live permissions, negative findings, pending PRs and one task.
   Link the actual published handoff comment, not a fabricated permalink.
3. Select one distinct successor instance ID in the SAME role. Post release
   of outgoing ownership; ask S000 Manager to transfer that SAME specific
   roster assignment to the successor. Do NOT let the successor independently
   claim another task while the transfer is pending. Any gaps PARK.
4. Read scripts/agent_handoff.py and docs/v2-agent-continuity.md. If possible
   use --role, --instance, --successor, --thread and --handoff-url with the
   ALREADY posted permalink; syntax validation cannot prove GitHub existence.
5. RETURN ONE COMPLETE, STANDALONE, READY-TO-PASTE NEW CHAT PROMPT.
   Include exact new identity/role, verified handoff permalink, task/paths,
   latest assignment roster permalink or pending transfer, verified code
   and CI evidence, unresolved blockers, root merging.md, instruction to
   confirm manager assignment and post [SUCCESSOR] CLAIM before edits.
   No placeholders, role-specific supplement, or required reconstruction.
6. Do not create the chat yourself, start Dolphin, discard research,
   auto-reserve files, or assert unverified training/swing results.

End with outgoing Role and Agent ID, assignment transfer state and one
OPERATOR STATUS. Your final copy-ready successor prompt must itself direct
explicit Role and Agent ID reporting on future CONTINUE messages.
```

## Use

**INIT** starts a new identity only after manager allocation. **CONTINUE**
keeps the existing instance and completes its assigned scope. **HANDOFF**
transfers the existing scope to a uniquely named successor after S000's
roster update. To replace a chat, paste its complete generated successor prompt,
not a new generic INIT. None of these instructions wakes other chats or
bypasses the operator's explicit live-game consent.
