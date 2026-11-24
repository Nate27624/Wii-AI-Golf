# V3 Work Queue — architecture and implementation contract

Canonical migration: [#485](https://github.com/Nate27624/Wii-AI-Golf/issues/485).
V2 AGENTS.md, merging.md, live/private consent and evidence gates remain
binding until reviewed cutover. The offline core is not a live dispatcher.

## 1. Permanent context, disposable workers

GitHub is authoritative for operator-approved goals and constraints, permanent
task IDs, role, priority, canonical issue, objective, acceptance, owned paths,
named resources, dependencies, lifecycle, latest checkpoint, evidence and
execution history. A worker is a temporary execution run, not a durable
identity. It must acquire before work, recover context from the Work Queue,
checkpoint regularly, and release atomically with its report. No previous
chat transcript is required. Record exact code SHA, PR, actual tests and CI,
remaining uncertainties and next bounded action; never raw private inputs.

The sole permanent manager task is S000-MANAGER. It is always display
position zero, including when blocked, leased or not due. It can see the entire
sanitized Work Queue, including all specialist leases and history. It is
responsible for project alignment, task creation, prioritization, dependency
and scope reconciliation, research gaps, blocker review and escalation.
It never becomes CLOSED or PARKED in normal operation. Its management
lease reserves only queue metadata, not all source paths. Specialists may
continue while the manager is active or temporarily absent; they cannot
mutate queue policy or operator goals. No discretionary management approval
is required for an otherwise merge-ready PR. Existing merge/evidence rules
continue to apply.

## 2. Work Queue state and dispatch

Task states: OPEN, IN_PROGRESS, BLOCKED, PARKED, CLOSED. Run states:
IN_PROGRESS or CLOSED, with terminal outcome EXPIRED, OPEN, BLOCKED,
PARKED or CLOSED. Run IDs are unique; task fences increase on acquisition.
The trusted broker supplies integer UTC seconds. A 120-second lease is
half-open: exactly at heartbeat + 120 the run is expired. Recommended
heartbeat every 30 seconds; it does not require code changes. A heartbeat
can save a durable checkpoint. On expiration the run closes EXPIRED and
the unfinished task reopens with the last committed checkpoint. Expired
tokens cannot renew or finish. Successful specialist finish stores the
receipt and releases scope atomically; exact terminal retries are no-ops.
Blocked, parked or completed tasks do not reopen merely with time.

The manager receives first dispatch priority when its review is due,
including after its own expiration while other workers remain active.
A successful management pass releases it OPEN but does not immediately
requeue an identical review. The offline policy uses review epochs for
expiry/completion and a five-minute review cadence (proposed default).
Role-specific invocations may still select specialists; a generic worker
uses the global manager-first candidate order. A dedicated manager slot is
recommended for an eventual concurrent executor. The queue distinguishes
active oversight from the last recorded review. If no eligible work exists,
report idle or blocked rather than spin. A blocked manager must await
authorized resolution; expiry never implies approval.

The offline schema version 2 requires exactly one reserved manager task,
a goal commit SHA, review epoch, reviewed epoch and review timestamp.
No production ledger exists yet; this is an internal pre-cutover schema.
All successful transitions are pure snapshots, never in-place writes.
Role/dependency and case-insensitive path/named resource conflicts fail
closed; legacy V2 holds block acquisition. The manager cannot reserve all
files, retire itself, or silently alter active specialist tasks.
manager_pass validates the active manager token and exact observed state
revision, atomically applies priorities/new OPEN tasks/parks OPEN tasks,
records review/checkpoint and releases the lease. Retired tasks are PARKED,
not completed. Stale snapshots and stale manager runs fail closed. Manager
mutation retries require broker reconciliation of the committed state/receipt;
no blind replay. Operator goal updates and approval resolution require
separate authorized broker operations, not manager inference.

## 3. GitHub store and broker (next implementation phases)

Use one dedicated state ref, proposed orchestration/v3-state, separate from
main. Each transition reads state head H, validates against it and proposes
a commit C with sole parent H. Advance the ref non-forced; siblings race
and only one can become authoritative. On conflict reread and recompute.
On unknown response reconcile operation/run receipt and actual commit,
never blindly repeat. Validate actual GitHub concurrency in a disposable
ref before production use; local Git feasibility is not GitHub proof.
Retain history and run ID tombstones; any future bounded compaction must
retain fencing and idempotency semantics.

A restricted broker is the sole authority for state writes and authoritative
artifact acceptance. Workers submit proposals; they must not have direct
state-ref/protected branch/merge credentials. Authenticate worker roles,
validate token/fence, trusted clock, scope, exact artifact hash, operator
approval and current policy. A Git fast-forward alone does not validate
authorization. Serialize external effects with intent/receipt reconciliation;
uncertain effects block, not retry. Revalidate lease for external publication
and define admission-time expiry; do not promise strict commit-time expiry
without proving enforcement. Schema validation alone is not privacy review.
Public records contain only sanitized evidence references, not raw RAM, ROM,
savestates, private paths, tokens or captures. LocalOps remains the approved
private transport; explicit operator Y/N and live-game permissions survive.

## 4. LocalOps, project knowledge and task history

The [operator-approved amendment](https://github.com/Nate27624/Wii-AI-Golf/issues/485#issuecomment-7143914532)
supersedes the original golf.py queue CLI proposal. The sole human-facing
console is the existing private **LocalOps** repository (Nate27624/LocalOps).
Keep scripts/golf.py and the research CLI for existing project commands.
LocalOps is a client and controlled Windows execution subsystem, not a
second queue authority. Expose status, tasks, blockers, goals, roadmap,
findings, history/results, approvals and feedback through authenticated
broker operations; separate read-only and operator mutation permissions.
Status lists the permanent manager first even when not eligible. Distinguish
effective expiry, durable reconciliation, accepted artifacts and actual
merged results.

The planned root knowledge contracts are ONBOARDING.md (universal entry),
GOALS.md (operator-approved objectives and constraints), ROADMAP.md
(goal-linked measurable milestones, evidence and task IDs), FINDINGS.md
(curated research knowledge) and the existing merging.md (sole merge
contract). No duplicate merge policy. The manager curates onboarding,
roadmap and findings via authorized fenced publication, while goals remain
operator-controlled. Reference existing research registries and immutable
evidence rather than copying logs or private data. Workers propose findings
with stable ID, goal/milestone, concise claim, validation status (candidate,
verified, refuted, superseded), provenance, immutable evidence, limitations
and applicability; manager reviews and links contradictions/supersessions.
Never promote a candidate into established fact without validation.
Completed tasks retain findings.

Per-task history is an append-only projection of the authoritative
state-ref commit/receipt chain, not another mutable log. The initial
read-only broker view traverses validated ledger revisions, emits
creation, task/checkpoint change, run claim/renew/release/expiry,
artifact acceptance, publication intent/resolution and manager oversight
changes. Operation IDs and commit SHAs correlate events; an exact retry
does not add a revision. Pages are newest-first by revision, limited to
1–50 revisions and a 500-revision cursor lookback; empty pages may have
a continuation. Same-revision ordering is deterministic, not a separate
timeline. No inferred events for effective-only expiry. Dedicated finding,
operator approval/unblock, milestone/decision and actual merge events
require future authorized transitions. Retain operation journals and
run tombstones; future archival/indexing must preserve all history.

One universal onboarding instruction: read ONBOARDING and relevant
knowledge, authenticate, atomically acquire highest priority eligible task,
load its context, act within scope, checkpoint and release. LocalOps
requests carry task/run/fence, stable request ID, pinned digest and
authorization scope; private receipts link to tasks by sanitized references.
A pending approval may block a task and release its worker, with a separately
supervised hold for unresolved external operations. Declined operations
must not be retried; approval alone does not authorize execution without
fresh fencing/policy admission or supervised durable intent. Existing
Y/N review, private boundaries and allowlists remain intact.

No actual AI executor is implied by a CLI or GitHub comment. Continuous
oversight and periodic sweeps require an authorized execution backend,
trusted time and supervised heartbeat. Without it, expiry is effective at
the deadline but persisted on the next invocation/sweep.

## 5. Migration and cutover gates

1. Offline lease/manager core: focused negative controls and full exact-head
   Windows/Ubuntu CI, review, objective merge checklist.
2. GitHub store: real isolated sibling contention, failed permission and
   uncertain-response tests, never force; restricted broker and fence
   enforcement including external effects.
3. V2 shadow import: verified current roster, claims, owner threads and PR
   heads; preserve all live/reserved paths as legacy holds, parked/completed
   states and evidence. No V3 acquisition in shadow mode.
4. Knowledge contracts, task history and private LocalOps unified CLI:
   end-to-end dry-run, fresh-worker recovery, verified cross-task findings,
   task-correlated approvals and manager-first visibility; separate operator
   authorization for private or live work.
5. Reviewed cutover: drain/freeze V2 new claims, reconcile ownership and
   pending approvals, pin source snapshot, verify no overlaps and no dual
   dispatch authorities. Operator approves activation and rollback plan.
6. Optional executor: continuous manager coverage, bounded worker slots,
   budgets and scheduling; separate authorization.

Rollback: disable V3 acquisition, fence/drain active runs and reconcile
external effects, restore a verified V2 snapshot without deleting history.
Do not automatically resurrect old claims, retry declined requests, or
allow a V2 and V3 manager to issue competing ownership.

## 6. Current scope and limitations

Phase 1 code implements pure initial/validate/candidates/dispatch_candidates/
acquire/renew/sweep/finish/manager_pass. It has no network, IO, background
clock, credentials, production state, goal updates, operator unblock,
or actual dispatcher. The broker must supply authentic identity and time.
The manager review epoch/cadence is an offline policy, not live scheduling.
Tests are synthetic; no native game parity, real training, private data or
Dolphin authorization is implied. Verify exact-head CI before merging.
