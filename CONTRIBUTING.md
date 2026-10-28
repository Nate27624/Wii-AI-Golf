# Contributing to Wii AI Golf

**ACTIVE operator rule (2026-10-27):** Every command an agent asks the operator to run MUST be a complete Windows PowerShell block (set repo directory, exact existing code, exit guard, safe output), NOT manual Dolphin, GUI or Git Bash. Reuse the source-validated A-button protocol and frozen S001 swing; never conflate the distinct A45 operations. Read [PowerShell operator contract](docs/operator-powershell-contract.md) and [repository map](docs/repository-map.md) BEFORE writing instructions. This rule overrides historical CLI/GUI examples and applies to all S000–S005 PRs.

This is **one project with multiple owned modules**, not independent competing golf launchers. Read [AGENTS.md](AGENTS.md), [research/README.md](research/README.md) and [docs/cli.md](docs/cli.md) before adding new scripts.

## Standard development commands

~~~powershell
py scripts/golf.py --help
py scripts/golf.py test
py scripts/golf.py test --pattern "test_unified_cli.py"
py scripts/golf.py demo
~~~

The source-local `scripts/golf.py` intentionally imports the **current checkout** without requiring `pip install -e .`. Existing specialized scripts remain compatible and are not to be deleted merely for style.

## Mandatory new-session read and rebaseline

**Every new or resumed agent MUST read** AGENTS.md, README.md ACTIVE header, docs/agent-session-protocol.md, docs/operator-powershell-contract.md, docs/repository-map.md, research/coordination.md, the relevant live owner issue/PR and actual source/tests before acting. Record an honest **read-attestation** and **Current baseline**: actual branch/head and reviewed status, study/P0 hypothesis, evidence source and last negative control, current blocker/owner, and next approved action. A different agent context does not inherit your live state or your cached GitHub status.

**Before every substantive reply**, reconcile the operator's newest terminal observation and refresh the relevant issue/PR/CI/branch evidence rather than trusting earlier messages. Keep the rebaseline concise and do not reread the entire repository for trivial replies. After substantial work, post a dated GitHub HANDOFF, with code revision, tests, safe uploaded observation (or NOT UPLOADED), verified/unverified facts, and next owner. See [mandatory session protocol](docs/agent-session-protocol.md).

## Adding functionality

1. **Claim a scope** on its GitHub issue before editing shared code. Work in an isolated `agent/<role>/<slug>` branch; do not overwrite another agent's files or rebase their branch without coordination.
2. **Put domain logic in its owned module** (`integration/`, measurement/audit, modeling, learning). Reuse the existing Felk RPC and canonical menu sequence; never introduce competing hardcoded A/A+B/A startup timings.
3. **Expose a CLI adapter** through `src/wii_ai_golf/cli.py` only if the tool is useful to operators. Delegate to a vetted existing entrypoint or a narrow module API, rather than copying behavior. Keep safe read-only operations offline and clearly label live mutations.
4. **Add tests** in `tests/`: CLI help and source-local imports under `python -I` / fake stale install; dry-run must not launch; live commands must reach the canonical launcher once; child cannot secretly reset or double-launch; pass flags/exit status faithfully.
5. **Record evidence**: study ID, source (synthetic/human/live game/verified measurement), exact action, attempt budget, failures and saved artifact provenance. A bridge ACK or gauge screenshot isn't a score.
6. **Review and merge a PR** with exact commands/tests actually run. Do not claim a Windows Dolphin test ran merely because Python mocks pass on another machine.

## Documentation conventions

- `README.md` is the high-level single project overview; `docs/cli.md` is the **canonical operator command reference**.
- `docs/architecture.md` defines layers; `docs/milestones.md` defines current acceptance gates.
- `research/README.md` is the shared study lifecycle; `research/queue.jsonl` is a proposed-study manifest, not a live execution queue.
- `research/ledger.md` is append-only history; do not erase old failures to make present status look cleaner.
- Detailed agent-specific research notes stay under their owned folder, with links to shared canonical docs rather than standalone conflicting startup scripts.
- Keep personal Dolphin game paths, savestate catalogs, traces, ROMs, screenshots and binaries out of Git (local `Wii-AI-Golf-Data`).

## Required automatic result handoff

Every user-run research/test command must **automatically upload an approved sanitized result** to GitHub's separate research/observations branch by reusing the existing research_cli.py publisher, unless the operator explicitly opts out or the privacy gate blocks publication. A new offline P0 analyzer that cannot do this is **not yet operator-ready**: implement a reviewed typed uploader adapter first, then test allowed, rejected and failed-upload cases without a live game.

Do not upload raw memory banks, PRIVATE reports, original per-frame traces, ROMs, savestates, pointers or local paths. Record failures and negative findings as carefully as successes. Post a dated **FINDING** in the owning issue/PR with study/run ID, sanitized record URL (or NOT UPLOADED), controls, source/evidence classification, limitations and next agent; preserve material conclusions in research/ledger.md through reviewed changes. The publisher must preserve local sanitized output on failure rather than requesting manual uploading.

## PR checklist
- [ ] New-agent read-attestation checked all ACTIVE rules and relevant owner issue/PR; does not claim unseen evidence was read
- [ ] Current baseline re-established against latest branch/head/CI and user terminal output before changes or user instructions
- [ ] Context-switch HANDOFF published with exact commit/tests/blocked gates/next owner and no fabricated live state
- [ ] Existing trusted publisher automatically posts safe result from the SAME operator command, or agent states and resolves the missing integration before operator use
- [ ] Significant positive/negative P0 findings are in owning issue/PR and linked research/ledger.md entry (or documented pending owner-reviewed integration)
- [ ] Privacy allowlist and upload-failure tests/handling: no native RAM or PRIVATE results in Git; distinguish UPLOADED from NOT UPLOADED

- [ ] Operator command is one fully copy/paste-ready PowerShell block, auto-cd + `$LASTEXITCODE`, or explicitly no action; no GUI/manual Dolphin/Git Bash
- [ ] Reused the canonical, proven S001 launch/menu and source-frozen 89-sample swing; distinguished A45 menu / A-prime / V1 lead / trace-neutral / follow-through semantics without swapping implementations
- [ ] Cross-owner changes, overlapping PRs and draft-only commands identified; source/privacy/live authorization gates checked

- [ ] Claimed paths and nonoverlapping agent ownership
- [ ] User-facing command is consistent with `golf` or documented advanced-only
- [ ] Focused/full tests listed with **actual** results and limitations
- [ ] Canonical fresh boot/intro and source-local import regressions covered
- [ ] Distinction between synthetic, user-observed, RPC-ack and validated score
- [ ] Study hypothesis, attempts/failures, holdout procedure and versioned evidence
- [ ] No secret, copyrighted game asset, personal path or accidental savestate write
