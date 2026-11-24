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


## Staged project-bound LocalOps read endpoint (wire v1)

The existing private LocalOps console remains the sole human CLI. The
`OperatorReadEndpoint(project, broker)` adapter accepts only exact GET
targets and one Authorization: Bearer credential, returning HTTP status,
fixed response headers and canonical JSON bytes. One host-configured
project maps to one trusted broker and independently provisioned project
credential registry; the caller cannot choose a repository or ref. A
worker/manager/maintenance credential is rejected even if it could use
the internal broker status method. Foreign projects, invalid/duplicate
query parameters, unrecognized routes and non-GET verbs are rejected
before state IO. This is an offline request handler, not a deployed server
or TLS/credential provisioning system.

Routes: `/v3/projects/{project}/status`, `/capacity`, and
`/tasks/{task}/history?limit=1..50&cursor=integer` under that project
prefix. The status projection exposes only the fields consumed by the
existing LocalOps view: effective/durable revision and time, manager-first
task ordering, task IDs/status/role/priority/thread/dependencies, checkpoint
head/evidence references, active lease metadata, oversight and publication
freeze. Task objective, paths, free-form checkpoint text, historical runs
and artifact records are omitted. History preserves event identity and
only the fields needed by the renderer. Capacity retains the existing
committed capacity report. The adapter bounds encoded output to 8 MiB,
returns sanitized errors and no-store headers, and never calls a
mutation operation. Internal broker status/history remain unchanged.

**Staging limitation:** this wire accepts full-state model version 2 only
and retains the integer revision cursor with the 500-revision history
window. It is intentionally not a production solution for the new indexed
hot state. Do not relabel compact state as version 2 or expose this endpoint
as cutover-ready. Replace with a jointly reviewed versioned compact
projection and pinned per-task cursor, then run actual cross-repository
client/adapter compatibility tests. The host must enforce TLS, header and
request limits, reject duplicate Authorization headers, keep logs
credential-free and isolate project-specific registries. No actual
network, credential, installation or production state-ref test is
performed by this adapter. Synthetic regressions cover project/principal
isolation before store IO, invalid routes/queries, read-only status/history/
capacity and expiry preview, byte-bounded and sanitized failure responses.


## Disposable persistent hot-root admission

The host may explicitly instantiate the same `Broker` with `hot=True` only
after initializing a disposable test ref through `GitHubStore.initialize_hot`.
There is no automatic format detection or fallback. Authentication, trusted
clock, lease/fence checks, manager authorization and checkpoint review remain
the same as for the full ledger. Supported actions are acquire, renew, finish,
manager_pass and maintenance sweep. Receipt/request/run lookups are bound to
one immutable hot root; the store commits the authorized proposal with
non-forced CAS. A fresh broker can replay an old acquisition from its terminal
run record, without granting an expired or released lease. A conflicting
request ID fails closed.

This is not a production mode. Artifact acceptance, publication reservation and
settlement are rejected before mutation. The existing LocalOps schema-2
status/capacity/history wire deliberately rejects hot mode; no silent partial
history or schema downgrade. Permanent task history, artifact/publication
indexes, compatible compact wire, deployment and activation remain gates.
Full-ledger mode continues unchanged. FakeGit regressions exercise the actual
broker/store combination, not a remote ref or deployed service.


## Staged LocalOps read-v2 contract (persistent hot history)

Routes: GET /v3/projects/{project}/read-v2/status and
GET /v3/projects/{project}/read-v2/tasks/{task}/history?limit=20[&cursor=...].
The same authenticated read-only principal and fixed project binding apply.
Successful JSON responses carry wire_version=2 (not the storage version).
Legacy routes are unchanged and fail closed on hot mode.

Status contains wire_version, head, durable_revision, effective_at, eligible
(always [] for the operator), task_order (manager first), manager_authorized
(always false for operator read), publication_supported=false, and state.
State contains version=3, revision, clock, oversight, tasks and runs. Task
entries retain the legacy allowlist: role, status, priority, thread,
dependencies, run, fence and checkpoint {head,evidence}. Runs contain only
active task references with task, status, fence, heartbeat, expires.
The publication_pending and publications fields are absent, not empty healthy
values. GET .../read-v2/capacity returns 503 {"error":"capacity unavailable"}
until its hot capacity contract is implemented.

