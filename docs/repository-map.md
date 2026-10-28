# Repository map and source-of-truth hierarchy (ACTIVE)

This page is the structural starting point for human operators and S000–S005 agents. It is a map of **responsibilities and lifecycle**, not permission to run any live game action. For operator response format, read [PowerShell operator contract](operator-powershell-contract.md) FIRST. For source-specific safety/merge requirements, read AGENTS.md and docs/merging-requirements.md.

## Where things live

~~~text
D:\Projects\Wii Golf AI\
|
+-- Wii-AI-Golf\                          ONE Git code repository (reviewed main)
|   +-- AGENTS.md                         Mandatory agent contract; current rules are at top
|   +-- README.md                         Operator start-here and project overview
|   +-- scripts\
|   |   +-- research_cli.py               Maintained sync/test/V1 result-sharing entrypoint
|   |   +-- golf.py                       Broader source-local CLI / offline inspection
|   |   +-- run_golf_experiment.py        Single canonical fresh-boot experiment dispatcher
|   |   +-- launch_golf.py                S001 Dolphin/controller/state startup
|   |   +-- launch_hitting_green.py       S001 source-owned menu intro
|   |   +-- collect_outcome_transition.py S002 same-shot result/candidate collector
|   |   +-- probe_swing.py                S001 experimental guarded swing internals
|   |   +-- *private.py                   Research-only offline readers, when merged/reviewed
|   +-- src\wii_ai_golf\
|   |   +-- integration\                  S001 Felk RPC, savestates, controller trace
|   |   +-- menu_sequence.py              S001 fixed A -> wait -> A+B -> release -> A
|   |   +-- audit\                         S002 read-only local RAM/outcome investigations
|   |   +-- lab\                           Historical/underlying typed helpers; GUI retired
|   |   +-- cli.py                         Existing source-local golf.py command routing
|   |   +-- evaluation.py, agents.py       Synthetic research scaffolding unless verified
|   +-- tests\                             Regression tests; synthetic != real emulator proof
|   +-- research\
|   |   +-- studies\                       Proposed protocols and private-data instructions
|   |   +-- queue.jsonl                   PROPOSALS, never a live autonomous work queue
|   |   +-- ledger.md                     Historical findings, evidence and open caveats
|   |   +-- claims\                       Agent ownership records; issue comments authoritative
|   |   +-- experiments.json              Shared typed Lab registry (may include historical)
|   |   +-- observations\                  SANITIZED GitHub branch results, not native RAM
|   |   +-- launch.local.json             Local ignored game/config values; do not commit
|   |   +-- savestates.local.json         Local ignored *slot labels*, not save bytes
|   +-- docs\
|   |   +-- operator-powershell-contract.md  NEW precedence/output/safety rules
|   |   +-- repository-map.md             THIS current map and role/branch structure
|   |   +-- cli-only-workflow.md          Maintained research CLI lifecycle
|   |   +-- cli.md                        Broader golf.py commands + historical experiments
|   |   +-- merging-requirements.md       Owner review/test/self-merge safety checklist
|   |   +-- cross-agent-cooperation.md    SPOCOC shared-interface and handoff ownership
|   +-- .github\workflows\                Hosted synthetic CI; not a Dolphin session
|
+-- Wii-AI-Golf-Data\                     PRIVATE sibling raw observations / MEM1/MEM2
|   +-- ball-study-20261027-212633\       Existing B0-B3 paired no-shot study
|   +-- captures\                         Private trial/candidate RAM reports
|   +-- research-cli\                     Local allowlisted result records
|
+-- tools\                                Local Dolphin/bridge installations, NOT Git
    +-- FelkDolphin-Clean\                Reviewed isolated clean Dolphin + User
    +-- FelkDolphin\                      Historical installation; do not fall back blindly
    +-- mcp_bridge_swing_legacy_eval.py   Separate isolated source-verified V1 bridge
    +-- mcp_bridge_swing.py              Existing bridge; its revision must be inspected
