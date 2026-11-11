# S003 — P0 swing-power discriminator, preregistration 01

## Status and scope

**Evidence status: candidate-only. No new weak/high real gameplay capture or
verified power measurement has been obtained in this study.** Offline analyzer:
`scripts/review_p0_swing_power_candidates.py`. Synthetic tests:
`tests/test_p0_swing_power_candidates.py`. No Dolphin, controller input,
arbitrary RAM scan, memory mutation, or private capture export from this study.

### Existing real observations (not new measurements)

- Operator-reported B0/B1/A0 source-gated no-A versus aim-only: 10 groups idle
  stable; `selected_player_record +0x3C` alone changed on human visual aim.
  Signed angle/units/controller mapping not yet proven.
- Existing original seven SHA/source-gated private pairs: selected ball current
  `+0x30` and player record `+0x30/+0x90` changed over W5–W7; CC/F0/FC
  cached endpoints and pin/tee remained stable. Operator phase labels are not
  machine guest-frame attestation.
- An independent 46-packet A/motion retrospective reports +0x30 near-one
  smoothing during M1, byte-like `+0x34` flags and idle/context drift at +0x90.
  Six M1 HIT-associated packets are **quarantined**, not a negative control.
- Source-selected ball +0x30 and cached CC have recent **human visual
  corroboration** in the read-only inspector. That is still not independently
  frame-matched rendered-ball identity, physical velocity, power or units.

## Falsifiable candidate classes

| Source-relative player/ball candidate | Alternative | Discriminator |
|---|---|---|
| Player record +0x30 | Easing/animation scalar | Must reject M0 motion-only and irreversible recovery; source writer required |
| Player record +0x34/+0x35 | Byte state or discrete activity flags | Distinct states insufficient for continuously graded power |
| Player record +0x90 | Idle drift / pose context | Repeated no-A idle, A-only, M0 and matched time controls |
| Player record +0x94/+0x98 | Pose / aim/trigonometric coupling | Opposite direction independent of swing-strength sweep |
| Selected aim +0x3C | Aiming/orientation | Explicit **not power** |
| Selected ball current +0x30 / caches CC,F0,FC | Projectile position and delayed cache | Explicit **not power**; non-atomic read skew |

No field is source-proven as a power variable. Reviewable owner/source-linked
writer evidence is required to make even a typed claim. Human visible gauge
percentage is an **operator label**, not calibrated physical power.

## Next experiment: precisely bounded operator-controlled S001/S002 capture

**No automated shot is authorized by this file.** Coordinate with the S001
operator-consent launcher and S002 source-gated reader, not a parallel capture
implementation. Record original local JSONL/SHA privately and derive a separate
small sanitized summary for S003.

1. Negative controls: `IDLE` with no A/motion, `A_ONLY` with manually held A
   and no motion, and `MOTION_NO_A` with human-attested no contact. Require
   source/scene/owner stable and preserve no-contact human uncertainty.
2. Four independently prepared, same-revision/scene/hole/selected-actor trials:
   `L1,H1,H2,L2` (weak/strong/strong/weak), each with **different shot_id**.
   This balances time/order trends. If a ball/scene/owner unexpectedly changes
   within a trial, STOP and discard; never reuse one shot identity for another.
3. Per trial three source-gated windows `PRE`, `GAUGE`, `RECOVER` of bounded
   sampling (up to 5000ms each). Record human-visible percentage at GAUGE;
   request low/high difference of at least 15 display points per paired block.
   Capture should start while Dolphin is **running**, before manual swing; if
   operator pauses to inspect the UI, do **not** issue Felk RPC into paused
   Dolphin. Sealed private packets must be written before pausing.
4. S002 produces source-qualified, unitless *derived per-field window values*
   from the original saved, SHA-gated packets. The console output must NEVER
   contain raw BE32 words, pointers, exact shot tokens or private paths.
   Decode BE32 as float only after typed source warrant; otherwise label
   numeric interpretations as hypotheses. A changed bit pattern alone is not a
   graded scalar; non-atomic sequential reads are not guest physics steps.
5. Stop or quarantine unexpected contact, recovered scene/owner failure,
   cross-shot duplicate, censored 100ft outcome, no visual meter, or absent
   source gate. Positive-contact capture requires separate explicit operator
   approval and an independently game-owned contact witness before claiming
   contact-positive validation.

**Preregistered contrasts** for a proposed candidate: all four PRE→GAUGE
changes must share a nonzero direction; both high trials have an absolute
effect at least 1.25 times their paired low; every RECOVER→PRE displacement
and each IDLE/A_ONLY/MOTION_NO_A control change must be less than 25% of the
minimum low effect. Confounded, missing or nonfinite data abstains/falsifies.
Even perfect passing results are only *visible-gauge-associated hypotheses*,
not physical power/velocity, game-side A acceptance or training data.

## Offline analyzer contract

```powershell
py -3 -I scripts/review_p0_swing_power_candidates.py --plan
py -3 -I -m unittest discover -s tests -p test_p0_swing_power_candidates.py -v
py -3 -I scripts/review_p0_swing_power_candidates.py --evidence "PRIVATE_DERIVED_SUMMARY.json"
```

The evidence JSON must have exact top-level keys
`schema_version=1`, `kind="p0_power_visible_meter_contrast"`,
`origin="synthetic"|"operator_reviewed"`, `revision="RSPE01 Rev1"`,
`trials` and `controls`. Trial order is `L1,H1,H2,L2`. Each trial has
`trial,shot_id,scene_id,hole_id,actor_id,generation,source_gated,owner_stable,
operator_precontact,display_percent,windows`; each window `PRE/GAUGE/RECOVER`
has `span_ms` and `values` (named allowlisted numerical hypotheses).
Controls `IDLE/A_ONLY/MOTION_NO_A` have
`source_gated,operator_no_contact,delta`. This is *not* the raw capture
manifest format; conversion from original packets requires future reviewed
source/identity checks from S002, not invented direct use of archived phases.
No labels or stats from original private files are included in this PR.

Output is categorical rows with explicit missing witnesses; all
`runtime_verified=false`, `training_eligible=false`,
`power_measured=false`, `training_approved=false`. The 100ft off-green
penalty is censored and must never become measured carry. No promotion is
possible from this analyzer alone.
