# S002 full native binary RAM — code-only, rolling capture

**Status: experimental.** This read-only script streams 24 MiB MEM1 (0x80000000) and 64 MiB MEM2 (0x90000000) through the *already-running Felk* memory.read_bytes RPC, writing real private `mem1.raw` + `mem2.raw` files. No GUI memory export, controller input, savestate, Dolphin launch/reset, or raw data GitHub upload.

**CRITICAL:** The existing Felk RPC polls on advancing frames, so **Dolphin must be unpaused** while dumping. The two banks span many emulator frames and are NOT atomic/same-pause snapshots. Don't rename the rolling files to the S002 #180/#184 native PRE/POST filenames or feed them to that paired-snapshot validator. The metadata marks `same_guest_frame_verified=false`, `same_paused_bank_pair=false` and training/publish/paused-analysis permissions false. Game mode4 and RSPE01 Rev1 are checked at start and periodically, but those checks do not prove ball, shot or hole stability.

## One paste in PowerShell: fetch the tool from GitHub, preflight, dump both full banks

Run with **first stationary ball displayed**, Dolphin RUNNING (not paused). There is no ZIP and no second launcher. New worktree is based on exact branch commit, so stale study worktrees won't interfere.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $root = 'D:\Projects\Wii Golf AI'
    $repo = "$root\Wii-AI-Golf"
    $branch = 'agent/research/full-memory-binary-rpc-20261028'
    git -C $repo fetch origin "refs/heads/agent/research/full-memory-binary-rpc-20261028:refs/remotes/origin/agent/research/full-memory-binary-rpc-20261028"
    if ($LASTEXITCODE -ne 0) { throw 'FullRAM fetch failed' }
    $rev = (git -C $repo rev-parse "origin/$branch").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'FullRAM branch cannot be resolved' }
    $work = "$root\Wii-AI-Golf-FullRAM-$($rev.Substring(0,8))"
    if (-not (Test-Path $work)) {
        git -C $repo worktree add --detach $work "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
    }
    if ((git -C $work rev-parse HEAD).Trim() -ne $rev) { throw 'Worktree revision mismatch' }
    $tool = "$work\scripts\capture_full_ram_private.py"
    if (-not (Test-Path $tool)) { throw 'Capture script not found' }
    & py $tool --probe --phase PRE
    if ($LASTEXITCODE -ne 0) { throw 'Small read-only RPC probe FAILED' }
    $session = "FULLRAM-$(Get-Date -Format yyyyMMddHHmmss)-PRIVATE"
    Write-Host "Session ID: $session"
    if ((Read-Host 'Type PRE if golfer stationary and Dolphin UNPAUSED') -cne 'PRE') {
        throw 'Canceled: no capture'
    }
    & py $tool --capture --session $session --phase PRE --confirm-phase
    if ($LASTEXITCODE -ne 0) { throw 'Full binary capture FAILED' }
    $dir = "$root\Wii-AI-Golf-Data\captures\$session\PRE-ROLLING"
    Get-Item -LiteralPath "$dir\mem1.raw","$dir\mem2.raw" | Select-Object Name,Length
    Write-Host "Session ID for next phase: $session"
}
```

Expected: `mem1.raw` = 25,165,824 bytes, `mem2.raw` = 67,108,864 bytes; total 92,274,688 bytes (88 MiB). Both reside under `D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\<session>\PRE-ROLLING\`, alongside a small `capture-meta-PRIVATE.json` with private SHA256/frame span. **The actual memory is in the raw files, NOT JSON.** The bridge's per-byte read may make this slow; do not pause Dolphin during capture.

For a later score screen, run `py $tool --capture --session $session --phase RESULT --confirm-phase` after validating the same session still exists. For a visibly displaced ball at the same hole, `--phase POST --confirm-phase --observed-displacement` is allowed but remains multi-frame/rolling: it CANNOT count as an authoritative landed-ball snapshot. If the ball has reset, do not label it POST.

Offline defaults: running without `--capture` produces only a dry-run plan and does not touch Dolphin. `--probe` checks header, frame progress, mode4, and 256 bytes from each bank with no files. Fail-closed behavior for paused frame counter, wrong revision/mode, malformed/short data, wrong bank sizes, or duplicate phase; partial `.part` never becomes a finished `.raw`.

S001 owns live swing/bridge; S002 #180/#184 owns same-pause snapshot qualification; S000 #154 owns publication. No raw RAM, game files or manifests may be uploaded to public GitHub. Actual Windows Dolphin success is pending the operator's local probe/capture.
