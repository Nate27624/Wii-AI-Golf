# S002 offline: differentiate idle counter drift from aim-responsive golfer candidate RAM

**Purpose:** Review *already recorded* private rows from S002 PR #129 (read-only 0x100-byte candidate main object and up to sixteen 0x80-byte first-level child objects). No Dolphin, second boot, controller input, new shot, network, RAM write, or raw publication.

## Relevant observations and hypothesis

Operator candidate-main capture `golfer-20261025T031834Z-85d5b836` (S002 GitHub PR #129 comments) contained 20 bounded samples and exactly one changing main +0x74 word, changing across 19 of 19 adjacent reads, zero plausible float-like transitions. Source-anchored scene-root trial `20261025T032225Z-720fcc31` independently found one stable static slot 0 with a RAM-shaped +0x9C child. Neither identifies swing power.

Hypothesis: a continuously changing +0x74 word is a background timer/state candidate, whereas aim-specific changes (if any) in source-constrained child windows deserve later controlled motion studies. Test **within each phase**, excluding operator-timed phase transitions. A source-constrained pointer-shaped child is NOT automatically a verified golfer/club object.

## One offline operator validation study

From the current primary checkout, use a **new isolated worktree**, and STOP if local tree already exists or focused/full tests fail.

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Golfer-Control-Audit"
$private = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"
if (Test-Path $work) { throw "Worktree exists; preserve it" }
git -C $repo fetch origin pull/NNN/head
if ($LASTEXITCODE -ne 0) { throw "Could not fetch auditor PR" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_golfer_phase_specificity.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused study audit failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full offline suite failed; stop" }
$raw = Get-ChildItem $private -Filter "golfer-*-RAW-PRIVATE.jsonl" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $raw) { throw "No S002 golfer RAW-PRIVATE locally" }
py scripts/audit_golfer_phase_specificity.py --input "$($raw.FullName)"
```

Replace NNN with the PR number. The audit reads the local private file, produces a NEW sanitized summary in the sibling Data/captures folder, and attempts the canonical GitHub publisher. A missing/not-yet-approved typed validator means it **fails closed**, preserving the sanitized local report; do not upload raw files, copy the validator from another worktree or bypass its check. The new output kind **requires S000 PR #126 follow-on allowlist review** before auto-publication can succeed.

## Algorithm and interpretation

- S002 sample shape: exactly 256 bytes of candidate main plus 0..16 first-level children, each 128 bytes; all regions remain in the same validated scene/main/child object instance across samples.
- Stage order: idle (>=2) -> aim_only (>=2) -> optional idle (>=2). Each row must carry increasing emulated-frame brackets and valid distinct stage labels.
- Compare only *adjacent snapshots in the same stage*. Stage boundary differences can be scene, delay or mode changes and are **excluded** from scoring.
- Per (region, relative aligned offset), report idle and aim within-stage change counts **and denominators**, sorting aim-enriched control candidates ahead of background-changing counters. Cap public ranked rows to 100 with an explicit truncation flag.
- Falsification criterion: a word changing in most idle and aim comparisons, such as previously observed +0x74, is `background_dynamic`, **not a power measurement**. Two or more same-stage aim transitions with at least +0.25 normalized increase over idle can be tagged `aim_enriched_control_candidate`, but still needs independent replication and source ownership before any club/power interpretation.
- Temporal advisory: >12 emulated frames per sample is too slow for fine-grained swing claims; no sample here is explicitly time-aligned with a hit.
- The emitted fields `power_verified=false` and `club_pose_verified=false` cannot be promoted without a NEW separately approved same-shot experiment.

**Next gate:** S002 and S001 need a bounded, validated golfer-related window and frame-timed a_hold/back/forward samples from the SAME stroke, while proving sampling overhead does not break the successful 45-frame A lead. S003 may then join truly distinct human-observed power bins; 100.0ft off-green stays a penalty.
