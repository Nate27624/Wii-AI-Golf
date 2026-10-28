# S002 P0: Preserved airborne MEM1/MEM2 vs original stationary B0 (OFFLINE ONLY)

**2026-10-28.** An actual operator-exported full-memory pair was captured when the ball was visibly airborne (power meter approximately one-third). The operator later hash-verified copies of MEM1 (24MiB) and MEM2 (64MiB) into an ignored unique private capture directory, with a local `manifest-PRIVATE.json`. Original B0-B3 stationary/aim checks were independently validated earlier. One old S001 70-frame selected-record watch during a different no-contact stroke is a distinct negative and must never be relabeled as this positive flight observation.

## Goal and source dependency

Compare **B0 stationary** and **airborne-human-labeled** saved bank pairs, without invoking Dolphin again. The PowerShell 5.1 operator entrypoint `scripts/Invoke-P0InFlightBallCompare.ps1` calls the reviewed S002 #160/#163 Rev1 source-gated roster/player/ball reader in a new small Python helper, preserving the private bank checks and RSPE01 Rev1 Golf mode selection. This new PR is stacked on S002 fullbank fourphase #181 and does not mutate its files.

Verification in BOTH phases requires the original native B0 manifest + hashes and the archived flight manifest + hashes, exact native bank sizes, game's source PPC dataflow, active golf scene, selected player slot, source hole and bounded objects. Missing fields or incompatible game/scene cause a **fail-closed** diagnostic, not guessed physics. The human airborne annotation is not a synchronized emulator-frame proof.

## Candidate source-based comparisons

- Selected player 51 × big-endian u32 record (`0xCC`): report changed relative offsets/count, not values.
- Player record +0x54 and +0x60 triplets, source-selected ball child +0x4C → translation triplet, child object +0x30 constructor translation, +0xCC/+0xF0/+0xFC caches. These are competing position/record-copy hypotheses, not verified physics.
- Independent current start/tee triplet as a negative control: inspect per-phase equality and whether start itself moved. If the start differs, explicitly flag cross-phase position comparison as confounded.
- Full MEM1/MEM2 differ-or-equal flags. Do not print full bank data, runtime pointers, private SHA or float values.

**Output always flags:** `mem1_mem2_exports_same_guest_frame_verified=false`, `same_boot_verified=false`, `actual_ball_world_xyz_verified=false`, `ball_velocity_verified=false`, `impact_frame_verified=false`, `power_ram_variable_verified=false`, `approved_for_training=false`, `allowed_to_publish=false`. Even changed source-selected coordinates are only candidate motion until time-locked game-side controls and a second confirmed flight phase validate them.

## Operator entrypoint

Once the review branch and offline CI pass, in a separate detached review worktree sibling to `Wii-AI-Golf-Data`, run:

```powershell
& 'D:\Projects\Wii Golf AI\Wii-AI-Golf-P0-InFlight-Compare\scripts\Invoke-P0InFlightBallCompare.ps1'
```

Default input locations: original `Wii-AI-Golf-Data/ball-study-20261027-212633` containing `B0-MEM1.bin`, `B0-MEM2.bin`, `checkpoint-manifest-PRIVATE.json`; preserved flight `Wii-AI-Golf-Data/captures/in-flight-human-20261028-054537477` containing `mem1.raw`, `mem2.raw`, `manifest-PRIVATE.json`.

To change location without editing source, pass `-Baseline '...'-Flight '...'` as proper separate PowerShell parameters. To run tests only, add `-TestsOnly`. The wrapper writes a uniquely named sanitized private JSON inside the archived flight directory, no overwrite. Stdout is the sanitized comparison JSON only; share it for review, NOT the raw `.raw`/`.bin` banks or manifest hashes.

## Risks and interpretation

- GUI exported banks may be captured at different instants; lengths and hashes are not synchronization.
- B0 and flight may originate from different boots, input programs, or hole; selected hole/slot matches are necessary but not sufficient comparability.
- If the source chain fails, investigate archive export layout/scene and do not change flags by force.
- No live shot, new memory dump, controller action, Dolphin process, GitHub upload or model-training promotion is part of this workflow.

Next S002 owner should adjudicate any changed ball-vs-start/record/cache patterns against public PPC writer/caller source (#219) and a truly synchronized independent contact-positive control; S000 handles field dictionary/training approvals.
