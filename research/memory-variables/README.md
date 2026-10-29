# Game-memory candidate registry — RSPE01 Rev1

The single **catalog and training-eligibility index** is [registry.json](registry.json). It records source-typed or unresolved field candidates, source-relative locators, original-bank provenance, controls, limitations and explicit training gates. It is not a shot dataset, ROM/RAM archive, emulator hook, source-reader implementation, or permission to perform a live shot.

As of this integration there are **35 candidates; none are training-approved**, and none may be used as an approved training feature or label. The physical rendered-ball world position, velocity, impact time and power remain unverified.

## Before interpreting a field

1. Locate its stable `id`; do not create a parallel source locator or assume same-number offsets in different objects refer to the same field. Revision must be **RSPE01 US Rev1**, with exact source provenance, big-endian type, object owner and scene/hole/Config controls. Dynamic heap addresses are not reusable locators.
2. Preserve both positive and negative original observations. The original seven numbered MEM1/MEM2 pairs are SHA/source-gated first-hole observations whose shot-phase labels are **human-supplied, not independently frame-attested**. D1's human airborne label conflicts with the selected current ball equaling START. W5→W6→W7 source-selected +0x30 changes are **candidate translation changes**, not verified rendered world XYZ.
3. Keep the independent score-table findings separate: the selected SequenceMgr +0x14 9×4 region and RPGolConfig +0x04 36-word region were each **0/36 changed** on the recorded comparisons; Config row orientation and official selected cell remain unverified despite public source evidence favoring hole-major indexing. These observations do not establish a mode4 reward or disprove delayed score updates.
4. FieldManager +0xA4 target-effect kill bool stayed **false in all seven numbered captures**. It is a source-typed UI negative control, **not** contact or target-hit evidence. A cache tag, Main +0x74 counter or selected-player record scalar must never be relabeled a guest physics clock, shot power or distance without independent proof.
5. Default all `training.approved`, `training.eligible_as_input` and `training.eligible_as_label` to **false**. Any promotion requires S002 source/owner and frame-aligned validation, physical or game units, independent control evidence, exact shot identity, terminal outcome censoring and a reviewed versioned dataset contract. A 100-foot off-green penalty is censored, never measured carry.

## Validation

On the exact proposed branch/head, run:

```powershell
python scripts/validate_memory_registry.py
python -m unittest discover -s tests -p test_memory_registry.py -v
python -m unittest discover -s tests -v
```

The [registry workflow](../../.github/workflows/memory-variable-registry-checks.yml) executes these checks on Windows and Ubuntu with **synthetic-only test inputs**. The registry validator rejects unsupported game revision, malformed locators, private dynamic MEM2 roots, duplicate IDs and premature training approval. No Dolphin, private data, controller input or automatic uploader is involved.

## Evidence preservation and ownership

The [source/behavior evidence ledger #154](https://github.com/Nate27624/Wii-AI-Golf/pull/154), [seven-phase parent #231](https://github.com/Nate27624/Wii-AI-Golf/pull/231), [global-ball provenance #240](https://github.com/Nate27624/Wii-AI-Golf/pull/240), and [canonical registry PR #205](https://github.com/Nate27624/Wii-AI-Golf/pull/205) contain the primary observations and unresolved hypotheses. The S000-cleanup-f handoffs on #205 preserve exact historical code/CI/negative results, including PRs #234, #238, #242, #245, #252 and #277. See the original [capture-priorities research history](https://github.com/Nate27624/Wii-AI-Golf/blob/50ad481c92a5efef42eff6bd46b29826a8164578/research/memory-variables/p0-capture-priorities.md) for detailed historical reasoning; it is **not** an active capture request.

Experimental private JSON inventory, selected-object triage, cross-hit recurrence and B0/flight three-reader matrix scripts are preserved in #205 Git history, **not installed as V2 production scripts**. They were exploratory and are not needed to validate the registry. Do not request repeat original seven-phase captures, create a second memory scanner, or run Dolphin without separate operator authorization. No raw banks, vectors, ROMs, savestates, credentials, private file paths or local configurations belong in Git.

S000 manages shared catalog integration; S002 owns source/measurement semantics; S001 owns explicitly authorized controller/launcher operations; S003–S005 may consume only approved typed evidence. Follow root [merging.md](../../merging.md) for current-main ancestry, full exact-head tests, platform CI, conflict checks and objective self-merging.
