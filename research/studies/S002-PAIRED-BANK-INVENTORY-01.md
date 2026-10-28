# S000 — saved MEM1+MEM2 source-chain inventory

**State:** single-pair local offline structural pilot. No new Dolphin, emulator pause, controller action, shot, network, training or public uploader. **Not a full-bank comparator** (that is S002 PR #151 + #155); also not a third symbol/PPC atlas.

The operator has already preserved `mem1.raw` (25,165,824 bytes) and `mem2.raw` (67,108,864 bytes) in the ignored sibling `Wii-AI-Golf-Data/mem-checkpoints/unclassified-*` directory. They were exported sequentially and MUST NOT be presumed same-frame or independently boot verified.

The `scripts/audit_golf_paired_banks.py` reader uses **only** exact RSPE01 Rev1 static scene-manager, config and field-manager slots and source-backed member offsets. It validates active Golf scene 5, scene-own ID 5, manager backlink, sport 2, mode 4, raw hole range, field pin/start counts and field-object pointer residency in Wii's MEM1 and MEM2. It prints **only** structural booleans, counts and bank labels. The first 0x100 bytes of the `scene+0x9C` target are checked for pointer-shaped words; one first-word source .data range match is a *hint* and not a vtable/typed object proof. No absolute runtime pointers, values, memory bytes, full dump contents, file paths, hashes or exact per-page location indices are output.

## Run on existing PRIVATE backup (zero Dolphin)

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Paired-Bank-Audit"
$backups = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem-checkpoints"
if (Test-Path $work) { throw "Do not overwrite an existing worktree" }
git -C $repo fetch origin pull/157/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work

py -m unittest discover -s tests -p "test_audit_golf_paired_banks.py" -v
if ($LASTEXITCODE -ne 0) { throw "Pair tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed" }

$folders = @(Get-ChildItem -LiteralPath $backups -Directory -Filter "unclassified-*" |
    Where-Object {
        (Test-Path (Join-Path $_.FullName "mem1.raw")) -and
        (Test-Path (Join-Path $_.FullName "mem2.raw"))
    } | Sort-Object LastWriteTime -Descending)
if ($folders.Count -eq 0) { throw "No preserved matched pair; do not re-export" }
if ($folders.Count -ne 1) {
    throw "Multiple backup pairs found; select the correct unclassified folder manually"
}
$pair = $folders[0].FullName
py scripts/audit_golf_paired_banks.py --mem1 (Join-Path $pair "mem1.raw") --mem2 (Join-Path $pair "mem2.raw")
if ($LASTEXITCODE -ne 0) { throw "Private pair rejected; report only fixed diagnostic" }
```

**NOTE:** The PR number above is fixed once the PR exists. The audit never modifies either backup, and any unsupported game state, missing bank or inconsistent object chain is a valid fail-closed result, **not evidence that the RAM files are corrupt**. The two files may be two minutes apart, so a runtime scene can change between them. The CLI deliberately refuses locations outside the sibling private Data directory.

## What the result does and does not mean

- A passing source-chain identity is evidence that the **combined image bytes** include a self-consistent plausible current scene structure; it does **not** establish that MEM1 and MEM2 were frozen in one emulator frame.
- The source pointer labelled `scene+0x9C` is **not proven RPGolMain`*`** across independent decomps.
- Source-supported field member pointers for pin/start/cup/wind/course/map are NOT the current ball XYZ, physical wind vector, trajectory or club pose.
- Counts of pointer-shaped words are not proof of player/club object identity; a code-module .data match does not prove a class vtable.
- To recover actual physics, S002 should next nominate source-typed MEM2 structures and PPC write sites, and design controlled, paired-bank time-matched checkpoints before any S001 frame-hook or S003 training.
- No model-ready fields will be promoted in S000 [field evidence ledger](../memory/field-evidence-ledger.json) solely from this result.

**Merge gate:** S002 source review and S000 privacy review plus complete Windows targeted/full suite. The locally constructed synthetic tests are not equivalent to operator's Windows tests or real private MEM1/MEM2 validation.
