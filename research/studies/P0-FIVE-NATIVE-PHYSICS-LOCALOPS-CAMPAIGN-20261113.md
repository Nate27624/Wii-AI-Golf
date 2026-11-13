# Five original-source studies for native Wii Golf flight — operator staging

**Status:** Staged research only. ZERO new LocalOps executions on this branch. **Current test mode has NO WIND** per operator clarification: [physics issue #415](https://github.com/Nate27624/Wii-AI-Golf/issues/415#issuecomment-6844221952). A separately prepared optional wind source script is DEFERRED for this mode, not a P0 run target.

## Exact five-study queue, with canonical owners

1. **Accepted-power calc liveness / same-object overwritten register** — existing S002 accepted-power owner, #418, source archive draft #454. Existing operator-approved #96/#99 triple-store/constant source findings are prerequisites, not shot-power proof. New CFG receiver alias/overwrite source study must be implemented *by that assigned owner* on their paths: distinguish r31/r29/r26/r3 and whether nonlinear calc output reaches selected launch rather than zero reset. No new runnable mode claimed by this draft.
2. **Selected Ball v0 must-def / branch identity** — existing S002 selected-v0 owner, #415 draft #455. Reuse its `--study mode` followed by `--study alternative` and `--study gates`, one qualified run/receipt at a time; distinguish selected/source-global/third receiver and vector overwrites. Do NOT submit unbounded `integrator` mode.
3. **+0x84 speed and q state refresh / airborne source order** — same S002 #455 owner `--study speed` existing bounded source study; hand result to assigned S003 airborne owner. Test retained speed/q versus recomputed state; source branch/receiver, guest timing and force-vector updates remain UNKNOWN until independently proved. This is distinct from v0 writer study.
4. **IMPACT-DAMPING-1: conditional contact vs airborne damping** — NEW staged no-argument script `scripts/research_p0_native_impact_damping_private.py`. Source-qualified direct integrator-to-force/collision/vector calls and bounded conditional 0x98 source neighborhood; output `damping_precontact_reachable=UNKNOWN`, `damping_frequency_per_step=UNKNOWN` until CFG/receiver proof. Hypotheses: 0.98/0.96/0.97 contact-only, or reachable precontact / repeatable under an eligible branch. Do not insert blanket drag into airborne model.
5. **Native Ball/KCol first contact and response** — NEW staged no-argument script `scripts/research_p0_native_kcol_response_private.py`. Source-qualified Ball+Player KCol call targets and state/velocity candidate D-form sites; output contact response order, selected receiver and query-radius semantics UNKNOWN. Generic first-contact numerical bugs (#467 and related) remain separate S003 owned corrections.

**DEFERRED optional source probe:** `scripts/research_p0_native_wind_transfer_private.py` remains on this draft branch only for a separately relevant mode; DO NOT queue its LocalOps execution in the present no-wind campaign.

## Source/research gate and shared Windows checkout

Both new P0 studies import the **same Git checkout** source reader from draft #454, not a separate native reader. Original manifest/header, all 14 original bank SHA before+after, public Rev1 source ownership, phases 1/5/7 equal PPC windows, native helper call gates, bounded output under 1900 chars and synthetic PPC controls are required; fail closed with sanitized `DIAGNOSTIC_ABSTAIN`. No ROM, private paths/bank bytes/metadata, Dolphin input, native shot evidence or training promotion. `allowed_to_publish=false`; `training_approved=false`.

S000 must refresh roster rev46 pinned to stale main, allocate the new Study 4/5 paths without overlapping existing S002/S003 source owners, resolve #454 dependency and actual S003 airborne agent CLAIM. Parent #454 is a draft: **this stacked branch MUST NOT be merged or checked out automatically.** Each LocalOps operation uses one separately reviewed exact-SHA Git head, clean shared checkout and the Windows operator's individual Y/N; inspect terminal `LOCALOPS_RESULT_V2`, provenance and feedback before proceeding. Do not queue simultaneous checkout or run five pending requests. No forced cleanup/retries after decline.

### Examples of PRIVATE LocalOps run_research request bodies — ONLY AFTER authorized checkout

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/research_p0_native_impact_damping_private.py","args":[]},"intent":"Read original Rev1 Ball integrator and conditional impact-damping PPC sites with provenance gates.","expected_output":"14-bank source-pass and branch/call candidate matrix; precontact eligibility and selected receiver unresolved."}
```

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/research_p0_native_kcol_response_private.py","args":[]},"intent":"Read original Rev1 Ball->KCol collision calls and state-field candidates after separately approved checkout.","expected_output":"SHA/phase/source-call gate and bounded PC/register candidates; native collision/ball radius unverified."}
```

**Do not send these templates until manager ownership and exact reviewed source checkout are confirmed.** Studies 1–3 are owned by existing agents, and their actual execution on private preserved evidence remains to be separately established. See [coordination request](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-6844077668).

## Independent follow-on: NORMALIZER-GUARD-1 (not a sixth queued local job)

**Why it matters:** Source-backed lift `L=(-vx*vy,vx²+vz²,-vz*vy)` and lateral `S=(vz,0,-vx)` are normalized on eligible nondegenerate paths, but the exact native compare, branch and zero-vector/near-zero threshold remain unknown. The existing provisional model's `EPS=1e-10` is a **Python simulator choice**, not a verified Wii guard. The finite force direction can reverse when horizontal velocity changes sign; implementing a guessed cutoff can make predicted flight diverge sharply.

**New, nonoverlapping read-only script** `scripts/research_p0_native_normalizer_guards_private.py`: inspects bounded original-PC neighborhoods `0x80295F3C..0x80295FE0`, `0x80295FE0..0x8029605C`, `0x8029605C..0x80296120`, **as candidate windows, not asserted complete function ranges**. Decodes source PPC `fcmpu/fcmpo` FP register operands, `bc` conditional branch BO/BI/AA/LK and targets, and direct helper `bl` to candidate magnitude/scaling target. Original archive 14-bank SHA pre/post, phases 1/5/7 identical, public source unit check and baseline nonlinear gates are required before releasing a compact private receipt. Even if a compare/branch is observed, the script correctly retains `native_epsilon_or_exact_zero_proven=false`, `zero_branch_operand_proven=false`, and `same_selected_ball_receiver_verified=false`; a follow-on must track FPR reaching definitions and path eligibility to prove semantics.

**Positive/negative offline controls:** tests reject noncompare XO instructions, signed/absolute misdecoded branch targets, altered source phase, truncated windows, output-cap overflow, and false promotion of FP compare syntax to native zero threshold. Separate cross-platform workflow verifies focused/full regression. No private source bytes, ROM, local paths, emulator, or training approved.

**Approval/ownership:** S000 should explicitly allocate this additional source-study file separately from all existing assigned #415/#418 S002 work (or assign it to an existing compatible source owner). Do not queue it ahead of the **five** critical-path launch/flight/contact studies and do not execute it unless the exact dependent reviewed #454 branch is present in the shared clean Windows worktree, the operator individually approves checkout and run, and CI has passed.

Optional exact private LocalOps request body *after all gates*:

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/research_p0_native_normalizer_guards_private.py","args":[]},"intent":"Source-audit Rev1 lift and lateral FP comparison and branch candidates at native normalizers.","expected_output":"Fourteen-bank SHA/phase qualified compact PPC compare/branch evidence; normalization epsilon and selected Ball remain unproven."}
```
