# Wii AI Golf — authoritative V2 agent operating contract

**Start here:** [V2 navigation](docs/v2-navigation.md) → [agent charter](docs/v2-agent-charter.md) → [evidence gates](docs/v2-evidence-gates.md) → [agent continuity / succession](docs/v2-agent-continuity.md) → root [`merging.md`](merging.md). These are the only authoritative V2 onboarding/ownership/merge procedures. Verify live main, actual CI, current GitHub CLAIM/HANDOFF and overlapping PRs before interpreting any dated document as current.

**Precedence:** root `merging.md` controls merging; `docs/v2-agent-charter.md` controls S000–S005 role boundaries; `docs/v2-agent-continuity.md` controls CONTINUE/HANDOFF; the operator must separately authorize any live game action. Historical workflow documentation in [the archived AGENTS snapshot](docs/archive/AGENTS-pre-v2-20261029.md) and [README snapshot](docs/archive/README-pre-v2-20261029.md) is *not* an active order. It preserves prior GUI/launcher requirements and research context; do not resurrect obsolete implementations from it.

## Roles and ownership

| ID | Owner | Canonical responsibility |
| --- | --- | --- |
| S000 | Architecture / integration / consolidation | Repo interpretability, PR disposition, shared contracts, status and operator questions |
| S001 | Dolphin runtime / control | Clean startup, controller, atomic A45, trace/bridge identity |
| S002 | Memory measurement / provenance | Original archive validation, selected/source-global candidates, shot identity |
| S003 | Swing modeling | Action parameterization, sensitivity and predictive candidates |
| S004 | Optimization and training | Fitting/optimization **only** with eligible verified records |
| S005 | Evaluation | Censoring, held-out baselines, acceptance and failure cases |

Use a globally *distinct* `S00N-name` instance label in GitHub comments; an existing GitHub login does not identify an agent. `scripts/agent_init.py` is a read-only local helper and **does not reserve** an identity. S000 may coordinate questions and collisions, but is not a discretionary approval requirement for an objectively merge-ready PR.

**Operator prompts:** use the three [universal V2 INIT, CONTINUE and HANDOFF prompts](docs/v2-universal-prompts.md), not separate instructions for each role. Same-chat continuation preserves the agent's identity; a successor gets a freshly generated complete prompt.

**First manager roster:** An already authorized S000 Manager with a
verified coordination CLAIM publishes the first exclusive assignment roster
before agents begin new tasks; that manager is the bootstrap authority and
does not wait for a roster entry assigning itself. All other agents PARK or
continue only independently verified prior claims. See
[continuity](docs/v2-agent-continuity.md) and manager playbook.

## Adaptive task selection

