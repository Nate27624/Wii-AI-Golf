# Wii AI Golf milestones and acceptance gates

Evidence date: 2026-10-24. This is the shared project status; older entries in `research/ledger.md` are chronological snapshots, not necessarily the current gate.

| Stage | Milestone | Verified status | Next acceptance gate |
| --- | --- | --- | --- |
| **M0** | Single repo, agent coordination, synthetic smoke tests | **Complete foundation**; unified CLI added, runtime tests pending | Stable source-local `golf` command with isolated tests and Windows confirmation |
| **M1** | Real controller, reset, recognized swing | **Partially validated in game:** human reports Python A button works and ball visibly moves under 89-frame forward swing; named Slot 2 restore/intro works | Repeat **3 independent** identical shots, retain trace and actual human outcomes |
| **M2** | Real outcome measurement | **Not achieved:** no confirmed raw landing score units, distance extractor or 100 unattended scored attempts | ≥100 full attempts with ≥95% complete, human-audited scores and all failures logged |
| **M3** | Parameter calibration and fair learning | **Not achieved in Wii Sports:** S003 design and S004 synthetic baseline work separate | Measure one-factor action–outcome response then honest equal-budget comparisons |
| **M4** | Held-out Hitting the Green challenge | **Not achieved** | Frozen model, untouched ten-shot run, replicates and documented score/medal rules |

**Do not merge these states:** verified Python command dispatch ≠ recognized in-game swing ≠ landed on green ≠ verified score ≠ optimized model. The first live JSONL confirms 89/89 bridge frames, human ball movement yes, green landing no, and a visual ~75% power-meter estimate only.

## Immediate priority

1. Record remaining identical fresh-boot trials with `py scripts/golf.py swing --slot 2`, preserving the 89-frame baseline.
2. S002 validates landing distance, score and their units against game evidence; cross-check RAM candidate hypotheses.
3. S003 varies one motion parameter at a time only when corresponding outcome labels exist.
4. S004 benchmarks random/heuristic/response-surface policies only after a genuine reward is measurable.
5. S005 generalizes to withheld shot layouts.

See [research/README.md](../research/README.md) for ownership, study budget discipline and evidence schemas. The pending open evaluation/modeling/learning PRs are **not** automatically verified by this roadmap update.
