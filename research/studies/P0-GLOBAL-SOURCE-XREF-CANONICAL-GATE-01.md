# S002 P0 — original seven-bank archive gate for global source-slot XREF

## Ownership and scope
Review-only child of [#240](https://github.com/Nate27624/Wii-AI-Golf/pull/240), not a change to its source xref reader, global pointer interpreter, or receiver provenance. Source-scanner audit_p0_global_ball_source_xrefs_private.py uses its own per-phase before/after digest, but absent an ORIGINAL manifest comparison an already-mutated, parsable bank could be treated as the preserved human-labeled wedge. [#247](https://github.com/Nate27624/Wii-AI-Golf/pull/247) and [#249](https://github.com/Nate27624/Wii-AI-Golf/pull/249) are separately hardening different global/roster readers; do not copy or modify those agents' scripts.

## What the separate wrapper verifies
- Source #240 is an exact tested parent and no changes to its scripts/ directory have occurred on this child branch or in its working tree.
- Pinned canonical #231 exact SHA 89aa3a2bd3e82532c4051168a466498e7195f596 is checked out separately, and its Python sources are unmodified.
- Full #231 audit_p0_seven_numbered_source_pairs_private.py --archive is run before AND after the bounded #240 wedge source-xref analysis. This verifies original 7-pair manifest descriptors, all 14 MEM1/2 bank SHA256, and Rev1 selected source gate each pass.
- Original manifest SHA256 stays unchanged over the entire operation. Only the xref reader's existing sanitized source-unit-relative labels/counts are printed.
- Xref report is checked for three qualified wedge phases, same source-global slot and source-code, stable wedge references, and all semantic/training publication gates remaining FALSE.
- Windows PowerShell 5.1 -SyntheticOnly calls the real xref suite with no capture path or original RAM present. CI never executes native sampling.

## Operator invocation (do not run until review)
From the existing Wii-AI-Golf repository, create a separate #231 exact-pinned worktree and another isolated checkout for this draft PR using the exact PR head after CI. Then:

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<XREF_CHILD_WORKTREE>\research\tools\Invoke-P0GlobalSourceXrefsCanonical.ps1" -CanonicalCheckout "<PINNED_231_WORKTREE>"

The wrapper finds exactly one locally preserved seven-pair ignored archive or accepts -Archive explicitly. Neither source nor archive is uploaded. Never run directly from a shared agent checkout, merge automatically, or treat positive unit-relative read/write xrefs as runtime execution.

## Limits
The existing local manifest is not an independently signed time/shot attestation. Direct D-form r13 stores in six Golf code units are NOT an exhaustive alias/xref scan and cannot alone assign the global slot's writer. No claim about rendered ball object, receiver r27 at runtime, code execution, physics axes, position, velocity, contact, power, score, model training or publication is established. Human phase labels and guest frames remain unverified. Keep the branch DRAFT pending S002 source owner review.