Before a NEW agent begins, check the newest manager `[S000-manager] ASSIGNMENT ROSTER V2` AND the advisory `[S000-manager] PRIORITY BOARD V2` on [coordination PR #320](https://github.com/Nate27624/Wii-AI-Golf/pull/320), fresh `main`, live issue CLAIM/HANDOFF notes, and overlapping open PRs. The priority board is NOT an assignment. Only the S000 Manager issues a unique role/instance, task, owner thread and bounded file scope in the assignment roster. New agents without a matching roster entry request allocation on #320 and PARK; never self-assign competing code. Use `python scripts/agent_init.py --mode suggest --live` as an optional read-only CLI if authenticated `gh` exists. For the SAME chat, `--mode continue --role ROLE --instance EXISTING --live` retains identity, finishes the existing claim first, then requests a new exclusive manager assignment rather than selecting from the priority board. If live data are unavailable, abstain rather than invent a current priority or approval. See [dynamic workflow](docs/v2-agent-continuity.md).

## Required agent procedure

1. Read current main and `docs/v2-navigation.md`, `docs/v2-agent-charter.md`, `docs/v2-agent-continuity.md`, and `merging.md`; inspect the live issue/PR queue and existing role claims. For memory work also read `research/memory-variables/README.md` and `research/memory-variables/registry.json`.
2. Accept one manager-assigned falsifiable bounded objective and the **existing** canonical owner issue or PR. Post `[INSTANCE] CLAIM` with owned paths, inputs/outputs, tests, evidence limits, dependency and overlap checks. Do not silently overwrite another agent's branch or create duplicate reader/launcher/publisher/GUI implementations.
3. Perform substantive research or code work, including positive/negative controls. Preserve original reports, SHA/source identity, falsified hypotheses, and unknowns. A research-only finding belongs in an existing GitHub thread, not a new PR solely for one note.
4. For code changes: focused tests, full `python -m unittest discover -s tests -v` at exact head, configured Windows/Ubuntu CI and privacy/compatibility checks. No direct main commits or forced shared-branch updates. Merge own non-draft work **only if every applicable root `merging.md` check passes**, then post merge SHA.
5. Post `[INSTANCE] HANDOFF` with exact branch/head/main SHA, changes, executed tests/CI URLs, disposition of other PRs, limitations, blockers, and next owner. End each user-facing response with exactly one CONTINUE / ACTION REQUIRED / DECISION REQUIRED operator status.

## Continuation and chat succession

- `CONTINUE V2` in the **same chat**: keep agent ID and work scope; reread latest canonical GitHub handoff and continue.
- `HANDOFF V2`: outgoing agent posts `[OUTGOING] SUCCESSION HANDOFF` on its existing canonical issue/PR (verify thread live), chooses a **new** successor instance in the same role, and returns one complete copy-ready prompt for a new chat. Existing `scripts/agent_handoff.py` prints a structured GitHub comment and standalone successor prompt, optionally with `--handoff-url` pointing to the posted comment. Operator, not the script, starts the new ChatGPT conversation; successor posts its own distinct CLAIM.
- A GitHub comment is durable coordination, **not** a background agent, live notification, or consent to launch Dolphin. Do not suggest otherwise.

## Evidence, privacy and runtime boundaries

- No private ROMs, RAM, savestates, captures, secrets, per-boot addresses, personal paths/configs or unrestricted logs in Git, PRs, comments or public artifacts. Use source-relative locators, immutable source/archive SHA checks and allowlisted sanitized conclusions.
- A successful CI, bridge RPC, frame callback, game-ready screen, human-described contact, score display, game physics frame, real ball XYZ and training eligibility are **separate evidence gates**. Synthetic tests establish synthetic behavior only. Training flags remain false until a verified data contract and independent evidence allow promotion.
- An off-green 100-foot displayed penalty is **censored**, not a measured carry; do not fit models to it as physical distance. Preserve the original seven-phase D1 airborne-versus-START contradiction and selected/global source distinction.
- Live Dolphin launch, game input, real shot, private capture, publication of private results or unattended runs always need **separate explicit operator authorization**. Historical commands and even `CONTINUE V2`/`HANDOFF V2` are not consent.
- V2 agent work is **CLI-first**; the canonical public CLI is `scripts/golf.py` and research orchestration is `scripts/research_cli.py`. Historical Lab/GUI implementations may be retained for provenance but are not a new V2 development requirement. Avoid new parallel interfaces.
- Source auditing may use existing private original captures locally only with approved, pinned, read-only scripts and original SHA/revision/identity gates. Do not ask for repeated bank captures when preserved evidence answers the question. No unstated local scripts, source rewrites or auto uploads.

## Historical evidence and PR cleanup

[Historical PR family/retention ledger](docs/v2-pr-triage.md) is a dated index, not proof an open PR is still active. Disposition an old PR only after inspecting its full diff, tests, original source blobs, current on-main files, GitHub comments and owner. Preserve unique reports and negative results with immutable links before closing, **without deleting the historical branch**. Never mass-close by title, age, or count. Current main has selectively integrated #331/#337/#329 and downstream result/privacy guards; source-only proof does not imply physical ball tracking or training readiness.

**Legacy material preserved in full:** [archived AGENTS](docs/archive/AGENTS-pre-v2-20261029.md) and [archived README](docs/archive/README-pre-v2-20261029.md). Their old GUI/launch details, operator experiments, and research caveats remain available for historical verification, but the V2 charter and safety/merge gates take precedence.
