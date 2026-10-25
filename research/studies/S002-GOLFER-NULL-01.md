# S002-GOLFER-NULL-01 — does `main+0x74` change without a swing?

**Status:** preregistered, offline analysis implementation proposed; no new Dolphin trial, and actual operator raw capture has not been read in this repo branch. Source of the existing data: S002 PR #129's `capture_golfer_memory.py` private JSONL from human-approved Hitting the Green RSPE01 Rev1 read-only capture. Do not upload/reproduce those files.

## Motivation and hypothesis

S002 live operator report in PR #129: 20 snapshots (12 idle and 8 `aim_only`), maximum snapshot non-atomic span 2 emulated frames. The candidate main object word `+0x74` changed in 19/19 adjacent comparisons (17 *within phase* and two *between phase*). This sounds like a per-frame counter/animation value, not a uniquely swing-driven power measurement; it has **not** been identified or decoded. The 19 pairs share one emulated session and are NOT 19 independent swing trials.

- **Null/control question:** Does the candidate 32-bit `main+0x74` change between repeated samples while the user reports complete stationary idle, with no swing RPC?
- **Falsification rule:** Any confirmed change inside a repeated `idle` stage refutes the claim that this word *changes exclusively upon a swing event*. It **does not prove** that no power-related information can ever coexist in the same word, that the word represents a clock, or that the game accepted/not accepted A.
- **Secondary observation:** Does the unsigned modular word increment equal, or remain bounded by, the actual emulated start-frame gap on adjacent **same-stage** snapshots? This is suggestive of time dependence, not definitive counter identification.
- **Controls:** `idle (stage 0)` → `aim_only` (operator label, may reflect WASD pointer movement rather than actual 3D camera) → optionally `idle (stage 2)`. Do not infer that a stage prompt reliably changed controller/game state. Exclude both stage boundaries from specificity inference.
- **Evidence provenance:** Private local S002 JSONL includes source-gated candidate main bytes, emulation frame brackets, stable scene/main runtime identities and human labels. The offline audit rechecks consistency but **cannot independently re-verify RSPE01 revision/mode or class identity from stored rows**.

## Procedure and privacy

On the operator's Windows machine, from an isolated review checkout of this PR, run offline synthetic tests then:

```powershell
py -m unittest discover -s tests -p "test_outcome_golfer_null_controls.py" -v
py -m unittest discover -s tests -v
py scripts/audit_golfer_null_controls.py --latest
```

The command selects the newest canonical `golfer-*-RAW-PRIVATE.jsonl` from `<checkout-parent>/Wii-AI-Golf-Data/captures`. It reads locally, uses no RPC, launches no Dolphin, makes no filesystem writes, and returns **only** aggregated stage counts/rates and the relative `main+0x74` offset. It will never print private capture file names, paths, heap pointer values, raw bytes, or individual word values. No GitHub publication is initiated; operator may paste only sanitized JSON.

Inputs fail closed if outside sibling private `captures`, symlink, wrong canonical basename, >4MiB, >60 rows, missing scene/main identity, frame reversal, within-snapshot frame span >12, wrong stage order/label, malformed `0x100`-byte main snapshot. The code ignores private first-level child windows, does not dereference them, and reports no verified score/power/pose.

## Outcome categories / stop rule

1. `changes_during_idle_refutes_exclusive_swing_event_indicator`: **stop treating +0x74 as a swing-only sensor**; hand to S003 to classify as a nuisance/animation-clock candidate unless new independent evidence contradicts it.
2. `changes_only_during_pointer_control_not_verified_power`: camera/pointer confounding candidate; no calibration claim. Consider separate S001-approved A-only stationary negative control once owner-reviewed and no extra live shot until necessary.
3. `no_observed_control_change_inconclusive`: insufficient negative control, not positive power evidence.

Once data returned, compare counts per *stage*, not independent trials, and investigate whether exact frame-step agreement occurs. If existing raw files are missing/incompatible, **do not auto-trigger live Dolphin**. S002 PR #129 must be tested/reviewed/merged into canonical CLI before proposing a newly captured equivalent read-only study.

## Coordination

- Upstream S002 PR #129 owns *live* read-only candidate golfer capture and raw-file schema.
- S002 PR #122 provides independently verified static singleton slot `0x804BF4D8`.
- S000/S002 PR #130/#132 gate scene/vtable/sport; confirm consistent source IDs.
- S003 PR #125 may consume this sanitized verdict after its schema contract mismatch with #129 is resolved, but must not treat this offline output as a same-shot positive swing.
- S001 PR #112 and S003 PR #123 would be required for exact live bridge/frame-joined action specificity later.
- S000 PR #126 controls automatic public result schemas. This study **does not call that publisher**, preserving raw privacy and avoiding schema bypass.

No power identification or independent shots are claimed.
