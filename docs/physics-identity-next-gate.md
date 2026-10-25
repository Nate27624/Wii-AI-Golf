# Source-guided physics identity: next gate

The public [doldecomp/ogws](https://github.com/doldecomp/ogws) decompilation explicitly targets **US Rev 1** but remains work in progress. Direct repository code searches for `RPGolfBall`, `RPSportsGolfBall`, `RPGolfField` did **not** locate a verified ball-object owner. Do not invent an offset based on suggestive names or assume that a rendering/effect pointer is ball physics.

## Established negative control

- Aim-only/no swing run: [20261025T001441Z-edf86056](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261025T001441Z-edf86056/research/results/hitting-green/20261025T001441Z-edf86056.json), 240 valid snapshots and **96 XYZ changes** at `0x925834D8` when the operator apparently rotated the camera.
- True tee-ready idle: [20261024T235737Z-90460728](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T235737Z-90460728/research/results/hitting-green/20261024T235737Z-90460728.json), 180 valid snapshots / **zero** change steps.
- Two-swing run: [20261025T000301Z-bfd74bbd](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261025T000301Z-bfd74bbd/research/results/hitting-green/20261025T000301Z-bfd74bbd.json), 300 samples, 40 continuous changes plus 176.3425-unit discontinuity.

**Policy:** `0x925834D8` (one-hop field +0x04, offset +0x50) is **not** a verified ball-world-position. Added `src/wii_ai_golf/ball_identity_gate.py` + unit tests: deny training eligibility if camera-sensitive, if controls are missing, and even when all motion tests are stable but no external ground truth exists. Other agents should consume this negative-evidence gate rather than training on the candidate.

## Discovery plan

1. **Source analysis first:** locate source-backed owner and update fields for golf ball trajectory. Record class, object lifetime, position coordinate frame, known static symbols; no guessed pointer chain.
2. **Multi-condition scans on DIFFERENT source-grounded candidates:** repeat tee-ready idle, aim-only, and controlled shot. Do not reuse camera-sensitive candidate as ball ground truth.
3. **Dynamic lifetime/geometry evidence:** require same object to remain world-stationary during camera aim and move during launch, then land; correlate with independently observed visual ball.
4. **Outcome validation:** only then derive velocity and compare actual score. Large 176-unit discontinuity is not ball velocity.

**Status:** source search did not yet identify a verified owner; live Dolphin capture not performed in this agent session. No new physics-ball identity claimed.
