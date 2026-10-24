# Wii AI Golf research program

This is a single research program, not separate optimizers for each worker. The core loop is **start known game state → replay a bounded controller trace → observe real result → audit score/units → compare candidate policy to a fixed baseline**.

## Ownership and stages

| Study | Owner | Input | Exit gate | Status interpretation |
| --- | --- | --- | --- | --- |
| **S001** reproducible control | Integrator | Legal Wii Sports image, Felk bridge, named checkpoint | Programmatic swing visibly contacts ball and repeats | **First live, human-confirmed hit has been logged**; repeatability remains open |
| **S002** score/telemetry | Evaluation | Full game state or footage + shot labels | Landing distance/raw units agree with human observation on defined audit set | Under investigation, not yet validated scoring |
| **S003** motion calibration | Modeling | S001 stable traces + S002 measured outcomes | Controlled action→power/distance response with uncertainty | Design proposals; physical units unverified |
| **S004** fair optimization | Learning | Measured, fixed-budget training/eval attempts | Beat random / heuristic under equal emulator shots | Synthetic baselines only until S002/S003 |
| **S005** generalization | Modeling/learning | Frozen policies and unseen scenarios | Out-of-sample performance reported without tuning on holdout | Blocked on earlier stages |

The `queue.jsonl` file is an explicit proposal manifest (**not an automated worker queue**). A `status="proposed"` row can remain in that file even while separate branches produce code and measurements. GitHub issues/PRs are the live work-state ledger. Prefer updating evidence and stage acceptance notes over rewriting proposed historical hypotheses.

## Evidence contracts

Save full, sensitive/raw trial artifacts locally in the sibling `Wii-AI-Golf-Data` directory. Version lightweight reports and code in this repository. Do not commit game ROMs, Dolphin executable, savestate bytes or credentials.

Every real trial should record at least: study ID, UTC run ID, game revision/build, actual saved scenario name and slot, bridge version, trace sample count/hash and release-frame timing, dispatched result, human observation + source, raw displayed landing value and literal units (if visible), and failures. Capture screenshot/video provenance when available. Never convert an estimated power-meter fill into a measured game power percentage.

The current swing JSONL is at `../Wii-AI-Golf-Data/integration/swing-probes.jsonl`. It includes bridge ACK and user-entered hit/green/power fields, *not* an automatically verified score. Run:

~~~powershell
py scripts/golf.py research evidence
py scripts/golf.py research evidence --json
~~~

The unified CLI counts valid local records without inferring outcomes from missing fields. The source `research_catalog.py` is deliberately read-only; it does not send emulator inputs or alter saved evidence.

## Next preregistered experiment: repeatability

**Control:** same 89-sample forward trace: 12 neutral A-held, 15 backswing, 20 forward, 30 neutral A-held follow-through, 12 released; A OFF first on sample 78.

**Design:** three *independent* complete fresh-boot trials from the same registered `green-pre-start` checkpoint, using the canonical intro every time. No speed/distance/direction/timing parameter changes until these complete. With Dolphin closed between trials:

~~~powershell
py scripts/golf.py swing --slot 2 --preset forward --follow-through-frames 30
~~~

**Labels:** visibly moved yes/no/unknown; landed on green yes/no/unknown; raw displayed distance + unit only when visible; visually estimated gauge fill labeled **human estimate**. No score claims without evaluation validation. If outcomes vary or intro fails, return to S001. If contact repeats, coordinate S002 scoring and then S003 one-variable sweeps with predeclared budgets.

## Standards for future studies

- **Hypothesis and baseline:** write down one variable, units, null hypothesis and a frozen reference trace before testing.
- **Attempt budgets:** count failed/reset attempts too; no selective deletion of misses.
- **Scenarios:** preserve shot-index/layout holdouts by group; never train and test on the same exact scene while calling it out-of-sample.
- **Measurements:** keep bridge-ACK, human labels, extracted game values, converted physical values and confidence distinct.
- **Methods:** start with controlled repeats, then randomized/counterbalanced parameter sweeps, then response-surface/search, then learning only when evaluable.
- **Reproducibility:** include Git commit, study ID, experiment manifest, environment versions, local evidence path/hash, code to regenerate summary, and explicit unverified steps.

Coordinate path ownership via [AGENTS.md](../AGENTS.md), [coordination.md](coordination.md), live GitHub issues and [ledger.md](ledger.md). Preserve negative attempts; do not overwrite the existing historical ledger. Keep operator guidance in [docs/cli.md](../docs/cli.md) instead of independently inventing launch snippets in every worker's README.
