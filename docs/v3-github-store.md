# Work Queue GitHub persistence — phase 2

Canonical migration: #485. Depends on offline lease/manager PR #486.
This adapter is not the authorized broker; production writes are disabled.

## Storage contract

One separate ref (proposed orchestration/v3-state) will hold the canonical
ledger. A disposable integration ref must be explicitly named
orchestration/v3-test-<identifier>. The store refuses mutations to main,
the production state ref or any other branch. A test bootstrap replaces
only the designated test ref's tree with a single canonical ledger.json,
using a new commit whose sole parent is the observed ref. It refuses
reinitialization. No private data or credentials in the ledger.

The envelope contains schema version, validated Work Queue state and
operation receipts (ID, revision, SHA-256 of parent and proposed state),
and, in the schema-2 envelope integrated by the broker PR, an immutable
artifact journal. Artifact admission is atomically bound to the same
receipt and state revision; its manifest is included in the digest.
Historical artifacts survive checkpoint overwrite and lease expiry.
The schema-3 publication phase also stores a durable intent/outcome journal.
An unresolved intent freezes all subsequent new transitions except its
matching resolution; the receipt digest includes the publication mutation.
Schema 1/2 are not auto-upgraded; use a fresh test ref. Production state
does not yet exist.
The ledger is canonical ASCII JSON, with duplicate keys rejected, and
a verified Git SHA-1 blob. A pinned read fetches ref, immutable commit,
tree and blob, and checks the exact identity and structure. Receipts
are retained for every revision including bootstrap. The conservative
2 MiB ledger cap is intentional: stop for a reviewed archival/compaction
design before exhaustion; never discard fences or receipts silently.

Publish requires the original snapshot, a single revision increment,
and a unique operation ID. It rechecks the current snapshot, creates
a blob, a single-file tree and a single-parent commit, then performs
one non-forced PATCH of the ref. A conflicting sibling cannot be
fast-forwarded. It never blindly retries a ref update. A durable
matching receipt reconciles a lost response, even if later updates
have advanced the ref. Reused ID with a different digest fails closed.
A stale snapshot or confirmed non-fast-forward requires reread and
recompute. If the outcome cannot be determined, report UncertainWrite
and stop for reconciliation. A receipt's observed_head is the ref
at reconciliation, not necessarily the commit that originally recorded
the operation; revision and digest identify the original transition.

## Capacity visibility and pre-cutover archival contract

The authenticated broker exposes a separate read-only capacity(token) view
so existing LocalOps status/history responses remain unchanged. It reports
the pinned head/revision, canonical byte count, limit, free bytes, receipt
and run counts, pending-publication flag and settlement reserve. Warning
starts at 75% utilization and critical at 90% or less than 1024 free bytes.
These are operational alerts, not a grant to discard data or mutate state.
New publication intents must fit while retaining 1024 bytes for settlement.
Schema 3 settlement adds one receipt (bounded operation ID, digest and
revision), one resolution (operation ID and observed SHA), and bounded
numeric clock/revision/epoch changes; expiry only shortens task/run strings
in aggregate. The reserve is conservative for this schema, not a guarantee
against transport failure, counter exhaustion or future schema changes.
Revisit it when the schema changes. Ordinary mutations still fail closed
at the hard limit; exact receipt replays and reads remain available.

**Offline conversion oracle implemented; next persisted schema not yet implemented.**
The archive_snapshot and restore_archive helpers partition older receipt
records and terminal runs into immutable canonical JSON pages, up to 64
records each, sorted by key and addressed by SHA-256. Active runs, recent
receipts, all task fences and checkpoints, holds, goals, artifacts and
publication outcomes remain in the hot manifest. Pending publication
prevents conversion. The manifest binds the source head and the SHA-256
of the complete original envelope. Restore requires an independently
trusted manifest digest and source head; it verifies every page, exact
membership, page bounds, duplicates and canonical partition, reconstructs
and validates schema 3, then checks the original envelope digest. Tests
exercise multiple pages, expired-run fencing, replay retention, corruption,
missing pages, mismatched identity and no authoritative ref mutation.

The read-only ArchiveIndex prototype uses independently trusted manifest
and source pins, nonoverlapping sorted key ranges and SHA-256 page checks.
An exact cold receipt/run lookup reads at most one page. Request-prefix
lookup includes both hot and archived receipts and fails closed when the
page-read budget is exceeded or any candidate page cannot be verified.
The manifest must first be validated against the complete original source;
a self-supplied hash is not evidence of completeness. Index lookups never
authorize a replay or a lease by themselves.

The disposable-test-only stage_archive method creates an immutable Git
commit with archive.json and its content-addressed pages, checks the
single parent and exact tree membership, reads the objects back, verifies
the full restoration against the original snapshot, and checks that the
source ref has not changed. It returns a candidate commit and manifest
and source pins. No ref is advanced; unreachable objects may be garbage
collected and are NOT durable roots. open_archive_index reads a previously
verified pinned candidate with lazy page access. Both are offline-tested
transport prototypes; no real archive objects have been staged by this
implementation pass.