~~~

This tree illustrates expected locations, not proof every optional artifact currently exists. A named savestate catalog entry is **not** proof the clean Dolphin User contains that save. Other isolated worktrees are developer checkouts, not the live operator runtime. No raw game RAM, DOL/ROM images, savestates, generated bridge source or secrets belong in Git.

## One canonical path per responsibility

| Operation / proof | Preferred entry or canonical source | Owner | Never do instead |
| --- | --- | --- | --- |
| Research sync/test and sanitized summary | scripts/research_cli.py, docs/cli-only-workflow.md | S000 | Invent GitHub tokens / custom unreviewed publisher |
| Source-local doctor, state read-only, broad CLI | scripts/golf.py | S000 | Launch new GUI, shell dashboard or clone a CLI |
| Live experiment fresh boot | scripts/run_golf_experiment.py -> scripts/launch_golf.py | S001 | Start Dolphin manually, copy A/A+B/A delays |
| Physical savestate load/menu navigation | launch_hitting_green.py, menu_sequence.py, StateCatalog | S001 | Load guessed slot / overwrite save |
| Controller trace / A setup / swing | wii_ai_golf.integration, source-pinned current trace | S001 | Reimplement a waveform, alternate RPC or A45 meaning |
| RAM memory audit / ball-to-target measurements | S002 source-gated studies, read-only offline scripts | S002 | Dump random pointers to public Git |
| Actual result / units / censored outcomes | S002 outcome capture/evidence gate | S002 | Interpret 100-ft penalty as real carry |
| Motion/power calibration | S003 consumes S001 traces + S002 outcomes | S003 | Label unverified RAM field as true club speed |
| Learned policy optimization | S004 | S004 | Optimize against invented Wii Sports scores |
| Held-out experiments | S005 | S005 | Treat a tuned shot as an unseen test |
| Coordination/contracts/merge order | AGENTS.md + GitHub issue/PR threads | S000 | Assume parallel chat agents share state |

An existing public CLI wrapper may delegate to an older internal script. **That is allowed and required**: there is one underlying canonical launch/state/controller implementation, not one Python filename for every operation.

## New agent context — read and refresh, don't guess

Any **new or resumed** S000–S005 agent starts with root AGENTS.md and README's ACTIVE NEW AI AGENT section, then [docs/agent-session-protocol.md](agent-session-protocol.md), the PowerShell contract, this map, research/coordination.md and current owning GitHub issue/PR/HANDOFF/FINDING. It must READ, not merely cite, and attest only to materials actually checked. **Every substantive reply** re-establishes a concise Current baseline from newest operator evidence and current relevant branch/head, PR/CI, source/claim owner, exact validated swing protocol, evidence gate and next action. Unknown state = NOT CHECKED, never inferred from a different chat. Post dated HANDOFF for future contexts. See the mandatory session protocol for precise fields and limits.

## Which source of truth wins?

1. **Latest direct operator instruction** (for this project, CLI only and paste-ready Windows PowerShell).
2. **Current AGENTS.md top section + docs/operator-powershell-contract.md** for operator interactions and validated-method reuse.
3. **Merged main code/tests and current docs/cli-only-workflow.md** for actual available flags, not speculative PR instructions.
4. **Canonical owner / live issue+PR claim** for proposed future changes, conflict resolution and evidence gates.
5. **Historical runbooks, old GUI guides, 2026-10-24 experiments, demo code** for research history only; cannot overrule active operator rules or give permission for manual Dolphin actions.

The main branch may not yet contain a draft feature. Do not pretend a draft PR is already present on the user's main checkout. Use separate, exact, read-only worktree commands for unmerged offline investigation only when truly needed.

## Results: automatic GitHub upload and research memory

