# Scripted full Wii RAM capture for S002 (draft)

This study adds `scripts/capture_golf_fullbanks_private.py` on top of the existing S002 shot keeper and analyzers. It uses the external `dolphin-memory-engine==1.3.1` Python reader to attach to an already-running Dolphin process. The operator **must pause emulation first**. The script does not control Dolphin, its menus, controllers or savestates.

Output is full binary Wii guest RAM: 24 MiB MEM1 (`0x80000000`) and 64 MiB MEM2 (`0x90000000`) as `PRE-MEM1.bin`, `PRE-MEM2.bin`, then optional POST and RESULT pairs. They are stored under the ignored sibling `Wii-AI-Golf-Data` and are never uploaded to GitHub. The existing private keeper produces phase manifests compatible with the PRE/POST and cup-distance analyzers. Small JSON provenance is supplementary; it does not replace the binary dumps.

**Trust limits:** Successful installation or hook does not guarantee compatibility with the operator's Felk Dolphin build. A paused human attestation is not independent emulator freeze verification. Banks are read sequentially; if emulation is advancing they are not a consistent shot checkpoint. Only label POST when the ball visibly moved and has not reset, on the same hole and process. Never confuse a miss or result-screen reset with landed POST. No swing velocity, verified world XYZ, power, game unit conversion or training approval follows from these dumps. Never share native banks publicly.

### Operator sequence

1. Launch into the first ball using the existing main-repo launcher, with the correct clean Felk binary and isolated V1 bridge. Do NOT relaunch if already at ball.
2. Install the binary wheel once: `py -m pip install --user --only-binary=:all: dolphin-memory-engine==1.3.1`. Python 3.13 x64 wheel is available.
3. In PowerShell, verify exactly one Dolphin.exe is running and its ExecutablePath is `D:\Projects\Wii Golf AI\tools\FelkDolphin-Clean\Dolphin.exe`. Do not let the memory engine pick between multiple emulators.
4. Create a fresh `SHOT-...-PRIVATE` folder under `Wii-AI-Golf-Data\captures`. Keep the same `$session` for the shot.
5. At stationary first ball, **pause Dolphin**, then run `py scripts/capture_golf_fullbanks_private.py --session $session --phase PRE --paused-confirmed` from the shot-reader detached worktree.
6. Verify both native PRE bin files and size checks. **Resume Dolphin**. Send exactly one S001-approved swing; the A90 lead is a separate experimental one-factor hypothesis, not verified contact.
7. If and only if the ball visibly moves, **pause before the game resets the ball**, then run the same script with `--phase POST --paused-confirmed --shot-observed --same-process-confirmed --same-hole-confirmed`. If the game transitioned before pause, do not fabricate POST.
8. Optional RESULT only after a genuinely preserved POST. Run `--phase RESULT --paused-confirmed --result-visible` and optionally `--displayed-distance NUMBER --ui-unit ft|yd|m`.
9. Run existing source-gated private analyzers, sharing only their sanitized, reviewed JSON summaries. No native RAM, ROM, savestate, hashes, pointers, or private manifest uploads.

The read API is the upstream Dolphin Memory Engine's read-only `read_bytes`; it is independent of Felk's frame-polled Python RPC. The complete memory capture does not depend on Dolphin's hidden GUI Memory panel.

**Validation status:** isolated synthetic tests of a prototype local implementation passed; a live pause/capture through this committed script on the user's Windows Dolphin has **not** been performed. Requires S001/S002/S000 review.