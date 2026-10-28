# P0: exact native OnCalculate → Golf main source-call census

## Original user evidence

In original 7 preserved RSPE01 Rev1 Golf mode4 captures, exact #279 commit
`367aa1e371040a65dfffd164c19ba89ea66ea2f6` with 13 synthetic tests and canonical 14-bank original SHA before and after, the two-source-word audit
at `0x8028DFA8` identified:
- `lwz r3,+0x9C(r3)` (scene member RPGolMain* candidate)
- exact non-linking `b` target `0x8028E158`.
- scene `+0x9C` member class MEM2 in **all seven** captures.
Public `kiwi515/ogws_info` RPGolScene.h labels `OnCalculate` at this address. Independent `doldecomp/ogws config/RSPE01_01/symbols.txt`, immutable Git blob `ec42efd5ef247dff7920e905f9004fc579dd3f74`, records exact `fn_8028E158` size `0x194` (101 instructions). The source function bound is corroborated; **vtable execution, simulation-step cadence, render-frame join and physics are not**.

## Novel bounded question (not another broad pointer scan)

With original seven-bank SHA and two-word source identity unchanged, scan ONLY the exact
`0x8028E158..0x8028E2EC` source code window and classify:
- source direct PPC `bl` destinations (public code PC and membership in
  known RPGolMain, RPGolMapObjBall or RPGolSimulateManager code units)
- static conditional branches `bc`, nonlinking direct `b`
- PPC indirect link/branch forms `bclrl`, `bcctrl` that prevent a no-simulator-call conclusion

Report source direct-BL count into published SimulateManager code region as a
**syntactic target count only**; `0` does NOT rule out indirect simulator
calls; `1` does NOT prove exactly one game physics update per OnCalculate
because branches and dynamic call eligibility remain unproven.
Source instruction windows must remain bitwise identical across all 7 captures;
`#231` original bank+manifest SHA before and after is mandatory.
No raw PPC words, private pointers, float values, RAM or ROM in report.
All guest physics clock, actor/renderer, XYZ/velocity/contact/impact/power/score,
frame attestation and model training remain FALSE.

## Pre-registered decision

1. **Positive syntax:** any direct BL targets published SimulateManager source unit →
   owner #279/#272 should assess whether that particular callee genuinely advances
   gameplay and is gated by branches; may require exact source CFG and game-step frequency.
2. **Negative syntax:** no such BL but indirect link/branch → ABSTAIN about actual update;
   do not start scanning arbitrary helper call chains.
3. **Stop:** no defensible game-simulation-step identity from this single 101-word
   source function → #215/#272 should focus on verifying installed Felk build/event
   API and smallest safe no-input, no-hook feasibility; no new source micro-PRs or shots.

## Ownership

Draft child stacked on #279; S001 #215/#166 owns runtime timing and any emulator
interaction, S002 #240/#219 owns global/selected ball provenance, S000 #205 privacy,
#248 owns dual-object sample acceptance. Do NOT merge child independently, alter
Dolphin, register breakpoints, pause/resume the coroutine, send gameplay input,
capture new shots or approve training/publishing. A frameadvance/bridge tick is
NOT an authenticated game physics step. One native source-only run after Win+Ubuntu CI
and exact immutable PR pin is sufficient.


## Independent original prefix witness and mandatory crosswalk (2026-10-28)

S002 agent's separate source-gated REAL original seven-bank archive #279 commit `26e821973da8a2d6e5768d4527febcfe24ff2356` (15 synthetic PASS; 14 SHA-preserved banks before/after; 7 scene chains) scanned ONLY first `0x100` bytes of exact public `fn_8028E158`. The original report established **10 direct BL source instructions**, **2** with targets in the published SimulateManager unit, at **FUNCTION relative** `+0x007C -> 0x8029B554` and `+0x0090 -> 0x8029B43C`, plus five conditional branches. External Rev1 ogws symbol source independently identifies both targets as function **entry points**: `fn_8029B554` size `0x28` and `fn_8029B43C` size `0x118`. This confirms call-site syntax in a limited 0x100 prefix only; it does NOT prove physics execution/cadence.

The initial #283 report field `source_main_unit_relative_pc` subtracts published unit start `0x8028E098`, not function entry `0x8028E158`, a difference of `0xC0`. A positive native report must show **both** coordinates consistently: `function+0x7C / main-unit+0x13C` and `function+0x90 / main-unit+0x150`. The new `source_main_function_relative_pc` field and `require_prior_prefix_match` enforce count 10, exact two entrypoint targets at those two function-relative sites, and unit-vs-function `0xC0` offset arithmetic, before the full 101-word source report may pass. A discrepancy is **ABSTAIN**, not a new simulation function claim. Further semantics and call frequency remain unknown despite exactly two syntactic direct calls.


## Real original complete 101-word OnCalculate main audit; three exact SimulateManager callees

