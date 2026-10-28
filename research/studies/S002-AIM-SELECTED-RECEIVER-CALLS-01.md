# S002 — verified PlayerManager callsites into rotation updater (Rev1)

**Evidence:** operator's source-gated read-only B0 memory scan, RSPE01 revision 1. Derived from preserved private B0 MEM1/MEM2 and cross-checked against selected-record source gates; this document contains only executable instruction addresses/words, no raw heap memory, private dumps, or user paths.

## Direct callsites (observed)

- `0x802A293C lwz r3,+0x334(r29)`; after reads and condition checks that do not overwrite r3, `0x802A2968 bl 0x8029ED2C`.
- `0x802A2B00 lwz r3,+0x334(r29)`; `0x802A2B04 mr r4,r28`, `0x802A2B08 mr r5,r27`, `0x802A2B0C bl 0x8029ED2C`.
- Both callers lie in `RPGolPlayerManager.cpp` text range `0x802A2210..0x802A3560` (RSPE01_01 public linker split).
- The manager's +0x334 field is already source-backed and was observed to equal the selected record address in the verified private snapshots (S002 #160/#163). This now links **the direct-call argument r3 to the source-selected player-record pointer**, conditional on the validated manager receiver identity in these caller functions.
- Callee `0x8029ED2C` stores incoming r3 to r29 at `0x8029ED50` (`mr r29,r3`). It adjusts a scalar at `+0x3C`, calls `RPGolMath.cpp` helper `0x802A3894` with output at `record+0x40`, and writes derived values at `+0x48/+0x4C`. Helper writes two adjacent floats at output+0/+4 via `0x802A38C0/C8`.
- B0→B1 idle and B2→B3 idle show no change in those fields; B1→B2 WASD aim changes scalar by **−25.12699 degrees** and associated two-dimensional rotation and quaternion-like candidates. Within-session *numeric consistency* is not an independently observed heading calibration.

## What this proves and what it does not

This is stronger than offset coincidence: two separate direct callers explicitly load their r3 argument from the source-selected pointer slot before calling the matched angle-update function. The exact control-flow and r29 manager provenance should still be independently reviewed. It does **not** verify absolute shot heading, axes, angle sign convention against the GUI, active ball world XYZ, velocity, shot power, or training suitability.

## Next tests

1. Assert both call sequences and callee pointer-transfer instructions against the existing private Rev1 B0 code image (synthetic tests for a forged or modified opcode).
2. Verify the caller's r29 provenance with a narrow source function-prologue walk. No new RAM dump required.
3. Later, once the owner authorizes input experiments, take opposing WASD-only aim observations with stable selected slot/hole and correlate delta sign. No swing required.
4. Keep publication of native memory and model training disabled until S000/owner review.

**Agent handoff:** S002 #162/#144 check pointer provenance; S002 #181 use this field map for the 17 aim-associated words; S001 #166 consume source-gated angle only after integration review; S000 #154 retain nontraining, nonphysics gate.

## Operator confirmation from actual B0 source-gated run

The operator executed `audit_golf_selected_aim_callers_private.py --private-root` on the real preserved B0 pair and returned **both** matching direct callsites, `callee_preserves_argument_r3_in_r29=true`, and `selected_player_pointer_source_contract_verified=true`. Output:

- `source_direct_calls_verified = 2`, with load/call PCs `0x802A293C → 0x802A2968` and `0x802A2B00 → 0x802A2B0C`;
- both show `argument_r3_loaded_from_r29_plus_0x334=true` and `r3_preserved_to_direct_call_on_checked_path=true`;
- `manager_r29_runtime_identity_independently_verified=false`, `actual_shot_heading_verified=false`, `ball_motion_verified=false`, `training_allowed=false`, `allowed_to_publish=false`.

These are **actual operator-run results**, not synthetic CI, and source-pointer linkage is now evidence-backed. The previous report's outstanding `r29` caller-owner identity caveat remains; a proof of a direct call through `+0x334` does not by itself prove every caller owns the same manager instance in every mode. It also does not prove world axes, shot power, or physical golf heading. The matching code and original private RAM were not uploaded to GitHub.

Next bounded source pass should identify each caller's `r29` definition and intervening instructions in the existing B0 code image; no additional emulator action is required.
