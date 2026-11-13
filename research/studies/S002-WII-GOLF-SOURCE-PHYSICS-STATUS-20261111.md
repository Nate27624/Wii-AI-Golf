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
- **This does NOT establish the alternate path executed**, nor that its initial incoming scalar was `<1.0`, nor even that an archived manager observation occurred on an accepted-shot frame. This specific table did not recheck the route flag, but an **earlier independent operator original-archive audit** did: see the reconciliation below. Humans labelled captures driver/putter/wedge, but the native case-to-club writer remains unproven.

Do not assume a captured Ball is the one that invoked the launch dispatcher without a shot-event gate. Do not generate percent power labels or train on these archived snapshots.


## Reconciliation with prior original-archive route data (do not repeat this audit)

Earlier operator SHA-verified source evidence already reported in [#418 comment 6518944979](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6518944979):

| Original capture(s) | Native calc state `+0x1A4` | Calc flag `+0x40` | `fn_802B2A40` route at caller mode `r4=0` |
|---|---:|---:|---|
| 1, 3, 4 | 0 | 0 | **B** `fn_802A8110` |
| 2, 5, 6, 7 | 3 | 1 | **A** `fn_802A7CD8` |

The earlier original study also noted the source-selected calculation object pointer matched across all seven captures and provided **W5/6/7 `calc+0x10=calc+0x0C` about 0.466131** (stable over their non-atomic human-phase snapshots); D2 `calc+0x10=calc+0x0C` about 0.586430. These are *intermediate source-selected scalars*, not accepted shot powers, physical-speed values, or on-screen meter labels. Exact runtime branch execution and private same-frame causal joins remain unverified.

**New combined evidence:** in 2,5,6,7, route A is **statically eligible under the archived calc flag**; the newly verified manager `+0x186C<300.0` does not block its geometric subpath. The remaining source gate to assess per capture is the selected scalar `s<1.0`: the earlier sample descriptions report W5/6/7 and D2 `calc+0x10` below 1, but should be requalified if an actual guest frame is needed. This implies a coherent *candidate* path for 2/5/6/7, not observed launch execution. Route A function and case0 callback do not supply a validated on-screen power percentage.

**Next high-value research:** prefer static branch/dataflow from accepted-shot event into Ball launch and third/prep→selected Ball propagation, plus exact mode-flag setter provenance, rather than additional club-index, constant, or route-flag remeasurement.


## 2026-11-11 continuation: setter/callback research gate (public symbols; not new private proof)

The operator's **already completed** `REV1_FLAG_INITIALIZER_CALLER_SCAN_PASS` [#418 comment 6812959343](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6812959343) proves original PPC for the complete `fn_802B4988` 20-byte leaf: `lfs f0,0(r2-13196)` (**0.0f**), `li r0,1`, `stb r0,64(r3)`, `stfs f0,440(r3)`, `blr`. Original GolfScene and GolfPlayer text units contain **zero direct BLs** to that target, not proof there are no indirect calls or direct calls elsewhere.

Independent **public RSPE01 Rev1 symbol map** shows `fn_802B4988 .text:0x802B4988 size 0x14`, and that the **candidate** selected calculator vtable at `lbl_803C8108` is a `.data` symbol with **size 0x10**; nearby four case vtable objects `0x803C7FE8,0x803C8028,0x803C8138,0x803C8178` have size `0x40`. Type/data contents have **not** been read from private archive in this continuation: don't infer `fn_802B4988` is actually in any of these tables without a real original static pointer match.

**Bounded next local source-only test:** scan only qualified static data `0x803C0000..0x803D0000` for the **exact pointer value** `0x802B4988` across original captures 1/5/7. Positive controls: four previously source-gated vtable `+0x38` method targets at `0x803C81B0/8170/8020/8060`. Check original 14-bank SHA pre/post, PPC setter leaf and address control gates and per-phase **candidate matches**, not blanket data-region equality (other fields may vary at runtime). Print only qualified public table addresses and whether the four-word `0x803C8108` candidate table contains source-text pointers. `NO POINTER MATCH` is a **negative result for the scoped 64KiB** only; it does not disprove registration in other data, direct B/BC tail calls or an address formed by instructions. A pointer match requires subsequent table/dispatch/calc-receiver proof before mode semantics.

**Progress priority:** a same-object invocation path for `+0x40` is higher value than further numeric coefficients or synthetic shot distance. True executed shot commit and prepared-to-selected-ball copying remain independent requirements.


## 2026-11-11 operator original-survey negative and subsequent accepted-power lead

Operator executed the independent, bounded `REV1_FLAG_SETTER_STATIC_POINTER_SURVEY_PASS`: original 14-bank SHA pre/post verified; PPC gates for `0x802B4988` and known four `+0x38` vtable positive controls passed; original 1/5/7 static pointer hits identical. **Exactly zero aligned dwords** in `0x803C0000..0x803CFFFF` contain `0x802B4988`. Candidate `0x803C8108` four-slot table's `+0x08` word was categorized as pointer `0x802B4E04`; the tool suppressed values that were not code pointers, so blank `+0x00/+0x04/+0x0C` are **NOT evidence of zero/null**. The public Rev1 symbols list `fn_802B4E04` as function size `0x5C`. No proof that the calculator vtable is an initializer dispatch table, and the scoped zero-match does not exclude other data, code-built function addresses, indirect calls, or unscanned direct calls. **Do not repeat the 64KiB exact-pointer sweep.**

More promising and independently **already operator-original source qualified**: [#418 comment 6813121520](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6813121520) traced `fn_802B2AB4`:
- `0x802B34D4 bl fn_802B2AB4` then `0x802B2AEC bl fn_802B2A40` (mode 0).
- Following selected scalar `x`, `0x802B2AF0..0x802B2B30` apply a threshold-triggered affine transform with unknown but statically referenced SDA2 constants `r2-13192/-13032/-13028/-13024`; the no-transform branch preserves `x`.
- Case index 3 selects a different threshold (`r2-13148` vs `r2-13020`) and 0x2B50..2B5C compares/CROR/branches to choose a smoothing coefficient (`r2-13016` vs `r2-13052`). `0x802B2B70 fmadds` then `0x802B2B74 stfs f0,+0x04(r31)` performs **one native f32 FMA update of calc+0x04**, not a separately rounded interpolation. `0x802B2B78 bl fn_802A7C50` next obtains a minimum-redline threshold, not yet an accepted-power label.
- The eight SDA2 numeric values, the exact CROR condition, and post-`2B78` consumers remain unverified as numeric results. The manager/calc receiver and original source PCs were qualified by the separate operator audit, **not reproduced in this document**.

**Next small discriminant** is source-gated static read of these eight f32 constants and CROR BT/BA/BB, followed by forward dataflow from the calc+0x04 write and redline getter; this is more informative than further attempts to find the flag setter in another arbitrary static region. Neither `calc+0x04` nor `calc+0x10` is promoted as native accepted percentage; `training_approved=false`.


## Original Rev1 operator source PASS — exact eight post-selector scalar constants and CROR (2026-11-11)

The operator returned `REV1_POST_SELECTOR_EIGHT_F32_CONSTANTS_PASS`, original 14 SHA before/after, source PPC phase1/5/7 equality, exact linked calls at `0x802B34D4→0x802B2AB4`, `0x802B2AEC→0x802B2A40` and `0x802B2B78→0x802A7C50`, `0x802B2B70 fmadds`, `0x802B2B74 stfs f0,4(r31)`, `0x802B2B58 cror BT=2,BA=0,BB=2`, `0x802B2B5C bc BO=4,BI=2→0x802B2B68`.

| Source SDA2 displacement | Label | Exact observed source float32 |
|---|---|---:|
| `-13192` | initial comparison threshold | `1.0` |
| `-13032` | upper affine reference | `1.25` |
| `-13028` | upper affine offset | `1.0299999713897705` |
| `-13024` | affine span | `0.2200000286102295` |
| `-13148` | case3/putter-like smoothing threshold | `0.10000000149011612` |
| `-13020` | cases0/1/2 smoothing threshold | `0.07999999821186066` |
| `-13016` | alpha on ordered `target <= threshold` | `0.009999999776482582` |
| `-13052` | alpha on ordered `target > threshold` | `0.05000000074505806` |

**Finite ordered input semantics** (the source FPU has per-instruction f32 rounding; the code below is structural, NOT bit-identical Python):

```python
if selected_scalar <= 1.0:
    target = selected_scalar
else:
    # The 1.25-1.0 denominator is exactly 0.25f,
    # but all subsequent intermediate arithmetic uses native PPC f32 behavior.
    target = 1.03_f32 + 0.22_f32 * (selected_scalar - 1.0_f32) / 0.25_f32

threshold = (0.1_f32 if selected_case == 3 else 0.08_f32)
# cror 2,0,2 overwrites EQ with LT||EQ. Subsequent bc BO4,BI2
# branches to 0x2B68 iff ordered comparison is > threshold;
# NaN / unordered must not be silently classified as normal input.
alpha = 0.01_f32 if target <= threshold else 0.05_f32
new_calc_plus_04 = ppc_fmadds(
    alpha,
    f32(target - old_calc_plus_04),
    old_calc_plus_04,
)
```

At positive finite `x=1.0`, the target is exactly `1.0`, whereas the right-hand limit `x→1.0+` is approximately **1.03**, a **source-backed discontinuity in this intermediate target**; whether any on-screen redline/gauge has the same discontinuity is unverified. At `x=1.25`, the transformed target is approximately 1.25. Do **not** claim unrestricted native input beyond bounded selector output, no unconditional clipping to 1.25 here, no exact f32 parity, or accepted-shot labeling. The distinct coefficients `0.01` and `0.05` apply to the **post-selector scalar** threshold, not directly to acceleration.

**Next priority:** source forward slice from `0x802B2B78` after `GetMinRedlinePow` to the next `calc+0x04` read, redline state, and native shot-commit/launch caller. Full `fn_802B2AB4` source function extends to `0x802B2F90` by public RSPE01 Rev1 symbols. Never assume `calc+0x04` is actual shot strength, a rendered gauge, or a launch velocity.


## Operator original PASS — forward slice after redline threshold (`0x802B2B7C..0x802B2C90`)

The operator's `REV1_POST_REDLINE_FORWARD_SLICE_PASS` verified SHA-256 of all 14 original private banks pre/post, phase1/5/7 identical original PPC across the bounded source interval, and a direct `0x802B2B78 bl 0x802A7C50` redline getter. The excerpt is **compiled source only**; it does not prove the function ran during a specific recorded shot.

### Post-smoother redline gate

`0x2B7C lfs f0,calc+0x04`; `0x2B80 fmr f31,f0` saves the smoothed power candidate **P**. `0x2B84 fcmpo P,f1` compares with the returned minimum-redline threshold **R**, followed by `0x2B88 cror 2,1,2` (CR0 EQ := GT OR EQ), and `0x2B8C bc BO4 BI2→0x2B98` branches on **not (P>=R)** for ordinary finite comparisons. If true, `f5=0.0`; otherwise `f5=calc+0x1A8` (`0x2B90`).

For finite source values:
```python
u = calc[+0x1A8] if P >= R else 0.0
```

This uses **different** CROR operands from the earlier `0x2B58 cror 2,0,2`; do not conflate threshold directions.

### Piecewise auxiliary mapping (temporary FP f5)

At `0x2B9C..0x2C54` the code checks `u>0`, `u>1` and applies different mappings. Ordinary finite-path interpretation, respecting per-op f32 roundoff and special zero-denominator checks:

```python
if u <= 0:
    q = u                     # here u is normally 0 due to prior redline gate
elif u <= 1:
    # f4 = 1.0 - 0.0 = 1.0, so denominator is nonzero
    q = clamp(0.15 + 0.85*u, 0.15, 1.0)
else:
    g = *(float32*)(r13-27392)   # = 0x804BE880, public Rev1 .sdata global
    # g is a runtime/global float; its value was NOT established in this source-only trace
    q = 1.0 if (g-1.0)==0.0 else 1.0 + 0.5*(u-1.0)/(g-1.0)
    q = clamp(q,1.0,1.5)
```

The exact zero/NaN comparison paths and legal domain are not fully established. `fn_802B2BB4 lfs f2,-27392(r13)` is in matching public Rev1 symbol object `lbl_804BE880` of type **`.sdata`**, **not** an immutable `r2` numeric constant.

### Second stateful value at calc+0x1AC

`0x802B2C58 lfs f4,428(r31)` reads **old calc+0x1AC** and `0x802B2C60 fsubs f3,f5,f4` forms **q-old**. `0x2C64` loads f32 0.10000000149, `0x2C6C fmadds f2,f2,f4,f3`, `0x2C70 stfs f2,428(r31)`:

```text
new_calc[+0x1AC] = native_fmadds_f32(
    0.10000000149011612,
    f32(q - old_calc[+0x1AC]),
    old_calc[+0x1AC]
)
```

**CORRECTION (verified ISA operand order):** PowerPC `fmadds FRT,FRA,FRC,FRB` computes `FRA*FRC+FRB` with one rounding; decoded `fd=2,fa=2,fb=4,fc=3` means `f2=fma(f2,f3,f4)`, **not** `fma(f2,f4,f3)`. Thus this **is a conventional 0.1 EMA**, `old+0.1*(q-old)` up to native f32 rounding. The earlier claim `q-0.9*old` was incorrect and is superseded. The `0x2C74..0x2C8C` branch compares old `+0x1AC` with zero, new `+0x1AC` with zero, and **f29 = the earlier P_old** with **redline R**.

**Research priority:** inspect `0x802B2C90..0x802B2D90` to establish the control effects and later consumers of `calc+0x1AC`; determine the live `.sdata` global `0x804BE880` only with a source-qualified, categorical/sanitized probe if necessary; do not assume the redline computation feeds the Ball launch setter or the actual guest shot. Still `training_approved=false`.


## Operator-original PASS — redline threshold crossing/audio call block (`0x802B2C90..0x802B2DA0`)

Operator returned `REV1_POST_REDLINE_BRANCH_FOLLOWON_PASS` with all 14 original capture banks SHA pre/post, phases1/5/7 native source equal, exact `fmadds` / branch gates, no training promotion.

For ordinary finite compare outcomes, side-effect block `0x802B2C98..0x802B2D74` can be entered when **either**:

1. `Qold=calc+0x1AC` was zero and `Qnew>0` at `0x802B2C74..0x802B2C7C`; OR
2. `Pold=calc+0x04` (saved in f29 before its update) was **strictly below** minimum-redline R at `0x802B2C80`, and `Pnew=calc+0x04` was **>= R** at `0x802B2C8C..0x802B2C94` with `cror 2,1,2` setting CR0.EQ=GT||EQ.

The original `0x802B2C98 lwz r29,-23868(r13)` loads global `0x804BF644`, which the public Rev1 symbols identify as **`spInstance__13RPSndAudioMgr`**. The side-effect block dispatches **two source-qualified virtual calls** with immediate r5 arguments **39** and **40**, passing an object-related `+2344` address; on a conditional success path each invokes **`0x801B6AB0`**, whose matching public Rev1 symbols and public decomp identify as **`RPSndAudioMgr::setRemote(u32 playerFlag)`** in `Pack/RPAudio/RPSndAudioMgr.cpp`. Public function implementation configures remote speaker output for an already attached system sound. This is concrete **audio/remote-speaker-related event handling** (the exact virtual method(s) still unresolved), NOT by itself a proven ball-strike/launch/accepted-power event. A further direct `0x802B2D28 bl 0x802A7BFC` and an eight-step virtual call loop remain unresolved.

At convergence `0x802B2D78`, root manager selected case index is compared with **3**. Case3 branches to `0x802B2DA4`; non-case3 goes through `0x802B2D88..0x802B2D9C`, where `Pnew` is compared with **1.0** and `f1` is assigned `min(Pnew,1.0)` for ordinary finite inputs (full consumer follows outside excerpt). **No proof this is HUD percentage or shot power;** requires source trace from `0x802B2DA0` onward.

Next falsifiable target: audit original source `0x802B2D98..0x802B2E80` and `fn_802A7BFC(0x802A7BFC..0x802A7C50)` to identify event/handoff store semantics and whether clamped `f1` is consumed as audio presentation or launch. Avoid another constants/club-index/flag scan; `training_approved=false`.


**Direct public code check:** `RPSndAudioMgr::setRemote` checks for an attached system sound, reads user parameters, and configures Wii Remote speaker output using `RPSndSpeakerMgr::setRemoteSend`. This supports *audio-event dispatch* at the threshold crossing. It does not prove an audio event was emitted by an archived runtime sample, and its specific sound effects 39 and 40 are not identified.


## Operator continuation receipt and output-key correction (2026-11-11)

**Source receipt:** The operator executed the read-only `REV1_REDLINE_CONTINUATION_SOURCE_PASS` on the original seven paired MEM1/MEM2 capture archive. The returned verification reported all ten gates true: `smoothed_scalar_store`, `redline_virtual_getter_call`, `redline_cror_ge`, `redline_payload_read`, `redline_skip_zero`, `anchor`, and the four `above_one_gain`/`above_one_clamp`/`below_one_base`/`below_one_gain` floating-point constant gates. This script reuses the qualified archive, 14-bank SHA pre/post, and phase-1/5/7 original source-identity checks, and shifted its **bounded symbolic tail window to `0x802B2D34..0x802B2E38`**. Do not claim a guest-executed launch from that source pass.

**Display caveat:** The operator's console printed an empty `=== REDLINE EVENT CONTINUATION ===` section because the PowerShell printer used the incorrect JSON field `$report.symbolic_tail`; the Python report stores the excerpt in **`$report.symbolic_tail_only`**. An empty display is **not a zero-length source slice or proof that the continuation has no instructions**. The next operator command is:
```powershell
$report.symbolic_tail_only |
    ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 6 }
```
Until those resulting instructions are supplied and reviewed, this particular pass adds **integrity and native-gate evidence**, not an independently interpreted `0x802B2D34..0x802B2E38` CFG. Other previously documented source passes (above) may independently cover overlapping PCs; do not conflate their provenance.

**Evidence boundary at this checkpoint:** Source-backed ordered finite remaps and `calc+0x04`/`calc+0x1AC` FMA updates are documented above, including the PowerPC `FRA*FRC+FRB` correction. The mutable `r13-27392` runtime value, same-shot accepted scalar, launch-wrapper input, and selected Ball handoff remain **UNVERIFIED**. Keep `training_approved=false`, avoid claims of HUD percent or native trajectory parity. Coordinate launch/selected-Ball trace through [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415); the power evidence log stays at [#418](https://github.com/Nate27624/Wii-AI-Golf/issues/418).


## Operator-original redline continuation: case clamp, flag gate and dependent FP signal (2026-11-11)

**Operator evidence:** Following the previously source-qualified `REV1_REDLINE_CONTINUATION_SOURCE_PASS` (original seven-pair/14-bank SHA pre/post and phase1/5/7 static PPC identity), the human operator printed the complete previously hidden `$report.symbolic_tail_only` excerpt for `0x802B2D34..0x802B2E34`. These are native instructions; the symbolic output of an address alone is not proof that the guest executed the path on a captured shot. The earlier empty section was solely a PowerShell field-name mismatch (`symbolic_tail` vs `symbolic_tail_only`), now resolved.

### Post-event dispatch and branch convergence

- At `0x802B2D34..0x802B2D74`, an **8-iteration** loop (r29 from 0, `cmplwi r29,8`, `bc BO12 BI0` looping while r29 < 8) calls a method through loaded object vtable **+0x54** (`lwz r12,+84(r12)`, `bcctr`) with `f1=1.0f`, `r4=2`, `r5=0`. The table base and semantic purpose of those calls are not yet source-qualified. This loop is in the preceding conditional event block and may be skipped through the `0x802B2D78` convergence.
- At `0x802B2D78`, root manager `[r13-23168]` supplies selected case index from `manager+0x1C`; `0x802B2D80 cmpwi index,3`; case3 branches directly to `0x802B2DA4`. For **non-case3**, `0x802B2D88 lfs f0,+0x04(calc)`, `0x2D8C lfs f1,1.0f`, `0x2D90 fcmpo P,1`; conditional selection and `0x802B2DA0 stfs f1,+0x04(calc)` implement **`calc+0x04 := min(calc+0x04,1.0f)` for ordinary finite inputs**. Case3 **bypasses this upper cap** at this point. This is a native state change, not merely a presentation-only f1 return.
- `0x802B2DA4 lfs f0,r2-13000`, `0x2DA8 lfs f1,+0x04(calc)`, `0x2DAC fmuls f0,f0,f31`, `0x2DB0 fcmpo f1,f0`, `0x2DB4 cror 2,1,2`, `0x2DB8 bc BO4 BI2→0x802B2EF8`: **for ordinary finite values, route to `0x2EF8` when current P is below `c * f31`**, where `c` is the unresolved SDA2 float at `r2-13000`. Earlier source in the same method shows `f31` saved the post-smoother value **before the non-case3 cap** at `0x802B2B80`. Do not conflate this with redline threshold R (which arrives in `f1`) or with the original raw latched peak. Additional control joins after `0x2E34` remain to be audited.
- On the other branch (`P >= c * f31`), `0x2DBC lfs f2,+0x1AC(calc)`, `0x2DC0 lfs f1,r2-13048`, `0x2DC4 lfs f0,r2-13096`, `0x2DC8 lfs f30,0.1f`, `0x2DCC fmadds f0,f2,f1,f0`; subsequent `0x2DD0 fcmpo f0,f30`, `0x2DD4 bc !GT→2DDC`, `0x2DDC fmr f30,f0` give **`f30=min(0.1f, fma_f32(calc+0x1AC, c1, c0))`** for ordinary finite inputs. Note this is an **upper**, not lower, selection; values of `c1,c0` at SDA2 `-13048,-13096` not yet qualified. In PowerPC FMA, the `fb` field is the ADDEND and `fc` is the multiplier.
- `0x802B2DE0 lbz r0,+0x40(calc)`; if **flag==0**, `0x802B2DE8 bc EQ→0x802B2EB4`, bypassing the `+0x1BC` / `+0x1B8` subpath. When flag!=0, `0x802B2DEC lwz r0,+0x1BC(calc)` is checked; if zero, `0x802B2DF8 lfs f0,0`, `0x802B2DFC stfs f0,+0x1B4(calc)`, `0x802B2E00 b→0x802B2EC0`. When `+0x1BC!=0`, `0x802B2E04 lfs f1,+0x1B8(calc)`, `0x2E0C fcmpo f1,0`, `0x2E10 bc !GT→0x2E18` (`0x2E18` XO40 is `fneg`), `0x2E1C` compares magnitude-like `|f1|` to SDA2 `r2-12996`; `0x2E24 bc !LT→0x2EC0`. This **resembles** a signed magnitude/timing guard but no native physical meaning is established. The next `0x802B2E28..0x802B2E34` compares `+0x1B8` with zero and branches to `0x2E3C`, outside the current bounded excerpt.

### Next bounded source-only discriminator

Read immutable SDA2 float32 constants at `r2-13000`, `r2-13048`, `r2-13096`, `r2-12996` using the previously verified **unique** `0.992f` anchor; gate their exact `lfs` instruction PCs `0x802B2DA4,0x802B2DC0,0x802B2DC4,0x802B2E1C`. Inspect source `0x802B2E34..0x802B2F90` to classify the remaining `+0x1B4/+0x1B8/+0x1BC` writers and return path. Continue maintaining owner handoff to [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415) for **selected Ball launch transfer**; do not repeat four launch wrappers, filter1/filter2 or seven-capture flag classification.

**Strict proof limits:** This new source excerpt does not source-prove final accepted shot power, on-screen meter percentage, a game-executed controller action, launch commit, or source-selected moving Ball identity; original archive remains read-only and `training_approved=false`.


## Original Rev1 source PASS — redline function tail, three additional state fields (2026-11-11)

**Human operator source evidence:** Corrected local environment-variable setup and reran the read-only `REV1_REDLINE_FINAL_TAIL_AND_F32_PASS` on the existing original Rev1 seven-capture/14-bank SHA-gated archive, PPC phases1/5/7 identity. Exactly reported original-source f32 results: `r2-13000 = 0.75`, `r2-13048 = 0.07000000029802322`, `r2-13096 = 0.029999999329447746`, and `r2-12996 = 10.995574951171875`. All were recovered via previously unique 0.992f SDA2 anchor and native `lfs` instruction gates. The operator printed the **full bounded symbolic tail** `0x802B2E34..0x802B2F8C`, not a dynamic instruction execution trace.

**Verified source structure and finite ordered-path interpretation:**
1. At `0x802B2DA4..0x802B2DB8` (from immediately prior original pass), selected current `P=calc+0x04` is compared with `0.75 * f31`, where `f31` is the smoothed value saved at `0x802B2B80` *before* optional non-case3 cap `min(P,1.0)`. Branch `bc BO4 BI2→0x802B2EF8` skips the subsequent angle-like adjustment when `P < 0.75*f31` for finite inputs.
2. At `0x802B2DBC..0x802B2DDC`, with `Q=calc+0x1AC`, `f30` starts at 0.1f, `0x802B2DCC fmadds f0,f2,f1,f0` computes `0.07f*Q+0.03f` (one PPC f32 FMA), then `fcmpo`/branch update `f30=min(0.1f, FMA(0.07f,Q,0.03f))` for ordered finite values. There is **no proven lower cap** in this selection.
3. The `calc+0x40` guard at `0x802B2DE0` branches to `0x802B2EB4` when zero: `calc+0x1B8 := f32(calc+0x1B8 + f30)` at `0x2EB4..0x2EBC`. When nonzero, check `calc+0x1BC`. If zero, `0x802B2DFC stfs 0,+0x1B4(calc)`, then skip to `0x2EC0`. If `calc+0x1BC != 0`, use signed `calc+0x1B8` to form absolute magnitude (`fneg` XO40 at `0x2E18` and `0x2E3C`), and compare to **10.995574951171875** at `0x2E1C..0x2E24`; on magnitude >= threshold, skip correction to `0x2EC0`. No physical units or angle meaning demonstrated.
4. In the magnitude < threshold correction path, `0x2E40..0x2E54` constructs `f1=0.85f` and `f2=(abs(calc+0x1B8)-10.995574951171875)/(SDA2 r2-12992)`, then calls `fn_802A3CF4`. **Constant `r2-12992` and native callee's exact FP contract remain unverified for this route.** `0x2E58..0x2E80` transforms the returned `f1` using **other unresolved SDA2 constants** `r2-13116` and `r2-13052=0.05000000074505806`, clamps the result to [0.05,1.0] (finite path), multiplies by `f30`, then if `calc+0x1BC==1` adds the step to `calc+0x1B8` (`0x2E94..0x2E9C`), otherwise subtracts it (`0x2EA4..0x2EAC`).
5. At `0x802B2EC0..0x802B2EF4`, `calc+0x1B8` is scaled by static `r2-13044` and passed to **`0x8002F898`**; returned `f1` is stored at **`calc+0x1B4`** (`0x2ED4`). The subsequent `fn_802A3CF4` call receives static `r2-13036` plus `frsp` of the prior function return, then multiplies the returned value by `calc+0x1AC` and static `r2-13040`, stores the product in **`calc+0x1B0`** at `0x2EF4`. These callee semantics and remaining constants are not qualified here; do not name `0x8002F898` sin/cos, spin, hook, etc. without source proof.
6. `0x802B2EF8..0x802B2F58` uses `0.5*f31` and a comparison of current `calc+0x04` with `f29` (saved pre-update P_old) to conditionally run a **second 8-iteration vtable +0x54 dispatch loop**. Exit epilogue `0x802B2F5C..0x802B2F8C` returns; there is no direct native `bl 0x80299ACC` in this excerpt. The virtual side effects remain unclassified.

**Interpretation boundary:** `calc+0x1B8` is updated by bounded signed/unsigned-like branches and passed to a transformation function, which generates two distinct state fields `+0x1B4` and `+0x1B0`. The native field roles (e.g., rotational/hook/spin/animation), exact current-vs-accepted launch scalar, and same-shot selected Ball transfer are **not proven**. Treat only qualified byte offsets, instruction operations, branch predicates and FP constants as established. No guest gameplay or training authorization; `training_approved=false`.

**Best next discriminant:** recover exact `r2-12992,-13116,-13044,-13036,-13040` constants and independently identify public symbol/code owner of `0x8002F898` and the specific `fn_802A3CF4` FP contract; then perform receiver-proven direct consumer census for `calc+0x1B0/+0x1B4/+0x1B8`, rather than repeating four club weights or first-contact modeling. Source-selected Ball handoff remains owned by [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415).


## 2026-11-11 operator corrected forward audit + public source symbol resolution

Operator supplied `REV1_CORRECTED_EVENT_AND_POWER_CONSUMER_PASS` after the preceding local script correctly ABSTAINed because its expected call PC was mistaken as `0x802B2D28`. The actual verified source is `0x802B2D28 lwz r3,-23168(r13)`, **`0x802B2D2C bl 0x802A7BFC`**. The corrected operator run confirmed original 14-bank SHA pre/post and static PPC phases1/5/7 identical; no guest execution. Its complete bounded `0x802B2D78..0x802B2E90` symbolic read confirms: non-case3 `calc+0x04=min(calc+0x04,1)`; `0x802B2DB8` guards against `P_current<0.75*P_saved_before_cap`; `0x802B2DCC` computes `f30=min(0.1f,fma(0.07f,calc+0x1AC,0.03f))` on ordered inputs (no lower clamp established); `calc+0x40`/signed `calc+0x1B8`/flag `calc+0x1BC` control a bounded magnitude-conditioned adjustment. No new native shot-commit proof.

**New independently public Rev1 symbol resolution:** `0x8002F898` is **`nw4r::math::SinFIdx`**, a sine table-index math routine (matching `config/RSPE01_01/symbols.txt`); `calc+0x1B4` receives its output at `0x802B2ED4` on the examined source path. This establishes a **sine-based state transform**, NOT typed ball spin or physical angle units. Also `0x800A600C` in `fn_802A7BFC` resolves to **`EGG::CoreController::stopRumbleMgr`**, reinforcing the side-effect branch as controller/audio feedback rather than proof of shot commit. The other direct callees `0x802A0CA8`, `0x802C7660` remain source-unsplit/unnamed; do not assign gameplay roles.

The downstream selected Ball investigation [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415#issuecomment-6813842377) independently achieved **conditional incoming-Ball+0x8C scalar pointer provenance** through case-vtable slot +0x10; it is **not** a selected velocity `+0x78..+0x80` proof. Next independent high-value microtask: original SHA-gated four wrapper prefixes `0x802B5FBC,0x802B5AC8,0x802AFC4C,0x802B0098`, decode their scalar `lfs f0` constants and intervening `op59` operations; then trace actual selected Ball velocity writer. Do not repeat the already finished vtable discovery/CFG. All training flags remain false.


## Source PASS — final five nonlinear constants and normalized signed adjustment (2026-11-11)

**Exact human operator receipt:** `REV1_REDLINE_NONLINEAR_CONSTANTS_PASS` (original seven paired Rev1 archive, all14 SHA pre/post `True`, PPC text phases1/5/7 identical `True`, all native `lfs`/branch/store gates `True`). The previous `DIAGNOSTIC_ABSTAIN` on first attempt was only an omitted local `WII_GOLF_AUDIT_SCRIPTS` environment variable; the corrected rerun completed successfully. Output constants decoded from original immutable SDA2 with unique `0.992f` anchor:

| Native PC / displacement | Purpose | Exact source float32 |
|---|---|---:|
| `0x802B2E44` / `r2-12992` | signed range denominator | `-10.995574951171875` |
| `0x802B2E58` / `r2-13116` | nonlinear return gain | `0.949999988079071` |
| `0x802B2EC4` / `r2-13044` | first helper input scale | `40.7436637878418` |
| `0x802B2ED8` / `r2-13036` | second nonlinear helper parameter | `0.550000011920929` |
| `0x802B2EE8` / `r2-13040` | final secondary-field scale | `5.0` |

**Finite ordered-path model, still not full PPC parity:** With `a=calc+0x1B8` and `L=10.995574951171875f`, conditional adjustment block only operates when `calc+0x40!=0`, `calc+0x1BC!=0`, `|a|<L`, and the enclosing `calc+0x04 >= 0.75 * f31` gate passes. `0x2E48..0x2E54` computes `t=f32(f32(|a|-L)/(-L))`, i.e. approximately `1-|a|/L`, then passes **`f1=0.8500000238418579f`**, **`f2=t`** to `fn_802A3CF4`. Its *return contract is not yet proven*. If returned scalar is `F(0.85,t)`, `0x2E58..0x2E80` computes `w=clamp(f32_fma(0.949999988f,F,0.050000000745f),0.050000000745f,1.0f)` and `step=f32(f30*w)`, with `f30=min(0.1f,f32_fma(0.07f,calc+0x1AC,0.03f))`. `calc+0x1BC==1` adds `step` to `calc+0x1B8`; other nonzero states subtract it. The role/units of `calc+0x1B8` remain unclassified, even if the constants resemble angular math; do not assert spin or aim.

**Further derived values:** `0x2EC0..0x2ED4` passes `40.7436637878418f * calc+0x1B8` into `fn_8002F898`, saving its returned f1 to `calc+0x1B4`. The returned f1 (via `fmr f0,f1` then `frsp f2,f0`) is also input to `fn_802A3CF4` with `f1=0.550000011920929f`; afterward `0x2EE4..0x2EF4` computes `calc+0x1B0=f32(f32(Q*5.0f)*returned_f1)` where `Q=calc+0x1AC`. Source-backed PC references prove **dataflow to +0x1B4 and +0x1B0**, but not the meaning/implementation of either callee. Explicitly distinguish the `0x802A3CF4` invocation with `f1=0.85` from its second invocation with `f1=0.55`.

**No runtime-shot claim:** all prior named calls and constants are from original static text; `power_internal=EXTERNAL_UNVERIFIED` for external launch model; `training_approved=false`. Do not conflate `calc+0x1B0/+0x1B4/+0x1B8` with selected Ball spin/velocity/heading until source receiver-consumer and same-shot handoff are proven.

**Next source-only priority:** bounded original PPC disassembly of `fn_802A3CF4` and `fn_8002F898`, resolve their exact FP contract and public function-symbol identity before inferring physical meaning; then source-qualify direct consumers of the three calculated fields. Coordinate first-contact and selected Ball transfer with [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415); do not duplicate per-club launch curves, controller filters or seven-capture flag audit.


## 2026-11-11 operator original PASS — first selected/incoming Ball +0x8C scalar values closed

Operator returned `REV1_SELECTED_BALL_SCALAR_WRAPPER_PREFIX_PASS`, **14/14 original numbered banks SHA pre/post**, PPC original phases1/5/7 identical, launch caller `0x80299B94 r4=r31+0x8C`, virtual +0x10 dispatch `0x80299BB4`, four vtables and each `stfs f0,0(r4)` original-source verified. The preceding `lfs f0` constants and intervening op59 instructions are now recovered numerically:

| Native case | Initial f32 constant | FP operation before store | Original store PC | Conditional scalar written to incoming Ball+0x8C |
|---|---:|---|---|---|
| 0 | 0.5 | `0x802B5FC0 fmuls f0,f0,f1` | `0x802B5FC4` | `f32(0.5f * s)` |
| 1 | 0.6000000238418579 | `0x802B5ACC fmuls f0,f0,f1` | `0x802B5AD0` | `f32(0.6f * s)` |
| 2 | 0.6000000238418579 | `0x802AFC50 fmuls f0,f0,f1` | `0x802AFC54` | `f32(0.6f * s)` |
| 3 | 0.0 | no intervening FP operation | `0x802B009C` | `0.0f` |

**Precise input domain and event:** `s` is **not automatically the accepted strength**. In the source-identified state3 branch of `fn_80299ACC`, `s=state[+0x1A8]` if `state[+0x1BC]==1`; otherwise `s=f32(state[+0x1A8]*Kstate)`, with `Kstate` the *still unverified* numeric SDA2 load at `r2-14636` (do not guess its value or identify `s` with the earlier internal UI/redline EMA). The caller only supplies incoming Ball as r31 on a **conditional** Main→Sim→Ball dispatch; actual guest shot execution remains unobserved. Store concerns **scalar +0x8C**, **not velocity triple +0x78/+0x7C/+0x80**, and is not a proved physical spin quantity.

This result is distinct from the four power-input magnitude getters `[0.037,0.041,0.045,0.15]` and launch-shaping curve families `p=[0.7,0.656,0.64,0.63]`; none of these three constant families should be conflated.

**Next research gate:** in original function-scoped PPC for `fn_80298E70` (`0x80298E70..0x80299528`) and `fn_80297A00` (`0x80297A00..0x8029855C`), find **candidate** D-form or indexed stores to offsets +0x78/+0x7C/+0x80, preserving receiver register and local control-flow context. Use `fn_8029A0E0` (`0x8029A0E0..0x8029A1D0`) as positive contextual reference for third/prep Ball vector stores. Do not assert selected velocity provenance from raw immediate-offset matches; confirm receiver lineage and call conditions separately. Training stays disabled.

## Public NW4R cross-check — signed transfer and sine-index composition (2026-11-11)

**Evidence class:** independently reviewed matching public decomp implementation; the operator's latest original Rev1 `REV1_REDLINE_NONLINEAR_CONSTANTS_PASS` already qualifies numeric operands and branch/store sites. **This section does not claim a new original-bank execution.**

1. `src/nw4r/math/math_triangular.cpp` implements `nw4r::math::SinFIdx(fidx)` as a signed sine using a 256-position periodic table and linear interpolation. `include/nw4r/math/math_triangular.h` explicitly defines `NW4R_MATH_RAD_TO_FIDX(x) = x * (128/PI)`. The verified source multiplier `r2-13044=40.7436637878418f` agrees numerically with `128/pi` (relative difference about 4e-8). Therefore, **on the qualified finite path**, `calc+0x1B4 = SinFIdx(f32(40.7436638f * calc+0x1B8))` is approximately `sin(calc+0x1B8)`. This is conversion of a **numeric argument** that resembles radians, **not proof of a physical heading, angle, ball spin, or camera coordinate**. The exact lookup and f32 behavior are not replaced by Python `math.sin`.
2. Previous #415 original-source analysis of `fn_802A3CF4` found `FLog` of absolute input, `FLog` of reciprocal shaping parameter, `FExp`, sign restoration, and a near-zero `abs(s)<0.001f` guard. Public `src/nw4r/math/math_arithmetic.cpp` corroborates both table-based `FLog` and `FExp`. For finite non-near-zero `s` and positive `p`, its **mathematical approximation** is `F(p,s) ~ sign(s)*abs(s)**log2(1/p)`, subject to original sign/NaN branches, table interpolation and rounding. The newly qualified `p=0.85f` and `p=0.55f` have exponents approximately `0.2344653` and `0.8624965`, respectively. **Exact native `F` values are not claimed from these exponents.**
3. Composing the separate, source-qualified calls at `0x802B2EC0..0x802B2EF4`: writing `x=calc+0x1B8`, `Q=calc+0x1AC`, `i=f32(40.7436638f*x)`, `z=SinFIdx(i)`, the source then shapes `z` with `F(0.55,z)` and writes `calc+0x1B0 = f32(f32(5.0f*Q)*F(0.55,frsp(z)))`. Independently, in the gated `|x|<10.99557495` adjustment path, `F(0.85, f32((|x|-L)/(-L)))` weights a signed update of `calc+0x1B8`. These are **different** calls with different arguments and must not be collapsed into a common gain.
4. The lookup supports an *angle-like mathematical transform*, but neither same-shot execution nor a `calc+0x1B0/+0x1B4/+0x1B8 → selected Ball velocity/heading` reaching definition has been shown. **Next unique original-only source task:** (a) compare exact helper `fn_802A3CF4` PPC in phases 1/5/7 against the already documented logarithm/exponential BL and sign/guard sites, then (b) run an opcode- and receiver-qualified `lfs/stfs` consumer census for offsets `+0x1B0/+0x1B4/+0x1B8` restricted to `GolfScene_unsplit.o` and independently trace the calc pointer; lexical offset matches on other classes are NOT direct consumers. Avoid repeat constant, club, filter or four-wrapper discovery scans. No private source bytes/paths/pointers exported.

**Integrity/approval:** original 14-bank SHA unchanged by this public-source analysis; no new original-bank test in this addendum; `training_approved=false`.

Public references: [math_triangular.cpp](https://github.com/doldecomp/ogws/blob/master/src/nw4r/math/math_triangular.cpp), [math_triangular.h](https://github.com/doldecomp/ogws/blob/master/include/nw4r/math/math_triangular.h), [math_arithmetic.cpp](https://github.com/doldecomp/ogws/blob/master/src/nw4r/math/math_arithmetic.cpp); prior original helper-source qualification at [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415#issuecomment-6788537837).


## Public Rev1 map corroboration — 0x8002F898 is NW4R SinFIdx (2026-11-11)

**Independent public source identification (NOT a new execution of private originals):** [kiwi515/ogws_info RSPE_r1.map.csv](https://github.com/kiwi515/ogws_info/blob/master/RSPE_r1.map.csv) names the exact Wii Sports US Rev1 symbol **`math::SinFIdx` at `0x8002F898`**, `math::CosFIdx` at `0x8002F904`, and `math::FrSqrt` at `0x8002F874`. This refines the previously verified native direct branch `0x802B2ECC bl 0x8002F898`. Independently, public matching decomp [`doldecomp/ogws/src/nw4r/math/math_triangular.cpp`](https://github.com/doldecomp/ogws/blob/master/src/nw4r/math/math_triangular.cpp) implements `SinFIdx(f32 fidx)`: normalize the absolute floating index, convert to integer and fraction, interpolate in a 256-entry sin/cos lookup table, restore negative sign as needed. Header [`math_triangular.h`](https://github.com/doldecomp/ogws/blob/master/include/nw4r/math/math_triangular.h) defines `SinRad(x)=SinFIdx(NW4R_MATH_RAD_TO_FIDX(x))`.

Combining these *distinct* provenance sources:
- Original user source audit `REV1_REDLINE_NONLINEAR_CONSTANTS_PASS`: `0x802B2EC4 lfs f0,r2-13044 = 40.7436637878418f`, `0x2EC0 lfs f1,calc+0x1B8`, `0x2EC8 fmuls f1,f0,f1`, `0x2ECC bl 0x8002F898`, `0x2ED4 stfs f1,calc+0x1B4`.
- Hence on this conditional original source path, **`calc+0x1B4 = nw4r::math::SinFIdx(f32(40.743663788f * calc+0x1B8))`**, using the library's table/interpolation semantics, not necessarily standard host `sin()` bit parity.
- `40.743663788` is approximately `128/pi`, i.e. an angle-in-radians to 256-indices-per-turn conversion. Therefore `calc+0x1B8` is strongly supported as an **angle-like, radian-unit accumulator** and `+0x1B4` a sine-derived response. This does NOT determine game-axis, camera/club/ball ownership, accepted shot power, or spin.
- A separate original callee at **`0x802A3CF4`** remains without a public name or verified native formula; the preceding failed independent helper dump was **`audit.symbolize` bounded-address `Abstain`**, not source mismatch. Further private-original source analysis requires a separately gated decoder with authorized bounds.

**LocalOps v2 transport audit:** User-requested private LocalOps mailbox `Nate27624/Wii-AI-Golf-LocalOps` has source-confirmed successful unattended `list_files` operation [issue #7](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/7) for `scripts` and [issue #13](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/13) for `research/source_maps`; the latter returned a public source-unit map JSON file. This proves **bridge operation on the configured `wii-golf` root**, not execution of the two-helper private original audit. The mailbox protocol allows only locally pre-registered named `run_task` `argv`, and current configured root is the viewer/project checkout, not the private original archive. Do not claim `0x802A3CF4` source pass from `list_files`. Existing `[LOCALOPS-v2]` `run_task` attempt [issue #10](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/10) has no `LOCALOPS_RESULT_V2` receipt as of this note; unregistered tasks are ignored by design. Register an exact bounded offline SHA-gated audit task **locally** if further original-bank evidence is required, without adding remote shell/argv capabilities. `training_approved=false`.


## Public code-unit split for remaining nonlinear helper (2026-11-11)

Follow-up to the independently source-symbol-qualified `nw4r::math::SinFIdx` result above: the tracked public text-interval index [`research/source_maps/RSPE01_01_public_text_units.json`](https://github.com/Nate27624/Wii-AI-Golf/blob/main/research/source_maps/RSPE01_01_public_text_units.json) is derived from doldecomp/ogws [`config/RSPE01_01/splits.txt`](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt). Independently of the private original archive, it partitions:

| Relevant original code PC | Public source unit interval | Unit label |
| --- | --- | --- |
| `0x802A3CF4` | `[0x802A3B84, 0x802A3DE4)` | `Pack/RPSports/RPGolScene/RPGolMathTrig.cpp` |
| `0x8002F898` | `[0x8002F898, 0x8002FCDC)` | `nw4r/math/math_triangular.cpp` |
| `0x802B2AB4` | `[0x802A79F8, 0x802C7924)` | `Pack/RPSports/RPGolScene/RPGolScene_unsplit.o` |

This explains the earlier original probe's `audit.symbolize` **owner-range abstention** at the first helper: `0x802A3CF4` is *outside* the script's strict GolfScene-unsplit owner range `[0x802A79F8,0x802C7924)`, despite remaining in a distinct Golf-related public source unit. The independently sourced split is not proof of precise semantics or dynamic call execution.

The public `doldecomp/ogws` configure script marks `RPGolMathTrig.cpp` as **`NonMatching`** and no corresponding published source file was found at its expected `src/Pack/RPSports/RPGolScene/RPGolMathTrig.cpp` path. Accordingly, the equation implemented by `0x802A3CF4` is **still unverified**, despite its concrete owning translation unit. Any native original disassembly must be strictly bounded to this `0x802A3B84..0x802A3DE4` public source interval, with operator's existing 14-bank SHA and three original-text phase checks. For `0x8002F898`, reuse the independently published SinFIdx source rather than repeating a private byte audit.

LocalOps v2 was actually used for read-only project filesystem discovery; private mailbox [#13](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/13) returned `research/source_maps/RSPE01_01_public_text_units.json` from its configured checkout. The existing private [#10](https://github.com/Nate27624/Wii-AI-Golf-LocalOps/issues/10) `run_task:redline_helper_consumer_probe` still has **no result receipt**; that is not source-pass evidence, and named tasks cannot be invoked until registered in the local-only config. `training_approved=false`.


## LocalOps approved original-math helper audit: environment abstention, not a negative source result (2026-11-12)

A separate scoped operator-approved `run_research` implementation has now been added for this source question in **draft [PR #453](https://github.com/Nate27624/Wii-AI-Golf/pull/453)** (`scripts/research_p0_math_helpers_private.py`, synthetic bounds and PPC branch tests). The method's three bounded source windows partition `[0x802A3CF4,0x802A3DE4)`, the published `RPGolMathTrig.cpp` object interval. It is intended to reuse the already operator-qualified local private source helpers, check 14 original bank SHA identities and original phase1/5/7 code equality before and after, verify three exact source callsites and return only symbolic instructions. It does not emulate a shot, train, or print private game bytes.

**Verified bridge receipt vs original source proof:** The private LocalOps Windows listener successfully processed `run_research` for three approved windows at an exact pinned clean Git revision, but **each failed closed at `PRIVATE_HELPER_DISCOVERY` before any original memory bank or PPC helper instructions were examined**. Earlier independent B0 caller audit separately abstained on missing/invalid source-manifest/asset gates; a swing bridge marker audit completed but the default inspected bridge and backup files were absent *at that checkout-relative location*. Those outcomes are **environment discovery results**, not original physics falsification, runtime ball proof, or a claim that the game is absent. The initial source study script had a strict unique nearby checkout discovery criterion.

Follow-up on the same PR #453 improved the bounded search to at most three levels beneath its project parent, retained symlink and module-presence restrictions and now emits fixed **MISSING / AMBIGUOUS** categorical reasons without leaking private paths. The reviewed replacement is pinned at `1f71c1adb95743e88d0f4b7959ffb158caf18e23`; user-local checkout approval succeeded and a *single* segment-0 rerun was queued for separate approval. As of this evidence update, **no original nonlinear helper SHA/callsite instruction output** from that rerun has been verified. Other two segments must not be re-requested until the first passes the source gates.

**Correction to prior chronological note above:** The older `redline_helper_consumer_probe` named-task request subsequently resolved with a structured `TASK_NOT_REGISTERED` error and closed. There was no native source execution from that request, and the previous “no receipt yet” statement is obsolete.

**Boundary / next handoff:** If the approved source checkout is MISSING or AMBIGUOUS, do **not** bypass local policy or publish machine paths. The human can separately add the preexisting source-audit checkout as a locally reviewed LocalOps project, or a uniquely validated checked-in source wrapper can be proposed for an approved root. A GitHub branch or public PR cannot edit the Windows user's local authorization. `training_approved=false`; original accepted power and selected Ball handoff remain unverified.