The operator ran exact reviewed immutable #283 code SHA `2d5fa0f1693490bab5771506a22a2dffdd934d6c`, 15+13=**28 synthetic tests PASS**, canonical original **14 banks SHA before/after PASS**, stable source code in seven Rev1 bank pairs, and independent 0x100 first-prefix gate PASS. Full `fn_8028E158` 0x194 (101 PPC instruction) source report yielded **18 direct BL instructions**, 5 conditional branches, 0 indirect linked branch, **3** direct calls to published `RPGolSimulateManager` function entrypoints:
- Main **function-relative +0x007C / Golf-main UNIT-relative +0x013C** → `fn_8029B554` exact Rev1 size `0x28` (10 PPC words)
- Main **function-relative +0x0090 / UNIT-relative +0x0150** → `fn_8029B43C` exact Rev1 size `0x118` (70 PPC words)
- Main **function-relative +0x0168 / UNIT-relative +0x0228** → `fn_8029B57C` exact Rev1 size `0x274` (157 PPC words)

All three public function identity/size bounds independently corroborated by immutable ogws US Rev1 `config/RSPE01_01/symbols.txt` blob `ec42efd5ef247dff7920e905f9004fc579dd3f74`. Original report fields explicitly preserve `actual_execution_or_receiver_type_verified=false` and `physics_step_verified=false`.

## Last static discriminator: caller control versus 3 exact function source footprints

This PR now adds a self-contained pure `scripts/review_p0_three_sim_callee_footprints.py` using **only** 10+70+157=237 exact PPC words of the **three** authenticated direct target functions, no indiscriminate code xrefs, and **four** intervening instruction slots at main function +0x80/+0x84/+0x88/+0x8C between first and second SimulateManager calls. Emit only bounded source-control categories: exact direct BL code-target PCs; D-form integer and float store/read syntactic site counts and displacements; conditional and indirect branch presence; conditional branch forward target that could bypass second call. Do NOT infer any D-form store accesses a ball or a function is a pure predicate from lack of recognized stores; X-form stores are counted separately but not resolved to object fields. The gate requires previous exact native main audit **all 101 words** and positive first 0x100 10-BL/two SimManager source-call witness, verifies all three callee words identical across seven original SHA/scene/owner-qualified captures and retains 14-bank SHA before/after. Zero raw source instructions/private RAM values/file paths/float content reported.

