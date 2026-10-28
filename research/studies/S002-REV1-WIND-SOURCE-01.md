# S002-REV1-WIND-SOURCE-01 — offline GetWind table shape audit

**Status:** source-backed, private-offline analysis implementation; real
operator/native bank result and full Windows suite PENDING. Stacked on
S002 canonical paired-bank source root #151; no parallel game launcher,
memory publisher, model feature or training implementation.

## Research question

Rev1 `RPGolConfig::GetWind(int *dirOut,int *spdOut)`, at
`0x8029CE74..0x8029CEA4`, source-decoded from operator-private US
Rev1 `main.dol`, indexes two MEM1 32-bit-word BSS tables by raw
`RPGolConfig.mCurrentHole+0x98`:

| Internal BSS | Code-intended return | Notes |
| --- | --- | --- |
| `0x804A8B54+4*i` | direction output raw integer | 9 words |
| `0x804A8B78+4*i` | speed output raw integer | 9 words |

`RPGolConfig.cpp .bss` has public Rev1 range
`0x804A8B48..0x804A8BA0` in
`doldecomp/ogws/config/RSPE01_01/splits.txt`.
Both nine-entry regions lie inside that BSS and are **live runtime state**,
not initialized data recoverable directly from the DOL.

The header
`kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolConfig.h`
independently documents the signature and current-hole member.
The input raw hole index 1 in previous local snapshots is NOT
independently verified to mean UI Hole 1. **No angles, units, MPH,
real wind speed or correspondence to GUI wind indicator are known.**

## Implementation, exact scope

- `src/wii_ai_golf/audit/golf_wind_table.py` imports/reuses
  #151's `audit_pair` and `_Banks` and **requires** US Rev1
  header, mode4, Golf scene ID/backlink/sport, valid selected field,
  *both* 24MiB MEM1 and 64MiB MEM2, then validates
  `0 <= raw_hole_index < 9` without clamping/modulo.
- It reads only the two **fixed source-identified** MEM1 BSS arrays
  (18 total big-endian u32 values), never scans entire RAM, and emits
  **shape-only** count/boolean metadata (distinct words, nonzero entries,
  active entry nonzero, array-constant flags). It does NOT expose raw
  entries, runtime pointers, private paths, memory bytes or private
  float/int arrays.
- `scripts/audit_golf_wind_table_private.py` checks that both source
  banks are exact size and live under a user-provided ignored
  `Wii-AI-Golf-Data` private root; memory is read-only `mmap`.
  No output file, Dolphin, RPC, controller, Git publication, network.
  CLI failure only prints a fixed redacted category.
- `tests/test_golf_wind_table.py` has eight **synthetic** source-bank
  tests: correct nine-word indexing, selected index, invalid index,
  wrong revision/mode, scene identity mismatch, all-zero permissible
  case, public JSON no numerical/wind-unit claims, and CLI error redaction.
- **No full source-chain acceptance for true wind semantics** follows
  from plausible nonzero values. Table data in MEM1 and config
  raw current hole in MEM2 were dumped around 111 seconds apart.
  This pair is not same-boot or frame-atomic verified; shape and
  code-target mapping alone cannot establish the wind shown in the UI.

## Owner-safe reproduction (no game activity)

Only after S002/S000 review, focused CI and full native Windows tests:

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$branch = "agent/research/source-wind-table-20261027"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Wind-Offline"
$private = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"

if (Test-Path $work) { throw "Preserve existing wind worktree" }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree create failed" }
Set-Location $work

py -m unittest discover -s tests -p "test_golf_wind_table.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused test failure" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failure" }

# These paths are deliberately illustrative. Use verified, privately
# preserved banks, not Dolphin's overwritable active Dump directory.
$mem1 = Join-Path $private "mem1.raw"
$mem2 = Join-Path $private "mem2.raw"
if (-not (Test-Path $mem1) -or -not (Test-Path $mem2)) {
    throw "Exact preexisting preserved bank paths unavailable; no export"
}
py scripts/audit_golf_wind_table_private.py --private-root $private `
    --mem1 $mem1 --mem2 $mem2
if ($LASTEXITCODE -ne 0) { throw "Wind source audit failed" }
```

If filenames differ, use the existing privately staged equivalents
and never infer same-time correspondence from file naming or
modification times. **Share only sanitized stdout JSON**, and only
after owner review; raw banks and any local raw wind table values
must remain private. No need to take another game shot/dump.

