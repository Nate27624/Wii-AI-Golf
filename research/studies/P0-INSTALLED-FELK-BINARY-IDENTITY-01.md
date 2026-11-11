# P0 — installed Dolphin/Felk binary identity, offline-only

**Purpose:** Close the basic provenance gap before S001 #272 can even attempt to review the installed scripting callback API. Public documentation, GitHub fork names and arbitrary `on_framedrawn` examples do NOT tell us which exact binary is installed on the operator's Windows machine.

The operator can run `research/tools/Get-P0InstalledDolphinIdentity.ps1 -DolphinExe 'FULL_PATH_TO_Dolphin.exe'` after S001 owner review. It:
- Reads ONLY the explicitly named local executable as a file (no recursive searches or auto-discovery), verifies MZ+PE signature, machine and bounded length, hashes the file with SHA256, returns sanitized FileVersion/ProductName or null.
- Reports **no full local filesystem path**, no game files, no process, no bridge connection, no guest RAM pointers, no ROM bytes, no screenshots, no raw executable code. There is NO upload/network operation; the user controls which categorical report is shared in chat.
- Refuses symlink/reparse-point and non-EXE inputs and malformed PE headers. Hash can identify exact installed binary bytes, but cannot map those bytes to public source or prove loaded plugins, patched script support, guest physics events or callbacks. **Even successful report is `LOCAL_BINARY_IDENTIFIED_SOURCE_UNVERIFIED`, never YES/NO callback proof.**
- Runs native-free generated dummy PE tests via `-SelfTest`; requires PowerShell 5.1+ on Windows. No Dolphin installation needed for those tests.

The explicit owner next step after obtaining a real hash (if user elects to run): match hash to trusted source/binary release and inspect *that exact fork/installed scripting plugin* for a noninterfering, game-sourced step callback. If source hash is unknown, **ABSTAIN** and do not register live handlers. An emulated `frameadvance`, frame-presented hook, bridge coroutine tick, or wall time is NOT one Wii Sports Golf physics step; this inventory proves none of those meanings.

**Prerequisites:** S001 #215 safe stationary reviewer (prefer one anchored-drift fix from #275) and #272 physics timing NO-GO remain. #248 downstream two-ball contract is synthetic-only. No guest-memory reads, scene callbacks, Dolphin startup, paused script, shot, remote upload, training or model-ready status authorized by running this tool.

**Stop gate:** one binary identity result sufficient; do not rehash alternate Dolphin builds unless operator has a specific reason to distinguish which build runs. Current code/test only inventories a binary, never proves it is the executable actually running a game.
