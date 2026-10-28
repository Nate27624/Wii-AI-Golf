# P0 Golf dynamic-memory triage: pointer-chain and float candidates

**Status:** private B0–B3 source-layout-compatible capture audit; **NO ball-world XYZ, hit phase or training use verified**. Dynamic pointer values and coordinates are local research artifacts. Do not add raw banks, full audit JSON or trace IDs to GitHub.

## Actual operator evidence (2026-10-28)

- The operator ran the pinned alias-audit Python code on their full RSPE01 US Rev1 private B0–B3 paired banks; 10 local unit tests passed.
- Source-derived Golf scene/scene manager/mGolMain chain remained consistent across B0–B3.
- First 512 bytes of main gave 34 stable pointer fields but only 33 unique 1-hop targets (aliases). The selective 2-hop graph enumerated **109 new unique targets**, sampled **109**, omitted **zero**; 142 total unique sampled pointees; `coverage_status: complete` **within the declared scope**, not full game RAM.
- Exactly **27 unique aligned changed words outside the root 4 KB** were recovered. Fourteen fall in one MEM1 cluster and 13 in a separate MEM2 cluster. Their pointer provenance is indirect; neither cluster is proven ball data.
- Two adjacent words in the MEM1 cluster decode as finite floating-point values changing across captures. Only two components have been established; a complete VEC3 and independent actual ball-motion relationship are unproved.
- Another cluster contains sentinel-like constants, flags, and changing pointer candidates; interpreting it as ball physics is unjustified.
- B0–B3 are from a single study, with unknown independently verified game phases. Different whole-bank SHA-256 values establish differing RAM snapshots, not proof of contact, projectile flight or different boots.

## Reusable checks

- `scripts/audit_golf_main_aliases.py`: bounded, alias-aware read-only pointer diff; explicit coverage and omitted-count; synthetic tests `tests/test_golf_main_aliases.py`.
- `scripts/triage_golf_float_candidates.py`: reads the *local private* alias-audit JSON and exact B0–B3 banks, checks that every reported changed word matches the bank bytes, inspects surrounding word values and possible neighboring three-float windows. Rejected on mismatch between report root or capture order and dumps. Synthetic tests in `tests/test_golf_float_candidates.py`.
- Both require automatic retrieval from the draft PR's pinned GitHub commit when running from an ordinary local main checkout. No GUI or Dolphin launch.
- A float window with two or three varying components is **not** a verified dynamic ball coordinate: demand shot-ID, frame-anchored pre/flight/post and controlled camera/aim-only negative trials, with stable tee/pin geometry and independently observed ball movement.

## Critical operator correction: a capture may show a ball still moving (2026-10-28)

The operator has explicitly recalled that **at least one of the JSON/capture observations did not show a fully settled ball**; the ball may have been falling or slowing down when memory was recorded. **Which JSON and which B0–B3 phase is affected is not yet identified**. Earlier assumptions treating all captures as settled/end-of-shot are therefore invalid. Do not resolve the uncertainty by assigning B2 or any other capture a phase based only on memory toggles or changed bits.

This makes the two moving BE-float-compatible words in the offline audit worth controlled follow-up, including the possibility of a real trajectory with one constant component. It does **not** establish that those words belong to the ball, nor does it justify training labels. Trace back local private manifests, exact run/shot identity, capture frames, visual status and any non-atomic read timing. Once a plausible true in-motion phase is located, compare **same-shot** before/during/after samples with human-confirmed movement and a stationary control, while checking static tee/pin/cup translation values remain fixed.

## Next validation gates

1. Verify the third neighboring 32-bit word and whether any candidate triplet forms a coherent float vector.
2. Preserve pointer provenance for candidate windows and reject aliases or unrelated allocations.
3. Establish B0/B1/B2/B3 shot-phase provenance before assigning semantic labels; B2 has toggle candidates, not a proven ball-contact state.
4. Capture one clear shot with confirmed ready-to-swing, known control trace and synchronized pre/moving/post memory samples; use the CLI's validated fresh session/guarded attach workflow, never assume an unverified menu-sequence log is enough.
5. Independently vary aim, shot, and hole to falsify static-source/layout coincidences; keep all guessed fields tagged CANDIDATE pending S002 review.
