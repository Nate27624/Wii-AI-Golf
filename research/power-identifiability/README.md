# S003 supporting research: censored power / distance identifiability

Issue #117. October 25, 2026 UTC. This is **offline analysis only**: no Dolphin swing, RAM capture or verified game score.

## Question and actual public observations

Can we fit continuous input-to-power or input-to-carry-distance from recent V1 trials? **No**. Approved sanitized observation branch: https://github.com/Nate27624/Wii-AI-Golf/tree/research/observations/research/observations

- 20261025T021350Z-5c73da554a: speed 0.8, 45 observed A-lead, 89 trace frames, historical V1 bridge SHA fe04cb..., starting pose back. Human contact yes; approximate meter 75%; not on green; displayed 100.0 ft.
- 20261025T021501Z-ec585ddab4: speed 0.9, otherwise matching bridge/lead/pose. Human contact yes; approximate meter 75%; not on green; displayed 100.0 ft. Settled screen changed before capture completion.
- 20261025T022242Z-4154dea732: backswing 0.8 and speed 1.0, same bridge/lead/pose. Human contact yes; approximate meter 75%; not on green; displayed 100.0 ft.

These are distinct waveforms, not replicate observations of the same intervention. They lack an explicit public scene identity. The off-green 100-ft display is a game penalty, **not physical carry distance**, and approximate gauge 75% is a human estimate, not a verified power sensor. There is no defensible continuous response curve.

## Contribution / use

Pure API: `wii_ai_golf.research_power_identifiability.audit_power_identifiability(records)`. Pass only in-memory already-sanitized V1 public dictionaries, not private capture JSON. It groups by bridge, explicitly declared scene (or missing), measured A-lead, starting pose, declared motion parameters and waveform. It never infers missing defaults or prints other untrusted payload fields. It retains unknown contact and human power, separates penalty-coded displays from other unverified human scores, and reports conservative identification gates. It does not touch the canonical S000 `evidence_review.py`, research CLI, publisher, or S001/S002 code.

Synthetic focused tests: `PYTHONPATH=src python -m unittest discover -s tests -p test_research_power_identifiability.py -v`. All 10 targeted synthetic tests passed in an isolated source-only environment during development; **not** the full current-main suite or Windows/Dolphin validation.

## Prospectively useful follow-up; no unattended run authorized

First finish S001 identical-waveform replication following S000's PR #105 study. Then request S002/S000 approval for a safe explicit scenario/shot fingerprint and a traceable power/ball measurement source. For any later one-variable experiment, require same named checkpoint, scenario, starting pose, bridge revision, A-lead and wave shape except the chosen intervention. Count failures and unknowns. Collect at least two repeats per arm before exploratory contrasts.

**Stop rule:** If displayed 100.0 ft persists off green, do not regress it against power or speed. If the gauge remains visually ~75% across conditions, stop blind motion scaling and investigate actual controller/power response. Binary ball-contact and on-green labels can be explored separately; a true continuous carry-distance model requires independently validated physical measurement. No reported 100-ft penalty should become a carry-distance training target.

Upstream S001: Wii controller/waveform; S002: measurement and safe publication; S000: public reviewer/CLI; S003: candidate motion calibration. Any new publication field or CLI integration needs owner acknowledgment. Evidence classification: sanitized human labels + synthetic unit tests only.
