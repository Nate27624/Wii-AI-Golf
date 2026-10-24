# Evaluation read-only capture handoff — 2026-10-24

Issue #3. New read-only capture/compare tool + seven offline mock tests; **not** proof of game variable extraction. No edits to integrator transport or controller code. See docs/game-data-capture.md.

Source-reviewed upstream bridge exposes memory.read_bytes and controller reads; client capped at 64 KiB. Screenshot RPC is not used due to potentially oversized framebuffer response; local preexisting screenshot hash support only.

First user action: run capture WITHOUT --range at game first-shot screen to confirm read-only RPC and controller reads. Optional later 4 KiB explicit-window capture before/after a manually made on-screen change. Compare supports unverified PPC big-endian f32/u32/s32 candidates.

No live Dolphin process in this session. Mock tests: seven passed in isolated local harness. Full repository tests still required before merging. Any game memory offset, shot value or unit is unknown.

Dependencies: Issue #2 visible Plus-button and named savestate verification; Issue #4 calibration; Issue #3 score double annotation. Do not count memory matches as valid ShotResult rewards.
