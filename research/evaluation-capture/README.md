# Evaluation read-only capture handoff — 2026-10-24

Issue #3. New read-only capture/compare tool + seven offline mock tests; **not** proof of game variable extraction. No edits to integrator transport or controller code. See docs/game-data-capture.md.

Source-reviewed upstream bridge exposes memory.read_bytes and controller reads; client capped at 64 KiB. Screenshot RPC is not used due to potentially oversized framebuffer response; local preexisting screenshot hash support only.

First user action: run capture WITHOUT --range at game first-shot screen to confirm read-only RPC and controller reads. Optional later 4 KiB explicit-window capture before/after a manually made on-screen change. Compare supports unverified PPC big-endian f32/u32/s32 candidates.

No live Dolphin process in this session. Mock tests: seven passed in isolated local harness. Full repository tests still required before merging. Any game memory offset, shot value or unit is unknown.

Dependencies: Issue #2 visible Plus-button and named savestate verification; Issue #4 calibration; Issue #3 score double annotation. Do not count memory matches as valid ShotResult rewards.

## 2026-10-24: successful live US Rev1 spatial probe

User-reported source: Windows Felk Dolphin `RSPE01` Rev1, Hitting the Green mode raw 4. `probe_golf_spatial.py` read plausible translations pin (210.100006,-7,-350.5), cup (210.100006,-7.04664135,-350.5), and start (2.20000005,-5.5,-318), exact pin/cup X/Z overlap. 56 repository tests passed before subsequent probe correction. Distances remain unknown coordinate units; visual/temporal correlation required before converting this into a game-state feature.

Important bug: the reverse-engineered `mpTrans at +0x44` annotation overlaps `mScale +0x3C..+0x47`; actual read `0x3F800000` is float 1.0, not pointer. Updated branch reads scale directly and computes relative game-coordinate distances without any pointer dereference. Six local focused tests pass after fix. Remaining S002 live score/ball position capture still blocked; next host run should verify scale and compare distinct targets.
