# P0 Rev1 Source-only Upstream Swing-Magnitude Writer Audit

**Status: source research / not executed on the original private archive by this agent.** Scope is a small, read-only PPC-window study in original SHA-verified RSPE01 Rev1 Golf code. It does **not** modify memory, start Dolphin, send controller inputs, or label real accepted shot power.

## Why this is the highest-information missing link

In previous original-revision operator-qualified traces, `fn_802B4794` writes an intermediate current `+0x08` with `0x802B4914 stfs f30,8(r24)` and a peak-like `+0x0C` with `0x802B4924 stfs f1,12(r24)`, following an apparent comparison with earlier `+0x0C`. The same calc receiver is forwarded `0x802B4938 bl fn_802B3BA0 → 0x802B3D04 bl fn_802B2F90`. This later routine conditionally loads `+0x0C` and writes `+0x10` in state3 at `0x802B31B0..31C4`. These are compiled **register/field** claims, not proof that the game consumes Wii Remote acceleration, computes rotational speed, or accepts the value as shot power.

Previous bounded source writer inventory also contains `r24 +0x18/+0x1C` and `+0x28/+0x2C` stores in the same `fn_802B4794` source window. Their role (input axis? previous sample? timer? scale factor?) remains unverified. The first priority is **reaching f30/f1 definitions and their direct/indirect producers, including the earlier scratch float stores and callbacks**. Keep this separate from #415's downstream case launch wrappers/transfer function.

### Source-only diagram

```
unknown game-consumed motion samples / mode / state   UNRESOLVED
               |
        fn_802B4794
        r24+0x18/+0x1C, +0x28/+0x2C   candidate intermediates
               |
        0x802B4914  stfs f30,+0x08(r24)
        0x802B4924  stfs f1,+0x0C(r24)
               |
        0x802B4938 → fn_802B3BA0
        0x802B3D04 → fn_802B2F90
               |
        state3 conditional +0x0C → +0x10
               |
        fn_802B2A40 state-dependent getter
               |
        virtual transfer → fn_802A3CF4 → fn_802A7A64
               |
        launch-prep Ball writer fn_8029A0E0
```

The bottom half is source-traced but **not a matched guest-executed shot/selected-ball transfer**. `+0x08/+0x0C/+0x10` are currently calc state candidates, not proven gauge percentages or "power 101."

## 2026-11-11 operator original-archive result — **SOURCE PASS**

User executed the source-only script on the existing untouched original 7-pair archive, and pasted the sanitized JSON. The audit returned:
- `status: REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS`
- `original_14_bank_sha_pre_and_post_verified: true`
- `native_mem1_code_phases_1_5_7_identical: true`
- `four_explicit_mr_receiver_copies_exact: true`
- `two_direct_bl_edges_exact: true`
- `calc_0x0C_accepted_power_verified: false`
- `game_input_consumption_verified: false`

**New arithmetic decoded from that original sanitized source excerpt:** PowerPC single-precision `fmuls` has primary opcode 59, XO 25; `fsubs` is 59/20; `fadds` is 59/21; `fcmpo` 63/32. IBM PowerPC instruction reference: https://www.ibm.com/docs/en/aix/7.2.0?topic=reference-appendix-f-powerpc-instructions

There are **two virtual `bcctrl` calls** at `0x802B48B8` and `0x802B48EC`. Each is preceded by a `lwz r12,56(r12)` virtual slot load. The actual callee address, whether these calls return equivalent signals, and whether either sees raw Wii Remote movement are **not** source-verified.

Downstream of those two return values, original native PPC corresponds to these **per-update source expressions** (grouped as real single-precision multiplications, not exact real-number equivalence):

~~~python
# This is an interpretation of original instruction semantics, NOT game source.
R1 = float_returned_by_virtual_call_at_0x802B48B8
R2 = float_returned_by_virtual_call_at_0x802B48EC

candidate_A = (calc[0x18] * R1) * calc[0x28]  # fmuls at 48C8, 48DC
candidate_B = (calc[0x1C] * R2) * calc[0x2C]  # fmuls at 48F8, 4908

old_A = calc[0x08]
calc[0x98] = candidate_A - old_A              # fsubs 4900 / stfs 490C
if candidate_A > old_A:                      # fcmpo 4904; bc BO=4 BI=1 4910
    calc[0x08] = candidate_A                  # stfs 4914
if candidate_B > calc[0x0C]:                 # fcmpo 491C; bc BO=4 BI=1 4920
    calc[0x0C] = candidate_B                  # stfs 4924
~~~

This shows **conditional running-maximum updates on this path**, not an arbitrary static scalar or a proven in-game power percentage. No assertion about resetting those maxima at the beginning/end of a shot is warranted yet. Both `+0x28`/`+0x2C` are also subject to earlier compare-and-conditionally-store instructions at `0x802B487C/4880` and `0x802B4890/4894`, making their earlier update definitions the next critical subproblem.

**New exact opcodes/branch guards:** The draft audit now checks those five arithmetic sites, two ordered comparisons, both BO4/BI1 skip branches, two `lwz r12,56(r12)` slot loads and two linked `bcctrl` instructions; it fails closed if a different native source is used. This is a reproducible source-math check and NOT executable game-frame confirmation.

