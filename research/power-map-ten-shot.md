# S003 Ten-shot power calibration — frozen preregistration, currently PAUSED

**Execution/evidence status (2026-10-29):** This is an archived, *proposed* ten-arm first-ball study, **not an active public, same-shot-joined study**. No trials are authorized by this document; any real Dolphin launch/input needs separate explicit operator approval. `py scripts/research_cli.py study` prints the original frozen commands only; it does not start Dolphin or authorize executing the commands. Existing observations remain human-only and must not be relabeled as verified distances or training records.

### Current CLI contract — no public study join

The ten commands printed by `study` include `--study-id S003-POWER-MAP-10-V1 --trial-index N`, but these flags **do not make a result joinable in the public `research/observations` branch**:

- The exact-child `--visual-first` M1.5 path **refuses `--study-id`** before launch (`scripts/research_cli.py::main`); it independently restricts speed to 1.0 and backswing to 1.0/1.2, so several frozen ten-arm settings are not valid M1.5 pilots.
- A non-visual legacy `v1 --live --study-id ... --trial-index ...` command can record study metadata in a **local-only** `kind=v1_attempt` report. It has no authenticated child shot/terminal join and **returns before `publish_summary`**, even if its optional human annotation says contact or shows a distance. `train_approved=false` and `numeric_distance_target_eligible=false`. These reports are not measured carry and are not public study rows.
- Current publication allowlisting intentionally **omits study_id/trial_index/trial_count**. Neither a generic published `kind=test` event nor a published individually joined M1.5 `kind=v1` event establishes a ten-arm study index. Do not loosen the S000 publisher or treat older observations as study rows.

See `tests/test_s003_study_contract.py` for no-emulator negative controls. Do not run the printed legacy commands merely to produce more unjoined 100-foot penalties.

## Historical observations (human labels; not verified memory or carry)

- Speed-only 0.8 and 0.9: both reportedly struck the ball, ~75% visible gauge, off green with a 100.0ft capped penalty.
- Backswing-only 0.8: reportedly struck the ball, ~75% visible gauge, off green with the 100.0ft penalty.
- Prior working control: 45 observed frames A-only lead + V1 bridge + fixed 89-frame A-held/released trace; two baseline 1.0 shots reportedly struck.
- These results **do not provide a continuous distance response**. The 100.0ft off-green display is a censored penalty, never physical carry. A human-visible percentage is not source-verified power.

## Frozen design — not approved to execute

Five conditions repeated twice in balanced order (speed scale, backswing scale), using the **same first-ball scenario** on separate fresh boots, not ten different holes:

1. (1.0, 1.0) control
2. (0.8, 1.0)
3. (1.0, 1.2)
4. (0.9, 1.0)
5. (1.0, 0.8)
6. (1.0, 1.0) control
7. (1.0, 0.8)
8. (0.9, 1.0)
9. (1.0, 1.2)
10. (0.8, 1.0)

Only one parameter changes per trial; original motion scale 1.0, A lead 45 and bridge revision are otherwise intended fixed. A new study must be separately authorized and preregistered; **do not silently rewrite these arms to fit M1.5**, improvise multi-hole transitions, execute old commands unattended, or claim retrospective joinability.

## Future acceptance before study activation

| Requirement | Current evidence ceiling / decision |
| --- | --- |
| Control and scene | S001 must verify clean Dolphin startup, correct original game/revision, first-ball scenario and exact requested action/bridge waveform identity. Startup, bridge callbacks and game-side A recognition are separate gates. |
| Same-shot action/result join | Collector must bind a unique run token, shot identity, immutable trace digest, dispatch/terminal phase and independently witnessed terminal outcome; missing/mismatched identities refuse rather than guessing from timestamps. |
| Measurements | Record initial club pose (unknown allowed), human contact, visible power percent (if shown), on-green yes/no/unknown, displayed score **and unit**, and whether screen transitioned before result capture. Do not promote human labels to machine-verified power, carry or frame. |
| Censoring and eligibility | `offgreen_100ft_penalty` is censored; uncertain or failed shots have no numeric carry target. All records stay untrainable until independent S002/S005 provenance, geometry and outcome checks pass. |
| Public study schema | Only after S000/S003 coordination and exact-head Win+Ubuntu tests may a separate typed, allowlisted `study_id` / trial index / version / run+shot identity contract be considered. Current public publisher does **not** implement it. |
| Authorization | Separate operator opt-in for each live run and any private result publication; this document and `study` display confer neither. |

## Intended outcomes and stop criteria (if a future revision is authorized)

Primary historical proposed outcome: proportion of **human-observed** ball contacts in each condition. Secondary proposed observations: on-green yes/no and visible power gauge; 100.0ft off-green is penalty/censored score, not a measured distance. No response-surface fit or policy training from current observations.

Stop for wrong first-ball scene, changed bridge/source identity, failed continuous A hold, inconsistent starting pose, scene transition before terminal evidence, or ambiguous shot identity. An all-~75% gauge result would motivate a different power-physics measurement hypothesis, **not** an automatically repeated parameter sweep. Preserve the original frozen trial order, historical human notes and negative results for future preregistration.
