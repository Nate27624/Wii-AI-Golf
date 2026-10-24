# Milestones

## M0 — multi-agent foundation

- [x] Repository initialization, collaboration contract and proposed studies
- [x] Policy and environment contracts, synthetic example, working local tests
- [ ] Merge foundation PR into default branch

## M1 — control validation

- [ ] Record Dolphin build and exact game region/revision
- [ ] Verify programmatic controller event playback recognized by the game
- [ ] Reproduce and audit a single shot with recorded input trace and output
- [ ] Document repeatable reset method or stochastic differences

## M2 — production-quality data

- [ ] Execute >=100 unattended scored shots
- [ ] Verify distance/units against human annotation
- [ ] Record all failures and time per shot
- [ ] Freeze unseen configurations/seed protocols

## M3 — learning

- [ ] Collect random and search baselines under equal attempt budgets
- [ ] Train a contextual/model-based candidate and evaluate blind
- [ ] Explore RL only with justified sample-efficiency assumptions

## M4 — challenge

- [ ] Verify medal threshold on the target game
- [ ] Freeze policy, score an untouched ten-shot run, replicate
- [ ] Save auditable plots and replay captures for video production
