# S002 GUI live run contract — current Golf Lab

**Current integration PR #62 is based on main's latest Golf Lab.** The existing V1 diagnostic and automatic merged test discovery remain the supported UI. Do NOT switch to stale PR #52 UI.

## Run from the GUI

On clean canonical checkout **after merge**, launch `py scripts/golf.py lab gui`. Choose **Minimap camera-only differential** or **Minimap manual-swing differential** and click **Run ONE live**. The single dialog authorizes that one session. The operator uses their real Wii Remote to navigate to Hitting the Green. The recorder prompts for tee readiness and prints sample progress. There is **no automated swing** for this S002 study.

This S002 path deliberately uses **physical Wii Remote fresh Dolphin** rather than S001's V1 **emulated Wii Remote**, so success of a V1 swing does **not** demonstrate S002 launch compatibility. Both are routed through the same Lab live-session lock and GUI, but their input contracts differ. The physical S002 reader starts Dolphin only once through its existing `session_bootstrap.ensure_intro()`. No outer `run_golf_experiment.py` should precede it; doing so would double-launch.

## Dependencies / merge order

S002's existing live collector lives on PR #14's evaluation worktree (`Wii-AI-Golf-Data`). The adapter `scripts/run_s002_lab_capture.py` validates the required files before spawning the child. This is a **transitional** dependency, not yet an integrated single-checkout package. If that checkout is absent or behind, the UI cannot run this experiment. The integration owner should move the reviewed S002 modules into the canonical package and add an exact preflight before calling it production-ready.

- Keep S001's working V1 swing diagnostic unchanged.
- Never use user-owned raw memory in Git; summaries only.
- Acceptance: `test_lab_s002_current_ui.py`, all `test_lab_*.py`, one user-authorized camera-only GUI run with observed sample progress, then one swing only if camera-only succeeds.
- No claim of tested Windows live S002 capture yet.

## Failure interpretation

An error naming missing S002 checkout means PR #14 code is not installed; it is **not** a Dolphin control failure. A missing Felk executable/bridge is an environment setup issue. An occupied port or existing Dolphin instance must fail closed rather than kill an unknown emulator. Any read-only capture with zero reports should be treated as failure, not a successful swing.
