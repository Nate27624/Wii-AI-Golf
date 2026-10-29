# Wii AI Golf — V2 agent research and consolidation

Build a reproducible Wii Sports Golf research pipeline from **Dolphin control → verified shot identity → provenance-gated observation → outcome → eligible training evidence**. **The full real-game pipeline and trainable ball coordinates are not yet verified.** Passing offline tests does not establish a real strike, game score, physical ball XYZ/velocity, or learning success.

**Operator copy/paste:** [Three universal prompts — INIT, CONTINUE, HANDOFF](docs/v2-universal-prompts.md). Use the *same* prompt for every role; each agent checks S000’s current coordination board and its own claims.

> **New agent?** Start at [V2 navigation](docs/v2-navigation.md), then read the [role charter](docs/v2-agent-charter.md), [agent continuity / successor handoff](docs/v2-agent-continuity.md), and root [self-merge policy](merging.md). These are the current V2 operating rules. Always check live `main`, GitHub claims, and CI; documentation is not a live PR dashboard.

## Current V2 operator contract

**V2 work is CLI-first and has one maintained implementation per behavior.** The canonical public CLI is `scripts/golf.py`; `scripts/research_cli.py` is the reviewed result-first research orchestration entry point. Legacy Python scripts are implementation details, source-review utilities, or historical experiments—not interchangeable user-facing launchers. A prior Lab GUI exists in repository history, but it is **not the V2 agent onboarding path or a requirement for new features**. Do not rebuild its retired workflow merely because historical documentation mentions it.

The authoritative operating rules are:
- Root [`merging.md`](merging.md): objective self-merge gates; current-main ancestry, exact-head full offline CI on configured platforms, compatibility, evidence/privacy, non-draft, no actionable overlap. No arbitrary extra manager approval.
- [`docs/v2-agent-charter.md`](docs/v2-agent-charter.md): S000–S005 roles and ownership. A GitHub CLAIM is a coordination record, not a daemon or lock.
- [`docs/v2-evidence-gates.md`](docs/v2-evidence-gates.md) and [memory registry](research/memory-variables/README.md): what has been shown, what is still uncertain, and what is *not* trainable.
- [`docs/v2-pr-triage.md`](docs/v2-pr-triage.md): historical PR families and evidence-preserving retirement policy; verify live state first.

## Safe local entry points (from your checkout)

```powershell
py scripts/golf.py --help
py scripts/golf.py doctor
py -m unittest discover -s tests -v
```

A local read-only research test can be performed with `py scripts/golf.py research test --local-only`. Other `research` commands may sync or publish **allowlisted** summaries; inspect the command and its permissions before running. The `research/observations` Git branch stores sanitized status—not physical shot evidence or a GitHub agent notification service.

**No agent may start Dolphin, issue controller inputs, collect private captures, publish private material, or conduct unattended shots without separate explicit operator authorization.** Do not upload ROMs, raw RAM, savestates, credentials, per-boot heap addresses, personal paths/configuration, or unrestricted logs. Human-observed outcomes are not machine-verified scores. An off-green 100-foot penalty is **censored**, never measured ball carry.

## Agent workflow

**Dynamic priority selection:** On each `INIT V2` or `CONTINUE V2`, inspect the newest [S000 manager priority board on coordination PR #320](https://github.com/Nate27624/Wii-AI-Golf/pull/320) and *live* claims/PR overlap rather than following a frozen task list. Suggestions do not reserve files or ID. The local read-only helper supports `python scripts/agent_init.py --mode suggest --live`, `--mode init --role S002 --instance S002-memory-c --live`, and `--mode continue --role S002 --instance S002-memory-c --live`; with no GitHub CLI connection, agents should use GitHub connector evidence and verify manually. Same-chat continuation must preserve the existing instance and active claim.

| Workflow | What happens |
| --- | --- |
| New agent | Use the operator's existing V2 initiation prompt; pick an unclaimed role-specific instance ID; read canonical docs and GitHub claims; post `[INSTANCE] CLAIM`. If a local checkout exists, run `python scripts/agent_init.py --role S002 --instance S002-memory-a` with a *unique* ID. |
| Continue same chat | Operator sends `CONTINUE V2`; agent keeps its ID/scope, checks current `main` and handoffs, and does substantive work. |
| Context-limit replacement | Operator sends `HANDOFF V2`; outgoing agent posts a complete `[OLD] SUCCESSION HANDOFF` in its existing canonical GitHub thread. `scripts/agent_handoff.py` can produce a **complete standalone new-chat prompt** using a distinct successor ID and optional posted-comment permalink. Only the operator opens the new conversation; successor posts `[NEW] CLAIM`. |

Read [full continuity rules](docs/v2-agent-continuity.md). Never assume a posted GitHub comment automatically awakens another chat.

## Repository map

| Location | Purpose |
| --- | --- |
| `scripts/golf.py` | Public source-local CLI |
| `scripts/research_cli.py` | Result-first offline/live research orchestration with publication gate |
| `scripts/agent_init.py`, `scripts/agent_handoff.py` | Read-only initialization and successor prompt generation |
| `src/wii_ai_golf/` | Core package, runtime integrations, audits, models, evaluation |
| `research/memory-variables/registry.json` | Stable, source-backed memory field registry and training-eligibility flags |
| `research/studies/`, `research/ledger.md` | Provenance-limited findings and historical negative results |
| `docs/v2-*.md`, `docs/S000-manager-playbook.md` | Canonical V2 navigation, evidence, coordination and retention rules |
| `tests/`, `.github/workflows/` | Offline regression tests and platform validation |

## Verified limits and current dependencies

The original seven-phase SHA-gated **offline** reader was selectively merged via #331; the distinct source-global/roster reader via #337; original B0 source/CFG adapter via #329. Observation publisher guards were integrated via #341 and follow-up hardening. These integrations are *not* proof of a rendered ball, guest physics-frame alignment, score or trainable data. The D1 human-airborne-versus-START contradiction remains part of the research record. The current registry contains no approved real-game training fields.

Research and runtime owners should reuse on-main code, not fork another renderer, memory scanner, launch path, or publisher. New live tests must be individually authorized and correctly joined to their action/observation/outcome identities.

## Historical documents and preserved work

Older guidance described several incompatible GUI, Lab, legacy launcher, and research workflows. Its text is preserved in [the complete pre-V2 README snapshot](docs/archive/README-pre-v2-20261029.md) and [pre-V2 AGENTS snapshot](docs/archive/AGENTS-pre-v2-20261029.md), with original Git blob SHAs and branch history. **Those are research history, not current operating instructions.** Do not delete historical PR branches merely to lower the open count. Follow [evidence-preserving PR retirement](docs/v2-pr-triage.md).

For implementation contributions: claim one bounded task, preserve unique source-backed findings, add relevant focused tests, run the full offline suite on the exact proposed head, and follow [`merging.md`](merging.md).
