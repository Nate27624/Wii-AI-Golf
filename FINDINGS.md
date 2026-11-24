# Curated findings

A finding describes a bounded claim, not a task or a permission. Status vocabulary: candidate, verified, refuted, superseded. Verified means the precise stated claim is supported, not that a broader hypothesis is proven. Keep original evidence, limitations and contradictions. No private raw data or copied logs.

## F-REGISTRY-001 — verified inventory

Goal/milestone: G-RESEARCH / M-OUTCOME. At integrated baseline 838c3699, the memory registry has 35 entries: 11 snapshot-correlated, 15 source candidates, 8 unresolved, 1 rejected. Every entry has training approval, input eligibility and label eligibility false.

Provenance: [immutable registry](https://github.com/Nate27624/Wii-AI-Golf/blob/838c36990b562030a15a4d40cf7e3e2902329ccd/research/memory-variables/registry.json), blob 596a5c4a59f9195ba0f54ee6786148775bcb0905; manager inventory review. Applies to RSPE01 US Rev1, not proof of runtime physical meaning. The registry and detailed evidence ledger remain authoritative for individual field provenance.

## F-CCD-001 — verified implementation, native parity unverified

Goal/milestone: G-RESEARCH / M-CONTACT. The provisional offline terrain first-contact solver accepts explicit initial state, separates modeled center and surface coordinates, and abstains when tree clearance is unknown unless the caller explicitly opts into provisional terrain-only analysis.

Provenance: [immutable solver study](https://github.com/Nate27624/Wii-AI-Golf/blob/838c36990b562030a15a4d40cf7e3e2902329ccd/research/studies/S003-P0-FIRST-CONTACT-SOLVER-01.md), [#482](https://github.com/Nate27624/Wii-AI-Golf/pull/482). Applies to the implemented numerical model, not native KCol, ball radius, game timing, bounce, roll or real-shot prediction. Training remains false.

## F-POWER-001 — candidate investigation

Goal/milestone: G-RESEARCH / M-POWER. Accepted native scalar and selected-ball launch transfer remain unresolved. Animation and redline threshold are not validated accepted-power labels.

Provenance: [#418](https://github.com/Nate27624/Wii-AI-Golf/issues/418) and [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415); ongoing source investigation, not an immutable verified physical claim. Requires original-source and same-shot independent controls; no training use.

## Curation procedure

Workers propose stable finding ID, goal/milestone, claim, validation state, task/run evidence, immutable source/CI references, provenance, limitations, applicability and any contradiction/supersession links. Manager checks uniqueness, referential integrity, evidence strength, privacy and exact fence before accepting. Keep superseded/refuted entries discoverable. No goal changes or promotion from candidate without the appropriate evidence and authority. Fenced curation is not yet activated; this initial seed is a reviewed source proposal under V2.
