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

This is a lossless conversion and integrity oracle, not a storage
migration: GitHubStore still accepts schema 3 only. Full restoration is
bounded by the original 2 MiB schema-3 cap, the manifest's page list grows,
and all pages are hydrated for validation. No indexed cold lookup,
persistent archive manifest commit, task event indexing, or ongoing
hot-state transitions against archived history are implemented.
Exact replay remains handled by the existing schema-3 store. A future
implementation must preserve the same oracle semantics without requiring
full hydration for each transition.

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
