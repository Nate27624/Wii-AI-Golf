# S002 candidate alias audit — 2026-10-24

**Source:** Published motion summary from real Felk Dolphin/Wii Sports US Rev 1 capture:
https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T085852Z-d39c3401/research/results/hitting-green/20261024T085852Z-d39c3401.json

**Context:** The user has confirmed a recognized golf swing in another worker's live test. Evaluation has produced S002 candidate vector reports, but ball XYZ and Hitting the Green score are not validated. Avoid tuning real controller action based on memory variables just because they change.

**Initial reported finding (published ranked subset only):** 111 candidates detected; 30 ranked records published; 18 unique memory starts, 9 starts repeated, 12 duplicate rows and 8 overlapping 12-byte vector span groups. Some candidate values resemble unit vectors, which could indicate rotation/direction rather than translational position; do not claim identification. Earlier contrasting report with zero published candidates: https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T085619Z-2f8a22d2/research/results/hitting-green/20261024T085619Z-2f8a22d2.json

**Independent deliverable:** New offline non-destructive auditor in src/wii_ai_golf/audit/motion_candidates.py, CLI scripts/audit_motion_candidates.py, targeted mock tests and docs. Takes only existing published summary JSON, groups exact addresses and memory-span overlaps, checks window offsets and truncated result accounting, flags unit-vector endpoints and retains comparison caveats. No gameplay reads, new actions, GitHub pushes, score fields or edits to in-flight evaluation files.

**Validation:** Eight focused tests were executed and passed under Python 3 in a minimal local reproduction of these NEW files, including a subprocess with Python -I. Complete user repo test suite and real published summary loaded into the NEW Python CLI were not executed from this connector-only environment. Next: operator runs targeted and full unittest suite, then uses the auditor on an existing local S002 summary, or the evaluator can integrate its output in PR #14 without merging conflicts.

**Interpretation rule:** A byte-address alias is not an independent sample; overlapping vector spans need manual semantic grouping; a candidate is not a ball coordinate or score until the live-game video/time-series correlation is validated on at least two distinct observed conditions. Preserve all raw local evidence; this audit never uploads or overwrites it.