**Decision and stop:** If the 10-word `fn_8029B554` is a branch/predicate gate, that can explain why the subsequent `fn_8029B43C` is conditional, but it does NOT verify real game behavior, physical velocity, step cadence or observable ball. If stores or direct calls appear in the 70/157-word target functions, only typed, owner-verified ball receiver/dataflow could justify ONE more targeted source hypothesis; otherwise STOP source scanning. Primary P0 remains local installed Felk binary identification, independent GOLF physics-step hook/cadence, same-hook selected/global/source CC read and rendered visual witness (S001/#272/#215 and #248) after S002/S000 review. No new Dolphin, shot, hook or training/publishing.


## Actual canonical original operator three-callee result (2026-10-28)

At exactly verified #283 commit `29568ac656ea5c6adee8b7a409a30cf3c52f36e9`, the operator passed **12+15+13=40 focused tests** and original **14 SHA-pinned banks before and after**, with all seven source/scene/function-prefix/callee window gates. Native report `P0_THREE_SIM_CALLEES_AUDIT=PASS`. No runtime emulator was launched.

| Callee | PPC words | BC | Indirect branch opcode | Direct BL | Observable source memory effects |
|---|---:|---:|---:|---:|---|
| `fn_8029B554` | 10 | 0 | 3 | 0 | no D-form stores, no float loads, no indexed-store candidate in bounded census; **not proved pure predicate** |
| `fn_8029B43C` | 70 | 8 | 1 | 12 | only **r1 stack-relative integer D-form stores**, 1 float load, 0 float D-form stores or indexed-store candidates; direct BL at function **+0x0038 -> fn_80299ACC**, **+0x0044 -> fn_80299BE4** |
| `fn_8029B57C` | 157 | 17 | 1 | 7 | **float D-form store** at function **+0x0050** using **r26+0** (D-form source f32 store class, not proven receiver), 3 float loads, 2 untyped indexed-store candidates, 2 r1 stack stores |

The same source main control gap between `B554` BL at function `+0x007C` and `B43C` BL at `+0x0090` has a **backward conditional branch at `+0x0088` targeting `+0x006C`**. This is a syntactic backward control edge; no dynamic loop count, per-scene update cadence, executed-call path or clock is established.

**Highest-signal link:** `RPGolScene::OnCalculate` annotated two-word thunk → `fn_8028E158` → `fn_8029B43C` → already independently investigated cache caller `fn_80299ACC`. That is a source-only chain into the cache-writer receiver study #254/#257/#263, **not** proof of source receiver object identity or any physical ball. Source `fn_8029B57C+0x50` `stfs ...,0(r26)` is a precise static FLOAT WRITE candidate; `r26` is not proved to alias selected/global+0x4C translation, so do **not** promote to world XYZ, velocity, power, contact or training.

### Code-review self-consistency fixes after real operator study

Reviewers identified two *synthetic-only contract weaknesses*, not failures of the original 40-test bank-qualified native report:
1. `require_prior_prefix_match` previously checked only 10 direct BL and two SimManager targets; it now also requires independent first-0x100 native-source `5 conditional BC, zero direct unlinked B, zero bclr/bcctr` on the actual original words. Its fabricated positive fixture was updated to include five BC and negative altered BC/B/bclr regressions.
2. `review_p0_three_sim_callee_footprints.analyze` previously trusted target rows from the same report without independently decoding matching `main_words[+0x7C/+0x90/+0x168]`; it now requires exact opcode-18 LK=1 and target equality, and refuses NOP/tampered or unlinked source BL with contradictory report rows.

These are **owner-review changes**, not independent revalidation of prior historical SHA. Do not request another original W5-W7 source scan just to reprint a previous result; require green synthetic CI and owner check before any future native use. Stop this static SimManager call tree unless a precise object/field alias hypothesis is independently sourced. The next P0 is guest game update-step provenance for the actual installed Felk binary and safe same-hook dual-ball+visual witness; existing public VI frame, frame-drawn, and raw code breakpoint events do **not** supply that step ID. All runtime/physics/training flags remain FALSE.

## Independent Gekko store-effect review: zero D-form float stores is not no state writes

Review of the three source-qualified SimulateManager call targets in this study identified a **source-classifier false-negative risk**, not an observed misclassification in original private banks. The previous exact 10+70+157-word footprints count D-form `stfs/stfsu/stfd/stfdu`, ordinary GPR D-form stores and a selected op31 X-form store list. They did NOT count the actual Wii/Gekko **paired-single memory store opcodes** or certain op31 stores. Source reference: public Felk/dolphin US Rev1-capable PPC opcode table [`Source/Core/Core/PowerPC/PPCTables.cpp`](https://github.com/Felk/dolphin/blob/a22afcb10b97c251e17e46f2982d4e37729d32a1/Source/Core/Core/PowerPC/PPCTables.cpp), immutable Git blob `24d9040c6ed7e2bbd47c339f4ca6a4e6b013c365`: primary `60=psq_st`, `61=psq_stu`; primary 4 table4_3 modulo-64 subop `7=psq_stx`, `39=psq_stux`; primary 31 XO `983=stfiwx`, `662=stwbrx`, `918=sthbrx`, `661=stswx`, `725=stswi`. These are source-recognized *memory writes* even when conventional `float_D_form_store_sites` and `X_form_store_candidates` are empty.

New synthetic-only fix to `scripts/review_p0_three_sim_callee_footprints.py`: adds `source_wii_memory_store_hazards_not_typed_to_ball` with **only source-function-relative code offsets, broad opcode classes, and `receiver_alias_or_actual_ball_write_verified=false`**, plus a hazard count. It does not pretend the paired-single quantization instruction has a plain 16-bit stfs displacement; no raw instruction bits or data are printed. Adds `source_store_effect_exhaustively_classified=false` to **all three callee records, including zero hazard count**, and retains `pure_predicate_or_game_ball_integrator_verified=false`. The previous D-form and common X-store counters remain for cross-report comparison.

Fabricated negative tests demonstrate that PSQ loads and paired arithmetic are **not** misreported as stores, ordinary `stfs`/`stfsx` are not double counted, all four PSQ Gekko store classes are recognized, and six unusual indexed/string/float-word stores are at least conservatively flagged. A source-only PASS on these synthetic tests does NOT mean those opcode classes occurred in the original Rev1 14-bank records or that `fn_8029B43C`/`fn_8029B57C` writes a golf ball. The earlier original user audit at commit `29568ac...` remains valid only for its **narrow named recognized D-form/X-form categories**; its zero float-D-form-store count MUST NOT be promoted to `does_not_modify_ball` or `pure predicate`. The existing actual `fn_8029B57C` `stfs f?,0(r26)` remains a source FLOAT store with an unproven r26 receiver, not physical XYZ, velocity, power, impact or score.

Owner next step is **one** source-gated rerun ONLY IF one of these additional store hazard classes would change the decision to investigate a particular callee; otherwise honor original STOP rule and focus on installed Felk execution-qualified game-step clock. No broad PPC scan, duplicate PR #283 inventory, Dolphin, shots, hooks, new dumps, raw output, physical render/kinematics or model training. Code review child stays DRAFT until #283/#279 S001/S002/S000 adoption.