### Most useful next operator-only read (no new code required)

The original source audit was run without `--detailed` and therefore did **not include 0x802B4820–0x802B485C** in the public output; that missing segment contains the earlier definitions of `f2/f3` and `calc+0x18/+0x1C/+0x28/+0x2C`. Run from the existing isolated **Calc-Source-Audit** checkout:

~~~powershell
py -3 -I scripts/p0_calc_magnitude_upstream_private.py --detailed
~~~

This does not start Dolphin or send controller input. It re-checks all original archive SHA gates and prints symbolic PC, relative field and FP operand information only. The next reverse trace should identify `r31` source-object provenance and the indirect vtable +56 callee for each virtual call.


## What the microaudit actually checks

New-only `scripts/p0_calc_magnitude_upstream_private.py`:
- Autodiscovers a **unique existing** `p0-private-numbered-capture-inventory` under sibling ignored `Wii-AI-Golf-Data/captures`. Reuses reviewed `audit_p0_seven_numbered_source_pairs_private._check_archive` to verify **all 14 original banks' SHA256 and exact manifest identity before and after reading**. It refuses wrong sizes, missing, ambiguous, linked archives or altered originals.
- Opens ONLY existing phase 1, 5 and 7 original MEM1 read-only, verifies the bounded Golf source text windows have **identical instructions** across these three snapshots. Public source unit is OGWS `GolfScene_unsplit.o 0x802A79F8..0x802C7924`.
- Validates exact PowerPC `stfs` stores `0x802B4914(+0x08,r24,f30), 0x802B4924(+0x0C,r24,f1), 0x802B31C4(+0x10,r27,f0)`; `lfs` source `0x802B31B0(+0x0C,r27,f0)`; state `stw` `0x802B31C0(+0x1A4,r27,r0)`; and two relative BL edges `0x802B4938 → 0x802B3BA0`, `0x802B3D04 → 0x802B2F90`.
- Produces only a bounded sanitized symbolic **PC/opcode/register/relative field/branch-target** table for `0x802B4820..0x802B4938`, and a compact focused subset `0x802B4860..0x802B4924` to resolve producers and scratch stores. NEVER prints native 4-byte words, raw float values, heap pointers, file paths, original private hashes or game state. Unknown FP operations remain explicit `opcode63, xo5/xo10` rather than guessed mnemonics.
- Does not claim that forward-only `set_wiimote_swing` parameters equal in-game angular velocity or real accepted power.

This is a **static instruction slice**. Calls, virtual branches and conditional stores require separate CFG/read-target verification before claiming a live control-to-power mapping.

## Windows operator command (source-only; no ROM path, no Dolphin)

Run only after PR and exact-head CI validation. This creates a separate isolated source worktree; it will refuse to reuse an existing directory. Use PowerShell 5 or PowerShell 7.

~~~powershell
$ErrorActionPreference = 'Stop'
$main = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Calc-Source-Audit'
if (-not (Test-Path -LiteralPath $main -PathType Container)) {
    throw 'Existing main checkout missing'
}
if (Test-Path -LiteralPath $work) {
    throw 'Audit worktree exists; do not overwrite'
}
git -C $main fetch origin refs/pull/437/head
if ($LASTEXITCODE -ne 0) { throw 'Source audit PR fetch failed' }
$head = (git -C $main rev-parse FETCH_HEAD).Trim()
if ($head -ne 'REVIEWED_EXACT_HEAD_SHA') {
    throw 'Source audit HEAD changed; review before running'
}
git -C $main worktree add --detach $work $head
if ($LASTEXITCODE -ne 0) { throw 'Isolated worktree failed' }
Set-Location -LiteralPath $work
py -3 -I -m unittest discover -s tests -p test_p0_calc_magnitude_upstream.py -v
if ($LASTEXITCODE -ne 0) { throw 'Synthetic source-audit tests failed' }
# No Dolphin or controller is started. Only already preserved original banks.
py -3 -I scripts/p0_calc_magnitude_upstream_private.py
if ($LASTEXITCODE -ne 0) {
    throw 'Source audit ABSTAINED; preserve data, do not run live shots'
}
~~~

If the unique archive cannot be autodiscovered, the script returns `ABSTAIN`; do not replace with a random unverified ROM or downloaded snapshot. An optional explicit `--archive` argument exists for a single already-verified local cohort, and it never asks for a game image. Report only the sanitized JSON, not raw banks.

## Decision after source report

1. Decode precise arithmetic/branch guards that produce `f30` before `+0x08` and `f1` before conditional `+0x0C`, including the candidate r24 `+0x18/+0x1C/+0x28/+0x2C` stores.
2. Trace CALL instruction destinations and receiver provenance, if any, that supply those intermediate values; source-select the actual Wii Remote input sampling function rather than projecting Felk movement parameters.
3. Verify whether `+0x0C` is peak-acceleration, animation, directional magnitude or a related candidate before equating with accepted power. Inspect A/state and redline separately.
4. Only then integrate #415 downstream nonlinear magnitude transfer and selected-ball launch writer, with independent real shot/guest frame evidence. `training_approved=false`.

Coordination claim: [issue #418](https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6788479516). Owns only the four new files listed there; no existing shared modules are changed.
