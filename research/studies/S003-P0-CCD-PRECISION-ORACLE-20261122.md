# S003 CCD first-entry precision oracle — synthetic only

- **Agent:** `S003-ccd-first-entry-oracle-20261122-b`
- **Task:** `S003-P0-CCD-FIRST-ENTRY-PRECISION-ORACLE-20261122-B`
- **Coordination:** [roster rev50](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7077873217), [canonical #467](https://github.com/Nate27624/Wii-AI-Golf/issues/467), [phantom #474](https://github.com/Nate27624/Wii-AI-Golf/issues/474)
- **Boundary:** Pure mathematical reference *for specified synthetic geometry only*. Not a production solver, native KCol collision rule, physical ball radius, verified launch or training dataset. The illustrative `r=0.5` is a source-query-route tag, not proof of ball size. No ROM, RAM, Dolphin, LocalOps or private source access.

## Independent analytic derivation

Take triangle `A=(0,0,0)`, `B=(2,0,0)`, `C=(0,0,2)` and a vertical segment at fixed local `(x,z)`, starting at `y=p` and ending at `y=q`. For an AB-edge-region sample `(x,z)=(1,-.25)`, its closest surface is `(1,0,0)`; the first-contact cross-section is `y_entry=±sqrt(r²-z²)=±sqrt(3)/4`, signed to match the starting side. For an A-vertex-region sample `(x,z)=(-.1,-.1)`, the closest point is `(0,0,0)`, giving `y_entry=±sqrt(r²-x²-z²)=±sqrt(.23)`. In both cases `t_entry=(y_entry-p)/(q-p)` and the **center is constructed directly from `y_entry`**, not from a rounded `t`. Surface and outward normal are calculated from the known local nearest feature, independently of the production CCD routines. The reference is intentionally restricted to known Voronoi regions; it does not solve arbitrary triangle CCD or mimic PR #469's conditioned roots.

- Edge and vertex height sweeps: H=2, 10⁴, 10⁵, 10⁶, 10⁸, 10¹⁰, and 10¹⁶ (edge also 100 and 10¹⁴). Exact Decimal precision=100, both entry center and contact surface.
- Exact tangent: edge `z=-.5`, `p=+.01`, `q=-.01`; first entry exactly at `y=0`, `t=.5`.
- Near inside: edge `z=-.4999`; first entry is `y=+sqrt(.25-.4999²)`, not closest approach.
- Strictly outside: the next negative IEEE binary32 value below `-.5` (bit pattern `bf000001`, `-.5000000596046448`), whose minimum radius **exceeds** `.5`; MISS regardless of length or split count.
- Zero-length outside = MISS; initial overlap/contact = explicit `ABSTAIN_INITIAL_OVERLAP` instead of fabricating an entry time.
- Reversing a path flips signed first-entry altitude; translating geometry shifts center/surface but preserves local normal and contact time. Splitting one straight path preserves the analytic first global time; float32-quantized subdivision of the outside case remains MISS for 1/2/4/10/20 segments.

## Distinguish root cancellation from time-representation failure

Even a **perfect** Decimal entry fraction must sometimes round to the same binary64 number as the closest-approach fraction. For edge H=10¹⁶, the true `t_entry=.5-(sqrt(3)/4)/(2H)`, but `float(t_entry)=.5`. A consumer reconstructing `center_y=H+t*(-2H)` would place the center at zero, penetrating by `sqrt(3)/4`, rather than at the first surface. In this extreme case the oracle's `time_resolution` is `ABSTAIN_BINARY64_TIME_COLLAPSE` **even while its independent Decimal `status` remains HIT**. This indicates a representation-contract problem, not permission for a production solver to synthesize hit coordinates.

Binary64's immediate representable predecessor to `0.5` is `0.5-2^-54`; half-ULP rounding to the midpoint means collapse when H exceeds approximately `7.80046e15` for this edge. Other magnitudes, translations, and reconstruction formulas can lose position accuracy earlier, so the original solver owner must evaluate center residuals and candidate ordering in addition to hit/miss.

## Comparator and known baseline defects

`python scripts/research_p0_ccd_precision_oracle_v2.py --summary --compare-existing` reads **only** the current repository `wii_ai_golf.physics.first_contact.segment_hit` and labels its observations without modifying it. Observed outcomes are *not* asserted to remain defective: tests pass if a future repaired production solver agrees with the oracle. Existing #467 documents high-speed false negatives and wrong earliest center, and #474 documents an outside-radius phantom depending on subsegment size; PR #469 already owns the independent *conditioned edge-root candidate*. This oracle adds **vertex truth, contact XYZ/surface, f32 one-ULP negative, subdivision, translation/reversal, zero motion and extreme binary64 normalized-time limits** without creating a competing solver.

## Transfer contract for the original S003 production owner

The original `S003-first-contact-solver-20261111-a` remains PARKED with exclusive `first_contact.py`, its tests, and original solver study. A later manager-coordinated owner should require: (1) edge/vertex H ladder returns a mathematically supported **earliest** center/surface or explicitly abstains for unresolved finite precision, (2) no phantom hit for one-f32-ULP-outside at short, long or subdivided spans, (3) exact tangency and inside entry remain supported, (4) translation/reversal/zero-length behavior is explicit, (5) time-fraction collapse never silently reconstructs a deep penetration as valid first entry, (6) exact-head Windows/Ubuntu full offline CI and root `merging.md`, (7) native/launch/training flags continue false absent independent native evidence. Do **not** treat this research as a mandate to change the protected solver, global tolerances, collision sidedness, or KCol semantics.

## Reproduce without private data

```sh
python -m unittest discover -s tests -p 'test_physics_ccd_precision_oracle_v2.py' -v
python -m unittest discover -s tests -v
python scripts/research_p0_ccd_precision_oracle_v2.py --summary --compare-existing
```

Dedicated GitHub Actions workflow `s003-ccd-precision-oracle-offline.yml` executes focused tests and full suite on Python 3.11 Windows+Ubuntu at each PR head. `native_kcol_parity_verified=false`, `selected_ball_launch_verified=false`, `training_approved=false` throughout.