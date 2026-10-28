# P0 cache receiver: conservative static PowerPC must-definition proof (S002 support)

**Draft source-only helper; never an executed-game receiver claim.** This is not the owner #240's four-roster source-global identity experiment, r13 source-xref study, or PR #219 broad callgraph.

## Existing source result and central narrow question

Real original snapshots (source owners #240, #230, #231) show the r13-based global MapObjBall is NOT any of four player-roster balls (7/7) and global position matches selected ball cache +CC in numbered W5/W6/W7. Exact static Rev1 code in #183 uses caller r3 saved to callee r27 and writes a triplet copied from source-global into receiver+CC. #240's two callsite windows have linear `mr r31,r3` prologue and `mr r3,r31` near target BL, but known branch hazards. The question addressed HERE is **whether every statically reachable caller path into each exact cache-writer BL must carry the function's incoming r3 through r31 back into callsite r3**.

## Source boundary inconsistency found (current highest-value output)

At both original #240 native-run code revisions and its later code, the first `CALLS` tuple is `(call_pc=0x80299B64, claimed_entry=0x80299ACC)`. Since `entry > call_pc`, the backward source window is EMPTY; a source-visible caller entry at 0x80299ACC cannot contain the earlier cache-writer call. As a result, #240's claim of *two* resolved `mr r31,entry_r3` chains contradicts these exact input ranges; #240's `trace_r31_inputs` even checks entry < pc and should ABSTAIN. This is a source-pinning/identity problem, not a physics finding. It was reported to owners on #240 and #219; the helper explicitly marks the first caller UNCERTIFIED and refuses it until the true containing Rev1 function boundary is established independently. Do NOT fill an invented entry or equate `fn_80299ACC` with the earlier callsite. The second `fn_80299C20` entry 0x80299C20 precedes its source call at 0x80299C58, but still needs real CFG examination.

## Independent bounded implementation

`scripts/review_p0_cache_receiver_cfg_mustdef.py` is a PURE library receiving `read_u32(pc)` for **independently authenticated original Rev1 PPC**. It contains public source function entry/call bounds:
- unverified claimed first entry 0x80299ACC, BL at 0x80299B64 (**invalid ordering; ABSTAIN**)
- fn_80299C20 entry 0x80299C20, BL at 0x80299C58
- callee fn_80299C70

It builds a worklist of direct b and conservative two-edge bc (overapproximating both branches) over the complete entry..callsite interval. Exact bl to cache writer is required. A real `blr` terminates an exit path. It tracks only whether r3 and r31 retain the original entry-r3 through canonical `or/mr`; loads, arithmetic destinations, base-update stores, lmw and r31 clobbers remove the proof. Unknown opcode classes, other calls/indirect branch, out-of-bounds branch destinations, missing original source, and exceeding bounded proof capacity result in **ABSTAIN**. If ANY path reaches the cache BL without definite entry-r3 in both r3 and r31, result is `NOT_PROVEN_FOR_ALL_REACHING_PATHS`, not a counterproof that runtime receivers differ. If all decoded paths meet the must property, label `STATIC_ENTRY_R3_MUST_FLOW`, **not runtime proof**.

This helper intentionally does not itself read native code, ROM, saved RAM or the network: the S002 #240/#219 owners must perform SHA/Rev1 source gate and only then supply their own private `read_u32`. It NEVER prints native instructions, memory words, code addresses, runtime pointers, private filenames or offsets. Output only categorical proof states, no physics or training claims. There is NO --dump-directory/--live mode.

## Limits / next owner responsibilities

- Valid only for explicitly supported PPC instructions. Unknown effects could write r31 or r3, so **fail closed** instead of guessing. PPC dynamic branch, call-return, exceptional paths and the runtime class of entry-r3 are **not resolved**.
- A static must-flow proof **would not** establish that the BL ran during W5/W6, that r3 is the selected player-linked ball, or that global object is simulation/preview/rendered. For actual receiver identity, trace each upstream `fn_8029B43C → fn_80299ACC` and `fn_8029A204 → fn_80299C20` incoming r3 to object construction/vtable, then await separately approved same-guest-frame visual association.
- Source original SHA and 14-bank controls remain owned by #231/#246/#247/#249. Human phase labels are provisional and potentially wrong; do not infer motion direction, flight stage or endpoint semantics.
- Nothing in this PR modifies source owner scripts, gameplay, Dolphin, controller, bridge, registry, S001 watcher, publication or training.

22 synthetic adversarial tests plus Windows/Ubuntu CI validate conservative branch paths, r31/r3 overwrites, indirect/jump hazards, source bounds, zero code, privacy and false validation flags. **Real original PPC result not yet calculated.** Owners should review before any integration or native run.
