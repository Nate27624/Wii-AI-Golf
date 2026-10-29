# V2 Consolidation Charter (proposal — not yet merged)
 
## Mission and boundaries
Recover a minimal CLI-only shot → source-validated observation → result → eligible training record pipeline. Keep existing main unchanged until all acceptance gates pass. No ROM, raw RAM, savestate, private path, secrets, or captured data in Git. Existing original captures stay local; do not solicit repeat captures unless a precise falsification gap is proven. No unattended live swing or publication.

## Agent identity and ownership
Use stable **role IDs**, never GitHub login as identity (multiple agents can share an account). At initialization select the one role assigned by operator, then choose a distinct `instance_id` (e.g. `S002-memory-a`). Include `[S002-memory-a]` prefix in GitHub comments and handoffs.

| ID | Role | Owns | Must not change without review |
| --- | --- | --- | --- |
| S000 | Coordinator/integrator | Architecture, PR queue, shared contracts, branch promotion | S001/S002 implementation |
| S001 | Runtime/control | Clean Dolphin startup, atomic A45, swing trace, live timing | S002 memory/outcome semantics |
| S002 | Measurement/provenance | SHA-gated snapshots, typed memory, shot identity, visual ↔ RAM hypotheses | S001 live controller |
| S003 | Modeling | Swing parameter representation, sensitivity, predictive candidates | Source measurement or live runtime |
| S004 | Optimization/training | Baselines and fitting gated on eligible verified records | Declare unverified data trainable |
| S005 | Evaluation | Held-out scenarios, ranking/censoring, acceptance tests | Change producer contract unreviewed |

Only S000 integrates cross-domain contracts; domain owners review contract changes. One integration PR per shared module, at most two active per instance. No new research PR just to record one observation.

## Initialization contract
1. Run `python scripts/agent_init.py --role S002 --instance S002-memory-a` (substitute role/instance); read its printed charter and checks.
2. Fetch latest `main`, inspect open PRs and `docs/p0-pr-consolidation-lanes.md`, read `docs/merging-requirements.md` and this charter.
3. Post `[INSTANCE] CLAIM` on the existing owner PR/issue: specific input, output, paths, contract, overlap check and expected test.
4. Do exactly one self-contained task. No competing UI, launcher, memory scanner or PowerShell replacement.
5. Post `[INSTANCE] HANDOFF` containing branch/head, changed paths, tests and exact SHA, evidence confidence, blockers, and next owner.
6. Do not merge without exact-head full offline tests, required reviews, clean ancestry, non-draft/branch protection. No force-push and no direct changes to main.
 
## Consolidation stages
- Stage A: Archive baseline commit/branches/PR references; classify each as integrated, reusable code, evidence-only, superseded, active. Preserve history.
- Stage B: Extract minimal source readers, startup/controller and result-first handling *selectively* from current main and reviewed branches; avoid wholesale stacked merges.
- Stage C: Establish one canonical shot identity & observation schema, typed finite coordinates with negative controls, terminal-result censoring.
- Stage D: Validate focused and full offline suite, human-supervised single-run live test only with explicit separate operator authorization.
- Stage E: Promote only after parity and safety review; close superseded PRs with evidence links, without deleting their branches.

## Acceptance gates
- Single known-clean Dolphin startup (not launched automatically by agent_init), atomic A45 callback + original waveform only when operator opts in, no duplicated launcher.
- B0/B1 archived samples original SHA-gated, D1 airborne==START contradiction documented, W5/W6/W7 selected translation motion vs stable controls retained, source-global object evaluated separately. No claim of world XYZ or velocity without frame/visual proof.
- Shot/run identity joined across action, observation, screen outcome; 100-ft off-green penalty censored, never treated as measured carry.
- No private data publication, no synthetic observations labeled real, training_approved=false until separate approval.
- Fail closed on missing identity, provenance, phase, frame, or uncertainty. Tests report which checks actually ran, including Windows and Ubuntu where required.

## Coordination and scope
Use the existing parent PRs: #231 seven-phase; #240 global-pointer; #163 baseline; #223 airborne; #219 callers; #315 timing; #310 crash diagnosis; #205 registry. Leave research-only findings on canonical parents. A new PR requires a unique executable change and explicit owner approval. This charter itself is an **isolated proposal**, not an architecture migration or authorization to merge/close any existing PR.
