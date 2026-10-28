# P0 — one function-bounded r26 source origin before SimulateManager distance return store

## Operator's real original B0 result (immutable PR #269)

Operator ran exact reviewed #269 `5abab86e2d12d65637969ce5cdff03e3551e322f` on their existing private original B0 (RSPE01 Rev1), passed 13/13 local native-free regressions and original manifest SHA before/after. The **only** direct immediate `stfs f1` among 18 source-gated `PSVECSquareDistance` calls was **RPGolSimulateManager.cpp+0x0038C**, exactly one instruction after square-distance BL at **+0x00388**. The store is source PPC `stfs f1,0(r26)`. Its base is NOT the conventional r1 stack pointer; `r26` is an untyped source register. The previous 0x80-byte prior suffix has an intervening control transfer and no recognized local r26 definition. Neither the source output nor this study proves ball-to-pin distance, a physical distance value, an executed store, or a persistent game object field.

## Stronger public source boundary

Independently the published `doldecomp/ogws` RSPE01_01 [symbols.txt](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/symbols.txt) lists **`fn_8029B57C` at US Rev1 PC `0x8029B57C`, size `0x274`**, inside published `RPGolSimulateManager.cpp`. The single exact BL at `0x8029B5C8` lies at **+0x4C bytes from this function entry**, not in an arbitrary backward 0x80-byte scan. Its following store is at +0x50. This source function boundary may allow us to discriminate whether `r26` receives an incoming argument, member pointer, stack-derived pointer, or remains unknown.

## New exact hypothesis test

`scripts/audit_p0_simulate_f1_r26_function_source_private.py` ONLY reads the first **19 PPC words** from published `fn_8029B57C` entry up to exact distance BL and verifies exact `stfs f1,0(r26)` via #269's reviewed previous source function. It classifies all bounded **recognized syntactic writes** to r26 with public source-relative site labels, nearest write class (e.g. `mr_from_rX`, `integer_load_from_rX_offset_+N`), counts earlier direct calls and control transfers, and records barriers after the last recognized write. It does not claim an all-path CFG, live `r26` object class, call retention, unit distance or guest-frame execution. It purposefully keeps `callee_preservation_or_all_path_r26_flow_verified=false` even if an apparently straightforward copy is present; r26 is ABI nonvolatile but source branch and completeness remain unknown.

This analyzer uses unmodified #219 original ignored **B0 MEM1** manifest/SHA/RSPE01 Rev1/public 832-unit source map **before and after** code inspection, no memory writes, no native bank export, no private heap addresses/code words, and no Dolphin actions, shots or captures. Existing original 14-bank user-shot cohort need not be rerun. Synthetic-only tests + Windows/Ubuntu native-free workflow are additive. A successful local run should report exactly one source row, not another 18-site matrix.

## Decision gate

- If r26 has a recognizable source `mr_from_rX` or `lwz` in this exact function prefix, investigate **ONLY that source object/code offset** in the owning source/CFG lane, after confirming branch and callee preservation. No automatic pointer dereference or physical field name.
- If r26 originates outside that function / is unresolved, document ABSTAIN and stop this source-only chain until a typed caller/ABI or *same-guest-frame* visual witness exists.
- Never promote physical world XYZ, velocity, square distance to cup, displayed score, power, collision or training from this evidence alone.

Keep this PR draft, do not merge without owner review and full repository gates, and do not ask for further B0 or original seven-bank runs unless the result gives a new, discriminating yes/no question.
