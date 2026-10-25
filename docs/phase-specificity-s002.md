# S002/S003 — Phase-specific RAM differential (read-only)

**Status:** research-only stacked change on S002 [PR #116](https://github.com/Nate27624/Wii-AI-Golf/pull/116), [Issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). Not a proven golfer/power decoder. No new Dolphin controller inputs or automatic swing.

## Change and exact contract

The existing source-gated S002 `summarize_phase_memory` now keeps:
- `top_changed_relative_words[].phase_change_counts`: counts for changed BE-u32 words **ONLY between adjacent snapshots in the same human-labeled stage**, keyed by destination phase;
- `top_changed_relative_words[].boundary_changes_into_phase`: distinctly labeled changes observed between different stages, where humans may have paused or controlled the scene; **NOT motion response**;
- `top_changed_relative_words[].phase_observation_opportunities`: valid adjacent same-instance comparisons by phase, **even when the word did not change**; a zero without observations is not evidence of stability;
- `within_phase_comparisons_by_region`: denominators for all source-gated windows, including no-change cases;
- `phase_frame_brackets`: per-snapshot `stage,phase,frame_start,frame_end` as actually bracketed by RPC; **not impact timestamps**;
- `phase_change_count_semantics=within_stage_only_boundary_counts_separate`.

Prior S002 summary keys remain. No addresses, bytes, before/after word values or private paths are output. All `confirmed_*_address` flags remain false. This is additive to the **S002-owned** summary contract and requires S002/S000 review before production/public GitHub publishing. This branch is based on S002 PR #116; it cannot merge into main until #116 has been reviewed and integrated.

## Operator control result: completed October 25, 2026

**Do not repeat this study just to collect more of the same fields.** One completed operator run, `20261025T031559Z-3dfd5bf2`, contained 24 source-gated snapshots (8 idle, 8 aim-only with human label `camera_moved`, 8 idle) at the tee. From the sanitized summary and a private offline check of the provided local raw data:

- `changed_word_count=0` across all three required windows; no full-window byte changes between any of the 24 snapshots.
- Each window was nonempty, remained in one instance and produced the same byte sequence in every capture. No relocation was skipped.
- Focused windows: golf_config 160 bytes, golf_field 168 bytes, sports_sequence 208 bytes.
- Within-stage same-instance comparison opportunities **per region**: 14 idle (across two idle blocks) and 7 aim-only; each snapshot's frame bracket spanned **9 emulator frames**.
- Source-verification and operator phase labels are not proof that camera coordinates, club pose, actual power or ball physics were captured. The config window ends at +0x9F and DOES NOT include the earlier source-undecoded +0xBC/+0xC0 broad-window changes.

**Interpretation:** credible negative control for these *specific* source-documented window bytes, not a detection failure of the entire game. With 9-frame read spans and no observed change, a next run using exactly these windows is low-information. This study remains private locally; GitHub coordination comments contain these sanitized counts only, never the RAW-PRIVATE JSONL.

**Next owner action:** S002 source-identifies the live scene instance and RPGolMain/golfer ownership (see PR #122); S001/S002 agree frame-synchronized, source-gated tiny gameplay reads inside the existing consented canonical swing path. S003 cannot train a numeric power model until there is independently varied, verified in-game power and negative-control specificity. **No additional operator live study is justified by this result until that instrumentation exists.**

---

## First operator study: three-stage idle → aim-only → idle

This is a **safe negative-control** and latency study, not power calibration.

**Preflight** — run in a separate detached worktree; do not replace/merge main and do not start Dolphin for offline tests.

```powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Memory-Phase-Test"
git -C $repo fetch origin pull/128/head
if ($LASTEXITCODE -ne 0) { throw "Cannot fetch review branch" }
if (Test-Path $work) { throw "Separate worktree already exists; do not overwrite" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Could not create worktree" }
Set-Location $work
py -m unittest discover -s tests -p "test_memory_phase_specificity.py" -v
if ($LASTEXITCODE -ne 0) { throw "Phase specificity tests failed" }
py -m unittest discover -s tests -p "test_golf_memory_phase_capture.py" -v
if ($LASTEXITCODE -ne 0) { throw "S002 phase collector tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed: do not run live control" }
```

**Live read-only control** — only after tests pass and a *single* canonical S001 Dolphin session is at the Hitting the Green tee.

```powershell
# In a separate PowerShell, from the CLEAN canonical main checkout,
# with Dolphin closed. This performs ONE approved canonical startup.
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/launch_golf.py --slot 2
# Confirm game is waiting at Hitting the Green tee. KEEP Dolphin open.
```

```powershell
# In the detached study worktree (not the launch shell), once tee is ready:
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Memory-Phase-Test"
py scripts/capture_golf_memory_phases.py --attach-running --scope focused `
  --phase idle:8 --phase aim_only:8 --phase idle:8 `
  --interval 0.75 --max-frame-span 30 --no-upload
```

Phase prompts: hands off / move WASD aim only (NO swing, NO A) / hands off. This collector attaches **only**; it never launches or sends controller motion. Observe/annotate prompts. A returned RPC ACK is not ball contact. It saves raw rows privately in the sibling `Wii-AI-Golf-Data/captures` and a **local sanitized** JSON summary. Do NOT send raw RAM or private local file to GitHub/chat. Note that `--max-frame-span 30` is a performance rejection threshold for this control, **not** permission to infer sub-frame or impact timing: power-event evidence eventually needs far narrower non-atomic spans and S001 event anchors.

## Success, failure, next step

Review summary for `phase_frame_brackets`, `within_phase_comparisons_by_region` and per-word `phase_change_counts`. In the controls, likely aim/camera effects must be demoted even when recurrent. Mark *missing or zero opportunities* as unknown, not stationary. Stop if mode/revision/pointer gates fail, Dolphin closes, memory read spans exceed threshold, frame counter rolls backward, or phase annotations are not reliable.

The next **separate** S001/S002-owned live study will require safe validated `RPGolScene.mGolMain`/player state, reciprocal shot IDs, bridge-observed A and trace-start/end frame anchors, and nonperturbing tiny read-only in-swing samples. These are NOT implemented by this change. Never regress off-green 100-ft penalty or human `~75%` meter estimates as true carry or measured in-memory power.

### Ownership / privacy / validation limits

S002 owns RAM capture and summary schema; S001 owns startup/controller/timing; S003 owns modeling/signal screening; S000 owns publication allowlist. This is a proposal to S002, not a new canonical launcher or memory scanner. No ROMs, savestates, runtime pointers, private RAM, paths or credentials committed. Validation: offline focused + full host suite required before live study or merge.