History response keys: wire_version, task, head (pinned commit), event_count
(total at pin), events, next_cursor (opaque string or null).
Events are in descending contiguous per-task sequence order, each with task,
sequence (1-based), kind, revision, operation, clock, source_commit
(original full-ledger SHA during backfill; null for newly indexed events),
and data using the legacy per-kind allowlist. Hot events identify the
committed transition by revision and operation, not by a circular self-SHA.
Kinds: created, task_changed, claimed, renewed, expired, released,
oversight_changed. No artifact/publication event claims until integrated.
A page contains at most limit events (1–50); a known task has at least one
creation event. No revision-window or empty-page traversal.

The cursor is a host-generated, URL-safe, HMAC-SHA256 authenticated opaque
token, at most 1601 ASCII characters, matching
[A-Za-z0-9_-]{1,1536}[.][0-9a-f]{64}. Pass it unchanged; never decode or
manufacture it in LocalOps. It pins project, repository, branch, task,
immutable snapshot, event count, next sequence and expiry. The host must
provision a separate persistent high-entropy key (32–128 bytes), never
included in source or worker credentials. A cursor expires 3600 seconds
after issuance (not extended by paging). Invalid signature, wrong binding
or expired cursor returns 409 {"error":"refresh history"}; restart without
cursor to obtain the latest pin. Malformed route/query returns 400 or 404,
unknown task 404, missing key/unavailable store 503. The authenticated
snapshot pin is checked before any cursor-selected Git commit lookup.
Concurrent appends do not alter the pinned page or remove older events.
No production host or credentials have been provisioned.

The earlier staging-only read wire remains available on full-ledger mode.
The new read-v2 route is explicitly separate and must be integrated and
tested with the private LocalOps client before activation.


## Hot journal admission (supersedes earlier unsupported-action note)

Hot mode now supports metadata-only accept_artifact, prepare_publication
and resolve_publication through the same authenticated broker admission
checks as full mode. Actual upload, source ref promotion and dispatch are
not implemented. Only a trusted host observation of a settled exact base or
head can release the queue freeze. The broker does not itself dispatch any
external IO. Old receipts remain replayable without a fresh lease or effect.

Read-v2 history can now contain artifact_accepted, publication_intent and
publication_resolved with the existing sanitized per-kind projections.
Read-v2 status continues to advertise publication_supported=false; while
an intent is pending it returns 503 response unavailable rather than
showing an unfrozen queue to a client that cannot represent the freeze.
The next compatible wire revision must represent pending intent and
settlement explicitly, and coordinate with the private LocalOps owner.
Hot capacity also remains unavailable over the current wire. No production
credential, endpoint or executor has been provisioned.


## Staged LocalOps read-v3 contract — explicit publication freeze and capacity

The read-v2 routes remain unchanged. New clients must select read-v3
explicitly, never silently fall back. GET /v3/projects/{project}/read-v3/status,
GET /v3/projects/{project}/read-v3/capacity and
GET /v3/projects/{project}/read-v3/tasks/{task}/history use the same project
binding, read-only credentials, response bounds and history cursor as read-v2.

Status has the same fields as read-v2, except wire_version=3 and
publication_supported=true. It additionally includes queue_frozen (boolean),
publication_pending (operation ID or null) and publications (empty if not
pending, otherwise exactly {operation_id: {"resolution": null}}).
The three fields must agree. Eligible remains [] for the operator.
The effective lease view can show an expired task as OPEN while the durable
queue remains frozen: never interpret the preview as permission to dispatch.
Publication support means journal admission and reconciliation, not an
installed source publication executor.

Capacity keys: wire_version=3, head, revision, used_bytes, limit_bytes,
remaining_bytes, level (normal/warning/critical), receipt_count,
active_run_count, archived_run_count, event_count,
settlement_reserve_bytes, publication_pending (boolean), capacity_scope
("hot_root_only"). used_bytes measures the exact committed hot.json blob,
including repository/ref/parent metadata; remaining_bytes=limit_bytes-used_bytes.
Counts are from the same pinned root, with receipt_count=revision+1,
active_run_count the durable (not preview) run count and archived_run_count
the sum of per-task archive floors. Event count sums per-task counts.
Warning begins at 75%; critical at 90% or remaining below reserve.
Reserve is 2048+64*task_count bytes. This is not total Git storage, index
size, network capacity, or an assurance of successful settlement.

History has identical shape and cursor semantics to read-v2 except
wire_version=3. It includes the sanitized journal event kinds. Status,
capacity and history each pin their own snapshot; never assume different
requests refer to the same head. Read-v2 status still fails closed during
a pending intent and its capacity route remains unavailable. Production
deployment and compatible private LocalOps client acceptance are still gates.


## Staged host-only disposable publication dispatch

