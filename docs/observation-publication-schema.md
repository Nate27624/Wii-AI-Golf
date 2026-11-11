# Proposed S002 human-observation publication schema v1

This is a **consumer-side schema proposal** for PR #86's GitHub publisher, deliberately separate from S002's capture modules and pending PR #14/#90. No real-time publication is enabled by this PR.

Only independently allowlisted human-observed contact, green, numeric distance and unit, the existing SHA-256 swing trace fingerprint, and bounded A-prime count are retained. The value `verified_game_score` is always false. Free-form notes, raw memory, pointer addresses, game paths, commands and file paths do not enter the output.

S002 must review field names, permitted displayed units, representation of missing observations, and privacy before we integrate the adapter with the network publisher. Do not claim game score, swing power or verified ball physics from this schema.

**Important limitation:** the deterministic observation hash is a content fingerprint, not a unique run identifier; identical observations share an ID. The eventual publisher must assign distinct verified run IDs rather than treating this hash as proof of independent trials.

Run locally:
```bash
python -m unittest discover -s tests -p test_observation_schema.py -v
```
