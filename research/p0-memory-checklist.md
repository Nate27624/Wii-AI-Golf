# P0 game-memory checklist and training gates

Research checklist (2026-10-27), **not proof of runtime-verified RAM fields**. Coordination: [#121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). Owners: [S001 #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2), [S002 #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3), [S003 #4](https://github.com/Nate27624/Wii-AI-Golf/issues/4), [S004 #5](https://github.com/Nate27624/Wii-AI-Golf/issues/5), [S005 #6](https://github.com/Nate27624/Wii-AI-Golf/issues/6).

## Source discovery and live confirmation

- [x] **S002/source:** identify source-backed scene_id: EGG SceneManager current ID at offset +0x18; US Rev1 manager singleton within .sbss 0x804BF4D8..0x804BF4E0. Exact 4-byte pointer slot remains candidate. [Investigation](scene-id-memory/README.md).
- [x] **S002/offline:** read-only MEM1/MEM2 diagnostic with synthetic tests, current-scene-object ID and manager back-pointer checks. No live proof.
- [ ] **S002/live:** independent Golf-at-ball snapshot with unambiguous singleton pointer slot, scene_id=5, pointers in range.
- [ ] **S002/live:** repeat on a distinct fresh boot, record actual capture identity/hashes.
- [ ] **S001+S002/live:** test independent non-Golf scene (sports main menu expected ID 9) to falsify spurious constant-5 matches. Record transition timing.
- [ ] **S002:** mark scene_id runtime-verified only after two independent positive boots plus one real negative, preserving verified static slot/dynamic pointer and provenance.
- [ ] **S002:** validate pre-shot ball_x/y/z and hole_x/y/z or independently audited initial distance+bearing; use truly different scenes, not repeated bitwise-identical dumps.
- [ ] **S002:** validate aim_angle and club_id/actual effective club when applicable, including native units and controlled changes.
- [ ] **S001+S003:** record exact swing_trace, A/button/motion/release phases and hashes; join commands and RAM by explicit SAME-SHOT identity and frame bounds, never loose timestamps.
- [ ] **S001+S002:** establish ball_contact from independently corroborated impact/motion, distinct from bridge ACK.
- [ ] **S002:** verify settled final ball XYZ or non-censored distance_to_hole + unit, plus reliable ball_stopped/result-ready marker. Off-green displayed 100 ft may be a penalty, not physical travel.
- [ ] **S003:** investigate internal swing_power, club pose/impact and velocity as additional physics targets; do not invent values or block a simple outcome predictor on optional P1 values.

## Validation, ownership and training

- [ ] **S000/S002:** track each address/pointer chain with game revision, type, endianness, unit, observed phases, negative control and status candidate/correlated/verified/rejected.
- [ ] **S000:** keep ROM, savestates, raw MEM1/MEM2, screenshots, secrets and private paths local; publish only existing reviewed allowlisted summaries.
- [ ] **S003/S004:** propose a typed per-shot state -> actual controller action -> verified outcome dataset, preserving null/missing and censored/invalid cases; obtain owner review before changing canonical shared schema.
- [ ] **S004:** define fixed real-Dolphin shot budgets and honest random/heuristic baselines. Calculate rewards only from validated game outcomes, count misses and data-collection cost.
- [ ] **S005:** freeze untouched shot-index/layout/scene holdouts, avoid same-shot or savestate leakage, report real-game prediction error and uncertainty.
- [ ] **S000:** preserve canonical single approved fresh Dolphin boot/intro and guarded one-shot collection; no unattended live training until measurement and authorization gates pass.
- [ ] **S000/S002/S003:** independently sign off P0 same-shot state/action/outcome completeness before real-game model training.

Proposed per-shot fields, **NOT an approved public schema**: run_id, shot_id, game_id, disc_revision, scene_id, scenario_id, shot_index, shot_phase, initial ball and hole XYZ OR audited target distance+bearing, aim_angle, club_id, swing_trace/hash, contact source, settled marker, final XYZ OR audited true final distance and unit, censored/miss status, confidence, training/test split.

**Current gate:** blocked pending live-memory validation and audited outcomes. Dolphin provides authoritative observations; an external learned model predicts hypothetical outcomes, with candidates verified back in Dolphin. See [architecture PR #190](https://github.com/Nate27624/Wii-AI-Golf/pull/190).
