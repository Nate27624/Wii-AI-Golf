# Independent offline audit of ranked Wii Sports motion candidates

This is a read-only supporting tool for the active S002 evaluation agent. It does NOT start Dolphin, swing, load a savestate, read raw game memory, upload files, or certify any ball/score position. **Live-game commands still require the full canonical Dolphin launch and intro.**

## Grounded observations from a published report

The 2026-10-24 [active-motion S002 report](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T085852Z-d39c3401/research/results/hitting-green/20261024T085852Z-d39c3401.json) reported 111 candidates but published only the top 30 ranked vectors. Those **30 published rows** include 18 unique starting memory addresses, 12 duplicate rows, 9 repeated addresses, and 8 connected groups of overlapping 12-byte float32 vector spans. Several endpoints are near unit norm, which might be directions/rotations instead of world XYZ, but neither interpretation is verified.

An earlier [50-sample contrasting report](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T085619Z-2f8a22d2/research/results/hitting-green/20261024T085619Z-2f8a22d2.json) published no moving candidates. This is not a blinded controlled baseline. In particular, do not say the *entire* set of 111 candidates contains only 18 unique addresses: the audit is restricted to the published ranked subset.

## Tool behavior

- Checks JSON schema, total candidate count and truncated-list conditions.
- Aggregates exact duplicate candidate addresses and retains their window names/activity maxima.
- Creates connected groups of overlapping [address, address+12) byte spans. Overlap does not prove semantic identity.
- Flags published address/offset inconsistencies and possible unit-length vectors as *hints*, not facts about the game.
- Optionally compares listed addresses to a second local report (published subsets only).
- Generates a structured sanitized JSON audit; output is local and exclusive-create, never overwriting source or prior audits.

## Run offline on an existing sanitized report

From the canonical repository after pulling this change:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py scripts/audit_motion_candidates.py --input "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\golf-motion-ACTUAL-RUN-summary.json" --out "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\audit-ACTUAL-RUN.json"
~~~

Replace ACTUAL-RUN with the real report filename. For a valid comparison add an optional "--baseline" argument pointing to another report. Input can also be a locally saved copy of the published sanitized JSON. This is **data processing, not a live experiment**, so unlike fresh capture commands it intentionally does not launch Dolphin.

~~~powershell
py -m unittest discover -s tests -p "test_audit_motion_candidates.py" -v
py -m unittest discover -s tests -v
py -I scripts/audit_motion_candidates.py --help
~~~

Eight targeted tests passed on a minimal local Python reproduction; the full Windows repository suite and any actual collected game reports are NOT claimed to have been executed through this audit tool.

## Next evidence gate

The S002 agent should compare a candidate's time series with human-confirmed (1) ball stationary before stroke, (2) ball traveling after visible contact, (3) ball resting after landing, and (4) a different pin or tee geometry. Different views of the same memory address are not independent training samples. A high motion count alone cannot certify a ball coordinate, distance in meters, or the game's official score.

This tool is deliberately separate from the evaluation agent's in-progress PR #14. Coordination: [S002 issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3).
