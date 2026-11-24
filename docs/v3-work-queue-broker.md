# Work Queue authorization broker — metadata and immutable artifact admission

Canonical migration #485. Depends on #486 and #487. This library is
host-side code, not a deployed service. Production state writes remain
disabled by the storage layer.

## Trust boundary

The host supplies a registry of per-worker high-entropy credential
hashes and immutable principal identities, allowed specialist roles,
manager authority and maintenance authority. Worker requests cannot
select their own role, identity, time or task. Authentication precedes
all state reads or writes. Never store the registry or worker credentials
in GitHub. Hashes are for random credentials, not human passwords.
The future transport must use authenticated TLS, bounded request sizes,
rate limits, rotation and revocation. Credentials must not be shared,
and principal IDs must not be reused for unrelated workers.

Only the host has the GitHub store credential and review callback.
Workers call status or request through an authorized transport; they
cannot import this host capability in an untrusted worker process.
Manager and specialists may see the full sanitized queue. Manager
authority is separate from the S000 specialist role. A maintenance
principal may reconcile expiry but cannot create a task by sweeping.
A distinct LocalOps operator-read principal has `read_only=True`, an empty
role set, and neither manager nor maintenance authority. It can read
status and task history, receives no eligible dispatch candidates, and
is denied every request mutation before any state IO or receipt lookup.
Operator goal/approval authority is separate and not yet implemented.

## Admission and receipts

A broker-owned clock supplies integer UTC seconds; rollback rejects.
Acquire chooses the highest-priority eligible task for authenticated
roles, preferring the permanent manager when due and authorized.
At most one active run per principal; an execution ID is bound to
the authenticated principal and acquisition request. All renewal,
finish and manager operations require the matching active task,
run and fence, with permission checked again. A manager pass uses
the exact durable revision returned by status, not the synthetic
effective revision. Other workers' writes may require a new review
snapshot. The manager never locks every specialist file.

Heartbeat without progress is permitted; checkpoint, finish and
manager changes require a host-supplied trusted review callback.
A callback must verify scope, privacy, immutable provenance and
acceptance evidence; it must not perform publication or other
external effects. Missing/negative review rejects. Time is sampled
again after review so expired workers cannot finish. This package
does not implement that semantic verifier; test callbacks are
synthetic only.

Each request uses a principal-scoped stable request ID, full payload
digest and durable operation receipt. An exact replay reads the
original receipt and current effective lease status, not a fresh
grant. Different payload under the same request ID rejects. The
broker submits at most one state proposal per invocation. A conflict
requires a fresh read and retry; an uncertain response requires
receipt reconciliation. A same-second no-op mutation may still
persist a receipt revision. An idle acquisition is not a committed
operation and can be attempted again when work is available.
An authenticated status call computes effective expiry but does
not persist it; an authorized sweep or subsequent mutation does.
Status and history each read a pinned immutable snapshot outside the
mutation lock; a concurrent append cannot change that snapshot's ancestors.
Views may be stale and are not lease grants. Read transport concurrency,
rate limits, bounded deadlines and project binding remain deployment
requirements; removing the lock does not remove API quota contention.
History still has a bounded revision lookback; safe archival/indexing
and receipt retention are prerequisites for indefinite operation.

## Immutable artifact acceptance

An authorized active specialist can submit exact base and head Git object
SHAs and a checkpoint that pins the head. The host-owned GitHub tree
inspector reads both immutable commits and complete recursive trees. A
proposal must be a single direct child of its base. Truncated trees,
case aliases, unrepresented directory changes, file/tree replacement,
symlink/gitlink changes and unknown entry types reject. The complete
changed-file manifest must match concrete case-exact owned file paths;
directory permission is not inferred. Renames are checked as both
deletion and addition. The worker cannot submit its own manifest.

The host reviewer receives the independently derived manifest, its digest
and the goal pin. It must establish that the base is authorized, inspect
the actual content and enforce privacy, acceptance/evidence and operator
policy. A valid manifest alone is not semantic approval. Clock and lease
are rechecked after inspection and review. Acceptance, checkpoint,
renewal and the immutable artifact journal record are committed together
by the Work Queue store. The journal binds task, run, fence, revision,
admission time, goal, base, head and exact changed blobs. An ordinary
checkpoint containing a head is not an accepted artifact. A historical
acceptance survives later checkpoints, expiry and release; a replay
returns the receipt, not fresh authorization. Accepted artifacts are
visible in status. The source_promoted flag is always false.

The artifact admission phase used ledger schema 2; the publication intent phase below uses schema 3. There is no production
ledger or automatic schema-1/2 upgrade; explicitly initialize a new
disposable test ref for integration tests. This phase does not provide
an upload channel for untrusted workers or a source-ref promotion/merge
operation. The host must stage immutable proposal objects through a
separately authorized mechanism and preserve their reachability.

## Durable publication reservation (schema 3)

The authenticated current owner of an accepted artifact may request
`prepare_publication` with task, run, fence, artifact receipt and a
disposable `orchestration/v3-publication-test-*` target. Host semantic
review must independently pin the target base and goal, verify exact
accepted contents and policy, and recheck the lease after review. The
store checks that the artifact still belongs to the active run and
matches its current checkpoint and goal. Only a single intent is allowed.
The reservation and its receipt are written atomically with the queue.
An acceptance receipt can be used for only one publication intent.

While a reservation is unresolved, **all new queue mutations freeze**,
including acquire, heartbeat, manager pass and maintenance sweep.
Read-only status reports no eligible tasks and identifies the pending
intent. Exact historical receipt replays do not write or issue new
authority. The freeze lives in the store as well as the broker; an
ordinary transition cannot bypass it. Lease time still elapses; the
resolution transition sweeps expiry before resuming dispatch.

Only an authenticated maintenance principal can request
`resolve_publication` with the pending intent ID. The host-owned
observer must establish a **settled** external result, including proof
that no earlier request remains in flight; simply seeing the old ref
during an ambiguous network operation is insufficient. Exact accepted
head means applied; exact base means not applied; any other or missing
observation leaves the queue frozen. The worker cannot supply the
observed SHA. Resolution is journaled once with a separate receipt.
An exact retry is read-only, and a settled not-applied outcome is not
permission to repeat the same intent. The pending record is not a grant
to perform an external write, and the broker exposes no source-write
method. A deployed executor must establish exclusive credential control,
durable exactly-once dispatch or conservative manual recovery, and
revalidate authorization before sending a write. The observer here is
only a host callback contract, not a deployed settlement verifier.
Use a fresh disposable schema-3 ledger; no production upgrade is implied.

## Unimplemented deployment boundaries

This phase provides metadata admission, not actual worker isolation.
The next deployment layer must restrict credentials and route all
source-ref promotion and merges through a fenced gateway, including
operator permissions, exact-head CI, immutable accepted proposal
identity, and durable intent/outcome reconciliation for external effects.
Never treat a metadata lease check as authorization for a later
unserialized GitHub write. No source-code write, live gameplay,
training, LocalOps approval, goal mutation or unblock operation
is implemented here. No automatic AI worker or heartbeat daemon
is created. V2 remains authoritative until reviewed cutover.

Focused tests use simulated credentials, clock, review and GitHub
transport. Green CI demonstrates the offline contract only, not
production authentication, timing, credential isolation or gateway
enforcement.