The hot broker's explicit host method
`dispatch_publication(maintenance_token, pending_intent, executor)` is
not a worker request action or an HTTP route. It requires the exact pending
committed root, an active original fence, unchanged goal and checkpoint,
complete reinspection of the immutable direct-child proposal, and a fresh
trusted semantic review (including exact-head CI, privacy and source policy).
It checks the committed root and lease again before and after the durable
dispatch reservation. The queue remains frozen after dispatch, even when the
transport reports success. Expiry or error after marker consumption does not
permit another send. A separate independently settled observation is required.

`PublicationExecutor` binds the disposable queue and source repository.
Its host callbacks must enforce an atomic, durable, permanently consumed
marker keyed by repository/queue/intent, and an exact-old source-ref update.
A marker binds the immutable queue head, disposable target, base, proposed
head and manifest digest; a conflicting binding cannot create a new marker.
Marker uncertainty stops before the send. An ambiguous send is not retried
and exposes no transport output. The marker must survive process restarts.
This is an injected host capability, NOT a deployed marker backend.

`exact_push_arguments` produces a one-ref Git push argument vector using
an explicit expected-old lease, not a REST read followed by PATCH.
The prior immutable inspection proves the head is a direct child of base:
no non-fast-forward source rewrite is authorized. Only the configured
GitHub repository and disposable target are eligible. The host must use a
trusted isolated Git object store and configuration, prohibit arbitrary
credentials/remotes/hooks and unreviewed content, verify the exact parent
and GitHub identity, and control the transport. A timeout or an up-to-date
reply is not proof of settlement. Never interpret an old-base read while
a send may still be in flight as a settled non-application.

The broker serializes these operations within one instance; cross-process
exclusivity between marker, dispatch and observer is a mandatory deployment
gate. The marker cannot by itself establish that a send is no longer in
flight. The observer must prove that independently before resolution.
No runtime wiring or host credential provisioning is provided here.
Tests cover unauthorized dispatch, changed manifests, denied review, expired
fences, restart with a consumed marker, ambiguous effects and an actual
offline disposable bare Git repository (successful exact-old update,
competing sibling and deleted-target refusal). No live GitHub source push,
production ref, automatic executor or merge endpoint is introduced.


## Durable single-host dispatch guard and conservative settlement

The previously injected marker contract now has a SQLite implementation
`DurablePublicationJournal` for disposable queue refs. Explicit first
provisioning binds the database to one repository and queue branch.
Opening a missing, incompatible, foreign or corrupt journal fails closed.
Never recreate a lost database or restore an old backup as if it were
authoritative. Use a trusted operator-owned directory and ACL, including
on Windows. SQLite BEGIN IMMEDIATE and synchronous=FULL serialize
independent connections on one host, not separate hosts or adversarial
filesystems. The journal retains immutable key/binding tombstones.

The irreversible phases are RESERVED -> SENDING -> ACKNOWLEDGED,
or absent/RESERVED -> CANCELLED. Before calling the transport the
executor commits SENDING. A process exit, timeout, negative result or
uncertain acknowledgement leaves SENDING unresolved; no automatic
retry, cancellation or settlement is allowed. The transport must return
literal True only for a successful synchronous terminal response; this
does not itself establish the external ref. A cancellation is an
explicit maintenance-only call to cancel_publication_dispatch, commits
CANCELLED even if no reservation exists, and cannot race a later send
successfully. Cancellation alone never releases the Work Queue freeze.

Configure the same DurablePublicationExecutor as the broker's
publication_observer and dispatch executor. The broker constructs the
command from the exact committed pending intent for dispatch,
cancellation and resolution, never from worker-supplied ref/SHAs.
With this configuration a different executor cannot send. Only
ACKNOWLEDGED plus independently observed exact proposed head, or
CANCELLED plus independently observed exact base, can settle. Even
a matching ref is insufficient in SENDING. Missing or different
ref or transport uncertainty fails closed. GitHubPublicationRefReader
provides the fixed repository/ref GET adapter with exact commit identity.
Existing callback-only fixtures remain staging compatibility, not
an alternative approved production effect path.

Tests exercise cross-connection contention, cancellation versus begin,
abrupt child-process exit after committed SENDING, missing/foreign
journal, conflicting binding, exact ref identity, frozen queue after
dispatch/uncertainty, and independent resolution after restart/expiry.
The host must still provision an isolated Git object store, executable
transport with no hidden retry, credentials and exclusive source/state
write authority; verify real remote CAS and crash/rollback procedure.
A SENDING marker requires separately reviewed manual reconciliation
with evidence of no in-flight requests. No automatic manual override,
network source push, host installation or production cutover is supplied.
