# P0 dual-object guest-frame evidence contract (S001 support only)

**2026-10-28 | DRAFT | no emulator, RAM, new shot, training or merge approval.**

## Why this is needed

S002 #240's real source-gated seven-bank study shows that the source-global MapObjBall +0x4C translation pointer used as the source of `fn_80299C70` differs from the selected player's ball object pointer **in all seven captured phases**. On W5/W6/W7 the source-global translation is bitwise equal to the selected object's cached +0xCC vector. The selected object's own +0x30 changes in both wedge intervals; only at W7 does it equal the source-global/CC value. D1 human-observed airborne yet selected ball appears at START. These are correlations from preserved human-labeled snapshots, not proof of rendered-projectile identity or an executed cache-write sequence.

A future source-selected live watcher measuring only selected +0x30 might track an actor other than the rendered moving ball. A watcher measuring only the global object would instead see a stationary wedge candidate. To discriminate them, **S001 must measure both objects and the selected +CC cache in the same guest-frame callback** alongside pin/start/source owner evidence, and tie the frame to externally attested gameplay motion before declaring a physical ball.

## Distinct scope from other owners

- S002 #240/#183/#219 owns r13 source-global pointer derivation, four-slot roster membership and r3/r27/r31 *source* provenance.
- S001 #215/#166 owns any real watched read, native Dolphin boot, bridge hooks, frame clock and shot waveform. This contribution must NOT be wired into S001 without owner/S000 consent.
- S003 #125 owns model evidence joins; this contract cannot approve modeling.
- This PR provides **only** a pure in-process *future trace schema and fail-closed reviewer* with synthetic tests. No live capture, no repository-wide CLI, no current seven-bank reader, no RAM writes, no new training/observations.

## Required per-sample privately held fields

- exact RSPE01 Rev1, scene5/mode4, selected slot/hole and source-chain gate
- stable boot/shot identity and stable selected ball, source-global, FieldManager, pin/start object identities
- *machine-attested* guest-physics-frame counter and same-hook observation attestation, **not bridge callback tick**
- selected ball translation BE-u32x3, source-global object translation BE-u32x3, selected ball cache +0xCC BE-u32x3; source pin/start triples and GolfConfig BC/C0/C4
- bounded read overhead <=5 ms; sample gap <=4 attested guest frames
- stage idle_control (bitwise stationary) or shot_observation (no physical meaning assigned)

All raw words and object identities are **private in-memory inputs**. The reviewed output only exposes 0..3 component equality/change counts and explicit no-physics/no-training flags. A source actor moving across frames is necessary but not sufficient for visual world-XYZ. The validator does not authenticate the externally supplied guest clock, boot IDs or source attestations. It only checks their shapes and consistency.

## Safety and next owner action

This study deliberately has NO input-file or live mode. Running `python scripts/review_p0_dual_source_frame_contract.py` prints a dry-run descriptor and touches no game process. Owner S001 should review the contract, determine a true machine game-frame identifier, and decide whether and how to implement a future same-hook read within existing observed A45/V1 89-event signal, with no unreviewed live session. Require source operator approval, stationary negative control, visual correspondence and independently observed contact before any causality or physical-unit claim. If machine guest-frame cannot be attested, ABSTAIN rather than use bridge ticks.

## Current verification

21 fabricated, entirely native-free tests challenge wrong frame clock, non-atomic provenance, malformed source chain, pointer relocation, changed pin/start with same pointers, Config drift, mixed boot/shot, frame rollback/gap, 5ms budget, idle motion, privacy and false training. Hosted Windows+Ubuntu CI is necessary but **does not validate real in-game behavior**.


## Review-only correction — distinct identities are mandatory

The original seven source-selected private pairs in S002 #240 source-qualified the selected player's ball and the separate source-global ball as **different runtime object pointers in every snapshot**. This contract previously only checked that the equality/alias relationship was *unchanged* over the sample sequence. A fabricated trace with the same pointer in **every** sample wrongly passed `accepted_for_offline_relationship_review=true` (with a contradictory `selected_global_object_pointers_distinct=false`). That is unsafe evidence selection: it admits a one-object trace to a required *dual-object* comparison.

This child review makes the contract fail closed if any row aliases selected and global object pointers. It retains the prior stable-pointer and no-physics-frame/renderer/training claims, all output privacy guards, and all sampling thresholds. Three fabricated tests require rejection of persistent same-object alias and one-frame collision while preserving acceptance for correctly distinct but stable source objects. **A passing contract still does not authenticate machine guest frames or visual/physics world XYZ.** No new live witness, emulator, RAM, controller or capture has been used.


### Additional motion-evidence qualification — shot label is not positive motion

The future trace schema accepts a `stage="shot_observation"` label, but this is an operator-provided annotation rather than a game-attested contact event. The previous reviewer checked stable identities and sample indices without asserting that *any* of the three object/cache source vectors had changed. Thus a wholly stationary sample cohort could be marked accepted for shot observation, even though its bitwise data could not help identify the moving ball. The source-only reviewer now **abstains** on shot-labeled samples when selected, source-global and CC triplets all stay bitwise unchanged across the cohort. This is a necessary source-motion condition, NOT proof of actual rendered-ball movement, physical axes, cause, collision, contact or shot success. Motion in ANY of the three is sufficient for source-only relationship review; physical positive/negative labels remain unverified. Idle control still requires absolute stationarity and emits `candidate_vector_change_observed=false`. Two new boolean schema fields clearly separate source bitwise changes from physical rendered-ball motion: `candidate_vector_change_observed` and `candidate_change_proves_rendered_ball_motion=false`.

No new live watcher, frame attestation, RAM access or Dolphin actions. Three additional fabricated tests: stationary shot label rejects, global-only candidate change is accepted without rendered-ball promotion, and stable idle remains accepted with explicit false motion.
