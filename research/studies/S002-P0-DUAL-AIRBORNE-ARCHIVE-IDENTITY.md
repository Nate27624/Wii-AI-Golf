# S002 P0: Verify whether two human-airborne archives are the same preserved bank pair

2026-10-28. Owner: separate S002 offline-only support. Training, physical XYZ, velocity, physics-frame and direct publication remain unverified/blocked.

## Why a separate study?

The operator has two separately named ignored private-airborne archives reported in S000/#205 and S002/#223 discussions:

- Source-copy format: Data/captures/in-flight-human-20261028-054537477/{mem1.raw,mem2.raw,manifest-PRIVATE.json}
- Separate p0-preservation format: Data/captures/p0-airborne-*-PRIVATE/{FLIGHT-MEM1.bin,FLIGHT-MEM2.bin,provenance-PRIVATE.json}

They may be two copies of one captured bank pair, or different flight-time captures. No public/private bank SHA equality was reported between these distinct formats. Two agents already own pin/cup decomposition and four-ball-slot specificity, so this study DOES NOT reimplement either. Without archive identity evidence, joining their results as one physical flight moment would be unsound.

Earlier source-selected ball position+0x30 and caches+0xCC/F0/FC changed 3/3 components B0-to-human-airborne; tee/start stayed 0/3, but source pin also changed 3/3. This strongly motivates source-specific followup while retaining a geometry confound, not trainable XYZ.

## What this audit does

New scripts/audit_p0_dual_airborne_archive_identity_private.py examines exactly two archive directories directly within the ignored Data/captures directory. Default left archive has the exact observed source-copy name; default right archive requires a UNIQUE p0-airborne-*-PRIVATE directory. Missing or multiple matches safely ABSTAIN; an explicit right input may instead be supplied. No recursive scanning.

Both banks MUST be exactly 24MiB and 64MiB. The left manifest must match the existing S002 #223 private human-flight provenance schema, including independently recomputed SHA256 of both left files and unverified frame/XYZ/training flags. The right provenance JSON is checked only for bounded readable metadata, NOT a guessed hash-schema; right_provenance_hash_schema_verified=false. SHA256 equality between each corresponding pair is computed privately; only MEM1_equal and MEM2_equal booleans are printed. A pair of TRUE values proves byte-identical archived files, not same game tick, same boot, actual moving XYZ, physics units, velocity, or training. A different result must not be interpreted as evidence of ball movement.

New scripts/Invoke-P0DualAirborneArchiveIdentity.ps1 is a PowerShell-only operator entrypoint. It runs fabricated privacy/failure tests first, then private SHA comparison; no Dolphin start, game input, ROM, savestate, new memory capture, writes, upload, ZIP or raw hash/path logging. Data outside the ignored root and symlinks are rejected. No automatic GitHub research_cli typed adapter exists; a curated sanitized FINDING on #223 and #121 is required after local execution.

## Ownership and merge requirements

S002 #223 owns actual B0-vs-flight source/geometry analysis. Its claimed pin decomposition and another agent's four-slot specificity are separate. S001 owns any future same-shot live watcher; S000 #205 owns registry and publisher. This PR adds only independent new files. Focused synthetic Windows/Ubuntu CI and PowerShell parse must pass, followed by S000/S002 review and complete Windows suite before any merge. No local raw archive has been examined by this agent and this PR remains draft.