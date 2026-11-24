# V3 orchestration: offline lease core (phase 1)

Canonical migration: issue #485. This module is not an active dispatcher. V2
AGENTS.md and merging.md remain binding until reviewed cutover.

## Task and run lifetimes

Permanent task IDs and ephemeral unique run IDs are separate. The trusted
broker provides integer UTC seconds. Acquire grants a 120-second lease;
renewal (recommended heartbeat every 30 seconds) does not require a code
commit. It can optionally carry a durable checkpoint. The interval is
half-open: at heartbeat + 120 seconds the run is expired. Sweep and all
successful transitions reconcile expiry. A closed EXPIRED run retains its
history; the unfinished task reopens with its last checkpoint. A new run
increments the fence; stale renewals and results are rejected. A successful
finish atomically stores the terminal receipt and releases scope. An exact
terminal retry is a no-op, even after a later acquisition; it does not grant
a new lease. Blocked and parked tasks do not reopen merely because time passes.

The model is pure: initial, validate, candidates, acquire, renew, sweep and
finish return a snapshot or reject without modifying input. The ledger
includes version, revision, last trusted time, tasks, runs and legacy holds.
Candidate selection is deterministic by priority then task ID, constrained
by role, dependencies and overlapping resources. Paths are conservatively
ASCII repo-relative and case-insensitive; shared named resources are explicit.
The broker must preserve the same resource naming convention. Every run ID
and fence is retained; production compaction must preserve tombstones and
idempotency. Initial import and task management are not worker transitions.
There is no automatic reopening of declined operator requests.

## What remains unproven

The state machine has no network, wall clock, background timer, permissions,
publication or external side effects. A broker must serialize transitions,
use trusted time, authenticate workers, restrict state/code/merge writes,
enforce scope and review sanitized text (schema bounds are not privacy
classification). No worker-supplied time or raw evidence. A GitHub store
must prove non-forced sibling-ref contention and recover uncertain responses.
A worker with direct write access can bypass the model. Do not enable
production V3 before gateway, shadow migration, CLI and cutover acceptance.

A capped chat stops heartbeats. Expiry is effective at the deadline, but
the durable state is reconciled on the next broker invocation/sweep; no
promise of a timer running while ChatGPT is inactive. A long-running test
needs a separate authorized supervised heartbeat facility or a checkpoint
and release. No live Dolphin, private captures, or training permission is
inferred from a task lease.

The eventual unified CLI should show OPEN, IN_PROGRESS, CLOSED, BLOCKED
and PARKED task state, run outcome and expiry, last checkpoint and next
action; it must distinguish committed artifacts from proposed results.
