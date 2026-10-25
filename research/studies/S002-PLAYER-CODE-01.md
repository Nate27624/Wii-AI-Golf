# S002-PLAYER-CODE-01 — Find defensible golfer/club member candidates before another swing

**Scope:** S000 supporting research, stacked on S002 source-discovery PR #122. Offline analysis of a lawful locally extracted Rev1 main.dol only. Never launch Dolphin, read live RAM or modify the Wii controller. Reuses S002's single established DOL section parser from scripts/audit_golf_singleton_code.py, not a competing parser.

## Why this is now the priority

S002's real 4–8–4-child RAM controls automatically published observations with 6/10/6-frame maximum snapshot spans, confirming that small read windows are feasible for coarse phases, not for precise impact timing. The first 28 plausible child windows yielded only four continuously-changing fields in the first 16; the other child windows produced no input-specific change. Independently S002's null-control audit determined main+0x074 increments equal frame gaps for 17/17 same-stage comparisons including idle. This is good **frame-counter nuisance** evidence, not a power signal. Further arbitrary idle/aim captures are not justified.

## Source-derived code regions (US Rev1 only)

From [doldecomp/ogws RSPE01_01/splits.txt](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt):

| Unit | Static text range, end exclusive | Source .sbss range |
| --- | --- | --- |
| RPGolMain.cpp | 0x8028E098..0x8028E900 | 0x804BF850..0x804BF858 |
| RPGolPlayer.cpp | 0x8029E62C..0x802A2210 | 0x804BF8C8..0x804BF8D0 |
| RPGolPlayerManager.cpp | 0x802A2210..0x802A3560 | 0x804BF8D0..0x804BF8D8 |

The text addresses are executable code, **not object pointers**. These static-storage ranges are merely source unit allocations, NOT verified singleton fields. RPGolScene +0x9C is typed RPGolMain* by one older source, but newer decomp leaves it unknown.

## Safe analyzer and falsification

The new script only reads exactly these three documented sections from a local extracted main.dol (never ISO or WBFS). Outputs:

- Load/store PPC D-form operations using r3/r30/r31 and 0..0x3FC offsets, each separated by source unit, opcode mnemonic, memory width, and occurrence count. No register is treated as a verified C++ this pointer.
- Explicit stfs/stfd floating store shortlists. These are *candidate mutable scalar sites*, not demonstrated club angle or power. True power may instead be integer/fixed-point or in another class.
- r13 signed displacement groups for source static-data access; **r13 runtime value unknown**, do not derive real addresses.
- Direct bl call counts between the three units. Does not decode indirect calls or infer class identity.
- The result never contains binary/code words, ROM excerpts, raw RAM, pointer values, private local paths, or unsupported field claims. The DOL alone does not prove RSPE01 revision 1, which stays explicitly unverified.

Fail/stop for absent/oversized source file, invalid DOL section tables, incomplete documented code units, or failing synthetic/full unit tests. No guess-scanning outside these source intervals.

## Optional Windows operator study

Only when a legally extracted LOCAL US Rev1 main.dol already exists. Never upload this file to GitHub or ChatGPT. No Dolphin, Wii input or new swing needed.

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Player-Code-Atlas"
$dol = "D:\PATH\TO\YOUR\EXTRACTED\main.dol"

if (Test-Path $work) { throw "Study worktree exists; do not overwrite" }
if (-not (Test-Path $dol)) { throw "No local extracted main.dol; do not rerun Dolphin" }

git -C $repo fetch origin pull/NNN/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_golf_player_code.py" -v
if ($LASTEXITCODE -ne 0) { throw "Atlas tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed" }
py scripts/audit_golf_player_code.py --dol $dol
~~~

This is offline local research, **not a new published observation kind**. For future automatic publication, S000 must separately add a narrowly typed allowlist and tests to the canonical Git-credential uploader. Until then no raw file or unapproved output is uploaded.

## Next same-shot bridge milestone

S002 must inspect real player-method calls and validate which base register is an actual player/club instance, then justify a tiny list of object-relative candidate fields. S001 is responsible for ADDITIVE read-only frame-thread watches on the canonical single-socket V1 swing runner, not a concurrent second RPC writer. Before requesting an instrumented shot, establish that memory reads add no harmful scheduling delay, frame labels distinguish dispatch from game-applied controls, and the 45-frame A lead/trace behavior is unchanged. S003 may begin memory-power regression only after distinct human-visible power labels align across clean-boot held-out shots with the same validated player/club member. The challenge's off-green 100ft remains a censored penalty.