## Advancement and stop rule

1. Source shape read passes: promote to
   `rev1_wind_table_source_bss_present`, NOT
   `game_wind_direction_or_speed_verified`.
2. A table with nine equal/zero entries is still source-valid, but
   cannot demonstrate varying wind; treat as inconclusive.
3. If raw hole index is out of range or scene/mode validation fails,
   stop. Do NOT coerce `i % 9`, mix captures, or guess another table.
4. For physical wind units/direction proof, source trace writer
   `RPGolConfig::CreateWind` and correlate multiple game-displayed
   wind configurations with *frame-aligned* native values, preserving
   the actual input identity, and test whether those values are
   stable under stationary controls.
5. S000 evidence ledger #154 must keep
   `windspeed_units_verified=false`,
   `wind_direction_convention_verified=false`,
   `visual_wind_correspondence_verified=false`,
   `approved_for_model_training=false`.

Related research: S002 PR #150 environment UI flags, S002 #159
pin/start direct translation, #160 selected player/ball source path,
and documentation-only #162 complete source links.


## 2026-10-27 REAL OPERATOR-REPORTED RESULT — all wind entries zero

Operator ran the exact `scripts/audit_golf_wind_table_private.py`
against an already-preserved private source-gated RSPE01 Rev1 / Golf
scene 5 / Hitting the Green **mode 4** MEM1+MEM2 pair. The sanitized
report established:

- Direction nine-entry table: `distinct_raw_word_count=1`,
  `nonzero_word_count=0`, `raw_all_entries_equal=true`,
  currently indexed raw value is zero.
- Speed nine-entry table: `distinct_raw_word_count=1`,
  `nonzero_word_count=0`, `raw_all_entries_equal=true`,
  currently indexed raw value is zero.
- `raw_hole_table_index_in_bounds=true`, source mode/revision and
  scene-chain gates passed, `game_getwind_code_execution_observed=false`,
  `same_boot_pair_verified=false`,
  `same_emulated_frame_pair_verified=false`.
- `runtime_gameplay_wind_verified=false`,
  `windspeed_units_verified=false`,
  `wind_direction_convention_verified=false`,
  `approved_for_model_training=false`.

**Interpretation matters:** The nine table values are ZERO, but that
does not falsify the **source-code lookup** by itself. An important
external/gameplay negative control is that independent original
Wii Sports guides explicitly describe **Hitting the Green as having
no wind on any hole**. This coheres with all nine runtime raw
direction/speed entries zero in one captured mode-4 state:

- GameFAQs, Crazyreyn Wii Sports Strategy Guide (2007):
  https://gamefaqs.gamespot.com/wii/933010-wii-sports/faqs/46417
  (Hitting the Green has no wind).
- Guías Nintendo original Wii Sports Golf training:
  https://www.guiasnintendo.com/2a_WII/wii_sports/wii_sports_sp/ent_golf_golpes.html
  (No wind in this training activity).
- GameFAQs / CheatCodes original Wii Sports walkthrough:
  https://www.cheatcodes.com/guide/faq-and-walkthrough-wii-sports-wii-97232/
  (Hitting the Green no wind; unlike Target Practice).
- Nintendo's original 2008 official Target Practice article:
  https://www.nintendo.com/en-gb/News/2008/On-target-with-Wii-Sports-golf-250745.html
  (Wind increases during Target Practice).

**Conclusion for the user's CURRENT mode-4 Hitting-the-Green
training target:** prioritize NO-WIND as an **externally corroborated
game-rule hypothesis** and fixed environmental condition. Zero
BSS entries in ONE paired non-atomic snapshot are *consistent with*
that rule, but not direct code proof of physics forcing zero wind,
nor a positive control for `GetWind` against a nonzero mode.
There is **no benefit in more wind-only mode-4 still captures**.
For code/units validation on the larger general golf research
branch, a source-side read of `CreateWindForGamemode` and its
config mode decision is preferable to introducing a new Dolphin
Target Practice session. If ever testing the nonzero decoder is
explicitly needed, perform that as a separate, owner-approved
phase/mode/boot-synchronized study; do not mix it with training
or disturb the current user automation.

This result is **research-complete for the bounded mode-4 B0
table-shape question**, but **not a physical/units decoder**.
Owner review/merge and independent gameplay state dictionary
acceptance remain pending. Existing raw dumps, actual numeric
entries and private paths were NEVER published.
