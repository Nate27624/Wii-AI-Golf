# Cross-agent golf evidence integration contract (2026-10-24)

**Purpose:** unblock actual golf learning without duplicate implementations. This is a proposal for the exact handoffs, not an assertion that publication or real-game scoring has been verified.

## Existing mismatches to reconcile

- Merged execution-status publisher (PR #86): writes `research/auto-results/<run_id>.json` to `research-results`; its run ID is `YYYYMMDDTHHMMSSffffffZ-<8-hex>`; it only asserts process completion.
- Read-only evidence reviewer (PR #105): reads `research/observations/<id>.json` with an ID pattern `YYYYMMDDTHHMMSSZ-<suffix>`, expects `id` matching the filename and a `kind`-specific schema. It therefore **cannot** directly consume the PR #86 upload records.
- Proposed human-observation schema (PR #91): emits `record_type=human_observation`, `observation_id` as content hash, and no distinct `id`/`kind`. Repeated identical outcomes produce the same content hash. Do not treat that hash as a per-shot trial identity.
- S002 calibration branches (PRs #100, #104, #96) add source-specific details. Only the S002 owner should map their raw capture fields into a public export. Never import private raw captures or infer scores in S000/S003 code.

## One canonical contract, two distinct record classes

1. **Execution status** stays in `research/auto-results/` and uses current strict publisher schema. It is *never* counted as ball contact or golf score.
2. **Public observations** will use distinct `research/observations/<id>.json` artifacts with a unique per-attempt, non-PII `id`, `kind` that the reviewed consumer explicitly supports, and source-specific allowlisted scalar fields. Only a vetted publication adapter may create these artifacts.
3. Do not silently convert process metadata, minimap-byte deltas, inferred power, or human reports into verified game measurements. Each observation must retain the field's source, units, and verification status.
4. For first release, do **not** expand private-file ingestion in `evidence_review.py` or give it GitHub write access. Instead have an S002-approved *sanitizer* produce the consumer's vetted public schema, then extend the publisher with a separate allowlisted observation write, tested with a fake API.
5. IDs must represent distinct trials, not identical contents. Replaying the same upload must be idempotent; different shots must remain separate even with identical human labels and trace hashes.
6. Results remain on isolated `research-results` branch; don't upload raw RAM, pointers, screenshots, ROMs, savestates, local paths, or arbitrary notes.

## Ownership and merge order

| Owner | Requested handoff | Gate |
| --- | --- | --- |
| S002 | Confirm canonical capture fields for contact, green, displayed distance/units, initial club pose, A-prime and trace SHA; specify what is human-labeled vs independently verified | Post exact source schema + sample **fully synthetic sanitized fixture** on PR #91 |
| S001 | Confirm successful canonical boot/held-A trace contract for S002 power probes; do not duplicate launcher or trace scheduling | Review S002 PR #104 before live experiments |
| S003 | Consume immutable S001 traces and S002 provenance; preregister the comparison and include missed/unknown attempts | Review S002 PR #100 and align old parameter generator in PR #17 |
| S000 | Keep shared publishing/consumer contracts and privacy tests; connect uploader only after S002 schema approval | Verify Windows offline tests and one authenticated publish to `research-results` |
| S004/S005 | Use only declared evidence fields, isolated train/test splits, and exact trial IDs; label synthetic versus real-human data | No model conclusions based on exit code or unverified power |

## Reproducible acceptance sequence

1. Operator-confirmed full Windows unittest suite: passed after PR #103. This does not validate network upload.
2. One **offline-only** Lab experiment, with `WII_GOLF_AUTO_PUBLISH=1` and private token, creates one status record on `research-results` (PR #86 smoke).
3. Independently inspect that JSON: it contains only the strict allowlist, and no local paths, raw RAM, secrets, or score claims.
4. Obtain S002 sign-off on PR #91's field names/units; then add a versioned observation exporter and fake-network privacy tests, without touching S002 capture internals.
5. One user-approved live shot records separately sourced human labels. Verify upload on `research-results` and that PR #105's read-only reviewer accepts it without promoting the labels to verified score.
6. Only then expand automatic downstream training/calibration.
