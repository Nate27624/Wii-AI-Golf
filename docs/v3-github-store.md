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
operation receipts (ID, revision, SHA-256 of parent and proposed state).
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
