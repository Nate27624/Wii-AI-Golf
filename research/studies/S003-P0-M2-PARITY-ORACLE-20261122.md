# S003 M2 — offline synthetic physics parity gate (2026-11-22)

- **Instance:** `S003-m2-parity-oracle-20261122-a`
- **Task:** `S003-P0-M2-SYNTHETIC-PARITY-GATE-20261122-A`
- **Manager authority:** [S000 roster rev50](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7077873217), main baseline `90d59cc3229003ac46f01ef10c68d8e7a9514d5e`.
- **Canonical owner issue:** [#472](https://github.com/Nate27624/Wii-AI-Golf/issues/472).

## Scope and interfaces

`src/wii_ai_golf/physics/parity_oracle.py` consumes the existing **M1** `AirborneTrace` (`samples=(numerical_step, xyz, velocity_xyz)`, `precision`, `assumptions`) without modifying `airborne.py`, `first_contact.py`, S002 readers/qualifiers, or any S001 runtime. The other input is an *independent* bounded sequence of typed `ReferenceSample` records, one `TraceIdentity` per side, and `EvidenceLabels` containing **only labels** from S002 guest-step/basis classifiers. Calling `compare_airborne` returns a bounded status dictionary and (only in eligible synthetic mode) per-step numerical residuals.

The comparator joins by exact **numerical step index**, not list position, host callback count, VI frame or unverified guest clock. A missing, duplicated, out-of-order or unaligned index produces categorical abstention, with skipped-step indices where a monotone comparison has gaps. Identity checks include symbolic source cohort/revision, boot, shot, scene, selected-Ball tag/epoch, coordinate basis, units, physics parameter provenance, precision, and model commit SHA. IDs in reports are suppressed. Invalid private-looking pointers, nonfinite XYZ and bad types are rejected. Source-velocity `None` remains `UNKNOWN` or `PARTIAL`, never derived from finite differences. Every result unconditionally has `native_game_parity_verified=false`, `training_approved=false`, `selected_ball_world_xyz_verified=false`, `verified_native_guest_step_count=null`.

For eligible *synthetic* traces, `ELIGIBLE_SYNTHETIC_COMPARISON` means **only that arithmetic is compared**. `first_divergent_step` identifies the first step exceeding explicitly chosen synthetic absolute thresholds (default zero); each residual provides position `model-reference`, its Euclidean norm, optional direct-velocity residual and norm. These are **numerical units in the caller-declared basis**, not feet/meters, native physical carry, a gameplay score, or a 1:1 game tolerance.

Float32 ULP distances are emitted **only** for synthetic steps `n>0` when M1 uses `host_f32` and the caller declares matching host-f32 operation/rounding semantics. Step 0 is intentionally excluded because M1 returns its unquantized caller input there. A representational host ULP is not a native Gekko/PPC instruction-order, FMA, subnormal or rounding proof. `binary64` generates no f32 ULP claims. Neither mode asserts validated native precision.

## Independent mathematical controls

Zero-wind, no-damping, constant acceleration with *exact quarter-fraction* values validates the M1 candidate recurrence against the closed form

`v_n = v_0 + n a` and `p_n = p_0 + n v_0 + (n(n+1)/2) a`.

Synthetic negatives inject a displaced X at step 3 while preserving the endpoint, a wrong position/force update order at step 1, accumulated per-step drift, identity/receiver/epoch/revision/model-SHA mismatches, missing/out-of-order/duplicate steps, absent direct velocity, non-atomic/stale packets, false host/VI clock, conditional basis labels, host-f32 versus binary64, PPC precision claims, spin `held_input` versus `recompute_from_velocity` speed-cache hypotheses, and a required vertical normalizer that raises M1's `UnverifiedNormalizerBranch`. The tests cover explicit fail-closed categories, no private identifier echo and immutable inputs.

## Source evidence gates (NO-GO for native M2)

Existing [S002 guest-step attestation #476](https://github.com/Nate27624/Wii-AI-Golf/pull/476) returns `SYNTHETIC_CONTRACT_PASS` **only for synthetic** cases; `CANDIDATE_REQUIRES_EXTERNAL_PROOF` is not an independently proven guest-step count. Existing [S002 Ball/KCL coordinate-basis #477](https://github.com/Nate27624/Wii-AI-Golf/pull/477) reports `CONDITIONALLY_CONSISTENT` for coherent *supplied* witnesses, yet always keeps `selected_ball_world_xyz_verified=false`. The M2 consumer uses these exact statuses as labels. It never upgrades the labels to native evidence even if a caller sets every boolean to true.

**Missing independent proof:** real same-shot selected Ball/revision/boot/pointer-epoch identity; source-qualified selected launch-v0 and runtime receiver; executed guest-PC and monotone guest physics-step counter, post-step atomicity and stride; physical Ball/KCL coordinate registration (not display-fit axes); exact native q/gravity/force/normalizer/speed-cache timing, PPC f32/FMA behavior. A physical shot needs explicit, separate operator authorization. Without these proofs every sanitized/native candidate abstains before numerical residuals or training status; no Dolphin, private source, LocalOps, Beads claim or training was performed in this task.

**Next falsifiable gate:** independently verify one selected-Ball post-physics guest-step sequence and its source/clock/coordinate mapping, then assign an authorized follow-up to design review of actual same-shot trace comparison. M2 synthetic correctness alone neither resolves KCol collision, trees, bounce and roll nor establishes physical-game parity.

## Offline validation

Dedicated `.github/workflows/s003-m2-parity-offline.yml` runs Python 3.11 focused `python -m unittest discover -s tests -p 'test_physics_parity_oracle.py' -v` and full `python -m unittest discover -s tests -v` on **Windows and Ubuntu** for all four assigned paths, with no Dolphin or private inputs. Record exact-head run URLs and test counts in the PR merge receipt before any self-merge.
