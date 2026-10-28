# P0: exact native OnCalculate → Golf main source-call census

## Original user evidence

In original 7 preserved RSPE01 Rev1 Golf mode4 captures, exact #279 commit
`367aa1e371040a65dfffd164c19ba89ea66ea2f6` with 13 synthetic tests and canonical 14-bank original SHA before and after, the two-source-word audit
at `0x8028DFA8` identified:
- `lwz r3,+0x9C(r3)` (scene member RPGolMain* candidate)
- exact non-linking `b` target `0x8028E158`.
- scene `+0x9C` member class MEM2 in **all seven** captures.
Public `kiwi515/ogws_info` RPGolScene.h labels `OnCalculate` at this address. Independent `doldecomp/ogws config/RSPE01_01/symbols.txt`, immutable Git blob `ec42efd5ef247dff7920e905f9004fc579dd3f74`, records exact `fn_8028E158` size `0x194` (101 instructions). The source function bound is corroborated; **vtable execution, simulation-step cadence, render-frame join and physics are not**.

## Novel bounded question (not another broad pointer scan)

With original seven-bank SHA and two-word source identity unchanged, scan ONLY the exact
`0x8028E158..0x8028E2EC` source code window and classify:
- source direct PPC `bl` destinations (public code PC and membership in
  known RPGolMain, RPGolMapObjBall or RPGolSimulateManager code units)
- static conditional branches `bc`, nonlinking direct `b`
- PPC indirect link/branch forms `bclrl`, `bcctrl` that prevent a no-simulator-call conclusion

Report source direct-BL count into published SimulateManager code region as a
**syntactic target count only**; `0` does NOT rule out indirect simulator
calls; `1` does NOT prove exactly one game physics update per OnCalculate
because branches and dynamic call eligibility remain unproven.
Source instruction windows must remain bitwise identical across all 7 captures;
`#231` original bank+manifest SHA before and after is mandatory.
No raw PPC words, private pointers, float values, RAM or ROM in report.
All guest physics clock, actor/renderer, XYZ/velocity/contact/impact/power/score,
frame attestation and model training remain FALSE.

## Pre-registered decision

1. **Positive syntax:** any direct BL targets published SimulateManager source unit →
   owner #279/#272 should assess whether that particular callee genuinely advances
   gameplay and is gated by branches; may require exact source CFG and game-step frequency.
2. **Negative syntax:** no such BL but indirect link/branch → ABSTAIN about actual update;
   do not start scanning arbitrary helper call chains.
3. **Stop:** no defensible game-simulation-step identity from this single 101-word
   source function → #215/#272 should focus on verifying installed Felk build/event
   API and smallest safe no-input, no-hook feasibility; no new source micro-PRs or shots.

## Ownership

Draft child stacked on #279; S001 #215/#166 owns runtime timing and any emulator
interaction, S002 #240/#219 owns global/selected ball provenance, S000 #205 privacy,
#248 owns dual-object sample acceptance. Do NOT merge child independently, alter
Dolphin, register breakpoints, pause/resume the coroutine, send gameplay input,
capture new shots or approve training/publishing. A frameadvance/bridge tick is
NOT an authenticated game physics step. One native source-only run after Win+Ubuntu CI
and exact immutable PR pin is sufficient.


## Independent original prefix witness and mandatory crosswalk (2026-10-28)

S002 agent's separate source-gated REAL original seven-bank archive #279 commit `26e821973da8a2d6e5768d4527febcfe24ff2356` (15 synthetic PASS; 14 SHA-preserved banks before/after; 7 scene chains) scanned ONLY first `0x100` bytes of exact public `fn_8028E158`. The original report established **10 direct BL source instructions**, **2** with targets in the published SimulateManager unit, at **FUNCTION relative** `+0x007C -> 0x8029B554` and `+0x0090 -> 0x8029B43C`, plus five conditional branches. External Rev1 ogws symbol source independently identifies both targets as function **entry points**: `fn_8029B554` size `0x28` and `fn_8029B43C` size `0x118`. This confirms call-site syntax in a limited 0x100 prefix only; it does NOT prove physics execution/cadence.

The initial #283 report field `source_main_unit_relative_pc` subtracts published unit start `0x8028E098`, not function entry `0x8028E158`, a difference of `0xC0`. A positive native report must show **both** coordinates consistently: `function+0x7C / main-unit+0x13C` and `function+0x90 / main-unit+0x150`. The new `source_main_function_relative_pc` field and `require_prior_prefix_match` enforce count 10, exact two entrypoint targets at those two function-relative sites, and unit-vs-function `0xC0` offset arithmetic, before the full 101-word source report may pass. A discrepancy is **ABSTAIN**, not a new simulation function claim. Further semantics and call frequency remain unknown despite exactly two syntactic direct calls.