The host-only archive_checkpoint prototype adds a physical archive-root
encoding on explicitly disposable test refs. It preserves the logical
schema-3 envelope, increments the revision once, records an archive-
prefixed operation receipt whose digest binds the source parent, next
state and receipt-retention setting, builds the immutable tree and
verifies complete readback before one non-forced ref PATCH. Existing
receipt reconciliation handles lost responses and conflicting siblings.
The root marker is distinct from an unpromoted archive candidate.
A reopened test store recognizes the root, verifies parent and tree
membership, restores the envelope and checks the checkpoint receipt.
Ordinary transitions can resume and task history traverses the checkpoint
as a single revision; prior archives remain reachable through ancestry.
Bootstrap cannot reset a ref containing an archive root or candidate.
Production archive-root reads/writes and checkpointing with an unresolved
publication are denied. Tests simulate CAS races, lost responses, reopen,
replay, subsequent renewal, history traversal and corrupt pages.
No real archive checkpoint ref has been advanced by this code change.

This is a persistence prototype, not a production storage migration.
Logical state remains schema 3 and full restoration is bounded by the
original 2 MiB cap. Ordinary transitions after a checkpoint write the
full envelope again. The manifest page list grows and root reads hydrate
all pages. No bounded ongoing hot-state transition engine, permanent
task-event index or integrated cold replay admission exists yet.
The checkpoint demonstrates reachable archival without losing records,
not increased capacity. A future schema must preserve the same oracle
semantics without full hydration for each transition.

**Proposed persisted next schema; not authorized for production.**
A permanently growing full snapshot cannot support indefinite operation.
Use an immutable, content-addressed archive/index rooted in the same
single-parent state-ref commit, with bounded hot state and separate indexed
receipt, terminal-run and task-event records. Preserve permanent task IDs,
current fences, active runs, legacy holds, current checkpoints, goal pins,
publication outcomes and durable request-ID tombstones. Archive lookup
must establish exact membership and digest, not infer absence from a
cache miss or a bounded history window. A closed run's archived receipt
must remain replayable without granting renewed authority. No unresolved
publication may be compacted. Atomic ref promotion must bind the new
manifest, archived records and hot state; a partial upload may leave
unreachable objects but must never advance authoritative state.

Before implementation, specify schema version and lookup bounds, exact
archive integrity rules, stable project-bound history cursors and replay
semantics; redesign model.validate's contiguous fence/run checks and
validate_envelope's contiguous receipt checks together, not independently.
Require offline tests with many workers and renewals, archive boundary
crossing, lost response, concurrent sibling compaction, stale fence and
request-ID reuse, corrupted/missing archives, pending intent refusal and
old history pagination. Reopen from the committed manifest and compare
against the uncompressed oracle. Test rollback/read compatibility and
real disposable-ref CAS before any migration. Archive data must remain
reachable and sanitized; neither deleting Git history nor resetting the
state ref is an acceptable capacity recovery strategy. Until this gate
passes, the bounded schema-3 ledger is staging only.

## Security boundary

The standard-library REST transport uses only api.github.com, no
redirects or automatic retries, bounded response bytes, and a bearer
credential supplied to the broker, never committed or displayed.
The store validates snapshot shape but is NOT a transition authorization
system: a direct writer could bypass it or propose a structurally valid
but unauthorized state change. The next phase must enforce authenticated
roles, trusted time, lease/fence, exact transition, sanitized checkpoint
review, and authorized artifact publication before calling publish.
Do not give workers the broker's GitHub credential. Production state,
source branch and merge authorization are separate from Git object CAS.
No private/live/LocalOps/training authorization is inferred.

## Verification

The offline tests exercise a thread-safe simulated Git graph, competing
sibling commits, stale/forged snapshots, response loss and idempotency,
permission denial, malformed ledger and production-write rejection.
The fake graph does not establish actual GitHub semantics. A real
disposable-ref concurrency test with non-forced sibling updates is
required before enabling production; end-to-end REST transport and
restricted credential/gateway enforcement remain separate gates.

No production state branch, background process, automatic dispatcher
or V3 cutover is created by this code. V2 remains authoritative.


## Incremental hot-state index prototype

IncrementalIndex uses immutable SHA-256-addressed radix nodes and copies
only the affected key path on insertion. Exact lookup and insertion are
bounded by the 64-hex-character key hash width (at most 65 node reads
or writes per key); the root is constant size. A missing referenced
node is an error, while an authenticated absent branch proves absence.
Leaf identity and placement are checked, and conflicting immutable
values or full hash collisions fail closed. Old roots remain unchanged.
The object backend must provide immutable, durable writes and reads
against an independently verified root. Arbitrary caller-supplied
roots cannot establish trustworthy nonmembership.

Receipt IDs, broker request-identity prefixes, and closed-run IDs
occupy separate namespaces. The request prefix is stored as an exact
key mapping to the original operation ID, so conflicting payload
reuse does not require a prefix scan. indexed_hot_projection imports
all receipts and terminal runs from the validated full-history oracle.
indexed_hot_transition takes a trusted host transition callback,
reconciles exact receipt replay first, checks the request identity,
supplies cold run-ID membership to the pure model, and emits one
proposed hot manifest with the updated index root and receipt. A
replayed receipt changes neither manifest nor index. The callback
must enforce the authorized transition, clock and fences; this helper
is not a broker. A failed proposal can leave unreachable objects but
cannot change its prior manifest.

