# Swing bridge regression: offline audit before another trial

User-confirmed contact occurred in S002 outcome captures (2.1 ft GREEN at 122 trace frames, 100 ft MISS at 89), then later shots no longer contacted the ball. Restoring the earlier no-prime trace in PR #44 did not restore contact. A separate confound is the generated local swing bridge V2 (S001 PR #39). For original 89 trace frames, V1 called the motion API 89 times while V2 calls it on only 35 nonzero-motion frames. For 122 frames the corresponding source-level counts are 122 versus 35. These are theoretical API dispatch counts, NOT measured club movements.

Successful observed shots predate the bridge V2 patch; this timing does not prove causality. Do not change swing power, duration, savestate, or menu timing while investigating.

## 1. Inspect bridge sources OFFLINE before another live game

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_audit_local_swing_bridge.py" -v
py -I scripts/audit_local_swing_bridge.py
~~~

This prints file existence, source markers, SHA256 fingerprints and safety of an earlier bridge backup. It does NOT start Dolphin, read RAM, modify save states, send controller input or transmit local files.

It inspects the existing generated bridge in sibling tools/mcp_bridge_swing.py and its first saved pre-V2 backup tools/mcp_bridge_swing.py.before-neutral-v2.bak. A backup can qualify as a possible V1 source only if it contains the atomic and swing marker but NO startup-autoload hook, which could silently reset the savestate twice. A backup marker cannot prove which bridge a previous emulator loaded.

If the audit does not find a validated pre-V2 backup, STOP and share its JSON rather than reconstructing an unknown script from guesses.

## 2. Optional controlled V1 copy only if backup validated

If v1_isolated_trial_possible is true, an operator can explicitly create a separate V1 source at tools/mcp_bridge_swing_legacy_eval.py with:

~~~powershell
py -I scripts/audit_local_swing_bridge.py --prepare-legacy-trial
~~~

This only copies validated legacy bytes into a new .py file. It does NOT overwrite current V2, previous backup, or launch Dolphin. The tool refuses unexpected sources and existing conflicting files.

A later explicitly chosen controlled test MUST still launch the full integrated session from CLOSED Dolphin, restore the correct named green-pre-start checkpoint, perform A/A+B/A navigation and only then run the action. After reviewing the offline audit and preparing the legacy source, one experimental full-start command is:

~~~powershell
py scripts/run_golf_experiment.py --send-live --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --bridge "D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_legacy_eval.py" --script collect_outcome_transition.py -- --send-live-swing
~~~

That may still miss. This is a controlled isolated bridge comparison, NOT a guarantee of reproducing a hit. Note independently whether A was held, club animation occurred, the ball actually moved, and the game displayed a distance. A complete RPC trace does not prove contact. Do not interpret misses as zero-distance scores.

The earlier backup is a candidate legacy bridge but not independently verified as the exact historical working source. Reproducing hits with V1 and not V2 under identical controller, savestate, trace fingerprint and scene conditions would strengthen the hypothesis; other failures would point toward emulator/controller/scene timing.

No installed patch is silently downgraded; no ROMs or raw memory dumps are uploaded.
