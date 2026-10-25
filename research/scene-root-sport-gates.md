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
