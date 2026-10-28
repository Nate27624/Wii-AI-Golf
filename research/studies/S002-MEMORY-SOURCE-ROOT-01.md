# S002-MEMORY-SOURCE-ROOT-01 — reuse existing local MEM1/MEM2

**Research-only, operator-requested.** The operator already has preserved
local `mem1.raw` (24 MiB) and `mem2.raw` (64 MiB) from their working Felk
Dolphin build, and asked whether the bytes need to be uploaded to GitHub.
The established repository `Nate27624/Wii-AI-Golf` is PUBLIC. GitHub
`research/observations` already contains sanitized data such as
`20261025T034248Z-7c597d65.json`, NOT a raw dump. **Never commit or
upload raw MEM1/MEM2** to this public repo: possible game data, runtime heap,
unreviewed user data, and project-specific privacy restrictions.

## Objective

Use just ONE already-preserved native raw RAM snapshot to establish which
*source-backed singleton roots and relative member slots* are accessible,
without another Dolphin boot, another swing, or four new memory checkpoints.

This is **not** a second B0/B1/B2/B3 comparator: S002's PR #151 remains the
canonical offline *change* analyzer, with PR #155 privacy hardening. This is
a preliminary one-snapshot source-identity check. S002 PR #150 separately
analyzes already-captured `outcome-*-RAW-PRIVATE.jsonl` environment windows.

## Implementation

`scripts/audit_golf_mem1_inventory.py` is read-only, stdlib and
`mmap.ACCESS_READ` only. Inputs are explicit local `--mem1`, optional
`--mem2`, constrained to the ignored sibling
`Wii-AI-Golf-Data` folder. Supported MEM1 lengths: exactly 24 or
32 MiB (first 24 MiB mapped at cached `0x80000000`); MEM2 exactly 64 MiB
at cached `0x90000000`. Does not write local reports or upload anything.

It checks the native RSPE01 USA Rev1 game header and Hitting the Green
mode 4, source-known static slot for RPGolConfig `0x804BF8C4`/mode
`+0x94`/current-hole candidate `+0x98`. It then validates source
RPSysSceneMgr static slot `0x804BF4D8`, manager `+0x18`
scene ID 5, `+0x0C` scene pointer, scene's `+0x1C` ID 5/
`+0x20` backlink/`+0x54` sport 2, and `+0x9C` candidate main
pointer *shape* (not typed RPGolMain).

It tests presence / Wii RAM shape / companion bank backing for
source-listed RPGolFieldManager static slot `0x804BF868` and its
map-data/pin/start/cup/wind/course object refs, plus plausible
pin/start count boundaries. **Does not dereference untyped children**.

Report: source candidate current-hole integer, boolean root/field/ref
checks, source-relative named members, all unknown gameplay decoder flags
false. NO raw words, live pointer values, heap addresses, private paths,
ROM contents, filenames, binary data or network. Explicit
`allowed_to_publish_to_github=false`: a LOCAL sanitized report may be
pasted for review but must NOT be automatically published without S000's
typed-schema authorization.

## Safe operator command (only after PR tests pass)

Use the existing *private* copies of both files, not files newly exported
or re-uploaded. In Windows PowerShell the operator can locate them locally:

```powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Single-MEM1"
$branch = "agent/research/single-mem1-source-inventory-20261027"
$private = "$root\Wii-AI-Golf-Data"

if (Test-Path $work) { throw "Worktree already exists; preserve it." }
git -C $repo fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work

py -m unittest discover -s tests -p "test_audit_golf_mem1_inventory.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused offline tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full offline suite failed" }

$mem1 = Get-ChildItem -LiteralPath $private -Filter "mem1.raw" -File -Recurse |
    Where-Object { $_.Length -eq 24MB -or $_.Length -eq 32MB } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $mem1) { throw "No preserved private MEM1 copy under Data. Stop." }

$mem2 = Get-ChildItem -LiteralPath $private -Filter "mem2.raw" -File -Recurse |
    Where-Object { $_.Length -eq 64MB } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($mem2) {
    py scripts/audit_golf_mem1_inventory.py --mem1 $mem1.FullName --mem2 $mem2.FullName
} else {
    py scripts/audit_golf_mem1_inventory.py --mem1 $mem1.FullName
}
if ($LASTEXITCODE -ne 0) { throw "Private source-root inventory failed" }
```

If the file is only in the Dolphin application's `Dump` directory, first
copy it into the private sibling Data folder using already-established
copy-and-SHA256 verification. The analyzer **intentionally refuses**
arbitrary Git worktree file paths or potentially stale app dumps.

## Interpretation

This is ONE paused/unpaused unknown-time snapshot. It cannot verify boot
independence, game score, player ownership, ball XYZ, numerical wind, shot
power, impact, camera movement or ball physics. If a source gate fails,
preserve the original dump and report only the safe fixed error string;
do not guess pointer addresses or bypass the guard. If roots validate,
S002 can target the player/club/ball source PPC writer cross-references
(PR #144) and later compare 4 checkpoints with reviewed PR #151.

The script and seven synthetic tests are authored in this PR but not
executed on the operator host yet; no raw input has been accessed from
ChatGPT or GitHub.
