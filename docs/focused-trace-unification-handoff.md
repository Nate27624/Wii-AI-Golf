# S002 evaluation → unified CLI handoff

**Scope implemented:** offline focused-XYZ JSONL time-series auditing. This is not a new game launcher or competing top-level CLI. In accordance with `AGENTS.md` and `CONTRIBUTING.md`, operator launch/startup stays with the integrator and public commands stay under `py scripts/golf.py` (coordinator-owned).

## Components

| Component | Ownership and contract |
| --- | --- |
| `src/wii_ai_golf/focused_trace.py` | Evaluation-owned pure Python offline `analyze_trace(path, motion_threshold=.1, reset_threshold=25.) -> dict` |
| `scripts/analyze_focused_trace.py` | Advanced internal adapter; no Dolphin, RPC or GPU |
| `tests/test_focused_trace.py` | Negative cases: reset not misclassified as flight; null pointers handled; no invented shot counts; no raw address leakage |
| `src/wii_ai_golf/cli.py` | **Untouched**, coordinator owns future public adapter |

## How to reproduce two-swing investigation (offline)

From the user's **evaluation worktree**; no prior Dolphin or terminal setup assumed:

~~~powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"
git fetch origin
git switch --detach origin/agent/evaluation/read-only-golf-snapshots
$env:PYTHONPATH = (Resolve-Path ".\src").Path
py -m unittest discover -s tests -p "test_focused_trace.py" -v
py scripts/analyze_focused_trace.py --input "captures\focused-object-xyz-20261025T000301Z-bfd74bbd.jsonl" --output "captures\two-swing-segments-summary.json"
~~~

This analysis runs over *local* raw JSONL (not available to GitHub-only workers). The summary includes only elapsed timestamps, number of observed motion runs, null samples, and discontinuities. It cannot infer swing count, ball contact, success, score, or camera identity. A 176.34-unit sample jump is explicitly isolated as a discontinuity, **not velocity**. Motion runs are **not validated shots**.

## Request to coordinator / other agents

1. Coordinator: after PR review, add one narrow operator adapter `golf research trace --input PATH [--output PATH]` to `src/wii_ai_golf/cli.py`; delegate to evaluation function. Do not fork startup, parse live bridge data or duplicate core algorithm. Update `docs/cli.md` and CLI regression mock tests in coordinator-owned PR.
2. Integrator: continue owning Felk startup, controller, savestates, timing and physical/emulated controller modes; provide a verified frame/contact event in future shared observation protocol. No S002 code changes needed.
3. Modeling: consume only explicitly **candidate/unverified** XYZ time series. Derive no ball speed or labels until camera/ball discrimination passes. Depend on the evaluation return contract, never local hardcoded RAM addresses.
4. Learning: avoid treating candidate movement as reward or score; await evaluation-validated landing/score measurement.
5. Evaluation: retain raw RAM/time series locally, publish only sanitized summary and source-linked evidence. Maintain claim and ledger pointers; don't force-update other branches.

**Validation state:** the module and offline tests are committed, but have **not** run against the user's local JSONL or a Windows Python environment in this session.
