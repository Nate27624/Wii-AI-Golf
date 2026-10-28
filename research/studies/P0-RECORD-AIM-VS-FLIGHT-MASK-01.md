# P0 selected-player record changed-word masks: no-shot controls vs airborne

**2026-10-28 / S002-support / draft stacked on #223**.

## Actual motivating evidence

Operator ran source-gated #223 on both independent archived airborne copies: two-bank hashes match exactly; selected record 51 u32 B0→human-airborne changed at **21 offsets**: +0x034,+0x038,+0x03C,+0x040,+0x044,+0x048,+0x04C,+0x074,+0x090,+0x094,+0x098,+0x09C,+0x0A0,+0x0A4,+0x0A8,+0x0AC,+0x0B0,+0x0B4,+0x0B8,+0x0BC,+0x0C0. Selected ball +0x30, caches +0xCC/+0xF0/+0xFC change 3/3; tee/start and player record +0x54/+0x60 stay equal, but separately verified PIN changes 3/3. Existing B0–B3 source-only idle/WASD no-shot controls showed aim-associated +0x3C and +0x40..+0x4C and 1/18/1 whole selected-record word differences between consecutive phases. These facts motivate a **disjoint-mask classification**, NOT a 21-word physical swing claim.

## New complementary tool

`scripts/audit_p0_record_flight_vs_aim_private.py` validates the EXISTING local **original B0/B1/B2/B3 manifest and each 24+64MiB full-bank SHA**, plus separately archived same-size airborne pair and private manifest SHA, via upstream #181/#223. It reuses exactly #223's Rev1 source scene/player/slot/hole/ball selected-object checker in each of FIVE snapshots. All selected owner slots and holes must match, and source constructor self-pointer gates must pass. No independent heap scan or synthetic phase attribution; original labels are the operator's historical annotations.

It reads only the selected source 51-word 0xCC player record per phase and returns field-relative changed-word **offsets, not values**: B0→B1 (idle), B1→B2 (WASD aim), B2→B3 (idle), union of no-shot changes, B0→flight changes, overlap, flight-only-vs-controls, and no-shot-only-vs-flight. It separately computes source-ball/start three-component changed counts and no-shot four-phase stationarity checks. The 'flight-only' label means **new relative to this control cohort only**, not physical flight, shot power, vertical velocity, unit coordinates or a verified velocity derivative. Producer/capture data can differ by boot or scene; the independent pin-confound PR #224 owns pin semantics. Aim-only no-shot data do not prove the semantics of 21 record words.

Never prints run-specific pointers, absolute RAM addresses, bytes, whole 51-word arrays, private paths, file hashes, numeric vectors or shot IDs. JSON console result is counts/known source-relative offsets/booleans only; source RAM remains under ignored Data, no direct GitHub publication. Explicit no frame atomicity, no same boot, no pin check in this tool and training=false. **Do not use for P0 score labels**.

## Owner and dependency

Stacked on draft #223 (and its inherited #181/#163/#160 source readers). This script does NOT edit #223 source reader or #224 pin owner, another agent's four-slot test, S001 #222 V1 swing/bridge, or S000 #205 registry. S002/S000 review needed; S001 already has 32/32 stationary and 70/70 no-contact reader feasibility but no source-joined actual flight. No new swing/export required for this offline question. Tests are synthetic until exact private source-gated Windows execution; do not claim actual 21-vs-WASD overlap without that operator result.
