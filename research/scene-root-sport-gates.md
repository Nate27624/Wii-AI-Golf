# Source-backed sport/vtable hardening for the two-cell golf scene-root probe

Review stack: S000/S002 PR #130. This is NOT a new controller, launcher, RAM scanner, or memory-derived power decoder.

## Verified source facts

* kiwi515/ogws_info RPSportsBaseScene.h: mSport is at scene-relative +0x54.
* kiwi515/ogws_info RPSportsSequenceMgr.h: SPORT_GOLF is enum 2 (after baseball and tennis).
* doldecomp/ogws eggSceneManager.h: mCurrentScene +0x0C, mCurrentSceneID +0x18.
* PR #130's Rev1 source split assigns the golf class data region 0x803C7718 to 0x803C7798. A vtable address in this range is plausibility evidence, NOT type proof.

The narrower two-source-cell 0x804BF4D8 / 0x804BF4DC approach is preferable to the older speculative 4KB global-pointer census PR #129.

## New protective logic

After RSPE01 Rev1 / Hitting the Green mode4 validation and manager scene ID 5, inspect a bounded scene pointer's source-backed sport ID +0x54 and vtable +0x00. Only if sport == 2 and the vtable is aligned and in the documented class-data interval may the read-only probe inspect the controversial scene member +0x9C. It NEVER dereferences the +0x9C value. Repeat two independent passes and require equal private pointer identities. If both storage cells match, report ambiguous not unique. All confirmed singleton, class identity, gameplay field and golf power flags remain false; output only static cell indices, counts, booleans, frame span and fixed warning. No raw RAM, pointers, local file paths or game assets go to GitHub.

## Operator result: source-gated scene-root identification

Operator ran the staged read-only probe in Hitting the Green mode4:
- Run ID: `20261025T032952Z-aedfaa3d`.
- `candidate_static_cells_checked=2`, `pass_count=2`.
- `stable_slot_indices=[0]`, `unique_stable_golf_scene_chain=true`.
- `stable_golf_scene_chain_count=1`, `stable_sport_id_match_count=1`, `vtable_in_golf_scene_data_count=1`, `possible_main_pointer_ram_like_count=1`.
- Non-atomic read span **8 emulator frames**.
- Confirmed singleton *type*, `RPGolMain` type and power location remain **false**, as correctly represented in the instrument output.

This was a **live, non-writing** pointer-shape and source-check success, not golfer power detection. Since it was a pass before the newly added own-scene-ID/backlink checks, **do not retroactively treat those additional two checks as having passed**. Separately S002's PR #129 reports an *independent* 20-sample candidate object audit in which relative `+0x74` changes during *every* adjacent snapshot, including idle. That pattern is consistent with a counter-like negative-control variable; it is not identified power and no same-shot frame join exists.

### Hardening after operator probe

The `EGG::Scene` RSPE01_01 source also defines:
- current scene object's own `mSceneID` at +0x1C;
- `mSceneMgr` backlink at +0x20.

The updated probe now gates the controversial scene +0x9C **candidate read** on both fields: own ID must equal 5 and backlink must exactly equal the currently read manager pointer (plus the previous sport2/vtable tests). Incorrect own ID/backlink abort candidate promotion; no arbitrary pointer-chasing or child object read. Added two synthetic negative-case tests, making the focused suite **14 tests**. These changes remain untested in full canonical Windows checkout; neither S002 nor S000 publication approval is implied.

**Research decision:** do NOT repeat focused static idle/camera controls, ten off-green power sweeps or manual in-swing sampler phases. Use verified identity chain as input to a future S001-owned same-shot tiny RAM sampling feature with S002's consent and S003's counter demotion.

---

## Latest operator scene-root control: both added identity gates passed

On October 25, 2026 the operator ran the updated two-pass read-only probe **after merging S001's WASD/Nunchuk controller fix** on the canonical launcher. Sanitized local run ID `20261025T035138Z-897dcadb`, Hitting the Green RSPE01 Rev1 mode 4:

| Source-anchored check | Observed sanitized result |
| --- | --- |
| Two candidate manager static cells | `candidate_static_cells_checked=2` |
| Independent passes | `pass_count=2` |
| Stable unique scene-root candidate | `stable_slot_indices=[0]`, `stable_golf_scene_chain_count=1`, `unique_stable_golf_scene_chain=true` |
| Manager's current scene ID 5, scene-relative sport ID 2 | `stable_sport_id_match_count=1` |
| Class/vtable data-range plausibility | `vtable_in_golf_scene_data_count=1` |
| **Scene object's own ID equals 5** | `stable_scene_own_id_match_count=1` |
| **Scene's manager backlink matches the same manager** | `stable_manager_backlink_match_count=1` |
| Candidate scene `+0x9C` RAM pointer shape | `possible_main_pointer_ram_like_count=1` |
| Largest non-atomic probe frame span | `max_sample_frame_span=10` |

