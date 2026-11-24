# V3 Work Queue — read-only V2 shadow import

Canonical migration: [#485](https://github.com/Nate27624/Wii-AI-Golf/issues/485).
This implementation is **shadow-only**. It does not initialize a live GitHub
state ref, issue new V3 ownership, invoke LocalOps, start agents, merge code or
authorize the cutover. V2 `AGENTS.md`, `merging.md` and manager roster remain
authoritative.

## Trusted input boundary

A trusted operator/broker must **independently fetch** the latest full
`[S000-manager] ASSIGNMENT ROSTER V2` comment from coordination PR #320.
The source body must contain exactly one pair of
`V2_ASSIGNMENTS_JSON_BEGIN/END` delimiters. Supply as separate, independently
verified inputs: exact comment ID, full source body, revision, current main
SHA, manager instance and an immutable operator-approved *goal commit* SHA.
Never derive a claim of source authenticity from the comment's self-declared
metadata. Re-fetch newest roster and exact source head immediately before any
future cutover. A successful local parse does not prove GitHub's current state.

`shadow_import.parse_roster(...)` strictly checks version 1, all eight
assignment fields, full finite valid JSON without repeated keys, 1–20
unique assignments, exactly one original V2 manager, recognized roles/states,
original thread URLs, individual scope limits, case-insensitive path
exclusivity, reserved V3 manager namespace and versioned source pins.
Missing, stale, partially enumerated or malformed data stops the preview.
No automatic correction or release of old ownership.

`shadow_import.preview(parsed, goal_sha=PINNED_GOAL_COMMIT)` returns a pure
dict with the original V2 state for each assignment, a SHA-256 digest of the
parsed roster data, immutable source references and an inert model snapshot.
The digest identifies *data*, not authenticated source provenance.

## Preservation and non-activation

The shadow model uses the same permanent singleton `S000-MANAGER` schema
as the staged V3 core. However, **the manager is BLOCKED** in shadow. Source
V2 states are preserved separately; `CLAIMED`, `ASSIGNED` and `BLOCKED`
map to V3 `BLOCKED`, `PARKED` to `PARKED`, and `COMPLETED` to
`CLOSED` in the inert snapshot. No imported task is OPEN or IN_PROGRESS.
This mapping is a safety gate, **not** a claim that work was reallocated
or independently verified as finished.

**Every V2 path reservation becomes a `V2-<task-id>` hold, including
completed tasks.** Those historical paths remain held until an explicitly
reviewed release at cutover. Unknown priority, dependencies, user approvals,
PR heads, CI evidence and resource locks are **not invented**: synthetic
priority 100 and empty dependency lists are placeholders on blocked tasks,
not safe values for dispatch. Resource reservations beyond concrete owned
paths need explicit separate reconciliation.

Expected tested source baseline at this implementation step: roster rev68,
20 rows and 79 paths, source comment
[#7143524743](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7143524743),
main `501361a9742f399891604a2c3f4b818de9b51fa8`.
These are **dated reference values**, never evergreen authority. During
cutover, stale inputs MUST be rejected rather than silently upgraded.

## Unfinished acceptance gates

1. Verify full live V2 roster, exact task owner CLAIM/HANDOFF notes, branches,
   PR heads, effective CI and non-overlap with open work; retain unresolved
   ownership and historical/paused work.
2. Create/review immutable operator goal manifest and independently pin goal
   SHA. Require an authenticated broker to perform live reads, trusted timing,
   role and approval checks; no untrusted chat worker direct credentials.
3. Add safe canonical `scripts/golf.py` Work Queue CLI and a cutover rehearsal
   proving manager-only queue mutation, stale-run rejection, ordinary specialist
   concurrency and recoverable frozen ownership.
4. Operator approves V2 drain/freeze and explicit rollback, checks zero
   incompatible claims and private approvals, then activates V3 separately.
   No dual V2/V3 authority or invisible automatic manager sessions.

## Tests

Synthetic offline controls cover no-dispatch and hold fidelity, malformed
and duplicate JSON, stale source pins, missing manager, ID/path aliasing,
unknown lifecycle state, invalid issue/PR thread, over-limit roster and
unverified goal pin.
A separate frozen **public GitHub #320 roster rev68** regression includes the
actual complete comment body and asserts 20 V2 rows, 79 held paths, exactly
one blocked permanent V3 manager and no runnable task. It proves this frozen
source shape can be parsed by the Python importer; it does **not** prove the
roster is still latest, nor authorize a goal pin, live ownership or cutover. Dedicated workflow runs focused and full
`python -m unittest discover -s tests -v` suites on Ubuntu and Windows,
using no GitHub write token, game files, or private inputs.

Passing synthetic tests does not establish that actual live roster/PR
reconciliation, source provenance, deployment or cutover succeeded.
