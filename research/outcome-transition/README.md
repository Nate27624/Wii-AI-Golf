# S002 outcome transition evidence handoff — 2026-10-24

Source-grounded read-only discovery prototype that does not overlap PR #14 or working swing calibration.

## What has been delivered

- src/wii_ai_golf/audit/outcome_transition.py: bounded 12 KiB-per-sample RAM capture with RSPE01 Rev1 / Hitting the Green mode 4 gates and fixed decomp-source golf static pointers; before/post/settled persistent 32-bit word candidates.
- scripts/collect_outcome_transition.py: action-only collector to be launched **through** the fresh-start canonical run_golf_experiment.py wrapper. Prompts first-ball readiness and single unchanged forward swing consent, records private raw JSONL phases and human landing label with a local candidate summary.
- tests/test_outcome_transition.py and tests/test_outcome_capture_cli.py: 13 mock tests for read-only and revision/mode gates, persistent change/false positive filtering, no overwrites, no double swing, and abort behavior.
- docs/outcome-transition-protocol.md: exact one-command setup, source caveats, and validation plan.

## Experimental hypothesis and preregistration

Hypothesis: Some bounded golf RAM words, if stable at the first ball and after the ball has visually settled, change persistently after a recognized real swing and may correlate with user-visible Hitting the Green distance/result. Initial baseline is identical 89-frame forward strokes from the same named green-pre-start checkpoint. First stage budget: three independent fresh-boot captures of this trace (including non-contact negative cases) before modifying any control or inferring field semantics. Record raw display number and original unit, do not automatically convert or assume it is the score.

Afterwards, two distinct observed landing results and scene/pin layouts must be held out for disconfirmation. A field only becomes a verified score/ball variable after independent visual/manual validation and repeated consistent changes, not simply a one-run numeric match.

## Evidence and limitations

Live Felk Dolphin/Wii Sports execution: **not performed by this GitHub-only session**. Thirteen focused tests passed in a minimal Python 3 scratch reconstruction with fake integration imports; full user's current checkout test suite and actual game transition still need validation. Data from snapshots is not automatically an actual in-flight ball trace (captures start after the motion trace completes and individual multi-frame reads may miss fast flight). Hitting the Green may leave mode 4 when the result overlay appears; current strict gate then aborts with private partial raw evidence. Research result is an unverified ranking, not an authoritative decoded score.

No raw RAM is committed to Git. S002 evaluation agent owns confirmed scoring, integration agent owns swing waveform. Claim in Issue #3; notify S002 owner before further interface modification.

Primary structure source: https://github.com/kiwi515/ogws_info (US Rev1 headers).
