# S005 — memory-derived outcome eligibility matrix (offline audit only)

**Author/instance:** S005 / `S005-heldout-audit-1` • **Manager task:** `S005-MEMORY-OUTCOME-ELIGIBILITY-MATRIX` • **Source main:** `a3bc139b907ca965377d3e5a5594b6174ab1cf2e` • **Status:** source-only candidate, **no verified real training sample**.

## Source anchors and evidence levels

- `research/memory-variables/registry.json` (source blob `596a5c4a59f9195ba0f54ee6786148775bcb0905`): status ladder `unresolved`, `source_candidate`, `snapshot_correlated`, `runtime_verified`, `rejected`; RSPE01 US Rev1 only. The selected ball-object current-vector candidate is relative `+0x30`, with pointer/selfref `+0x4C`; selected record position/start-copy candidates `+0x54`/`+0x60`, caches `+0xCC`/`+0xF0`/`+0xFC`. W5→W6→W7 same human-labeled wedge shot shows 3/3 selected current components changed with inactive balls, tee and pin static, but source-linked **guest-frame atomicity, physical axes/units, velocity, rendered actor, lifecycle, contact and measured score remain unproven**. The D1 human-airborne vs source-selected START discrepancy cannot be silently resolved as moving physical XYZ. Pointer-value equality is not object-lifetime evidence.
- `scripts/collect_outcome_transition.py` (blob `3ad7f18a7033d559f5beb4f4710b942e8452eee5`): human visual-first result entered as `G/M/U/T`, with `M:100ft` explicitly classified `offgreen_100ft_penalty`; `run_token` created separately. Human answer does not prove game-native terminal score or its same-shot linkage.
- `src/wii_ai_golf/protocol.py` (blob `75b404b8cf2afe6799c514e66da0c92ba46202e6`): `Observation` has scenario ID and normalized numeric features only; `ShotResult` has nonnegative finite distance and free-form metadata. Neither type authenticates run/shot/event/frame, physical outcome, source identity or censor-free carry.
- `src/wii_ai_golf/evaluation.py`: prior evaluator source-only defect reported [Issue #6 HANDOFF 6499321509](https://github.com/Nate27624/Wii-AI-Golf/issues/6#issuecomment-6499321509), explicitly censored synthetic-tagged 100ft could enter numerical aggregates; S004 owns this module and subsequent corrections. No S005 code change authorized.

## Mandatory provenance/eligibility fields

| Field | Required machine proof | Current supported claim | Fail-closed decision |
| --- | --- | --- | --- |
| `executable_sha, revision, scene` | Exact installed binary identity, revision and active Golf scene | Source/static layout and some snapshots pinned to RSPE01 Rev1 | Abstain across unknown build/scene |
| `run_id, shot_id, event_id` | One immutable joined attempt across request, input, RAM, result | Collector may generate run token; exact guest shot/event association unproven | Abstain if missing, reused or mismatched |
| `request_waveform, requested_frame` | Ordered issued input trace with timestamps | Requested A/hold and trace information is **not** game-side accepted input | No contact inference |
| `accepted_input, contact_witness` | Independently source-located game latch and true contact transition for same attempt | G1 acceptance/contact remains unresolved; callback alone insufficient | `false/unknown`; no positive stroke |
| `selected_ball_root, global_ball_root` | Source chain, selector/index, bounds, same actor identity | Selected `+0x30` translation candidate; global/rendered independent match unproven | Treat as candidates only |
| `object_generation, lifetime` | Monotonic generation/epoch or source-backed reuse detector | Matching pointer values across captures do not guarantee same object lifetime | Abstain on replacement or unknown |
| `guest_frame, physics_step, capture_atomicity` | Same guest simulation frame from an independently verified counter/physics step | RPGolMain `+0x74` only monotonic *untyped* counter candidate | Do not label samples frame-aligned |
| `rendered_ball, trajectory_xyz, velocity` | Independent link between selected object, rendered ball and physical units/axes | W5–W7 3-component changes; not verified physical XYZ | Null/missing validity mask |
| `terminal_label, source, censor` | Same-shot game terminal outcome with provenance and censor interpretation | Human result-first `G/M/U/T`; `M:100ft` explicitly censored | Non-numeric if censored or unknown |
| `uncensored_carry, training_approved` | All independent gates and physical calibration pass | No verified source/action/outcome physics join | **null, false** |

## Fabricated negative-control matrix

All entries are *hypothetical records* for parser/consumer design, not screenshots, RAM readings or real-game examples.

| Synthetic fixture | Perturbation | Expected decision |
| --- | --- | --- |
| N1 | Same visible ball pointer, different `object_generation` after reset | ABSTAIN: identity reused |
| N2 | `run_id` same but `shot_id` / `event_id` differ between RAM and terminal result | ABSTAIN: unjoined attempt |
| N3 | Selected and rendered/global root disagree despite finite selected `+0x30` | ABSTAIN: wrong actor |
| N4 | Requested A45/input callback true, game-side accepted-A/contact missing | ABSTAIN: request != contact |
| N5 | RAM snapshots have unrelated guest frame / capture not atomic | ABSTAIN: no velocity or terminal join |
| N6 | Human D1 `airborne` tag while selected source candidate equals START | ABSTAIN: contradiction, do not relabel automatically |
| N7 | Human `M:100ft`, metadata `offgreen_100ft_penalty` or explicit censor flag | ABSTAIN: display penalty, no measured carry |
| N8 | Self-declared `source=synthetic` and `distance_m=30.48` without authenticated real source | Can be toy-data only; **never promote to physical real outcome** |
| N9 | Same run, shot, actor and frame labels but no game-side contact witness | ABSTAIN: missing independent gate |
| N10 | All identifiers self-consistent by construction, but physical calibration or machine result reader absent | ABSTAIN: internally consistent synthetic fixture is not physical proof |

**One positive control, explicitly synthetic only:** A fabricated self-consistent ToyGolfEnvironment observation/result with `source=synthetic`, matching scenario and no censor flag may support toy unit tests and toy reward comparisons. It **does not** justify `training_approved=true`, world XYZ, physical carry or unattended gameplay.

## Consumer decision pseudocode (not executable)

```text
if any of build/scene/run/shot/event/source identity is unknown or contradictory: ABSTAIN
if accepted-A/contact, selected↔rendered object lifetime, guest physics frame
   or same-shot terminal source is unknown: ABSTAIN
if terminal source is human-only, result unknown or explicit censor penalty: ABSTAIN
if physical units / uncensored machine result are unverified: ABSTAIN
ONLY THEN evaluate a real-sample proposal; require independent owner review.
```

## Owner handoffs and next evidence

- **S001:** Provide independently demonstrated accepted-input latch/contact identity, waveform-to-game-frame mapping and idle/A-held controls. Current A callback or trace dispatch is insufficient.
- **S002:** Preserve source-selected/global roots, selector/index, relative offsets, object lifecycle and same-guest-frame tests; adjudicate airborne D1==START contradiction without assuming a physical XYZ scale. Must use exact source/runtime provenance and private raw data only in authorized local environment.
- **S004:** Maintain a typed consumer contract with explicit validity masks, refused mismatched run/shot/frame/actor/censored data, and no approved training from source-only candidates.
- **S005:** Audit any proposed terminal outcome against independent machine source and censor rules, never convert an offgreen 100ft display penalty into physical distance.
- **S000:** Keep exclusive lane ownership, assign source evidence acquisition before further model tuning.

**No operator shot authorization was requested or inferred.** No raw RAM, ROM, savestates, local paths or personal captures are included. This study is an evidence/eligibility checklist, not a new reader or a source-verified RAM mapping.
