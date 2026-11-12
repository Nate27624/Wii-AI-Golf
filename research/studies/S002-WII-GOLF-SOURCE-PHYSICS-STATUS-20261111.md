# Wii Sports Golf RSPE01 Rev1 — swing-to-launch physics research status (2026-11-11)

**Status:** operator-original read-only source research and provisional offline numerical model. **NOT** a validated game-executed shot-power estimator, rendered-ball trajectory model, or training dataset. `training_approved=false`.

**Coordination:** native accepted power [#418](https://github.com/Nate27624/Wii-AI-Golf/issues/418), downstream Ball/physics [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415), upstream controller magnitude [draft PR #437](https://github.com/Nate27624/Wii-AI-Golf/pull/437), first-contact/model owner S003. This file is a research consolidation, not ownership of code/tests or approval to merge another agent's changes.

## Integrity / evidence levels

- Human operator executed bounded PowerPC/source-only reads against the original RSPE01 Rev1 **seven paired MEM1/MEM2 capture archive (14 banks)**. Local outputs reported manifest SHA-256 **pre/post PASS**, static source equality across phases **1/5/7**, and `training_approved=false`. New raw game bytes or private paths are **not** recorded in this document.
- **Static-original-source VERIFIED** means exact compiled PCs/instructions/immutable constants qualified, not that a specific native function was exercised on a particular accepted shot.
- **Public-decomp CORROBORATED** refers to `doldecomp/ogws` RSPE01 Rev1 matching symbols/layouts and math helper names.
- **Capture ASSOCIATION** means a read-only value was seen in archived captures with *human-supplied* club/phase descriptions; neither atomic frame synchronization nor club enum writer is fully proven.
- **Provisional MODEL** means code/math derived from static source but neither native floating-point parity nor recorded-flight prediction parity.
- Do not promote source-selected Ball translation to proven rendered XYZ, the hypothetical `s=0.5` to accepted on-screen power, or 100-ft off-green penalty to physical carry.

## Manager, cases, club correspondence

Source constructor `fn_802AA380` allocates parent (~6264 bytes), constructs four polymorphic children, stores them in `parent+0x0C/0x10/0x14/0x18`, and publishes **the parent** at `[r13-23168]` (SDA global `0x804BF900`). It also stores a *separate* Ball child at `parent+0x1874`; do not confuse the parent, child and selected/third Ball. Both `fn_802B4794` multiplier calls use index `parent+0x1C` and vtable slot `+0x38`; the Ball dispatcher uses selected object's slot `+0x0C`.

| Native case | Vtable | `+0x38` leaf getter | exact return f32 (display approx) | `+0x0C` launch wrapper | `+0x18` scalar method | operator-linked club |
|---|---|---|---:|---|---|---|
| 0 | `0x803C8178` | `0x802B5CF4` | 0.03700000047683716 | `0x802B5FCC` | `0x802B5DCC` | driver |
| 1 | `0x803C8138` | `0x802B5800` | 0.04100000113248825 | `0x802B5AD8` | `0x802B58D8` | iron (previous club-index context; no sample in seven captures) |
| 2 | `0x803C7FE8` | `0x802AF984` | 0.04500000178813934 | `0x802AFC5C` | `0x802AFA5C` | wedge |
| 3 | `0x803C8028` | `0x802AFE74` | 0.15000000596046448 | `0x802B00A4` | `0x802AFF4C` | putter |

All four `+0x38` leaf getter bodies are `lfs f1,<SDA2 disp>(r2); blr`. Original vtable/constant reads agreed across phases 1/5/7. The operator's **independently observed parent index** was `[0,0,3,0,2,2,2]` for captures 1..7; human archive labels are driver (1,2,4), putter (3), wedge (5,6,7). This strongly corroborates the club correspondence; a complete native club-enum → parent-index writer/control-flow proof is still an explicit boundary.

## Source-qualified input and magnitude pipeline

- The controller accessor `fn_8019BAE8` is consistent with `RPSysCoreController::getExCoreStatus` and indexes samples of `KPADStatus`, stride 0x84. Golf `fn_802B4794` uses extended-status selections 1/2/3. Filter-2's `record+0x18` = **filtered acceleration norm** `acc_value`; `record+0x1C` = **filtered acceleration-difference norm** `acc_speed` (per matching public decomp `ExStatus::calc`), **not** gyroscope angular velocity. Controller `mKPADReadLength` at +0x854 is source-matched.
- Separate filter-1 path: `fn_802B4474` calls `fn_800A6400`, copying `acc.x/y/z`; the two-f32 circular history uses filtered `acc.x` (optional sign flip) and `acc.y`, not `acc.z` in that pair. This path is distinct from the filter-2 magnitude product.
- Golf decay factor at `r2-12892` is exact f32 `0.9919999837875366` (~0.992). On the verified instruction path, with `h` the calc object and `q` the filtered status-2 record, `h+0x18` and `h+0x1C` are conditional maxima of `q.acc_value`; `h+0x20/0x24` are separate persistent recurrences of the form `f32(previous * 0.992 + q.acc_speed)`, subject to exact instruction order. `h+0x28/0x2C` retain conditional maxima of the corresponding accumulators.
- The two indirect `+0x38` calls return a **case-dependent constant** when the selected case is unchanged. Source products at `0x802B48B8/48EC` and subsequent instructions are:

```text
k = [0.03700000047683716, 0.04100000113248825,
     0.04500000178813934, 0.15000000596046448][selected_case]
A = f32(f32(calc[+0x18] * k) * calc[+0x28])
B = f32(f32(calc[+0x1C] * k) * calc[+0x2C])
calc[+0x98] = f32(A - old_calc[+0x08])
if A > old_calc[+0x08]: calc[+0x08] = A
if B > old_calc[+0x0C]: calc[+0x0C] = B
```

This pseudocode is **not** a bit-exact emulator of PowerPC NaN/rounding/branch behavior. Reset and beginning/end-of-shot conditions remain open. In state3 `fn_802B2F90` **conditionally** copies `calc+0x0C → calc+0x10` (not guaranteed unconditionally).

## State-dependent selection and post-processing

- At `fn_802B2A40`: `calc+0x1A4` state **1 → constant 0.0**; state **2 → calc+0x0C**; other observed switch branches → `calc+0x10`. Check all CFG conditions before treating this as exhaustive game behavior.
- Launch caller `fn_80299ACC` passes `r4=0` at `0x80299AE8 bl fn_802B2A40`. The selector branches between:
  - `fn_802A8110`: selected case's virtual `+0x18` callback then bounded clamp **[0,1.25]** (exact constant f32 values).
  - `fn_802A7CD8`: much more involved alternative transformation; bounded snippets show another virtual call, piecewise subexpressions, clamp [0,1] of intermediates, thresholds involving 20 and 75, `fn_802A3CF4` calls, multiple comparisons; its full CFG/formula and runtime branch predicate remain unresolved.
- Case0 virtual `+0x18` method `fn_802B5DCC` has piecewise math and calls `fn_8029683C` with `f2=0.08` lower and alternative upper `f3=0.75` or `0.25`; native `fn_8029683C` is three-way `clamp(f1,f2,f3)`. Other case callback bodies and predicates not fully interpreted.
- Alternate function calls Player `fn_8029E6D8`, which obtains two pairs of position-like fields and for a positive squared horizontal distance uses `fn_8002F874` = public-identified `nw4r::math::FrSqrt`; multiplying `distance_squared * reciprocal_sqrt` approximates **horizontal Euclidean distance**. Exact geometry owner and role in accepted shot still unverified.

## Four launch-wrapper curves (separate coefficients from magnitude multipliers)

From original PPC launch wrappers and matching `nw4r` math source, a **provisional finite-positive internal scalar** `s` is shaped by:

```text
T_p(s) ~ s ** log2(1/p)                  # FLog/FExp approximation
m      = low + T_p(s) * (high-low)
vprep  = m * (heading_x*cos(loft), sin(loft), heading_z*cos(loft))
aux    = aux_multiplier * T_p(s)
```

This is not exact NW4R lookup-table implementation, f32/Gekko parity, a gauge percentage, or a verified horizontal heading normalization.

| Case | shape p (approximately) | low | high | nominal loft | auxiliary coefficient |
|---|---:|---:|---:|---:|---:|
| 0 | 0.700 | 0.020 | 3.320 | 11° | 0.7 |
| 1 | 0.656 | 0.020 | 2.300 | 25° | 0.5 |
| 2 | 0.640 | 0.010 | 1.280 | 43° | 0 |
| 3 | 0.630 | 0.004 | 0.410 | 0° | 0 |

`fn_802A3CF4` has an original-source near-zero guard `abs(s)<0.0010000000475`, and unusual NaN/negative-input branch behavior. Normal positive capped path at case0/1/2 clamps input to <=1; case3 high cap not yet established. Do not rewrite the native function as an unconditional generic `pow`. `fn_802A7A64` constructs launch-prep output, and `fn_8029A0E0` writes to a **third/prep Ball** (`+0x88=aux`, `+0x8C=0` in the original examined path); proof of source-selected *moving* Ball identity/transfer is missing.

## Downstream physics/terrain scope

- An independent offline provisional `launch_cases_provisional.py` had 19/19 **synthetic** tests PASS and four case-specific `s=0.5` launch-prep oracles:
  - magnitudes approximately `[2.33, 1.51568, 0.8228, 0.25978]`.
- A read-only synthetic point-center/zero-spin/zero-wind integration against an operator original 2,498-triangle course collision OBJ (private exact SHA separately recorded in #415) returned **four provisional first-contact steps**, but these are **not guest-game physics ticks**, not physical carry in yards, not exact source KCol sphere-radius contact, and not evidence of real-shot landing accuracy.
- The visual mesh inspector's manual visual alignment and scale are display-only. Physics must use original source KCL native coordinates, not preview transforms or decorative tree silhouettes.

## Priority open gaps / next independently testable claims

1. **Native per-shot accepted scalar / branch condition:** verify which `fn_802B2A40` state + mode path is selected during a shot; resolve `calc+0x40` writer and the live state3/commit event. Previous human 101% gauge is not a native label.
2. **Alternate transfer:** complete `fn_802A7CD8` CFG / branch predicates (including `fn_8029E6D8`'s distance) with exact PPC FP semantics and case callback contracts. Do not fit free parameters before source audit.
3. **Club enum join:** locate writer of manager `+0x1C` and establish native club enumeration vs selected case. Seven-capture label association is strong but not the complete writer provenance.
4. **Ball identity/physics:** trace `fn_80299ACC → fn_8029A0E0/0x8029A5EC` and prove which prepared fields are installed in the **source-selected actual Ball**. Validate `+0x84` speed refresh, spin/trajectory timestep and KCol radius/triangle contact.
5. **Calibration:** only after native same-shot synchronization, compare accepted game value, on-screen percent, selected Ball motion and timed outcomes under independent trials; retain non-atomicity and censoring guards.

**Hard boundary:** no original-bank bytes, private heap pointers, coordinates, ROM, savestate, sensor payloads, or secret paths exported; no Dolphin actions or state mutation performed by this research document; no training promotion.


## Further source research — actual ExStatus nonlinear filter

The public matching `doldecomp/ogws/src/Pack/RPKernel/RPSysController.cpp` implementation of `CalcAcc` is **not** a simple fixed-rate low-pass filter. For each of X/Y/Z, writing `old` for the previous filtered component and `raw` for the incoming KPAD component:

```text
delta = raw - old
normalized = abs(delta) / threshold
gate = 1                    if abs(delta) >= threshold
       normalized**4        otherwise
alpha = rate * gate
filtered_new = old + alpha * delta
```

The public default parameters are `threshold=0.1` and `rate=0.05` for **extended status index 2** (Golf's filter-2 magnitude input); index 1 has `0.1/0.015`, index 3 `0.1/0.02`. `setExAccParam` can change the parameters, so these are **defaults, not yet proved effective in every shot**. Source for `ExStatus::calc`: starting `prev=status[0].acc`, iterate sample indices from `count-1` **down to 0**; write `acc_value=length(filtered_new)` and `acc_speed=length(filtered_new-prev)`; update `prev=filtered_new`.

**Analytical illustration (not a measured game response):** with filtered component initially 0, target acceleration `0.05`, threshold `0.1`, rate `0.05`, the gate is `(0.05/0.1)^4=0.0625`, `alpha=0.003125`, and the component moves only to `0.00015625` in one smoothing update. By contrast, for an impulse `abs(delta)>=0.1`, the gate becomes 1 and `alpha=0.05`. The discontinuity is in the **slope**, not the gate value at the threshold. These are mathematical illustrations, not calibrated Wii Remote units or exact Gekko rounding.

**Consequences for modeling:** a replay model cannot derive Golf magnitude from isolated nominal swing amplitudes alone. It needs filtered prior state, the actual sample ordering/count, input units, and potentially parameter overrides. The input waveform → controller-status conversion also remains unverified for the emulator swing primitive. This is primary-source **decomp evidence**, not newly SHA-gated PPC for the complete `ExStatus::calc` body.

Matching public primary-source links:
- [RPSysController.cpp](https://github.com/doldecomp/ogws/blob/master/src/Pack/RPKernel/RPSysController.cpp) (`CalcAcc`, `ExStatus::calc`, defaults, `setExAccParam`).
- [RSPE01_01 public symbols](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/symbols.txt) (`FrSqrt__Q24nw4r4mathFf` at `0x8002F874`).
- [NW4R FrSqrt implementation](https://github.com/doldecomp/ogws/blob/master/src/nw4r/math/math_arithmetic.cpp) (reciprocal square-root estimate/refinement), independently supporting the Player `fn_8029E6D8` positive squared-distance branch.


## Additional original-source branch result: when the alternate transfer is bypassed

Operator-original symbolic PPC around `fn_802A7CD8` gives a useful **early-exit predicate**:

- `0x802A7D14 fmr f26,f1` preserves the incoming scalar.
- `0x802A7D28 mr r29,r3` keeps the manager receiver, and `0x802A7D4C bcctrl` calls its selected case's virtual `+0x18` callback; `0x802A7D54 fmr f28,f1` saves that callback's scalar result.
- `0x802A7D50 lfs f0,-13944(r2)` is original source `1.0f`. `0x802A7D58 fcmpo f26,1`; `0x802A7D5C bc BO=4,BI=0→0x802A80A0` jumps to final clamp whenever the incoming scalar is **not ordered less than 1.0**. For ordinary finite positive scalars, `s>=1` skips the entire distance-dependent section.
- If `s<1`, `0x802A7D60 lfs f2,6252(r29)`; `0x802A7D64 lfs f0,-13924(r2)`; `0x802A7D68 fcmpo f2,f0`; `0x802A7D6C bc BO=4,BI=0→0x802A80A0`. Thus a second threshold tests **manager+0x186C** against a still **numerically unread static SDA2 f32 threshold**. Ordinary finite `manager+0x186C >= threshold` also bypasses the distance-dependent logic.
- Tail `0x802A80A0..80C4` bounds the returned `f1` by **[0.0,1.25]**, but the return of the selected case callback and its full side-effects/inputs are not yet validated in game runtime.

**Research consequence:** the alternate geometric/distance math is only eligible for a strict subset of scalar + manager-context values on the examined path; it is unsafe to apply it to all shots. The remaining minimum informative original-archive observation is **only** the constant `r2-13924` and a **categorical** per-capture test of `parent+0x186C < threshold` (never export the original runtime floats/addresses). This source gate is much smaller than another complete disassembly. This does **not** show that alternate mode actually ran during any archived shot or establish game-accepted power.


### 2026-11-11 operator original 14-bank execution of context threshold probe — PASS

The operator ran a narrowly source-gated standalone PowerShell/Python inspection on the preserved original seven paired snapshots, returning `REV1_ALT_CONTEXT_GATE_PASS`, `original_14_bank_sha_pre_post=true`. Original PC gates `0x802A7D50/58/5C/60/64/68/6C` confirmed both early-exit comparisons and source root lineage; the statically qualified SDA2 constant at `r2-13924` is **f32 300.0**. Every original capture (cases `0,0,3,0,2,2,2`) had a finite `parent+0x186C` strictly **below 300.0**. Only the boolean comparison was reported, not its source float value or native heap pointer.

**Exact logical inference:** For these archived contexts, the **manager-context early exit does not block** the distance-dependent branch of `fn_802A7CD8` *if that function is invoked*. This is only an eligibility gate. The incoming scalar must independently be **ordered less than 1.0**, and the prior `fn_802B2A40` routing based on `r4` and calc `+0x40` must first call the alternate function. No captures were proven to be at the exact shot-commit frame. **Do not claim** all seven ran the alternate transfer, that distance influences every club/shot, or that the 300-unit threshold equals game yards/feet.

**Next minimum discriminant:** inspect only source-selected Player `+0x8C` calc pointer (with original selected-player provenance), its `calc+0x40` byte and `calc+0x1A4` state, plus the source-scoped selected Ball `+0x138` calc-like pointer equality. Report boolean mode flags, integer states, and categories for scalar `+0x0C/+0x10`, never private raw floats or pointers. Confirm the native selector `r4=0` means `calc+0x40==0` takes `fn_802A8110`, nonzero takes `fn_802A7CD8`; no game-frame execution inference.


## Operator-original seven-capture discriminator: distance path threshold is 300.0 (2026-11-11)

Operator pasted a successful `REV1_ALT_CONTEXT_GATE_PASS` from their existing RSPE01 Rev1 seven-paired source archive: **14 original bank SHA-256 verified pre/post**, PPC startup SDA register checks, static load/compare/branch gates at `0x802A7D50..0x802A7D6C`, and all four parent-child vtables qualified in captures 1..7.

- Original `r2-13924` scalar is **300.0f**.
- `parent+0x186C` was **finite and < 300.0** in **all seven captures**: native case sequence `[0,0,3,0,2,2,2]`.
- Therefore the second early-bypass condition in `fn_802A7CD8` **would not** skip the distance-dependent section if execution reached it in those snapshots.
- **This does NOT establish the alternate path executed**, nor that its initial incoming scalar was `<1.0`, nor even that an archived manager observation occurred on an accepted-shot frame. The separate `fn_802B2A40` branch to `fn_802A7CD8` or `fn_802A8110` is not resolved by this table. Humans labelled captures driver/putter/wedge, but the native case-to-club writer remains unproven.

Recommended next narrow discriminator: determine `calc+0x40` branch byte **from the same source-qualified calc object** at the Ball dispatcher `0x80299AE4 lwz r3,+0x138`, identify calc object's runtime pointer/value provenance and capture mode under the actual source-selected Ball, then examine selected calc state `+0x1A4`. Do not assume a captured Ball is the one that invoked the launch dispatcher without a shot-event gate. Do not generate percent power labels or train on these archived snapshots.
