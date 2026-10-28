# S002-FOUR-CHECKPOINT-DIFF-01 — private offline RAM checkpoint differencing

Status: implementation for S002/S001 review; **no Dolphin acquisition capability assumed or verified**. Complements PR #148 (S002 full-state discovery), PR #147 (S001/S002 same-shot plan), and PR #122/#146 (player source atlas). No gameplay, bridge, launcher, controller, shared CLI, automatic publisher, or public schema changes.

## Four controls, one canonical golf session

First obtain S001 confirmation that the **existing Felk Dolphin fork** supports safe read-only native memory dumping. Do not substitute a savestate for a RAM image and do not use per-byte memory.read_bytes for a whole MEM1 dump. Do not pause the frame-polled bridge via unreviewed RPC calls.

B0 = tee-ready and stationary, B1 = stationary after fixed idle time, B2 = WASD pointer-only aim with no A/swing, B3 = after release/return to stillness. Record independently whether pointer movement was actually visible. Verify exactly the same source ROM revision, region (MEM1 or MEM2), hole, scene, memory base and loaded session at each checkpoint. A scene transition, ambiguous pause/dump, truncated dump or changed memory mapping is a stop condition.

Use full, headerless, read-only paused native MEM1 dumps of exactly 25,165,824 bytes or MEM2 dumps of exactly 67,108,864 bytes. The analyzer will reject any other size. Never overwrite original dumps.

## Offline command (only AFTER verified native dump acquisition)

Open a dedicated checkout for this PR. Use four private files under the sibling Wii-AI-Golf-Data/captures directory. From the PR worktree in PowerShell:

    $data = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"
    py scripts/analyze_golf_ram_checkpoints.py --mem mem1 `
      --b0 "$data\mem1-B0.bin" --b1 "$data\mem1-B1.bin" `
      --b2 "$data\mem1-B2.bin" --b3 "$data\mem1-B3.bin" `
      --out "$data\mem1-B0-B3-PRIVATE.json"

Script needs Python standard library only. Input files are opened read-only; it never starts Dolphin, sends controller/RPC commands, networks, uses Git, or uploads research artifacts. It refuses JSON output outside the sibling Wii-AI-Golf-Data directory or overwriting an existing report. Console output is a small set of aggregate counts, not offsets or raw values. Optional JSON is **PRIVATE**: it contains hashes, local relative page/word offsets, and counts but no RAM values.

Do NOT publish the JSON, memory images, runtime offsets, private paths or SHA digests to GitHub. S000 must approve an explicit typed sanitizer before any future public observation.

## Classification — NOT semantics

- idle_changed_words: B0 differs from B1; an uncontrolled timing/animation/relocation nuisance.
- aim_changed_words: B1 differs from B2; an observed transition, not confirmed aiming.
- reversible_aim_candidates: B0 equals B1 equals B3, and B2 differs; a reversible pattern.
- persistent_aim_candidates: B0 equals B1, B2 equals B3, and B2 differs; possible persistent changed state.
- ambiguous_aim_words: B1 differs from B2 without qualifying for either preceding specific pattern.

32-bit words are compared in PPC big-endian order. Counts are also given for changed bytes per transition, with candidates grouped into ranked 4 KiB pages. Top pages include up to eight relative offsets each in PRIVATE JSON. A matching pattern does not establish its type, object owner, physical meaning, source provenance, causality, or game-applied input. This is not an impact/power decoder. A real candidate still needs pointer-owner/source verification, PPC read/write tracing, independently restored-session replication, and frame-thread tiny-watch controls.

## Verification and ownership

Author ran synthetic tests with Python 3.13 on Linux: 5 passed. Four 24 MiB synthetic MEM1 images were compared end-to-end: one reversible altered word at relative 0x2000 correctly detected in about 3.5 seconds. compileall passed. These are offline tests, not a live Dolphin test. Full canonical Windows suite and native Felk dump capability have not been checked. Therefore **draft, not merge ready**. S002 owns data acquisition and source semantics; S001 owns debugger/same-frame integration; S000 owns publication; S003 owns the downstream power model. Stay isolated from concurrent agent paths.
