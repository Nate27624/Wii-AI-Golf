# S002-EXPANDED-OBJECT-WINDOWS-01 — existing B0-B3 game memory, richer local analysis

## Owner permission and scope

The operator explicitly approves more expansive **game-memory research** instead of aggressive minimization. Existing B0/B1/B2/B3 paired 24 MiB MEM1 + 64 MiB MEM2 snapshots are sufficient. This study DOES NOT request fresh dumps, Dolphin interaction, a new swing, or file publication. Detailed game numeric values can be inspected and shared privately with the operator/assistant for analysis; they are not silently committed into the GitHub public repository.

## Code and evidence gates

This is a new-only draft PR stacked on S002 #174 → #163 → #160. It reuses their strict RSPE01 Rev1, Golf scene5/sport2/mode4, player-manager source selector, selected record +0x88 ball object, ball translation +0x4c, current start +0x4c, bounded PPC and native bank gate. Four original B0-B3 bank files are verified against their private manifest SHA256 first.

Read windows only from these source-known and bounded game structures: scene 0xa0, RPGolMain candidate 0x80 (including previously observed +0x74 tick), config 0x9c, field 0xa8, start and optional pin 0x50, four 0xcc-stride source-roster player records, four 0x1ac SimulateManager/RPGolMapObjBall candidate objects, and two source-identified nine-word wind tables in MEM1. Never recursively follow arbitrary pointers. All other memory is left untouched.

Save a single new `golf-object-windows-PRIVATE.json` inside the existing ignored B0-B3 session folder. The JSON includes all read source-gated game object word hex values, per-phase guest object addresses, changed byte offsets on stable object identity, and candidate ball/record/start/pin f32 vectors. The values remain typed as hypotheses: decoding three BE floats does NOT demonstrate actual world axes, units, active ball, power, or motion. Object relocation prevents comparison. Terminal prints only aggregate changed-word counts and local detail path.

## Windows operator procedure (no emulator actions)

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Expanded-Memory"
$branch = 'agent/research/golf-source-object-windows-private-20261027'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path $work) { throw 'Worktree already exists, refusing to overwrite' }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Worktree add failed' }
py -m unittest discover -s "$work\tests" -p 'test_golf_source_object_windows_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Targeted tests failed' }
$rootPrivate = "$root\Wii-AI-Golf-Data"
$matches = @(Get-ChildItem $rootPrivate -Filter 'checkpoint-manifest-PRIVATE.json' -Recurse -File |
    Where-Object { (Test-Path (Join-Path $_.DirectoryName 'B0-MEM1.bin')) -and
                   (Test-Path (Join-Path $_.DirectoryName 'B3-MEM2.bin')) })
if ($matches.Count -ne 1) { throw 'Expected exactly one existing B0-B3 session' }
$session = $matches[0].DirectoryName
py "$work\scripts\audit_golf_source_object_windows_private.py" --private-root "$session"
if ($LASTEXITCODE -ne 0) { throw 'Private audit failed; preserve source images' }
```

Review local `golf-object-windows-PRIVATE.json` before choosing to upload it in this conversation. The script never auto-uploads and uses exclusive creation; on repeated runs, pick a new private output filename via `--output-private` (ending `-PRIVATE.json`) rather than overwriting evidence.

## Interpretation

- If player/ball records stable and scene/main/field changed during WASD aim, rank only source-relative offsets in those windows for later typed field investigation.
- If all windows unchanged while whole RAM changed, aiming is represented elsewhere (camera input/IR/buffer), and we should not invent field attribution. A separately authorized wider neighborhood scan may then be justified.
- If a candidate Vec3 differs between B phases while the user confirms no shot, it is **not** proof of ball flight; classify it as invalidated stationary expectation or proxy/camera suspicion.
- Recovered actual numeric game state is useful for research, but all actual-ball XYZ, velocity, contact, power and model training flags remain false pending source and visual correlation.