Synthetic tests exercise 300 indexed keys, bounded IO, immutable
historical roots, missing/corrupted nodes, and 30 acquire/finish cycles
against the full-history oracle with replay and stale-ID rejection.
The initial conversion currently refuses any artifact or publication
records; their immutable provenance and outcomes require separate
index namespaces and validation. Task event indexing, archived
terminal response construction, and manager/operator transport are
not implemented by this helper.

This is still a pure proposal/object-backend prototype. No authoritative
Git tree or ref currently commits its root. A persisted next-schema
implementation must make the hot manifest, reachable index objects and
receipt authoritative together by one non-forced CAS, validate the
migration from a trusted source, reconcile uncertain responses and
protect prior roots. Repeated Git API calls along a path also need
measured latency/quota and a bounded read/write strategy before
deployment; the node-count bound alone is not a timing guarantee.
Existing schema-3 production writes remain disabled.


## Disposable persistent hot root

`initialize_hot(expected, operation)` converts an exact full-history
snapshot with no artifact or publication records into a compact hot
manifest. One new revision and initialization receipt are committed.
`read_hot()`, `hot_lookup(kind, key)`, and
`publish_hot(expected, operation, digest, authorized_transition)` read
and advance only explicitly disposable test refs. The ordinary full
ledger reader does not silently hydrate or overwrite a hot root; the
bootstrap path also refuses to reset it.

Each radix node is a real Git tree containing a canonical node.json blob
and child tree links named by the hexadecimal radix digit. The commit
root has exactly hot.json and index (tree). The manifest binds the
repository, branch, parent commit, current operation, original source
head, compact state and logical index root digest. The linked radix root
is not a flat list of every archived key. Tree hashes use actual Git
binary SHA-1 object encoding; node bytes independently retain their
SHA-256 digest. Readers validate blob/tree identities, non-truncation,
entry modes and exact child membership, and load child nodes only from
references discovered along the anchored tree. Old roots remain reachable
through commit ancestry. A fresh client reconstructs only the relevant
paths, with no required process-local index.

Every transition stages a new single-parent commit containing the hot
state, root and receipt, verifies the candidate and attempts exactly one
non-forced ref update. Reconciliation reads the current committed root
and searches its receipt index; replay cannot invoke the transition
callback or write a second ref update. Different request payload under
the same operation prefix fails closed. Archived terminal runs remain
queryable and cannot be reused by the pure acquisition callback.

Tests cover real Git tree hashing, synthetic reachability and old-root
lookup, fresh-client reopening, terminal history/receipt replay,
concurrent sibling proposals, uncertain update response, staging
failure, corruption, bootstrap rejection and production write rejection.
The fake transport is not evidence of GitHub REST CAS behavior; actual
disposable remote integration and latency/IO measurement remain gates.

**Not a deployed broker backend:** the callback is a host-only trusted
capability. Existing broker authorization, artifact/publication records,
task-event indexing, stable pinned pagination and compact read wire
still require integration. No production migration, deletion, source
publication or operator execution is authorized. A hot root is not
readable by the existing full-state broker; do not initialize one on a
ref used by that broker. Keep the legacy full ledger and all historical
objects until an independently reviewed cutover and rollback procedure.


## Permanent task-event index (disposable history format 2)

The persisted hot manifest now uses indexed-hot-history-2 with event_counts
(one positive monotonic count per permanent task). The pure projection oracle
still accepts the earlier prototype format, but persisted history readers
reject old hot roots: no automatic upgrade or invented earlier events.
Initialize a fresh disposable ref from a complete full-ledger history.

Conversion walks the single-parent full-ledger chain, checks consecutive
revisions, receipt retention, nondecreasing clock and immutable terminal runs,
then imports every task/run/oversight delta in chronological order. The
initial creation records are retained. Legacy events pin their original
commit. The one-time backfill is limited to 500 prior revisions and keeps
commit locators rather than all full snapshots in memory; beyond the reviewed
limit, conversion fails without changing the ref. Artifact/publication
records remain unsupported and block conversion. No partial history is
published.

Each subsequent transition writes per-task event records before terminal-run
compaction, together with the receipt, archived run records and new hot
state, in a single non-forced Git ref CAS. A failed candidate does not
advance counts; exact replay adds no events. Records are addressed by
SHA-256(task,sequence) in the same immutable Git-tree radix index. Counts
grow in value, not in number of entries per task. Reads pin one committed
root and fetch up to 50 exact event keys; no scan of intervening revisions
or hydration of unrelated terminal history. Event sequences are contiguous
per task, newest first. New hot events use revision and operation as
identity; they cannot contain the SHA of their own enclosing commit.
See broker docs for the project/ref-bound signed cursor contract.

The new schema remains test-only: actual GitHub disposable-ref behavior,
complete artifact/publication indexing, hot capacity, larger-history
conversion and migration/rollback validation remain open. No production
state, deployment or credentials.
