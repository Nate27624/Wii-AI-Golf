# Canonical game-memory variable registry — required agent workflow

**Single source of truth:** [registry.json](registry.json), with all findings for Wii Sports RSPE01 **US Revision 1**. This is the game-state variable **catalog**, not the trainable shot dataset or memory-dump storage. S000 coordinates shared semantics; S002 owns validation/provenance, S001 owns live frame/capture mechanics, S003–S005 consume only approved features/labels.

## Before and after every memory investigation

1. **Read this registry at the beginning of each agent context.** Search for existing logical `id` before scanning RAM, proposing a new field, or claiming an offset verified. Check open research PRs for overlapping work, particularly [P0 memory study PR #192](https://github.com/Nate27624/Wii-AI-Golf/pull/192) and [same-shot evidence #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121).
2. **Record each distinct memory variable**, including failed, disproven, constant, and ambiguous candidates, in `registry.json` as part of your own feature PR. Use stable IDs such as `golf.ball.world_xyz`; never silently rename an ID. Avoid duplicating a variable merely because its dynamic pointer changed.
3. **Record its retrievable locator**: game ID/revision, source-derived static singleton slot where available, pointer dereference chain/relative offsets, big-endian read type, expected dimensions and units, and object/scene lifetime. If no proven stable resolver exists, set locator kind `unresolved` and `expression:null`. Session-specific heap addresses are *not* portable offsets and remain PRIVATE.
4. **Record what actually happened**: source URLs, same-shot capture/run/phase provenance, human-only versus machine-verified observations, confirmed positive/negative controls, counterexamples, and exactly what remains unknown. File names of private capture collections may be kept in local artifacts; GitHub gets only sanitized evidence group labels/issue links.
5. **Do not erase contrary evidence or promote by intuition**. Transition `unresolved → source_candidate → snapshot_correlated → runtime_verified` only when appropriate controls pass. `rejected` is a useful documented result. If a field is merely static scene geometry, do **not** relabel it as dynamic ball XYZ.
6. **Training safety is a separate gate**. `training.approved` must remain `false` until the S002 owner signs off a verified, frame-anchored reproducible measurement with independent controls and units; source version, accepted phase, censor/miss logic, training/test partition and exact per-shot ID must be defined in the approved dataset contract. Distinguish features available **before** action from future outcome labels; no target leakage, no sharing private RAM to Git.
7. **Run the validator** and existing repository tests before PR review:
   ```powershell
   py scripts/validate_memory_registry.py
   py -m unittest discover -s tests -p test_memory_registry.py -v
   py -m unittest discover -s tests -v
   ```
   Cite results accurately; synthetic tests cannot count as live-game validation. Changes to registry schema/status/training contracts require S000 and S002 review before merge. PRs must meet [merging requirements](../../docs/merging-requirements.md).

## Minimum required variable record

`id`, `name`, `role`, `priority`, `status`, `datatype`, `unit`, `game` (ID/revision/endianness/mode), `memory_locator` (root+typed steps or explicitly unresolved), `evidence` (URLs, capture groups, observations, confidence), `phase_provenance`, `limitations`, `required_controls`, `owner`, `training` (approved/feature-or-label eligibility/reason), `review` (reviewer/date), and `last_evidence_date`.

Use **literal source-backed offsets** in `memory_locator` so later extractors can resolve variables against new RAM sessions; never bake the heap address of one Dolphin instance into a training feature definition. Any automatic extractor must additionally validate game revision, scene, pointer range, endian type, snapshot consistency and per-field control proofs.

## The important current distinctions

| Registry ID | What we know | Missing before training |
| --- | --- | --- |
| `scene.current_id` | Source-backed manager+0x18, snapshots agree with scene 5 | Independent fresh boot + actual non-Golf transition negative |
| `golf.main_ptr` | Golf scene +0x9C pointer corroborated in B0–B3 | Does not identify ball physics |
| `golf.tee_start.map_translation_xyz` | Candidate map-object translation from field manager +0x50 and base +0x30 | Object semantics, controlled scene change, coordinate units |
| `golf.pin.map_translation_xyz` | Candidate map-object translation from field manager +0x44 and base +0x30 | Independent pin/hole variation, axes and units |
| `golf.cup.map_translation_xyz` | Cup pointer +0x54, unverified inherited base +0x30; aligns horizontally with pin | Cup class inheritance and physical coordinate meaning |
| `golf.unknown_float_pair.change_cluster` | Two changing finite floats in one local study | Complete reusable locator, verified phases, actual ball correlation |
| `golf.ball.world_xyz` | Not discovered yet | Real flight + stationary controls and exact frame-linked shot |
| `golf.ball.velocity_xyz` | Human recalls at least one non-still JSON-associated ball; downward direction uncertain | Same-shot identification and measured velocity vector |

**2026-10-28 operator correction:** at least one JSON-associated ball capture was not fully stationary; *downward velocity was suspected, not measured.* Which JSON maps to the B0–B3 RAM snapshots is unresolved. Do not label B2 or another bank as falling/settled based on a bit toggle.

## Access for future training code

A later approved feature extractor may load `research/memory-variables/registry.json`, select records with `training.approved=true` and `training.eligible_as_input=true` or `eligible_as_label=true`, then read their verified typed locators **against matched private same-shot RAM captures**. Keep extraction tools versioned, persist registry commit SHA and training-data manifest, and fail closed on missing variables, revision mismatch, failed pointer checks, invalid phases, censored values or units. There are **zero training-approved fields currently**.

For a PowerShell-only catalog view after merging, run:

```powershell
Set-Location -LiteralPath 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$registry = Get-Content -Raw 'research\memory-variables\registry.json' | ConvertFrom-Json
$registry.variables | Select-Object id,status,datatype,unit,
  @{Name='Trainable';Expression={$_.training.approved}} | Format-Table -AutoSize
```

**Publishing boundary:** commit safe *schema and source-derived resolver descriptions* in regular reviewed PRs. Private raw MEM1/MEM2, ROM, savestate, raw JSONL, local directories, dynamic pointers, low-level vectors, source-derived private output, and secrets must not leave `Wii-AI-Golf-Data`. Publication of an allowlisted sanitized result to `research/observations` remains the existing reviewed `research_cli` workflow; do not add a second uploader.
