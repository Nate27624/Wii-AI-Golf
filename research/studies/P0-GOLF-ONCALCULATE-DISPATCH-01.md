# P0 — Is the public Golf OnCalculate virtual a 2-instruction main-object forwarding thunk in native Rev1?

**Status: SOURCE-CANDIDATE until a real pinned operator audit. Draft / no emulation or training.**

## Why this narrow question matters

Public [kiwi515 ogws_info `RPGolScene.h`](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolScene.h) annotates `RPGolScene::OnCalculate()` at code PC `0x8028DFA8`, its next `OnReset()` at `0x8028DFB0` (exactly two PowerPC instructions later), and a typed `RPGolMain* mGolMain` at scene **+0x9C**. Independent public Rev1 text-unit bounds from #240/#219 place `RPGolMain` in `0x8028E098..0x8028E900`. These are published source annotations, NOT proof that the real US Revision 1 binary at those code PCs dispatches from the live vtable or runs physics.

**Falsifiable two-instruction claim**: at `0x8028DFA8`, first PowerPC D-form is `lwz r3,+0x9C(r3)` and second at `0x8028DFAC` is a **nonlinking direct relative** `b` to the published RPGolMain text-unit bounds. If both hold in all seven Rev1 source-qualified private archives with full SHA before/after, we have a candidate **scene main-object dispatch target** for S001 to review. If either differs, the typed thunk hypothesis is NEGATIVE (not an endorsement of another hook). A matching branch is **not** a proof of vtable identity, actual execution, call frequency, physics update, visual correspondence, or same-guest-frame timing.

## Implementation

- New-only `scripts/audit_p0_golf_oncalculate_dispatch_private.py` stacks on **exact #231** canonical seven original BANK SHA gate (`_check_archive` before/after) and source selected scene/player/ball/pin/tee (`_get`). Only reads the two declared public .text words from each of seven already preserved native MEM1 banks; no broad scan, no arbitrary memory child walks, no Dolphin.
- Source scene+0x9C pointer is checked as an owner **class only** (`MEM1/MEM2/null/unmapped`) without reading speculative child fields. The script emits only these classes, static branch target (a public code address, if qualified), and bools. No actual PPC words, heap addresses, native vectors, archive hashes or private paths.
- `tests/test_p0_golf_oncalculate_dispatch_private.py`: wholly synthetic wrong register/offset/opcode/link/conditional/indirect/out-of-text branch, PPC signed offset, malformed word, full SHA fail-fast, no-training markers and isolated `python -I` CLI help.
- Windows and Ubuntu native-free Actions tests, no private capture in GitHub.

## Confidence/stop rules

1. The public `RPGolScene.h` address annotation might be from a different revision. A two-word binary match is evidence of its **instruction shape**, not independent vtable resolution. The source `OnCalculate` runtime target and named method remain **unverified until vtable / callsite proof**.
2. Even an authenticated scene callback that forwards to RPGolMain can encompass zero, one or many actual golf simulation steps. **Only game-physics update entry/exit provenance**, independent guest-step clock and same-hook selected/global/pin/tee/config read can support frame-timed ball measurements. The existing Felk `event.frameadvance()` count and cached latest screenshot are insufficient. See #272.
3. If output `oncalculate_to_main_direct_thunk_supported=false`, **STOP this annotation path**; do not keep increasing static search windows without a new source reason or owner direction.
4. Neither #240 global constructor nor #215 S001 watcher should be auto-edited/merged here. S001/S002/S000 explicit approval required before any clock hook or no-swing live probe. W5/W6/W7 phase labels disputed; code identity is label-independent.

## Optional local operator validation after source/CI review

Use an exact Git commit pinned detached worktree from PR (no moving head trust): `py -m unittest discover -s tests -p test_p0_golf_oncalculate_dispatch_private.py -v`, then `py -I scripts/audit_p0_golf_oncalculate_dispatch_private.py --archive <unique-original-p0-new-cohort-PRIVATE>`. All 14 original banks are checked twice and all seven source contexts verified. No game/ROM write, capture, controller, network/private upload, training or publication.
