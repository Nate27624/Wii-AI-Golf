# P0 seven numbered human-phase snapshots: source-gated offline review

**Scope.** User's real local Windows operator performed 7/7 *paired* 24MiB MEM1 plus 64MiB MEM2 source-to-archive SHA verification. Native originals `tools/FelkDolphin-Clean/User/Dump/1.1.raw ... 7.2.raw` unchanged. Archive `Wii-AI-Golf-Data/captures/p0-new-cohort-*-PRIVATE` with manifest kind `p0-private-numbered-capture-inventory`. These historical capture descriptions are human-operator notes, not machine-joined numeric phase labels:

1. Driver midair, power meter rising, ~27 visible (not RAM).
2. Same driver shot landed/stationary before transition.
3. Putter backswing, A not pressed.
4. Driver backswing, A pressed.
5. Wedge airborne near apex, ~31 on visual meter (not RAM).
6. Same wedge shot slightly later while descending (operator inference).
7. Same wedge strike flag, 'Nice on', ball stopped around 15.2ft (human visual estimate).

**Tool.** `scripts/audit_p0_seven_numbered_source_pairs_private.py --archive <private preserved folder>` reuses #223 full-source Rev1 scene/source selected golf chain and original player record / ball+0x30 plus three caches. It FAILS CLOSED if any bank integrity, expected seven pair membership, scene chain or pin selfref is unavailable. No generic memory scan. It compares only five meaningful edges (1→2, 3→4, 5→6, 6→7, 5→7) guarded for same selected player and hole, reports u32 component-change counts (0..3), selected player record +0x34/+0x38/+0x74 boolean changes, ball-cache equality and pin/start pointer comparison flags, Config selector+0xBC/+0xC0/+0xC4 equality flags. User's original archive manifest has hashes and raw lengths; only sanitized non-numeric positions/paths and no hash text printed.

**Precautions.** A pass is source-chain plausibility and inter-snapshot change only, NOT verified physics, guest same-frame atomicity, independent interval timing, axes, velocity, shot power, actual impact frame or approved training. In particular the 7 numbered pairs cannot be treated as a contiguous 7-frame sequence or as a single shot; they represent different club and shot phases. No new Dolphin, guest memory writes, capture or raw RAM upload. S001 live watch / S002 source ownership / S000 registry remain separate. Pilot only after offline tests and owner review; user runs PowerShell pinned worktree from canonical source checkout. Original bank archive has independently copied hashes, not GitHub observable file bytes.

**Known operational failure mode.** `_get` requires the original selected pin object's +0x4C selfref and Rev1 source-selected player/ball chain to be valid in *every* phase. If the wedge contact / transition phase fails, report ABSTAIN, not a fabricated zero or a direction of movement. Request next narrower owner-gated per-phase audit if needed.

**Status at creation.** Synthetic tests only. No real seven-pair bytes available to remote agents. Dedicated CI Windows/Ubuntu and operator local read must be recorded separately. Do not claim source-vector velocity without two time-indexed physical positions.
