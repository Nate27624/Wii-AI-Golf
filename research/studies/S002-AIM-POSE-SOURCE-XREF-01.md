# S002-AIM-POSE-SOURCE-XREF-01 — first Rev1 write/callee trace for the 17 B0–B3 aim-correlated fields

**Status:** source-PC candidate atlas + operator-confirmed 4-phase negative controls; NOT a proved C++ class/field or game-applied yaw. Source: operator-provided original B0 `RSPE01 Rev1` native MEM1 cached PPC `.text`, source-compilation boundaries `RPGolPlayer` (0x8029E62C..0x802A2210). This is deliberately **not another generic whole-RAM scanner**. The real B0–B3 banks remain on the operator PC. No code bytes, runtime heap pointers, arbitrary RAM values or raw file hashes committed.

## B0–B3 operator-evidence summary

All four source-gated selected records and paired banks passed. Across B0 idle/B1 later idle/B2 human-confirmed changed WASD aiming/B3 release-then-idle, source-selected slot0 word offsets +0x03C..+0x04C (five 32-bit fields) and +0x094..+0x0C0 (twelve fields) ALL persisted after B1→B2 aim, with no changes in idle controls. Three inactive player records stay unchanged. Separate +0x090 word changes during idle/aim/post-aim; do NOT treat as aim-specific. Source field, selected nested ball translation, all four Ball-like objects and start/pin/cup/course/wind remained unchanged. Source/semantic claims are distinct. The 17 are an association after one aim transition, not independent replicated doses.

Operator real B0–B3 math validator `audit_golf_aim_pose_math_private.py` PASS: four-phase selected `+0x03C` f32 and `+0x040..0x04C` four-float matrix satisfy `[sin(a),cos(a);-cos(a),sin(a)]` max residual B0/B1 5.938e-5, B2/B3 6.912e-5. Determinant absolute errors B0/B1 1.5024e-4, B2/B3 1.4143e-4. Both candidate 4-float groups at +0x0A0..+0x0AC and +0x0B0..+0x0BC norm approximately unity across phases (errors <=3e-8). +0x094/+0x098/+0x09C change all 3 components on aim and not idle; unknown scalar +0x0C0 also changes only with aim. This supports *rotation/pose-like encoded state* not verified physical club pose, world position, actual yaw/angle, power or trainable label.

## Direct Rev1 source instruction witnesses checked in original B0 cached MEM1

| PPC PC | Instruction-level fact | Source-relative candidate | Limit |
|---|---|---|---|
| `0x8029ED90`, `0x8029ED9C` | `lfs f1,+0x03C(r3)` then `stfs f1,+0x03C(r3)` | angle-like word | Receiver is not runtime-verified selected record |
| `0x8029EDA0`, `0x8029EDA4` | `addi r3,r3,+0x040` then branch-and-link to `0x802A3894` | four-float 2D matrix update helper | Target semantics not identified |
| `0x8029EDAC`, `0x8029EDB4`, `0x8029EDB8` | read +0x040 and +0x044 from `r29`, write +0x04C and +0x048 via f32 stores | rotational component relationship | `r29` player ownership requires caller/register analysis |
| `0x8029EE1C`, `0x8029EE2C`, `0x8029EE30` | second path loads/stores +0x03C, calls the same `0x802A3894` helper with +0x040 | independent alternate code path for rotation update | Same receiver not proven by static code-region alone |
| `0x8029FAEC`, `0x8029FAF4`, `0x8029FAFC` | three consecutive f32 stores `+0x094/+0x098/+0x09C(r28)` from stack floats | three-float candidate | Source `r28` provenance and game-space units unknown |
| `0x8029FB0C`, `0x8029FB20`, `0x8029FB28` | conditional alternate f32 stores to same 3 offsets | dynamic update path candidate | condition meaning unverified |
| `0x8029F9CC` | `stfs f1,+0x0C0(r28)` | aim-specific scalar candidate | not a swing-power field |
| `0x8029FB38`, `0x8029FB3C` | computes `r28+0x0A0` and passes it as arg to `bl 0x80295304` | first four-float group processing | actual quaternion encoding not proved |
| `0x8029FB7C`, `0x8029FB80` | computes `r28+0x0B0` and passes it as arg to same helper | second four-float group processing | target helper semantics not proved |
| `0x8029F644`, `0x8029F648` | computes `r31+0x0B0`, calls `0x8029528C` | earlier second-group source-consumer/producer | receiver lifetime not proved |
| `0x8029F6C0` | computes `r31+0x0A0` for additional transforms | first four-float group | nearby path, no dynamic identity proven |

These PCs and D-form operands were read directly from the paused Rev1 cached executable in MEM1 (no extracted main.dol needed). Many other Player compilation unit accesses to the same numerical displacements are *stack* `r1`, pointer/vtable-table offsets, or unrelated objects; do not count them as record writers without a `this` register/dataflow proof.

## Prioritized next technical investigation (no new operator input required)

1. **Trace producer provenance for record `r28` in function containing PCs `0x8029FAEC..0x8029FBA8`**: identify function entry prologue, how `r28` derives from `r3` or selected roster pointer, any conditional branches keyed to input/swing vs animation, and the true `0x80295304` helper semantics. The `+0x094` vector is NOT the ball vector: Ball object+0x04C/start stayed fixed.
2. **Trace +0x03C/0x040 rotation update call** near `0x8029ED90..0x8029EE44`: confirm the target `0x802A3894` operates on the four-float matrix, and prove caller selected-record pointer. This is strongest candidate for actual applied aim rotation if both code and future left/right response align.
3. **Determine 4-float helper semantics** at `0x8029528C`, `0x80295304`: check for quaternion multiplication/normalization vs general 4D vector rotations. Do not name it quaternion yet.
4. **Study `+0x090` separately as confound**. It was idle-sensitive, so never add it to the aim target. Other 17 fields persisted on aim; do not overfit to that single observation.
5. **Propose independent counter-direction human test only after source review and clean Dolphin session compatibility**: B0 first aim left/ B1 aim right/ B2 return center, source-resolve identical selected record, compare changes and angle–matrix monotonicity/direction; no shot or training. This is a distinct experiment from now-complete idle/aim controls and should not overwrite prior captures.

## Gate for S000 model evidence

Claims allowed: operator-confirmed no-shot aim-correlated 17 relative offsets; rotation/pose-like mathematical coherence; two candidate unit-length 4-vectors; source instruction *candidates* above. Claims NOT allowed: verified game yaw, club head angle, quaternion C++ type, physical position, collision/contact/ball flight, swing power, causal monotonic input mapping, same-frame native guest timing, model training. All raw RAM and local output remain private.