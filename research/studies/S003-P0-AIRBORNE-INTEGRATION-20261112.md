# S003 M1 — Offline zero-wind airborne integration candidate (2026-11-21)

**Owner:** `S003-airborne-integration-20261112-a` (S000 roster rev46, [PR #320](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-6842921942)). Beads supplemental claim `wgr-s003-m1`, [private LocalOps receipt #121](https://github.com/Nate27624/LocalOps/issues/121). Canonical physics issue [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415); owner CLAIM posted there. Starting `main` SHA: `b3b7e466979e05f7acaacfd228dae95d1c3cdfaa`.

## Precise contract

`src/wii_ai_golf/physics/airborne.py` adds `sample_trajectory(p0_xyz, v0_xyz, FlightParameters(...), steps=N)` and returns an immutable `AirborneTrace` whose `samples` are `(numerical_step_index, xyz, velocity_xyz)`. The zero sample preserves the **exact supplied** p0/v0 values. In host-f32 mode internal state is separately rounded to binary32 before the first computation and after each illustrative arithmetic operation. All subsequent sample indices are strictly increasing integers; they are **not** measured Wii guest frames or physical seconds.

The candidate no-wind numerical order is:
```text
u_n = v_n + a_n
p_(n+1) = p_n + u_n
v_(n+1) = damping * u_n
```
Caller explicitly provides acceleration and damping. This is derived as a **source-guided candidate order**, not evidence that any source-selected Ball executed it on a particular shot. `FlightParameters(acceleration_xyz=(...), damping=...)` has no unlabelled gravity or native-v0 default. `host_f32` uses Python host IEEE32 pack/unpack; `binary64` is a separate numerical reference. Neither proves Gekko fused-single/native subnormal, exception, or actual function branch behavior.

`SourceSpinCandidate` is optional. It uses *normalized* source-direction candidates `S=(vz,0,-vx)` and `L=(-vx*vy,vx²+vz²,-vz*vy)` with source-associated illustrative gains `0.001*speed_like*lateral` and `0.0012*speed_like*lift`. **Required caller-defined** `normalizer_guard_assumption` is not the missing Wii native epsilon. A **required** direction that is exactly vertical or within this guard raises `UnverifiedNormalizerBranch` instead of pretending a native decision. Inactive force terms skip their own normalization: for `(vx,vy,vz)=(1e-5,0,0)` the assumed `1e-8` guard rejects lift (`|L|=1e-10`) but permits lateral (`|S|=1e-5`). This is candidate-level dead-term handling, not proven native source CFG behavior. Initial speed-like scalar is **mandatory** if spin is requested; an explicit `held_input` versus `recompute_from_velocity` flag models two incompatible speed-cache hypotheses rather than silently treating `Ball+0x84` as fresh `norm(v)`. Spin decay and force timing remain assumed.

`predict_provisional_contact(trace, triangles, contact_mode=..., assume_tree_free=...)` calls the existing canonical `first_contact.predict_contact_from_trajectory`, never a second collision implementation. Trees unknown => abstain. The source route-tagged `swept_kcol_query_0p5` uses 0.5 as a **query parameter**, not physical ball radius.

## Synthetic controls

`tests/test_airborne_integrator.py` covers sample-zero identity, exact no-force and acceleration/damping step order, constant-acceleration closed form, explicit-step subdivision differences, deterministic f32/f64 divergence, normalized source spin signs, vertical/near-vertical abstention, held/recomputed cache differences, invalid data/overflow, synthetic first-contact center/surface XYZ, tree-clearance abstention, no-contact horizon, and source query radius provenance. Full offline suite and configured Windows/Ubuntu CI on the **exact PR head** are mandatory before any merge. Any failures must be repaired on this owned branch; do not conceal them.

### Expected usage (synthetic, not a real shot)
```python
from wii_ai_golf.physics.airborne import FlightParameters, sample_trajectory, predict_provisional_contact
from wii_ai_golf.physics.first_contact import Triangle

params = FlightParameters(acceleration_xyz=(0., -0.002, 0.), damping=0.999000013)
trace = sample_trajectory((0., 2., 0.), (0.1, 0.15, 0.), params, steps=200)
flat = [Triangle((-10, 0, -10), (0, 0, 10), (10, 0, -10))]
contact = predict_provisional_contact(trace, flat, assume_tree_free=True)
assert contact["native_game_parity_verified"] is False
```

## Open evidence gates / prohibited inferences

- **UNKNOWN**: accepted shot power, club-to-launch case, selected Ball initial v0 and object pointer/receiver; handled by existing S002 owners on #418 and #455.
- **UNKNOWN**: actual guest physics cadence; source q/gravity branches, damp/impact order, speed-cache initialization, near-vertical exact native epsilon, Wii PPC float32 fusion/rounding, selected-scene branch eligibility.
- **KNOWN provisional CCD defects** #467, #473, #474 and triangle/finite edge cases #465/#466 remain solver-owner scope; M1 must not modify `first_contact.py`.
- **No private data**: no ROMs, savestates, live captures, raw RAM, private paths or source archive bytes in any public commit/comment.
- **No execution**: no Dolphin/game input, source-study command, real-shot capture, or training promotion. `native_game_parity_verified=false` and `training_approved=false` unconditionally.

This creates the M1 offline interface needed before an M2 frame-by-frame parity oracle can be evaluated. It is **not** a 1:1 Wii Sports Golf physics result.
