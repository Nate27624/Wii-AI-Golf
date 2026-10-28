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


## P0 offline source-pointer validation guard (October 28, 2026)

The offline reviewer previously accepted every *nonzero u32* for
selected-ball, source-global ball, pin, start, and field manager pointer
identities. This allowed obviously malformed candidate evidence such
as nonaligned 0x90001001 or out-of-native-range 0x12345678 to pass
the offline relationship acceptance check when all other fields were
fabricated as valid.

The review now requires all five pointer fields to be aligned on a
4-byte boundary and contained in one of the **original native captured
guest RAM address ranges**: MEM1 [0x80000000,0x81800000) or
MEM2 [0x90000000,0x94000000), with room for a 4-byte word.
Unknown mirrored/uncached aliases are **not** silently accepted;
source owners must explicitly qualify alternate address forms before
any relaxation. New synthetic tests reject pointers outside the banks,
odd/halfword addresses, nonzero null-like aliases, and values exactly
at upper bounds; accept boundary-aligned final words and distinguish
valid MEM1/MEM2 selected/global pointers.

**This is a syntactic/canonical range gate, not object-type proof.**
A numeric address falling in MEM1/MEM2 does not establish that it is
a valid Golf ball, currently live, rendered, of stable boot identity,
or sampled atomically with game physics. All attestation, game-frame,
visual, XYZ, velocity, power, score and training flags remain unchanged.
No Dolphin process, game action, private capture or pointer value
has been read to implement this fix. Owner #248, S001 #215 and
S000 #205 must review before integration.

## Independent source-span review: native bank containment for ball-object +0x4C field

Review of the canonical address-range guard in [#290](https://github.com/Nate27624/Wii-AI-Golf/pull/290) found a more specific acceptance bug: a valid aligned pointer to the **last word** of MEM1 or MEM2 (`0x817FFFFC` or `0x93FFFFFC`) passed the five-pointer gate even as a **selected or source-global RPGolMapObjBall**. However earlier source-qualified S002 [#240](https://github.com/Nate27624/Wii-AI-Golf/pull/240) found these ball objects are dereferenced at offset **+0x4C** to acquire a translation pointer. A ball-object base that cannot contain the four-byte member at +0x4C cannot support even this necessary outer chain. This is not evidence the +0x4C target is a valid live translation vector; that remains externally asserted by source owners.

The child review requires each selected/global ball **base** to be 4-byte aligned inside one native guest RAM bank with **0x50 bytes** available (offset +0x4C plus 4-byte field), preventing a bank-end chain from being marked `accepted_for_offline_relationship_review=true`. No general object-size inference: pin, start and field-manager pointers retain the existing one-word range rule because their minimum member spans are not independently established in this contract. The tests include MEM1/MEM2 last-word and off-by-four negatives, exact last-full-member positive boundary, non-ball type guard preservation, and wrong minimum-length inputs.

**Scope:** This is a *necessary syntactic containment* check, not an object type, nested pointer validity, actual guest execution, renderer association, pixel/guest-frame join, world XYZ, velocity, contact, score, impact, power, training or publication. It cannot independently authenticate row booleans. All runtime/physics claims remain FALSE. No Dolphin, game input, new dump, private memory, raw addresses or model training. Tests use fabricated public bank boundaries only; owner #248/#290 review before merging.
