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
- Validates the proposed S002 phase-differential output (PR #116): region-relative
  offsets, source-derived role vocabulary, bounded counts and human phase labels.
  It rejects runtime addresses/raw bytes and normalizes the public warning.
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
