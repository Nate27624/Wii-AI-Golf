# Wii Golf agents — LocalOps v2 (private Windows command bridge)

**Status:** The operator's read-only LocalOps v2 test completed successfully
via [private mailbox request #3](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/3):
`wii-golf/git_status` reported short HEAD `b8cd643b` and a clean tracked
worktree. This verifies that **one agent-issued private request** was executed
on the Windows machine at that time; it does **not** prove the agent is
currently online, authorize additional operations, or verify game/physics.

The **separate private utility** is
`Nate27624/Wii-AI-Golf-LocalOps`, using
[`LocalOps v2`](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/pull/2).
Its Windows watcher, locally held config, and GitHub token are **not**
part of this public source repo. The old
`[WII-LOCALOPS-v1]` / `wii-golf-localops-v1` protocol is superseded; do
not request v1 commands or launch another v1 agent.

## Authorization and coordination first

1. Read the authoritative [V2 navigation](v2-navigation.md), root
   [AGENTS.md](../AGENTS.md), [charter](v2-agent-charter.md),
   [continuity](v2-agent-continuity.md), and [merge gates](../merging.md).
   Follow the current S000 assignment roster and active CLAIM. Access to
   LocalOps does **not** grant ownership of work or bypass reviews/CI.
2. Use your **connected GitHub tool** to verify
   `Nate27624/Wii-AI-Golf-LocalOps` is accessible and PRIVATE. If not
   accessible, **stop** and ask the operator to connect the private
   repository; never use a public issue or ask for the agent's PAT.
3. Determine which locally registered tasks exist from operator-approved
   setup or previous successful receipts. Do **not** assume the public
   example still matches the live local `config.json`. Adding task
   names or changing their execution/approval policy is a **local operator
   configuration change**, not something an agent can do by posting JSON.
4. Issue only one narrowly scoped request at a time. Do not interpret a
   prior result, claim comment, or a pending GitHub issue as a current
   execution guarantee.

**No game input**, controller commands, emulator boot, live shot, capture,
source-RAM upload, or private artifact publication without **separate
explicit operator permission**. A functioning bridge or a locally registered
task is **not equivalent to permission** for live game actions, training,
or work beyond the assigned role. The public/source privacy rules apply
to every LocalOps result and PR.

## Creating a request inside ChatGPT

Use the installed **GitHub connector** (not a browser automation task,
external URL, remote shell, local runner trigger, or GitHub Actions
workflow). Request a new **issue** in the private repo:

- Repository: `Nate27624/Wii-AI-Golf-LocalOps` (MUST be private).
- Exact issue title: `[LOCALOPS-v2]`.
- Body: **only** the strict JSON below, without backticks or commentary.
- The authenticated issue creator must match a trusted actor in the
  local agent's policy (the installed default is `Nate27624`).

### Harmless read-only status (runs automatically)

```json
{"schema":"localops-v2","project":"wii-golf","operation":"git_status","params":{}}
```

### List bounded project filenames (runs automatically)

```json
{"schema":"localops-v2","project":"wii-golf","operation":"list_files","params":{"subdir":"scripts"}}
```

Only simple **relative subdirectories** within the approved project
checkout are accepted. No `..`, drive, absolute, hidden secret directory
or symlink escape. The agent cannot read arbitrary file *contents* using
this operation.

### Run one locally registered named task

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_task","params":{"task":"inspector_tests"}}
```

The starter local config includes these **examples**, subject to operator
changes:

| Task name | Local command purpose | Starter policy |
| --- | --- | --- |
| `python_version` | Python version (fixed `py -3 --version`) | `auto` |
| `inspector_tests` | Existing synthetic memory-inspector test suite | `confirm` |
| `viewer_tests` | Existing synthetic 3D-inspector test suite | `confirm` |
| `launch_inspector` | Start the private FC3 viewer with operator-local paths | `confirm` |

The remote request contains a **task name only**. The program and
arguments are predefined in `%LOCALAPPDATA%\AgentLocalOps\config.json`
on the operator's computer. Do not submit a `command`, `argv`,
`script`, arbitrary `powershell`, extra parameters, path to execute
or secret. **Unregistered task names are rejected locally.** A task
marked `auto` can run unattended if the Windows watcher is running.
Tests and viewer launch are not enabled for unattended execution in
the starter policy.

For a new test/audit task, obtain operator review and update of the
**local** config first; then issue its exact registered name. Avoid
designing a broad `run_anything` task because that would erase the
allowlist boundary.

### Opt-in scoped research studies (only on upgraded LocalOps)

The operator supports a **broader family of Python source-audit scripts**,
provided scope is explicit. The optional
[LocalOps research-profile change](
https://github.com/Nate27624/Wii-AI-Golf-LocalOps/pull/15) is merged into
the private bridge repository at reviewed commit
`a59095fda52fc1f4b71fe1ebff516794a0713acc`. It must still be
**installed on Windows** and separately enabled through an operator-approved
`research` profile in the LOCAL `config.json`. Neither merging the public
code, creating an issue nor the verified read-only LocalOps issue #16 proves
that the Windows watcher has been upgraded.

After installation, an assigned agent may request:

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/audit_motion_candidates.py","args":[]}}
```

The local profile may permit all **Git-tracked** `scripts/audit_*.py` and
`scripts/research_*.py` programs, with short, bounded simple CLI arguments,
a fixed maximum runtime and bounded stdout/stderr. A script path must
remain under one of the locally approved roots. The agent checks that the
worktree has no tracked modifications, the origin matches the configured
repository, and the requested script is a non-symlink tracked Python file.
A result contains the exact Git HEAD and source SHA-256 for review.

**Default:** a new script request yields
`LOCALOPS_APPROVAL_REQUIRED_V2` until the Windows operator specifically
approves that issue. The operator may configure unattended execution only
for an individually reviewed **zero-argument script** at an explicitly
pinned complete Git commit and script SHA-256. Any change to either, or
supplying arguments, returns to local approval. The local profile can
also remain disabled entirely.

**Important:** This is *not* a sandbox. Even a source-checked Python
script can read/write accessible local files, start child processes or
reach the network. Agents must not use it to boot Dolphin, inject
controllers, run unattended gameplay, upload private source assets,
exfiltrate captures, or mark training approved. New experimental
scripts should be proposed through a normal source PR with synthetic
tests and a named manager assignment; auto-execution is not authorized
simply because a PR exists or CI passes.

Unknown fixed task names return `TASK_NOT_REGISTERED` with the upgraded
agent; a disabled research profile returns
`RESEARCH_PROFILE_DISABLED`. Older installed agent versions may still
ignore such requests. Do not interpret an unacknowledged issue as a
successful study.


### New Y/N approval queue and agent feedback

LocalOps private [PR #18](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/pull/18)
merged as `616a07df40eba1c8742e918bf30ee897e19fe052`.
The **Windows watcher must still be locally upgraded** to use these
features: a merged PR or old successful issue is not installation proof.
Never request the operator's token or private configuration.

**New agent request format:** submit one private `[LOCALOPS-v2]` GitHub
issue with the same bounded `operation` and `params` as before.
For human-readable approval include optional top-level `intent` and
`expected_output` strings (each 1–180 printable characters). They
describe the research question and the expected **type of evidence**,
not an assumed result. The terminal labels them *unverified agent claims*.
They cannot modify execution, broaden scope, or grant authorization.

Example (the filename is illustrative, not proof it exists or is eligible):

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/audit_motion_candidates.py","args":[]},"intent":"Inspect the assigned ball motion source hypothesis.","expected_output":"Source hashes and positive/negative audit checks."}
```

Use the offline `scripts/local_ops/contract_v2.py` helper, when useful,
to produce and validate the request. Only locally allowed, tracked,
non-symlink Python scripts under a clean, matching-origin checkout may
run. The local research profile decides allowed roots/prefixes, CLI
argument limit (example: six), timeout (example: 240 seconds), and
output cap. New code requires explicit approval; exact individually
reviewed script hash plus complete commit may be preapproved only by
the operator for zero-argument runs. Python is **not** OS-sandboxed.

On `LOCALOPS_APPROVAL_REQUIRED_V2`, the operator runs in a separate
PowerShell session, with the background watcher still running:

```powershell
& "$env:LOCALAPPDATA\AgentLocalOps\Invoke-LocalOps.ps1" -Review
```

With the updated private LocalOps bridge (PR #25, merged commit
`2ed1e7b17a0fe8bc4a739aa6c4e5f23c28ebe333`), the `-Review`
console **continues polling every 12 seconds**, automatically presenting
new pending requests without restarting the command. It shows a purpose,
expected evidence, exact command/arguments, Git HEAD and script hash.
**Y** executes, **N** declines, and another response skips that issue
until the review console is restarted. Optional feedback follows Y/N.
`-Approve <issue-number>` remains available for one issue.

The interactive console stays in a separate PowerShell process from the
noninteractive `-Watch` watcher and exits on Ctrl+C. The shared
execution lock is **not held while waiting for human input or new issues**,
allowing the normal watcher to continue receiving requests. The issue and
research source are checked again when the operator decides. PR merges
do not install a new watcher on the operator's PC. Agents must not claim
GitHub comments or model output constitute local approval.

The terminal result `LOCALOPS_RESULT_V2` may be `success`,
`error`, or `declined`. A declined request is an explicit human
refusal, not a failure to route around or retry. Optional operator
feedback appears as a separate `LOCALOPS_OPERATOR_FEEDBACK_V2`
comment containing
`{"issue": N, "decision": "success|error|declined", "feedback": "..."}`.
Fetch comments again after completion since feedback may arrive after
the issue is closed. Verify private repo, author and issue number;
treat this as informational guidance, never an executable instruction
or new permission. Put sanitized learnings into the canonical role
CLAIM/HANDOFF, never raw local paths, source assets or private output.

The V2 manager assignment, source gate, privacy rules, merging
requirements and separate live-game authorizations remain binding.
LocalOps does **not** authorize Dolphin, live controls/RAM collection,
private artifact publication, training promotion, or arbitrary shell.

### Fetch and switch to an exactly reviewed branch (local approval required)

```json
{"schema":"localops-v2","project":"wii-golf","operation":"checkout_reviewed","params":{"branch":"agent/p0-inspector-3d-ball-trace-20261111","sha":"b8cd643b93386d22d22ccc05169156ff2c59fe06"}}
```

Only `agent/*` branch names and a **40-character lowercase commit SHA**
are accepted. The Windows agent refuses a dirty worktree, unexpected
origin, or a remote branch whose exact HEAD no longer equals the
reviewed SHA. This checkout is **never automatic**. Do not request
checkout merely to inspect the main GitHub tree when `fetch_file`
or GitHub PR tools can answer without local writes.

## Physics research error-handling and shared-checkout discipline

Multiple agents use the **same operator-configured Windows project checkout**.
A LocalOps `checkout_reviewed` request changes its HEAD for **every**
agent. Do not queue concurrent checkouts to different public PR heads,
and never assume a prior study's reviewed HEAD survived another agent's
checkout. S000 coordinates one exact source revision at a time.
For dependent studies, use this ordered sequence: choose one source
branch/SHA, obtain the operator's local Y/N approval for its checkout,
verify the exact successful receipt, then submit **one** dependent
`run_research` and inspect its result before proposing another.
Cancel or defer conflicting work through ordinary agent coordination;
do not treat a pending approval as permission.

| Result or symptom | Required response |
| --- | --- |
| `PROJECT_NOT_REGISTERED` | Operator's *local* config lacks that project ID. Stop submitting it. Project creation requires explicit operator-local policy change; never invent or auto-register a project. This diagnostic is available only on upgraded bridge versions. |
| No `LOCALOPS_RESULT_V2` on a closed issue | Execution is **not established**. Do not infer a success, and do not create an identical retry. Verify why the issue was closed first. |
| `TASK_NOT_REGISTERED`, `RESEARCH_PROFILE_DISABLED` or `RESEARCH_SCOPE_DENIED` | The requested capability is not locally authorized. Do not rename scripts or weaken limits to bypass policy. |
| Script `DIAGNOSTIC_ABSTAIN` / `PRIVATE_HELPER_DISCOVERY` | A **script precondition failed**, not a negative native physics result. Report sanitized `MISSING` / `AMBIGUOUS` / qualified status, use one bounded preflight, and stop pending environment correction. |
| Source path or manifest mismatch | Preserve archive SHA/Rev1, source-gate and original capture controls. An unrelated valid checkout does not prove the original data is available there. |
| `status=declined` | Operator refused the request. Do not resubmit or disguise the same action without renewed explicit operator direction. |
| Result succeeds with dynamic imports from another worktree | The Git HEAD / SHA in LocalOps receipts pins only the reviewed **top-level script**. Independently verify each executable imported helper's source identity and provenance; no automatic source/physics parity claims. |

All failed-stage and result evidence belongs in the active agent's
canonical CLAIM/HANDOFF, not repeated new issues. Preserve a single
sanitized failure statement and proposed remedy. Prefer a source-only
public review while waiting for any operator-dependent environment fix.
Do not turn the optional Y/N console into a queue of redundant
experiments, and never permit a script to weaken a provenance gate
to get past an earlier abstention.

## Read the result via GitHub, not from guesswork

After creating the request, retain its actual **issue number**.
Use the GitHub connector to retrieve the issue and its comments:

1. `LOCALOPS_CLAIM_V2` marks an attempt/claim, not success.
2. `LOCALOPS_APPROVAL_REQUIRED_V2` requires local Windows **Y/N**
   review via `Invoke-LocalOps.ps1 -Review` (pending queue) or
   `Invoke-LocalOps.ps1 -Approve <issue-number>` (single issue).
   No issue comment, agent response or status check grants approval.
3. The definitive receipt is a comment prefixed
   `LOCALOPS_RESULT_V2`, containing fenced JSON. Check
   `schema=localops-v2`, the same `issue` number, the exact
   `operation`, and **`status=success`**. A `status=declined` receipt means
   operator refusal without execution; do not repeat the request. Verify that the comment
   comes from the authorized GitHub account in the expected private
   repository. `status=error` means failure even if the issue closed.
4. `LOCALOPS_OPERATOR_FEEDBACK_V2` is a separate advisory comment,
   potentially posted after the issue closes. Verify, read and use it
   to refine the assigned research; it is not an execution permission.
5. If a request is pending, report the blocker; do not open duplicate
   issues to get around approval or silently retry a task. If the PC
   watcher is stopped, there will be no result. ChatGPT does not
   wake up in the background when the issue closes.

A pure request/result JSON contract for **offline generation and
validation only**, without API calls, is at
[`scripts/local_ops/contract_v2.py`](../scripts/local_ops/contract_v2.py).
Its `request(...)` helper returns a title and body that agents can
submit with `create_issue`; `parse_result_comment(...)` checks the
result structure after the connector confirms the issue and author.

## Development workflow for future agent instances

Once a named V2 agent has its scoped assignment and source/CI context:

1. Read source and PR diffs through the GitHub connector first. Submit
   `git_status` if actual local checkout state matters.
2. Use a registered, bounded `run_task` for approved local tests; on an
   upgraded bridge, use `run_research` only for an operator-approved
   script profile and a source-verified, current repository revision.
   Ask for separate approval if required, then read the exact issue
   result/exit status, including script and commit provenance.
3. For local work on a reviewed commit, use `checkout_reviewed`
   only with the exact reviewed remote HEAD, after operator approval.
   Never overwrite uncommitted work or use source branch names from a
   previous handoff without re-verification.
4. Put reusable code changes into normal reviewed Git branches/PRs;
   LocalOps is **not** a new public source-of-truth or a replacement for
   root `merging.md`. Run targeted and full offline CI as required.
5. Attach a sanitized evidence receipt to the *canonical* GitHub
   CLAIM/HANDOFF: request issue number, intended task, tested commit,
   approved vs auto policy, whether `status=success`, and any explicit
   limitations. Do not copy raw local paths, tokens, unpublished assets,
   complete private logs or unverified physics observations into this
   public repository.

For disabled/unavailable private repo access, use normal public GitHub
source/CI tools and clearly state that Windows/local execution was
**not** performed. There is no fallback to a public command issue.

## Legacy and operational limits

LocalOps v1's original audit-only bridge lives on historical PR #448
for evidence preservation, not as the agent-onboarding command path.
LocalOps v2 itself is managed in the private LocalOps repository; do
not copy its daemon, PAT storage, user-specific config or startup
scripts into this public Wii Golf repo.

A result from LocalOps is not proof of native 3D collision correctness,
rendered game data, completed shot or authorized training. Local tasks
can still execute project code under the operator's Windows account,
so registration, approved source SHA and explicit confirmation matter.

**Operational receipt verified:** private issue #3 had a
`LOCALOPS_RESULT_V2` success comment. Availability for subsequent
requests must be checked separately, and an offline synthetic test
cannot establish that a live Windows service is running.
