# V2 — Start Here

This is the main entry point for agents. Review these in order:

1. Root `merging.md`: objective checklist for self-merging.
2. `docs/v2-agent-charter.md`: role boundaries and identifiers.
3. `docs/S000-manager-playbook.md`: manager coordination routine.
4. `docs/p0-pr-consolidation-lanes.md`: historical research families.
5. `docs/v2-evidence-gates.md`: verified observations, contradictions, and stop rules.
6. `docs/v2-pr-triage.md`: backlog dispositions and safe closure criteria.

Startup command (change to your role and unique instance):

```powershell
python scripts/agent_init.py --role S002 --instance S002-memory-a
```

Start from the latest `main`, review the live queue and existing CLAIM comments, then claim one bounded task on the corresponding parent issue. Each handoff should include exact SHA, files, tests, limitations, and next owner.

## Canonical paths

| Behavior | Current integration |
| --- | --- |
| Main operator CLI | `scripts/golf.py` |
| Research / result-first orchestration | `scripts/research_cli.py` |
| Human outcome collection | `scripts/collect_outcome_transition.py` |
| Atomic controller preparation | `scripts/prepare_atomic_a45_bridge.py` |
| Seven-phase **read-only source-gated offline reader** | `scripts/audit_p0_seven_numbered_source_pairs_private.py` on `main` (merged PR #331) |
| Additional seven-phase experimental research | historical parent #231 **closed unmerged**; unique evidence/negative findings retained in linked history, not all experiments integrated |
| Global-ball provenance research | minimal source-global receiver/roster core merged via #337; historical parent #240 remains a separate draft/research source, not wholly integrated |
| Authenticated original-B0 source writer/CFG adapter | `scripts/audit_ball_xyz_source_callers_private.py`, `scripts/audit_p0_cache_cfg_original_b0_adapter.py` and pinned source map merged via #329; abstains on unresolved callers |\n| Final sanitized observation publication boundary | `scripts/research_cli.py` allowlist gate merged via #341; no unverified shot data published |\n| Agent initialization and successor transfer | `scripts/agent_init.py` and offline `scripts/agent_handoff.py`; [continuity and handoff contract](v2-agent-continuity.md) |\n| Manager procedure | `docs/S000-manager-playbook.md` |

PR #331 integrated the minimal seven-phase **offline** SHA/source reader, #337 selectively integrated the separate global-ball receiver/roster reader, and #329 integrated the source caller/CFG adapter. Historical research branches contain additional work and remain evidence sources rather than assumed main functionality. These source comparisons **do not** establish the rendered ball, guest physics frame, physical XYZ/velocity, contact, game score, or training eligibility. The human-labeled D1 airborne-versus-START equality is still unresolved. Before claiming integration status, verify live main and the exact file/PR—this table is a map, **not** a dynamic CI/status dashboard.

## Functional milestones

- **S001 / S005:** exact-shot action and human-observed outcome, including explicit censoring of off-green 100-foot penalties.
- **S002:** adjudicate selected versus global effective translation on preserved archives, especially the D1 contradiction.
- **S000 / S003 / S004:** align one typed action-observation-outcome contract, with eligibility gated on proven evidence.

Do not treat callback counts as guest-frame verification. Do not classify a source candidate as rendered-world ball coordinates solely from consecutive memory changes. Previously preserved captures should be analyzed before requesting further captures.

## Working conventions

Maintain one canonical implementation per behavior and prefer existing owner PRs. Keep small changes, test them, and use the root `merging.md` checklist for autonomous merging. Coordination does not impose an extra manager approval requirement. Preserve unique code, tests, and research history before closing PRs.

## Continue across agent chats

Read [agent continuity and **successor handoff** protocol](v2-agent-continuity.md). Every agent ends with one actionable operator status: CONTINUE / ACTION REQUIRED / DECISION REQUIRED. `CONTINUE V2` resumes the same instance; `HANDOFF V2` prepares a distinct successor at the conversation limit, using the **user's existing initiation prompt** plus a durable canonical GitHub handoff. Neither command creates a background agent, grants live-shot permission, or substitutes for source/CI verification.
