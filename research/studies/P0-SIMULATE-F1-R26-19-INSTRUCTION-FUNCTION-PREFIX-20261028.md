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


## REAL operator original-B0 result — 2026-10-28 (supersedes "pending" above)

Operator ran the EXACT reviewed source SHA `a2ad1117dde5ca0506a5201e35c72b838a32d692` from an isolated pristine Windows GitHub CLI checkout. **14/14 new and 13/13 parent synthetic local tests PASS**, original B0 manifest/source RSPE01 Rev1 SHA **before/after PASS** and source report evidence checks PASS; no original bytes, runtime addresses or bank hashes uploaded.

Actual sanitized function-prefix report:

| Source result | Real observation |
| --- | --- |
| Published function entry source-relative | `+0x0033C` |
| Exact distance BL offset from function entry | `76` bytes (`+0x4C`) |
| Source prefix words | `19` |
| Recognized source transfers before BL | `2` |
| Direct BLs before distance BL | `1` |
| Recognized syntactic `r26` writes | `1` |
| Nearest recognized `r26` producer | **`addi_or_addis_from_r1`** |
| Source unit relative write site | **`+0x0035C`** |
| Recognized controls after last `r26` write | **`1`** |
| Float result store at `+0x0038C` | **`stfs f1,0(r26)`**, as qualified in earlier real #269 |

**Interpretation / STOP:** r26's candidate value is **derived from PowerPC r1 stack pointer** in this function's prefix, making the `stfs f1,0(r26)` a strong **stack-derived temporary/output slot candidate**, rather than a source-typed persistent ball/result field. This corrects an overly optimistic reading of the earlier `NONSTACK_GPR_BASE_UNTYPED` classification: direct instruction RA not r1 does NOT rule out a stack-backed destination. The reported classifier does not distinguish `addi` from `addis`, and there is a control-transfer hazard after the candidate write; **not a proven stack-local/runtime store**. With no verified ball/pin vector owners, runtime FPR1 reaching definition, rendered guest frame or UI output, **deprioritize this specific call+stfs chain and do not launch another general source scan or repeat preserved memory**. The other 17 square-distance callsites had unresolved FPR arithmetic/move; this finding does NOT rule them out, nor does it identify a general shot distance variable.

Next beneficial work must switch to independent higher-information lanes: source-typed actual rendered-ball/cache receiver and direct gameplay mode 4 result/UI presentation with same-guest-frame evidence. #240/#219/#254 and #256 already own those. No auto-merge, new capture, score table re-run or training/publish approval. `allowed_to_publish=false`, `training_approved=false`.
