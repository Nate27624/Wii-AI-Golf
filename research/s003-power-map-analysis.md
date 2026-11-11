# S003 power-map analysis: interpretation before optimization

**Status:** Offline implementation for review. No new real Dolphin trial has been run for this change. The ten-shot schedule is already registered on main by PR #114; this work does not modify it or generate another live command.

## Research question and recorded evidence

Can the ten-shot, five-condition, twice-replicated **same-first-hole** experiment distinguish reliable contact, on-green success, and an input-to-power response without confusing Wii Sports' result display with physical ball carry?

Prior to the new tagged study, the operator reported two human-confirmed 1.0 baseline strikes, contact at speed-only 0.8 and 0.9, and contact at backswing-only 0.8. Power was visually estimated near 75% in the latter trials. All cited off-green results displayed **100.0 ft as a penalty**, not a measured flight distance. These are valuable exploratory observations, but do **not** fill the ten preregistered trial IDs retroactively. One earlier on-green report of 2.1 ft is a different input condition and a human-reported result, not a calibrated carry measurement.

**Scientific distinction:** The 100.0 ft off-green output is a *game penalty code*, not a numeric right-censoring threshold on physical carry. Off-green and on-green records are different measurement regimes. Even an on-green foot value should be treated as a human-annotated game display (proximity to target), **not inferred carry or a verified model target**. Fitting either as continuous swing travel would manufacture a response curve.

## Implemented, read-only S003 contract

New pure stdlib function: wii_ai_golf.modeling.power_map_analysis.analyze_power_map(records, schedule, *, study_id, expected_bridge_sha256).

- Input: existing public, sanitized observation dictionaries only. Caller supplies canonical research_cli.POWER_MAP_STUDY, POWER_MAP_ID and trusted historical V1 bridge SHA; the analyzer **does not duplicate** or revise the schedule.
- Output: JSON-safe condition counts, explicit unknown human labels, human-only contact/green Wilson intervals, penalty counts, human power estimate summaries, missing/duplicate indices, exclusion reasons and deliberately negative score/carry-identification gates.
- Eligibility: exact study ID/index/count, original run kind/schema, V1 bridge SHA, 45 observed A-lead frames, 89 reported waveform samples, valid trace hash, planned speed/backswing/motion request, matching optional controller scales, initial human club pose back, capture provenance, successful process completion. These are *comparability filters*, **not verification that the game received inputs**.
- Two published records with the same trial index invalidate both from comparison; the module never keeps whichever produced the preferred result.
- Unknown/absent contact or green labels stay unknown; a nonzero process exit or mismatched trace is **not** silently counted as a missed ball.
- It ignores untrusted extra fields and never accesses raw RAM, ROM, Dolphin or files. Data retrieval/network integration belongs to S000, result validation to S002, motion execution to S001.

## Interpretation and stop gates

The ten-shot plan has only **two independent attempts per condition**. Even a perfect 2/2 observed-contact rate has a descriptive 95% Wilson lower bound of approximately 0.342; it cannot establish repeatability or statistically rank five settings. The module requires at least three human-labeled contacts/misses per condition even to set its *exploratory comparison* flag; this is not a formal significance test or authorization to expand trials. Its power_response_identified and physical-carry/verified-game-score outputs remain false/zero by construction.

After ten shots:
1. If contact or club starting pose is inconsistent, return to S001 control/A continuity and pose repeatability rather than tuning swing strength.
2. If contact repeats but every gauge remains ~75% and off-green, ask S002 to instrument objective game power and an interpretable landing/trajectory proxy **before** running a larger sweep. Do not interpret identical penalties as identical ball travel.
3. Only if game output becomes an independently verified numeric target should S003 preregister a new calibration study and held-out prediction error. Maintain fixed bridge, first-hole scenario, A timing, single-axis variants and exact attempted-shot budgets.
4. The original 10 shots should never be retroactively relabeled as randomized holdout evidence, and controller RPC ACK is never treated as recognized strike or verified score.

## Integration and collision control

**Owner:** S003 issue #4. New paths only: src/wii_ai_golf/modeling/power_map_analysis.py, tests/test_power_map_analysis.py, this note. Independent of stale draft PR #17 (swing waveform design), pending S000 PR #105 (public evidence review), S002 capture changes and the merged #114 schedule.

S000 may add a reviewed *read-only* adapter inside the single scripts/research_cli.py after acknowledging the interface; do not create another public CLI, game launcher, UI or background worker. S002 should validate field semantics and screen-transition provenance. No production schema changes are proposed here.

## Validation/provenance

- **Offline isolated Python/source-equivalent unit run:** PYTHONPATH=src python -m unittest discover -s tests -p test_power_map_analysis.py -v : **9/9 pass**.
- **Full canonical Windows suite:** not run in the GitHub connector environment; required before any self-merge.
- **Live emulator trials / actual scored shots / automated carry measurements:** zero for this PR.
- **Privacy:** no raw captured data, absolute local paths, game files or generated bridge code added.

Related: [S003 issue #4](https://github.com/Nate27624/Wii-AI-Golf/issues/4), [ten-shot design](power-map-ten-shot.md), [PR #114](https://github.com/Nate27624/Wii-AI-Golf/pull/114), [S002 issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3).
