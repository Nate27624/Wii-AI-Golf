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
| Additional seven-phase experimental research | parent PR #231 and stacked studies; **not** all merged into `main` |
| Global-ball provenance research | parent PR #240, not yet integrated into `main` |
| Manager procedure | `docs/S000-manager-playbook.md` |

PR #331 integrated only the minimal seven-phase **offline** SHA/source-reader dependency closure and its synthetic tests; it did **not** import the remaining #231 experiments or independent #240 global-ball reader. None of these source comparisons verifies the rendered ball, a guest physics frame, physical XYZ or velocity, a shot outcome, or training eligibility. Continue to treat the human-labeled D1 airborne-versus-START equality as unresolved. Do not describe unmerged research-branch functionality as available on `main`.

## Functional milestones

- **S001 / S005:** exact-shot action and human-observed outcome, including explicit censoring of off-green 100-foot penalties.
- **S002:** adjudicate selected versus global effective translation on preserved archives, especially the D1 contradiction.
- **S000 / S003 / S004:** align one typed action-observation-outcome contract, with eligibility gated on proven evidence.

Do not treat callback counts as guest-frame verification. Do not classify a source candidate as rendered-world ball coordinates solely from consecutive memory changes. Previously preserved captures should be analyzed before requesting further captures.

## Working conventions

Maintain one canonical implementation per behavior and prefer existing owner PRs. Keep small changes, test them, and use the root `merging.md` checklist for autonomous merging. Coordination does not impose an extra manager approval requirement. Preserve unique code, tests, and research history before closing PRs.

## Continue across agent chats

Read [agent continuity protocol](v2-agent-continuity.md). Every agent ends with one actionable operator status: CONTINUE / ACTION REQUIRED / DECISION REQUIRED. The user can say `CONTINUE V2` to resume the most recent canonical handoff without repeating instructions. This does not grant live-shot permission or background execution.