**Interpretation:** This is a **successful real-game positive structural/root control** and a successful live post-WASD canonical launch. It strengthens the earlier operator run `20261025T032952Z-aedfaa3d` which *had not yet included* the own-ID/backlink gates. No raw RAM, pointer values, executable, private file paths, or savestate data entered Git. It is NOT proof of singleton symbol/type, `RPGolMain` class, golfer pose, club motion, numeric power or carry; all three `confirmed_*` flags in the output remain `false`. Source consistency is not a same-shot physical measurement.

**Follow-up:** S002 PR #129 already has a separate read-only candidate object sampler and private control data (reported 20 samples with `main+0x74` changed in idle). Instead of duplicate idle studies, validate this prior dataset offline with S002 #138's negative-control auditor and/or #135/#137's stage-aware summary only after owner/schema review. S001/S002 should then design frame-synchronized tiny gameplay-owned reads integrated with a controlled *same-shot* waveform; S003 should reject counter-like and minimap-effect observations from power calibration. This root probe alone does not authorize arbitrary further pointer dereferences or automated swings.

---

## Static source-based next object clues (no new memory reads)

The public [doldecomp/ogws RSPE01_01 splits](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt) include bounded module/class **compilation-unit ranges**:

| Unit | Code `.text` | `.data` |
| --- | --- | --- |
| `RPGolMain.cpp` | `0x8028E098..0x8028E900` | `0x803C7798..0x803C77C0` |
| `RPGolPlayer.cpp` | `0x8029E62C..0x802A2210` | `0x803C7CC8..0x803C7DD0` |
| `RPGolPlayerManager.cpp` | `0x802A2210..0x802A3560` | `0x803C7DD0..0x803C7DE0` |

These ranges **DO NOT prove exact class vtables, object type, or field offsets**. A first object word falling within a module's class-data interval could be a structural *hint* (if the type has a vtable); a mismatch is NOT conclusive evidence against a nonpolymorphic structure. Source-backed assembly/callsites must validate a full candidate player/manager relationship before following arbitrary child pointers.

S002 #129 has reported an independent 20-sample candidate-struct inspection with `main+0x74` changing during every adjacent capture *including idle*. This weakens its specificity to physical golf power; the field is not decoded. Our successful two-pass source-root probe does NOT itself have any of those candidate object bytes, so no new code-derived gameplay measurements are claimed here.

## Safe operator commands, once owner review and full Windows tests pass

Use a separate PowerShell session. The following fetches PR #132 into a detached worktree, never overwrites main. Stop if the directory already exists:

~~~powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Scene-Root-Gated"

git -C $repo fetch origin pull/132/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
if (Test-Path $work) { throw "Study worktree exists; do not overwrite" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_scene_root_probe.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed: stop before live probe" }
~~~

After source/owner review and both checks pass, CLOSE any Dolphin instance. Then, from the CANONICAL main checkout ONLY, start the one approved S001 launcher. The slot must be registered as Hitting the Green on your machine; do not create or overwrite a savestate.

~~~powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/launch_golf.py --slot 2
if ($LASTEXITCODE -ne 0) { throw "Canonical startup failed" }
~~~

Visually confirm the Hitting the Green first tee, keep Dolphin running, and in the tested DETACHED worktree:

~~~powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Scene-Root-Gated"
py scripts/probe_golf_scene_root.py --attach-running --no-upload
if ($LASTEXITCODE -ne 0) { throw "Read-only probe failed" }
~~~

Provide only printed SANITIZED output, never raw private RAM. This probe does not swing.

## Interpretation / next owner

One stable source-like slot with sport 2, vtable plausible and +0x9C RAM-pointer-like gives a CANDIDATE only; the newer decomp calls +0x9C unk9C, not confirmed RPGolMain. Zero slots means investigate source assumption mismatch; do not widen scan. Two slots mean unresolved ambiguity, no automatic selection. No extra low-information idle/camera repeat is proposed.

S002 and S000 must acknowledge this stacked shared-contract change; S001 eventually owns nonperturbing frame-synchronous action capture. S003 must wait for independently validated, varied game power before fitting response. Full canonical Windows tests and real Dolphin behavior are not claimed by this PR.
