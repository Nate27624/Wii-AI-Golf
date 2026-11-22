# S002 — Ball/KCL coordinate-basis provenance (offline, 2026-11-21)

**Owner:** `S002-coordinate-basis-20261121-b`; task `S002-P0-BALL-KCL-COORDINATE-PROVENANCE-20261121-B`, [S000 roster rev48](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7073967068), [canonical issue #415](https://github.com/Nate27624/Wii-AI-Golf/issues/415). This is **not** the guest-step witness applicant A, accepted-power owner, selected-v0 owner, KCL exporter, or S003 first-contact solver.

## Question and falsifier

Do source-selected **Ball effective translation** and original source-qualified **KCL prism vertices** use the same native XYZ basis, units and handedness, or an independently established transform? A perfectly coherent synthetic Ball trajectory and original KCL mesh cannot establish native first contact if Ball and terrain frame provenance differ. The merged first-contact solver accepts coordinates as **caller-supplied** without verifying transforms; rendering/inspector display-fit alignment is not native coordinate proof.

Previously established evidence relevant to the question:

- Source-selected versus source-global Ball translation is distinct; W5/W6/W7 changes and D1 airborne==START contradictory human labels do not establish rendered-world XYZ. [V2 evidence gates](../../docs/v2-evidence-gates.md).
- Original local KCL OBJ candidate has 2,498 terrain faces and is **not distributed** in the repository. [S003 first-contact solver study](S003-P0-FIRST-CONTACT-SOLVER-01.md). Its `source_query_radius=0.5` is a path-specific KCol query, not a confirmed visible ball radius.
- S003 M1 zero-wind `sample_trajectory` produces caller-defined numerical-step XYZ with no selected-Ball v0/guest-clock/native PPC parity. [S003 airborne study](S003-P0-AIRBORNE-INTEGRATION-20261112.md).

**Conclusion from existing published data:** no independently source-attested 3D matching landmark correspondences and Ball-to-KCL basis transform have yet been verified here. Native coordinate compatibility is therefore **UNKNOWN**. No new original source study or Dolphin run was authorized for this task.

## Bounded validation contract

`scripts/review_p0_ball_kcl_basis_provenance.py --input <locally reviewed sanitized JSON>` reads a maximum 64 KiB JSON and prints **only a categorical report**, never archive hash, source reference, shot label or coordinates. No network, file writes, private source scanner, KCL parser or game control. It takes:

- `schema="wii-golf-basis-claim-v1"`.
- `ball` with `source_kind="source_selected_ball_translation"`; `terrain` with `source_kind="source_kcl_prism_vertex"`. Each requires exact revision `RSPE01 Rev1`, same **source cohort SHA256**, scene/shot IDs, independently source-qualified marker, units, handedness and distinct basis ID. A cohort ID is a *supplied provenance assertion*, never a computed hash check of private files.
- Four or more **corresponding, independently identified, noncoplanar** landmarks in **each** system, matched by stable landmark ID. The input anchors are *basis-control landmarks*, not an instruction to equate an arbitrary flying ball center with a terrain vertex. The full-rank condition rejects a planar-only surface proof of a 3D axis convention.
- A *separately sourced* `transform_witness` with explicit `kind="independent_source_transform"`, qualifying source reference and boolean, basis IDs, unit names, uniform positive length scale, 3x3 transformation and translation. Checks similarity (no arbitrary shear), determinant sign versus claimed handedness, and residuals under a strict caller-defined finite tolerance. **Fitting the witness from these same landmark pairs is not independent evidence.** The script cannot cryptographically verify source authenticity or execution.

Output `CONDITIONALLY_CONSISTENT` means solely that the **supplied** source/transform assertions and synthetic/reviewed anchors are internally consistent. `INCONSISTENT` identifies a numerical mismatch **under the supplied witness**; `ABSTAIN` rejects provenance/identity/independence gaps. None means the actual game Ball/KCL world basis or first-contact XYZ has been verified. Three output flags remain unconditionally false: `selected_ball_world_xyz_verified`, `native_game_parity_verified`, `training_approved`.

## Positive/negative controls

Synthetic positive controls: identity; independently declared translation; proper axis rotation; deliberate scale/unit conversion; handedness-changing reflection only when explicitly declared and witnessed. Negative controls: swapped axes under an identity witness, silent translation, missing scale conversion, same-handed reflection, nonuniform scale/shear, wrong archive/cohort/scene/shot, incorrect source-selected vs source-global Ball owner, unmatched identifiers, planar-only landmarks, missing/uncorroborated transform, uncertain handedness, nonfinite/bool inputs, excessive tolerance, invalid source revision and accidental raw information in CLI output.

Run focused suite with `python -m unittest discover -s tests -p test_p0_ball_kcl_basis_provenance.py -v`, then full `python -m unittest discover -s tests -v`, with exact-head Windows/Ubuntu CI required under root `merging.md` before merge. All fixtures are fabricated mathematical coordinates; synthetic positive results are **not** source/game parity measurements.

## Next S003/S002 handoff

Before integrating any *source-labeled* KCL contact:

1. S002 source/shot owners establish same effective selected Ball receiver, exact original source/KCL candidate identity and independent, same-scene 3D matched anchors (four noncoplanar landmarks); do not assume selected/global equivalence, D1 world XYZ or known frame cadence.
2. Independently recover an original Rev1 coordinate mapping or positively prove identical units and handedness; **do not fit a display transform or trajectory endpoint** to rationalize model parity. Treat lack of basis witness as `ABSTAIN`.
3. Only then can S003 apply a source-qualified mapping to caller-supplied trajectory and terrain coordinates, with protected CCD and guest-step/shot evidence gates. This task does not modify the existing contact solver or assert one native game collision.

No ROM, RAM, archive contents, savestates, original OBJ, per-boot addresses, private paths, Dolphin input, original-source LocalOps execution or training approval were used or published.
