# S002-SPATIAL-RELATIONS-01 — same-MEM2 source-selected landmark alignment

**DRAFT, private-offline only.** Stacked on existing S002 #163/#160 Rev1 Golf scene, player selection, current-start and ball-related object source gates. Unlike broad S002 #178/#181 B0–B3 word-change atlases, this test asks whether source-labelled **pin, cup, tee, current start and selected/nonselected ball-like objects** already form a coherent positional geometry within ONE MEM2 capture. It neither conducts a RAM sweep nor modifies the game. No gameplay shot/contact or raw ROM/RAM uploaded.

## One operator-provided private snapshot: specific observed relationships

The user-provided native 24MiB MEM1 (US RSPE01 Rev1 header/source PPC) and 64MiB MEM2 were inspected in private. Source-resolved FieldManager `+0x44` (current pin), `+0x54` (cup), `+0x50` (current start), `+0x2C` (tee) all held mapped MEM2 objects with `obj+0x4C == obj+0x30` translation self-reference. These offsets are named in `kiwi515/ogws_info/RPGolFieldManager.h`; the `+0x30` translation and `+0x4C` getter are corroborated by private Rev1 `RPGolMapObjBase` PPC source.

From the actual, single MEM2 image:
- **Pin vs cup:** vector component 0 matches bitwise, component 1 differs, component 2 matches bitwise: `[true,false,true]`.
- **Selected record 0 / current start / nested ball-related object:** all 3 translation words match bitwise (selected record +0x54 and +0x60 had previously been independently source-checked by #163).
- **Nonselected ball-like record slots 1, 2, 3:** their ball-child nested translation triplets are bitwise identical *to each other*, but none equals the selected current-start triplet.
- **Tee** is a separately mapped self-pointer-bearing map object with a distinct coordinate triplet. It is not interpreted as an active ball position.

This corroborates a plausible **pin/cup common horizontal alignment** and **ball-at-start initialization** in one source-backed game-state snapshot. Yet `components 0,1,2` are NOT formally verified horizontal X, vertical Y and depth Z axes; coordinate units, world/local transform, exact game physics object, active human, motion, ball impact, and course distance remain UNKNOWN. The MEM1 and MEM2 native exports are not independently same-frame proven. All geometric vector equality comparisons themselves occur **within a single MEM2 image**, so their internal relationship does not depend on which other moment the separate MEM1 code image was exported, although source gate timing still matters.

## Implementation

`scripts/audit_golf_spatial_alignment_private.py` reuses #163's actual `analyze_one` scene/Rev1/PPC/roster/selected-record/source-start/selected ball gates and reads only these mapped MEM2 source-field child pointers and bounded 3×BE-u32 vector words. It rejects missing/null pin, cup or tee objects, nonself-referencing translation pointers, bad firstword source region on ball-related objects, NaN/Inf or huge coordinate candidates, unaligned/out-of-RAM pointers. It compares only BITWISE source candidates, rather than integer raw coordinates, Euclidean distances or inferred units. Outputs ONLY a boolean comparison mask, small equality counts and explicit `physical_xyz`, `axis_convention`, `distance_units`, `game_motion`, `training` FALSE flags.

Synthetic tests exercise source valid geometry, corrupted pin/cup/tee selfrefs and pointer values, NaN/Inf/large coordinates, one broken pin/cup component, a divergent nonselected ball, a divergent selected ball, wrong Rev1/selector, private word/path redaction and CLI error. Cross-platform CI and owner review required; no live data or Dolphin run.

## Optional safe replay (no capture required)

This tool uses the already-preserved **private** MEM1/MEM2 pair under ignored sibling `Wii-AI-Golf-Data`. From a detached worktree of this PR (replace branch if owner rebases):

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Spatial-Review"
if (Test-Path $work) { throw "Existing spatial worktree; preserve it" }
git -C $repo fetch origin pull/182/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_golf_spatial_alignment_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Synthetic source gate failed" }
$privatePair = Read-Host "Existing PRIVATE staged pair directory with mem1.raw/mem2.raw"
py scripts/audit_golf_spatial_alignment_private.py --first-dir $privatePair
if ($LASTEXITCODE -ne 0) { throw "Private source / map-object geometry gate refused" }
~~~

The two banks must already exist, and filenames must be the locally preserved `mem1.raw` and `mem2.raw` in the ignored private pair directory. Never copy game memory into a tracked checkout or paste raw path dumps. No need for more swings or any new export. If a map object is intentionally absent in a different mode/hole, **abstain**; do not fabricate its position.

## S002 / S000 next checks

- S002 #159/#162: confirm subclass constructor/vtable identities for pin and cup, and whether matched components are runtime position or visual transform; if no source proof, keep language at "translation-like component".
- S002 #181: in the broader B0–B3 private atlas, compare pin/cup exact word-change and object ownership separately from camera/aim offsets. Do not call this source test a replacement or duplicate fullbank scan.
- S000 #154: record `pin_cup_component_0_2_equal_single_MEM2` and `selected_ball_current_start_triplet_equal` as **observed source-candidate relations**, not verified physics/world axes or a training feature.
- A later approved moving-ball experiment should test whether **selected** ball-related nested translation changes while start/pin/cup stay invariant, and whether the screen shows corresponding displacement. Stationary still geometry alone cannot do this.

**No training, no new game activity, no semantic promotion from coordinate plausibility.**
