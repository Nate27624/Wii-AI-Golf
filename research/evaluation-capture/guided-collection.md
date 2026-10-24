

## 2026-10-24 — guided shot-by-shot collector / auto-publish

User requested a single command telling them which Hitting the Green shot to reach, Enter before the swing, manual swing, Enter on result, and upload for external analysis. Added `scripts/collect_hitting_green.py` and `src/wii_ai_golf/golf_collection.py` with an interactive read-only before/after state and human score protocol. Local evidence defaults to canonical repo sibling `Wii-AI-Golf-Data/captures`; GitHub publication pushes a whitelisted JSON per run on a unique `data/hitting-green-...` branch based on `origin/main`, not raw game bytes/frames and not code main. Optional `gh` Issue #3 comment carries only the link. Supports optional observed scenario plan from integrator PR #15. The project still has no verified automatic swing or independent score extraction; every result is human-observed, not an AI-generated shot. Requires local Git push credentials and first live run.
