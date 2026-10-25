# Research-observation publication gate

The `research/observations` Git branch is **already working** with existing
Git credentials: operator-reported offline test success, independently confirmed
in public record
[`20261025T024510Z-fe87c132b7`](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T024510Z-fe87c132b7.json)
(commit `514edbf6a672e19fb600fe82a8f2c411052863bc`).
The record is a PASSING **process test**, not a golf hit or score.

## Why a publication gate is necessary

`scripts/research_cli.py publish_summary` previously wrote the supplied dict
without checking its `id` or contents. A future collector using that transport
could accidentally upload an unreviewed extra field, nested private label, or
dangerous filename. Successful test publication did **not** prove the generic
publisher's privacy contract.

The pure `wii_ai_golf.shared.public_observation.public_observation` gate now:
- Requires safe per-attempt IDs and known record kinds before *any* Git work.
- Validates known `test` and human-labelled `v1` fields, including nested
  label and controller structures.
- Drops potentially unbounded local `settled_screen_observation` and fallback
  `warning` text from V1 public records, leaving them intact locally.
- Validates S002 phase-differential output (PR #116): region-relative
  offsets, source-derived role vocabulary, bounded counts and human phase labels.
  It rejects runtime addresses/raw bytes and normalizes the public warning.
- Allows the S000/S002 PR #130 `golf_scene_root_candidate_triage` **only**
  with its exact source-gated Rev1/mode-4 schema: two static cells, two passes,
  at most 40 emulation frames per read, slot indices 0 or 1, bounded counts,
  and all `confirmed_*` flags **false**. The stricter stacked PR #132
  emits exactly four additional own-scene/backlink/sport/uniqueness fields
  and a different fixed warning; this is accepted as a **second, exact
  producer shape**, not arbitrary schema extension. Contradictory booleans,
  partial add-ons, count/gate mismatches, mixed warnings, pointer values,
  private paths and unsupported fields are rejected before any Git call.
  A report with **zero candidates is valid and informative**.
  Two surviving cells remain **ambiguous**, never a confirmed singleton.
- Recognizes the **already-published S002 24-run cohort** record kind
  `golf-memory-cohort-relative-words` with a separate exact schema, safe
  `cohort-` ID, bounded recurrence counts and source-defined warning. A
  cohort is not an individual shot or verified RAM power address.
- Rejects unknown kinds rather than silently publishing a private schema.
- Does **not** change the Git clone/push mechanism, add credentials, start Dolphin,
  or claim unverified ball/club/power variables are known.

## Owner handoff and acceptance

S002 is responsible for actual private capture internals and public source facts.
**PR #116 must verify its actual output is accepted by this gate**; changes to
new observation kinds need schema review, synthetic fixtures and test coverage.
S003 should consume only the tested schema and preserve 100-ft penalty censoring.

Before merge, run in a clean Windows test checkout:

```powershell
py -m unittest discover -s tests -p "test_public_observation.py" -v
py -m unittest discover -s tests -p "test_research_cli.py" -v
py -m unittest discover -s tests -v
```

Network publication should also be spot-checked using the existing
`py scripts/golf.py research test` command **after merge**, not from an
unreviewed detached branch. No live Dolphin permission is implied.

## Existing unmerged scene-root pilot

PR #130 intentionally checks `public_observation` before using the existing
Git-based publisher. If that module is absent in its independent worktree,
publication must be **refused** while its already-written sanitized JSON stays
private. It does not mean the Dolphin probe failed. Because PR #126 has not
merged into `main`, neither `main` nor PR #130 currently contains this
module. After PR #126 passes the targeted+full Windows regression suite and
S002 approves the source fields, merge #126; then refresh PR #130 against
reviewed main and rerun tests. **Do not bypass validation or force publication.**

The operator should run `py scripts/golf.py research validation` from the
separate canonical clean `Wii-AI-Golf` main checkout (which includes merged
PR #127), not from the historical detached/diverged Scene-Root-Pilot branch.
Do not `git pull` into the pilot merely to get an unrelated CLI command.

## Publish a SAVED scene-root result, without repeating a Dolphin test

After PR #126 is reviewed, Windows tested and merged, use the **clean canonical
main** checkout with the existing research CLI (Git's configured credentials,
no new PAT). This reads exactly one sanitized scene-root summary from the
private sibling `Wii-AI-Golf-Data/captures` directory by validated ID:

```powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only origin main
py scripts/research_cli.py publish-saved-scene-root --id YOUR_FULL_RECORD_ID --local-only
py scripts/research_cli.py publish-saved-scene-root --id YOUR_FULL_RECORD_ID
```

The first call validates without network access. The second publishes only
after the built-in clean-main sync, exact source schema/type check, file size,
ID match and pre-Git privacy sanitizer all pass. It never attaches to Dolphin
and cannot choose an arbitrary raw file. The ID is the middle token in the
existing local filename `golf-scene-root-<ID>-summary.json`. Do not copy
or upload `RAW-PRIVATE.jsonl`. The original report need not be re-captured.

From a divergent experimental worktree do **not** `git pull origin main`
just to use this command. Use the canonical clean main checkout. If main is
dirty, stop and inspect status; never force-reset, merge or stash automatically.

The replay command is **in pending PR #126 only**, not currently available
in merged main. Check that it passes tests/owner review before using it.
