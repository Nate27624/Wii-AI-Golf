# Wii AI Golf — one shared cross-agent interface

Issue #47 owns the unified experiment lab, registry, GUI, live runner, and CLI adapter. This document is a coordination contract, not a competing runner.

## Owner and interface boundaries

| Study / owner | Modules and responsibility | Shared interface |
| --- | --- | --- |
| S000 coordinator (Issue #47) | lab registry, one runner, optional GUI, run history | delegates to the existing tested entry points; no second Dolphin |
| S001 integrator (Issue #2) | Felk bridge, named savestate, Emulated Remote, A / A+B / A menu intro, swing trace | one canonical fresh session for all live commands |
| S002 evaluator (Issue #3) | memory candidates, human labels, eventual verified outcome decoder | does not equate RAM changes or RPC ACK with game score |
| S003 modeling (Issue #4) | parameter sweeps, action-response calibration | consumes S001 action provenance and real S002 measurements |
| S004/S005 learning (Issues #5/#6) | policies, comparators, frozen holdouts | never trains on synthetic/unverified reward as real score |

The user-facing application should have one study registry and one dispatcher across CLI and GUI. The GUI should call the same runner, not implement motion, Dolphin boot, savestate loading or score calculation independently. Keep advanced scripts available for diagnostics only.

## Shared implemented bridge identity contract

All agents can import the same stdlib-only read-only API:

~~~python
from pathlib import Path
from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file, audit_bridge_sources

identity = inspect_bridge_file(Path("D:/Projects/Wii Golf AI/tools/mcp_bridge_swing.py"))
# JSON-compatible identity including path, sha256, revision, byte count, and markers.
~~~

Source marker labels: V1-neutral-swing-calls, V2-neutral-button-only, unknown-or-unexpected, missing, and too-large-or-empty. Do not mistake a V2 source marker for proof that running Dolphin loaded that exact bridge. SHA256 helps compare reproducible run provenance, but local identity is not a cryptographic source-attestation system.

Use this identity in run metadata alongside actual selected bridge path, Dolphin build, game revision, named savestate profile, full controller trace hash/frame count, button-only A prime requests, human-observed contact, original visible score/unit and decoder-validation status. Unknown is not zero. A completed subprocess or controller trace does not prove a scored shot.

The earlier S001 offline command scripts/audit_local_swing_bridge.py now imports this shared module instead of containing a second copy of the source-marker and V1/V2 classification logic. Its original public functions remain usable under the same names, preserving compatibility with existing tests and scripts.

The optional isolated pre-V2 copy remains explicit only. Never auto-downgrade a generated bridge behind the operator's back, because that silently changes the experiment's actuator. Never modify original bridge or backup in place.

## Current empirical bridge question

The operator's actual local audit reports V2 active (SHA256 prefix 0dcd138f9a8c, 20,256 bytes), and valid saved V1 (fe04cb0ba312, 19,530 bytes, no embedded autoload). Two earlier outcome collector shots had visibly recognized ball contact, but later V2 trials did not. Source-level motion API calls differ (89 versus 35 for an 89-frame trace) and justify one isolated controlled replay, not a claim of confirmed V2 causation.

The lab should distinguish at least these evidence gates: emulator boot acknowledgement, trace RPC completion, independent observed ball contact, human-readable result label, and independently verified game score.

## Ownership and testing

This change intentionally does NOT touch Issue #47 lab files or registry, S001 generated bridge or swing waveform, S002 collector, open S003/S004 PRs, ROMs, savestates or raw RAM. Cross-issue handoff documented on Issues #47, #2, #3, #4, #5 and #6.

Offline validation:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only
py -m unittest discover -s tests -p "test_audit_local_swing_bridge.py" -v
py -m unittest discover -s tests -p "test_shared_bridge_provenance.py" -v
py -I scripts/audit_local_swing_bridge.py
~~~

Tests on the user's Windows checkout and a live Dolphin session remain necessary; source-only tests do not prove a ball strike.
