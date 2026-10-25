# Standing authorization and safety policy for AI research agents

The operator permits agents to work independently on **routine low-risk development** without requesting approval for every change. This is not blanket consent for every action on the host.

## Autonomy by risk

**Proceed without asking:** inspect source/issues, propose experiment manifests, run unit tests and synthetic/offline analyses, create branches and PRs, update non-sensitive docs, implement narrowly scoped reviewed code, fix normal test failures, and merge low-risk PRs that pass applicable checks with no conflicts or ownership disputes. Inform other agents in the shared issue/ledger.

**Ask operator before:** any fresh live Dolphin run or controller movement (unless operator has explicitly started the exact live trial in Golf Lab), changes to ROM/savestates/game files, overwriting data, moving or deleting private local captures, broad filesystem writes, privileged/system changes, purchases or cloud costs, installing executables, credential changes, publishing private data, and training likely to consume substantial GPU/CPU or long unattended host time. A live experiment started via the UI is permission for *that one run* only; it is not permission for repeated autonomous swings.

**Never automatically:** fetch and execute arbitrary code from unmerged PRs or JSON manifests; force push, reset or delete another agent's branch; bypass validation or safety prompts; modify game memory when only read-only capture is authorized; upload ROMs, savestates, raw memory, personal paths or secrets; label a process ACK as ball contact or score.

## Package design contract

1. One installable Python package under `src/wii_ai_golf`; one operator entry `py scripts/golf.py` and Golf Lab UI. Domain modules own algorithms. No extra competing Dolphin launchers.
2. Experiments enter the canonical `research/experiments.json` registry with stable id, agent owner, explicit offline/live/planned mode, typed reviewed kind, documented input/outputs, evidence source and reproducible tests.
3. UI **Sync reviewed** pulls only merged `origin/main` on clean local main. Restart UI to load new code. Newly published PRs do not execute themselves.
4. UI **Run safe batch** runs only hardcoded zero-input offline tests/demos; source list is an allowlist independent of manifest descriptions. A new kind is not auto-executable until a code change and tests approve it.
5. Live actions require explicit click/confirmation for one run, a fresh canonical Dolphin startup, a single bridge, named existing checkpoint, manual tee gate when needed and complete per-run provenance. No background live queue.
6. Research claims distinguish synthetic/mock/human-observed/live-game/independently verified. Negative findings remain in history. The camera-sensitive `golf_field +0x04` player shadow is excluded from ball-ground-truth labels.
7. All PRs must run relevant tests; no success claims without real output. Low-risk changes may be merged independently when tests and branch ownership checks pass. Shared API/schema/startup changes require collaboration and compatibility review.
8. When instructions are ambiguous, choose the non-destructive offline option first. Ask concise clarification if an essential safety boundary is unclear, not for routine implementation preferences.

## Workflow

Agent proposes study → code/test in owned branch → PR with honest validation → merge low-risk reviewed work → Golf Lab **Sync reviewed** → restart → execute offline allowlisted batch. User intentionally launches individual live trials. Record results in the lab and shared evidence ledger.
