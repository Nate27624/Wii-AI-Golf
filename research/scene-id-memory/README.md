# P0 scene_id: source-derived US Revision 1 memory investigation

**Evidence status: SOURCE LAYOUT FOUND / RUNTIME NOT VERIFIED.** Read-only offline dump work. No game-memory writes, emulator launches, ROMs, savestates or raw RAM committed.

## Exact structure offsets and candidate static location

These are for Wii Sports RSPE01 US **Revision 1**, not older v1.00 Gecko codes.

1. [EGG SceneManager layout](https://github.com/doldecomp/ogws/blob/main/include/egg/core/eggSceneManager.h): current scene pointer at **manager +0x0C**, current scene integer ID at **manager +0x18**. Do not confuse it with previous/next scene IDs.
2. [EGG Scene layout](https://github.com/doldecomp/ogws/blob/main/include/egg/core/eggScene.h): for RSPE01 Rev1, scene's own ID at **scene +0x1C** and manager back-pointer at **scene +0x20**.
3. [RPSysSceneMgr](https://github.com/doldecomp/ogws/blob/main/include/Pack/RPSystem/RPSysSceneMgr.h) derives from the above and uses the static spInstance pointer ([singleton macro](https://github.com/doldecomp/ogws/blob/main/include/Pack/RPSingleton.h)).
4. [RSPE01_01 splits](https://github.com/doldecomp/ogws/blob/main/config/RSPE01_01/splits.txt): the *entire* SceneMgr source unit's .sbss section occupies **0x804BF4D8 through 0x804BF4DF**. Which of the aligned 4-byte slots **0x804BF4D8 or 0x804BF4DC** contains spInstance is NOT yet independently proved. Probe both, then require consistent pointer chain.
5. [RPSysSceneCreator enum](https://github.com/doldecomp/ogws/blob/main/include/Pack/RPSystem/RPSysSceneCreator.h): Golf scene ID **5**, Sports main-menu scene ID **9**.
6. Do **not** use SceneCreator mPrevSceneID at +0x08 as the current scene: [implementation](https://github.com/doldecomp/ogws/blob/main/src/Pack/RPSystem/RPSysSceneCreator.cpp) says previous scene.

Read-only proposed chain, where S is exactly one of the two singleton candidate slots:

    manager = read_BE_u32(S)
    active_scene_id_location = manager + 0x18
    scene_id = read_BE_u32(active_scene_id_location)
    scene = read_BE_u32(manager + 0x0C)
    assert read_BE_u32(scene + 0x1C) == scene_id
    assert read_BE_u32(scene + 0x20) == manager
    assert scene_id == 5  # ready Golf / any Golf subphase

If validated, the specific RAM address for scene_id in that boot is the checker-reported scene_id_field_address. It is a **dynamic heap address**, not a hard-coded global constant. A scene ID of 5 says the Golf scene is active; it does NOT establish ready/aim/swing/ball-stopped phase.

## Run offline on your private Windows captures

Use full, raw, same-snapshot MEM1 and MEM2 banks only (not truncated/partial/chunked captures). MEM1 must be 24 MiB, MEM2 must be 64 MiB; BE console byte order; Wii header RSPE disc revision 1. The checker **never launches Dolphin** and writes nothing. It exits 0 only on one consistent pointer slot, but even success reports verified_live=false until independent control trials.

From PowerShell (the first line automatically enters the correct repository):

    Set-Location -LiteralPath 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
    Get-ChildItem -LiteralPath 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data' -Recurse -File |
        Where-Object { $_.Name -match 'mem1|mem2' } |
        Select-Object -Last 20 FullName,Length

Choose actual same-snapshot paths from this listing, then replace both placeholders:

    $mem1 = 'FULL_PATH_TO_MEM1_FROM_ONE_CAPTURE'
    $mem2 = 'FULL_PATH_TO_MEM2_FROM_THE_SAME_CAPTURE'
    py scripts/probe_scene_id_dump.py --mem1 $mem1 --mem2 $mem2 --expect 5

A separately captured Sports main menu can be checked with --expect 9. Do NOT reuse two identical snapshots or assume any pre-start checkpoint is a genuine menu negative. If files are partial captures, coordinate a separate S002 offline adapter: do not pad missing RAM with zeros.

Interpretation: status snapshot_consistent_not_runtime_verified proves consistency only within **one** bank pair; no_consistent_slot means failure, and ambiguous_multiple_slots means multiple candidates/no unique singleton. Exit codes 0, 1, 2 correspond to single consistent candidate, no/ambiguous candidate, invalid file/header respectively. The printed JSON is PRIVATE because it includes dynamic pointers and must **not** be sent to the automatic observation publisher.

## Acceptance before training use

- [ ] One genuine Golf scene at-ball capture: single candidate slot and matching manager scene ID, scene-object scene ID and back-pointer.
- [ ] Another independent fresh-boot Golf capture: same source pointer slot, scene 5 and pointer-chain consistency. Record secure local hashes; never confuse repeated frames with independent boots.
- [ ] A genuine non-Golf control (e.g., menu scene 9) changing appropriately, with provenance and controlled timing.
- [ ] S002 owner reviews data-source, game revision, phase, address resolution and failure behavior, then publishes only sanitized variable verification status.
- [ ] Only after that, S000 may consume scene_id through an approved typed public/internal observation contract; current script does not modify it.

Owner: **S002 evaluation**. Coordinate readiness/boot timing with **S001** and phase alignment with [#121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). Keep game assets and private captures strictly local.
