# S002 accepted-power → selected-launch boundary

**Instance:** S002-accepted-power-successor-20261122-b. **Task:** S002-P0-ACCEPTED-POWER-TO-LAUNCH-20261112. **Manager:** [S000 roster rev60](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7078315412). **Canonical issue:** [#418](https://github.com/Nate27624/Wii-AI-Golf/issues/418). Same-role administrative successor; former instance superseded for future edits, without a verified outgoing handoff. Selected-Ball initial velocity is independently owned on [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415).

**Scope:** This study records earlier original-SHA-qualified source findings and creates host-only synthetic path/f32 falsifiers. It did not examine any original ROM/MEM1 bank, connect to Dolphin/LocalOps, run a private source study, witness an accepted shot, or establish training eligibility.

## Source-qualified evidence ledger

| Edge | Status | Evidence and limitation |
| --- | --- | --- |
| fn_802B499C zero initialization through r3 | **PASS — static only** | [Source #96](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844088017), [literal #99](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844226780): original 14 banks SHA verified pre/post, phases 1/5/7 PPC/source identity. One f1=0.0f is stored at offsets +0x19C, +0x1A0, +0x1A8, +0x1AC, +0x1B0, +0x1B4, +0x1B8. Reset scalar is NOT accepted power. |
| fn_802B2AB4 nonlinear calculation to calc +0x1B0(r31) at PC 0x802B2EF4 | **PASS — static store; committed scalar UNKNOWN** | [Source #86](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6843895549). Other +0x1B0 read/write bases r26/r29/r3 are not proved to alias r31. Equal field offset does not establish receiver identity or executed instruction ordering. |
| fn_802B3BA0 direct zero-initializer call at PC 0x802B3E80 | **UNKNOWN — receiver/CFG** | [Static caller join](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844106926). Prove whether r3 at call aliases r29 of later +0x1B0 writes, with feasible branch/path timing. Lexical earlier/later PC ordering is not execution proof. |
| calc +0x40, state +0x1A4, flags +0x1A8/+0x1BC, fn_802B2A40 selector, possible fn_802A7CD8 route | **UNKNOWN — acceptance/commit branch** | Need branch reaching-def, context and live acceptance semantics. Raw controller magnitude, animation frame +0x90, human meter 101%, transient +0x08/+0x0C, and redline threshold are not validated committed power. |
| Source-conditional wrapper fn_802A7A64 case1 auxiliary at PC 0x802A7ACC | **PASS — conditional static transform only** | [Case1 witness](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844637943): aux=f32(0.5*f28), exact inversion in ordinary f32 absent halving underflow. No proof that the qualifying case1 executes on the selected shot or f28 is accepted power. |
| fn_8029A0E0 third/prep Ball +0x88 aux and +0x7C prep vector to actually selected Ball launch +0x78/+0x7C/+0x80 and pre-step epoch | **UNKNOWN — selected Ball receiver** | [Conditional two-field invariant](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844658942). Third/prep vs global vs source-selected Ball, state==3, mode r4/r30, copy/overwrite, shot clock and first eligible guest step belong to the separate #415 owner; first post-step measurement is not pre-launch p0/v0. |

**Overall:** actual_accepted_power_verified=false; selected_launch_p0_v0_verified=false; native_game_parity_verified=false; training_approved=false. Static instruction evidence is real original-source-qualified evidence; passing a new host-only test cannot promote it into a guest-executed or same-shot fact.

## Implemented bounded synthetic falsifiers

The newly added script evaluates paths with synthetic receiver identifiers and ordered symbolic operations nonlinear / reset / other_write / read. For one receiver, nonlinear→reset→read is killed; nonlinear→read→reset is live at that read; a reset on a distinct receiver cannot kill the first. The checker classifies bypass/no-definition, mixed feasible branches, incomplete CFG, unproven alias, and malformed/unbounded input without inventing native receiver equality. All test outputs explicitly identify synthetic scope and never set native power, launch, or training flags true.

The case1 half-multiplication numerical control verifies 1,001 ordinary host float32 round-trips and the smallest positive subnormal failure. Host float32 arithmetic is not verified Gekko FMA or native SinCosFIdx parity.

Source-only CLI: python scripts/audit_p0_accepted_power_launch_boundary_private.py --stage=ledger; additional synthetic controls: --stage=synthetic-controls. These emit allowlisted JSON only. They never read private source/captures or execute Dolphin/LocalOps.

## First native-source discriminator — requires separate Y/N authorization

On a reviewed exact-SHA pinned script/head and operator-approved local original archive, derive the feasible CFG paths through the fn_802B3BA0 call PC 0x802B3E80 and show PPC must-def of incoming r3 versus the later r29 +0x1B0 writer and nonlinear r31 output PC 0x802B2EF4. Follow f28 to fn_802A7A64 only when source-qualified receiver, guard and same-shot commit allow. Return sanitized typed SAME_RECEIVER_AND_LIVE / DISTINCT_OR_KILLED / UNKNOWN, preserving 14-bank pre/post SHA and source-phase checks. Include branch bypass, overwrite, reset-after-consumption, ABI call-clobber and incompatible state/flag controls. Then cross-link the qualified third/prep→**selected** launch receiver proof needed from #415. Do not repeat already completed #86/#96/#99 broad scans or assume a field is an accepted power label.

## Test and merge constraints

- Focused: python -m unittest discover -s tests -p test_p0_accepted_power_launch_boundary.py -v
- Full: python -m unittest discover -s tests -v
- Exact-HEAD Windows and Ubuntu CI required before non-draft/merge, per root merging.md.
- No changes to S001 launch, S003 model, #415 selected Ball v0 files, common source readers, native/private source, or training/publication.

**Unresolved blocker:** current source receipts do not provide same-shot full receiver/CFG or actual selected Ball transfer. Any actual new source study requires separately verified script/checkout authorization and one operator Y/N via private LocalOps.