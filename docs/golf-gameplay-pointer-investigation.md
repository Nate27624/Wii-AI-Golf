# S002 / S001: source-anchored golf gameplay pointer investigation

## Source-verified facts

The public [ogws_info](https://github.com/kiwi515/ogws_info) Wii Sports
US Rev1 `RP/RPSports/RPGolScene/RPGolScene.h` contains a
`RPGolMain* mGolMain` at **offset +0x9C within an RPGolScene instance**.
That **does not establish the address of an RPGolScene instance**.
The source also documents the RPGolScene methods
`OnConfigure` (0x8028DFF0), `OnCalculate` (0x8028DFA8),
`OnReset` (0x8028DFB0), and destructor (0x8028E030).
These are executable code addresses, **not object pointers**.

`RPSportsBaseScene.h` defines inherited scene fields through +0x98.
It does not provide a reliable global address of the active scene object.
The expected RPGolMain header is not present at the checked source path.
Neither `golf_field` nor `minimap_ball_effect` is a substitute for
`RPGolScene`.

## Read-only offline symbol reconnaissance

The upstream repo includes three distinct root-level files:
[`RSPE_r1.map`](https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.map) (Ghidra map),
[`RSPE_r1.map.csv`](https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.map.csv) (CSV), and
[`RSPE_r1.dmap`](https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.dmap) (Dolphin map).
The scanner accepts either the plain map or the CSV. Use the **CSV**
file below; run these commands in the separate PR #122 worktree, not
the main checkout:

```powershell
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Scene-Test"
if (-not (Test-Path "$work\scripts\audit_golf_scene_symbols.py")) {
    throw "PR #122 worktree missing; first complete Step 1"
}
Set-Location $work
$map = Join-Path $env:TEMP "RSPE_r1.map.csv"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kiwi515/ogws_info/main/RSPE_r1.map.csv" -OutFile $map -ErrorAction Stop
if (-not (Test-Path $map) -or (Get-Item $map).Length -eq 0) {
    throw "Public symbol map download failed"
}
py scripts/audit_golf_scene_symbols.py --map $map
```

This downloads only a public symbol map and performs an offline,
read-only scan afterward; it does not connect to Dolphin. If downloading
is blocked, download the same CSV through the GitHub file page, save
it manually, and provide the actual local file path to `--map`.
Do not copy `D:\path\to\...` literally; it was only a placeholder.

The tool only counts symbol-map lines grouped by scene-related class
names and possible singleton naming conventions. It never prints memory
pointers, symbol addresses, or raw local map lines. A map entry
named `RPGolScene` is NOT evidence of a runtime instance address.

## Next evidence gate — do not skip

1. From independently reviewed Rev1 source/decompilation, establish the
   **active scene-manager pointer source**, how the active scene object
   is selected, its exact type check and lifetime.
2. Separate addresses of **code functions**, **static pointer storage**,
   **live scene object**, and **RPGolMain object**.
3. Only after the pointer source is proved: propose a bounded,
   read-only, opt-in probe gated on `RSPE01` Rev1 and training mode 4,
   null/valid RAM pointers, repeated reads, and emulated-frame span.
4. Contrast static-aim, A-only, backswing, swing, flight, and rest
   with camera-only and failed-shot negative controls; never promote
   inferred club power or XYZ from a single changed word.

Existing 24-capture audit mostly identifies scene/UI transitions and
minimap effects. No verified club power, club pose, ball XYZ or score.
No Dolphin action or pointer dereference is introduced in this PR.
