# S003 P0 — Provisional First-Contact Terrain Solver

Owner: `S003-first-contact-solver-20261111-a`. Canonical issue: https://github.com/Nate27624/Wii-AI-Golf/issues/415. Manager's exclusive roster rev46: https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-6842921942.

## Interface

`src/wii_ai_golf/physics/first_contact.py` is a pure-standard-library offline model. `predict_first_contact(start_xyz, initial_velocity, terrain, *, acceleration, speed_like, lift, lateral, spin_axis, contact_mode, assume_tree_free, max_steps)` takes explicit source-coordinate XYZ/vector and `Triangle` data. Local OBJ mesh files can be loaded with `read_obj`. The tool **does not export or transform collision geometry**. It accepts the previously established, operator-local, 2,498-face original collision OBJ but does not embed it in Git.

On modeled contact, returns fractional **numerical step count** (not seconds or verified game frames), separate ball-center and terrain-surface XYZ, triangle index, uninterpreted material, contact feature (face/edge/vertex), assumptions, source-vs-approximate provenance, and `native_game_parity_verified=false`, `training_approved=false`. With unknown tree clearance, it abstains unless the caller explicitly opts into provisional *terrain-only* analysis using `assume_tree_free=True`. No game launch actor or accepted shot power is inferred.

## Contact modes

- `point_center`: radius 0, modeled ball-center intersection.
- `swept_kcol_query_0p5`: **optional route-tagged** query radius 0.5, from original Rev1 Ball→KCol source. This is not evidence that 0.5 is a universal physical ball radius. Generic two-sided continuous triangle collision checks face, edge and vertex, with radius-inflated candidate bounding boxes. Native KCL octree, prism thickness, one-sidedness and exact game collision sequencing remain unverified.

Initial penetration, degenerate triangles, invalid vectors/radius/mode or bad mesh fail closed. No trees, bounce or roll are modeled.

## Motion model and source boundaries

Partial zero-wind source-guided recurrence is `v1=v+a; p1=p+v1; v_next=0.999000013*v1`. Default acceleration is `(0,-0.002,0)`; user-supplied lift/lateral/spin are explicitly *illustrative* approximations (0.0012/0.001 coefficients and 0.9985/0.997 scalar decays). Original evidence: https://github.com/Nate27624/Wii-AI-Golf/issues/415#issuecomment-6787015935.

Not ported: source-exact f32/LUT, native `fn_80297A00` position writes, branches, guest-step clock, exact wind/spin direction, collision sidedness, launch prep→selected Ball, true v0, club/power/pose mapping, real flight XYZ. Operator's original local scratch work (11 airborne tests, 30 point-contact tests, 19 swept-sphere tests) informed this implementation; those original private scratch files were not silently copied or represented as exact-source parity.

## Run locally from repository root

```powershell
py -3 src/wii_ai_golf/physics/first_contact.py --assume-tree-free
py -3 src/wii_ai_golf/physics/first_contact.py --assume-tree-free --mode swept_kcol_query_0p5
py -3 src/wii_ai_golf/physics/first_contact.py --obj C:\\path\\to\\private-course.obj --assume-tree-free --start 0 1 0 --velocity 0.01 0.05 0
py -3 -m unittest discover -s tests -p test_first_contact_solver.py -v
py -3 -m unittest discover -s tests -v
```

Default demonstration uses synthetic planar geometry only. Do not publish private source OBJ coordinates, ROM/RAM, screenshots or source paths. Tests cover face/edge/vertex, point-vs-sphere times, reversed winding, vertical face, tunneling, miss, alternate elevations, invalid geometry, initial penetration, local OBJ parsing, negative/no-contact controls, abstention and explicit provenance.

## Delivery / evaluation gates

A tested provisional API is an offline numerical instrument, not a verified Wii Sports Golf landing predictor. Native initial-ball state transfer is S002's separate assignment, and real same-shot/guest frame physics/contact evidence requires S001/S002 independent evidence and separate operator authorization. No live Dolphin, game actions, private capture or training eligibility is authorized by this code. Source and source-coordinate systems must not be replaced by visual display-fit transforms. `training_approved=false` always.


## External airborne trajectory boundary (2026-11-12)

\`predict_contact_from_trajectory(samples, terrain, *, contact_mode, assume_tree_free)\`
accepts strictly increasing \`(t, xyz, vxyz)\` tuples. The caller defines the
time coordinate and all spatial units; \`vxyz\` is validated but never used to
extrapolate a hidden launch state. Between samples only **linear geometric CCD**
is performed. Contact returns \`contact_t\`, \`time_base=caller_supplied_unverified\`,
ball center, terrain surface, and contact feature. This does not claim native
game seconds, guest ticks, a verified starting velocity, or change ownership of
the independently assigned S003 airborne stepper.

When speed-like strength and nonzero illustrative lift or lateral terms are
provided, an explicit nonparallel spin axis is now mandatory: otherwise the
model fails closed rather than silently zeroing these forces. The actual native
spin-direction formula remains delegated to the S003 airborne owner.
OBJ zero vertex indices are rejected; original private meshes remain local.


## Coplanar point-center completeness and metamorphic controls

The synthetic/Euclidean \`point_center\` reference now includes an explicitly
**generic two-sided** zero-radius coplanar entry check. A trajectory lying in a
triangle plane can enter through a finite edge or vertex without crossing that
plane. A bounded convex halfspace clip provides its earliest in-plane entry;
parallel misses and slightly off-plane tracks remain no-hit. This is **not**
evidence of native KCol sidedness or that in-plane motion counts as a game hit.
Exact start-on-surface remains a fail-closed initial-overlap error.

Additional synthetic controls exercise split triangles, zero-length tracks,
initial contact at the .5 source-*query* radius, and high-speed tunneling.
The r=.5 KCol query remains route-specific, not the verified physical ball size.