**A local run is not the end of the workflow.** For every approved operator test or experiment, the existing canonical research_cli.py path must automatically publish a **SANITIZED, allowlisted** result to the dedicated research/observations branch in the SAME operator command (unless a user explicitly selects --no-upload or privacy gates reject publication). For a novel study without a reviewed publisher adapter, S000/S002 must first extend the one existing publisher and test the exact workflow; agents must not quietly tell the operator that a private-only script has auto-upload.

- **Local data:** Wii-AI-Golf-Data holds full/private observations and snapshots; never push native RAM, source memory pointers or local file paths.
- **Published result:** research/observations is a separate Git branch for automatically uploaded safe study/run metadata and bounded outcome fields, NOT a copy of the local captures directory.
- **Important finding:** date-stamped GitHub FINDING comment in the owning S001–S005 issue/PR with study/run ID, sanitized result URL (or NOT UPLOADED), evidence class, positive/negative finding, controls, caveats and next owner.
- **Durable science:** update research/ledger.md through the owner's reviewed PR/integration, linking the finding and source result without overwriting other agents' entries.
- **Publication failure:** preserve the sanitized record locally and report the problem clearly, rather than asking the operator to upload raw data or claiming a GitHub artifact exists.

Automated results upload **does not** mean unattended Dolphin control, silent Git force-push, model training approval, or unrestricted private-data publication. S000 owns the publisher/schema contract; S002 reviews scientific provenance. See the active docs/operator-powershell-contract.md for exact operator response requirements.

## Study/workstream status and branch rules

- **main:** reviewed code source for operator; may contain stale historical docs until this rule PR lands. Never push feature changes directly.
- **agent/<role>/<slug>:** isolated feature/research branch. Open a draft PR, post exact tests and what was NOT validated, coordinate collision paths and seek canonical owner acknowledgement.
- **research/observations branch:** only existing allowlisted small sanitized result records, not raw captures. Code must not be merged here.
- **Wii-AI-Golf-Data:** local raw snapshots, full 51-word arrays, exact private numeric vectors, before/after memory and any secrets; do not publish.
- **S001–S005 and GitHub Issues #2–#6:** actual agent ownership and cross-agent decisions; issue #121 coordinates current P0 memory/contact research. **queue.jsonl does not run a task.**

### Current P0 sequence

Existing source-selected no-shot aim and candidate start/pin geometry are useful but do NOT certify physical axes, game power or ball velocity.

1. S001 reviews clean Dolphin + existing named save **physical presence**, one frozen prior controller trace and no-watch one-shot visible ball contact. Old/GUI launch recipes are not permitted.
2. S002 reviews source-gated same-shot monitored selected player/ball record (#166/#189), negative controls (#191), independent trace-to-memory link (#193), before/after/settled/result outcomes (#180/#184/#185), and no false training claims.
3. S000 validates output privacy/public schema and P0 field-evidence dictionary; S003 holds training until real independently validated outcomes; S004/S005 remain downstream.

Open PRs can change status at any time: always recheck real issue/PR state before calling something merged or live-ready.

## Explicit agent review checklist before asking operator to act

- Can I satisfy the request using an **already merged** existing script without rewriting S001's launcher or 89-sample waveform?
- Does my answer include **one PowerShell block** with Set-Location, exact path/flags, preflight and exit-code checks? Or explicitly say no local action?
- Have I distinguished 45 menu-final-A, 45 A-prime button-only, 45 V1 A-lead and 45 trace-held samples? No substitution by equal numbers.
- Is the action offline/dry-run/live clearly labeled? For live, do I have S001/S000 review, one canonical fresh launch, real named checkpoint and human opt-in?
- Have I checked the current claim/PR to avoid duplicating or clobbering another agent's code?
- Will the operator's output be a safe summarized result rather than raw native RAM? Can I distinguish human-observed from physics verified?

If any check fails, **fix the code or stop and report the blocker**, rather than telling the operator to operate Dolphin by hand.
