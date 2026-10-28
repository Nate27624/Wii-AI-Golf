# P0 V1 source-ball motion evidence: offline-only secondary auditor

**2026-10-28. S002-support. DRAFT. No Dolphin, new swing, native memory read, or GitHub raw upload.**

## Why

Operator explicitly approved proceeding toward a defensible same-shot moving-ball XYZ test, rather than any more broad idle/aim RAM scans. The real B0–B3 captures provide strong stationary negatives: source-selected player+0x54/+0x60, ball child+0x4C->+0x30 and caches +0xCC/+0xF0/+0xFC remain stable; player aim+0x3C/+0x40..4C changes. Existing V1 contact-positive 3 PRE/2 POST/3 SETTLED captures include minimap effects, not the source-selected ball; 8 effect-handle words and 5 unsettled tail words are not physics.

Existing S001 V1 watched bridge/collector (#166→#189→#202→#206→#211) can sample 51 selected-player u32 and source-selected ball/record/start VEC3s at sample interval4 and requires 45 OBSERVED Dolphin A-held frames and 89 unchanged trace samples. It is DRAFT, not approved for live. PR #215 stationary-only no-shot qualifier attempted a native Dolphin launch, but the game process crashed with `0xC0000005` BEFORE bridge preflight. Do not attempt another live launch until source owner identifies fault module and approves clean runtime. Read-only game qualification/native <=5000us read timing, shot contact and V1 parity remain unverified.

## New code, without touching S001

`scripts/audit_p0_v1_ball_motion_private.py` reads ONE future S001 V1 private selected-ball-frame-watch JSON (under the ignored Wii-AI-Golf-Data). This is not a watcher; **it does not acquire or edit memory**. It is complementary to the independent trace-link validator #193 and source ranker #191; both remain mandatory S001/S002 gates.

Before reporting phase-related observations it independently fails closed unless all are true:

- Exact private record schema, completed watched state, controller `kind=swing` and 89/89 trace; one integer trace ID matches all trace-stage samples; strictly ordered unique trace indices and increasing sampled callback ticks.
- Source stable owner, selected slot (0–3), hole (0–8), valid mapped 51 big-endian u32 record words; raw record+0x54 f32x3 must exactly match the separately emitted same-sample record vector; conditional +0x60 start-copy is only checked for finite type and change counts.
- Separate `operator_contact_human` and `operator_observation` visible-movement labels; both agree with the producer's safe_summary and are never conflated.
- One A-button-only request with >=45 *observed* held-A frames; >=24 separately observed idle frames; max 5000µs sample-read bound; source checked and watch complete.
- Requires stable idle/A-only/neutral/backswing negative ball-control vectors, stable tee/start, and sampled forward/followthrough, before saying a **source-selected candidate trajectory correlates with observed movement**. A source vector changing during neutral, precontact backswing, a-only, or when contact/movement are not both independently YES cannot pass.

Console output is **only** stage/sample counts, booleans, and conservative gate statuses. No 51 raw words, 3D coordinates, pointer addresses, actual trace ID, source native paths or controller trace content. Always marks `actual_ball_world_xyz_verified=false`, `same_guest_physics_frame_verified=false`, `actual_ball_velocity_xyz_verified=false`, `collision_frame_verified=false`, `approved_for_training=false`. A 2D/3D changed vector in callback time does NOT establish guest-physics velocity, axes, units, contact frame, carry or landing. Original S001 V1 schema does NOT sample +0xCC/+0xF0/+0xFC caches: this script explicitly flags `source_ball_cache_cc_f0_fc_sampled=false` instead of inventing coverage. S001 owner must add cache reads inside its own callback if a private native <=5ms performance qualification and RPC size budget allow it; do not add another RPC/socket to collect physics.

## PowerShell, offline-only — only after a V1 private watched shot is obtained

The script requires a real watched V1 report filename, which **does not yet exist as a confirmed-contact capture**. Do not run on unrelated B0–B3 or V2/no-hit records. The complete source-pinned operator PowerShell command must be generated after S001 owner review and one approved watched V1 report is actually present. For now, this is a software validation/review deliverable; **No PowerShell action is needed from the operator**.

## Owners, merge and next action

S001 issue #2 owns fixing the native startup crash, code source+prepared bridge validation, stationary no-shot native performance, selected-ball/watch cache acquisition, canonical fresh launch and the frozen swing. S002 issue #3 owns this secondary source-ball candidate interpretation plus separate #193 frame/trace join and 51-word analysis. S000 #205 owns typed registry and training permissions; no registry edits or publishing are proposed here. S003 should only receive eventual approved typed fields, never this speculative phase-motion signal. Follow all dependency order before an approved live shot. This branch is main-based with ONLY new files and has no runtime implementation edits.

All tests are synthetic mocks across Windows and Ubuntu; they **do not establish** actual memory changes, native <=5ms reads or a verified shot.
