# Canonical game-memory variable registry — required agent workflow

**Single training-access index:** [registry.json](registry.json), with typed source-derived locators, candidate evidence, and training-eligibility gates for Wii Sports RSPE01 **US Revision 1**. The existing [33-field evidence ledger (PR #154)](https://github.com/Nate27624/Wii-AI-Golf/pull/154) remains the deeper provenance/identity/behavior record; this index references it and **does not supersede or duplicate its evidence ownership**. This is the game-state variable **catalog**, not the trainable shot dataset or memory-dump storage. S000 coordinates shared semantics; S002 owns validation/provenance, S001 owns live frame/capture mechanics, S003–S005 consume only approved features/labels.

## Current P0 research and private-capture discovery

- [P0 capture and analysis priorities](p0-capture-priorities.md): reuse S002's source-selected ball-object +0x4C vector, +0xCC/+0xF0/+0xFC cached vectors, selected record +0x54/+0x60, and angle-like +0x3C; do not confuse source layout with physical world XYZ.
- [Read-only local private JSON inventory](../../scripts/inventory_private_golf_json_motion.py): helps locate the *specific* JSON associated with the operator-observed moving ball without opening Dolphin, downloading full memory, or publishing raw numeric values.
- The [source/behavior evidence ledger PR #154](https://github.com/Nate27624/Wii-AI-Golf/pull/154) tracks 33 existing claims. Index records include `evidence_ledger_field_ids` so a future training extractor can trace their provenance. Both PRs are pending review; **neither schema is automatically on `main` yet**.

Offline PowerShell JSON index after this PR is available locally:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
$dataRoot = Join-Path (Split-Path -Parent $repo) 'Wii-AI-Golf-Data'
py -I (Join-Path $repo 'scripts/inventory_private_golf_json_motion.py') --data-root "$dataRoot" --top 20
```

This scans bounded local `.json`/`.jsonl` only and writes `json-motion-inventory-PRIVATE-*.json` **inside the ignored sibling private data directory**; stdout prints anonymized file IDs, field counts and phase annotations, no raw ball values, world-space coordinates or local file paths. Review the local index to locate the relevant file, then correlate via actual shot/frame IDs. An apparent velocity field or changing pair of floats is still **not a measured vertical velocity or verified ball XYZ**.

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

As of the current #205 registry integration, **35 candidate entries are recorded and zero are training-approved**. The catalog includes source-derived selected-ball translations and caches, separate player records, source-only UI controls and unresolved physical game variables; a source label does not by itself establish a rendered-ball or training interpretation.


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
$repo = (git rev-parse --show-toplevel).Trim()
$registry = Get-Content -Raw (Join-Path $repo 'research/memory-variables/registry.json') | ConvertFrom-Json
$registry.variables | Select-Object id,status,datatype,unit,
  @{Name='Trainable';Expression={$_.training.approved}} | Format-Table -AutoSize
```

**Publishing boundary:** commit safe *schema and source-derived resolver descriptions* in regular reviewed PRs. Private raw MEM1/MEM2, ROM, savestate, raw JSONL, local directories, dynamic pointers, low-level vectors, source-derived private output, and secrets must not leave `Wii-AI-Golf-Data`. Publication of an allowlisted sanitized result to `research/observations` remains the existing reviewed `research_cli` workflow; do not add a second uploader.
