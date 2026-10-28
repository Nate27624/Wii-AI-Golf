# Felk Dolphin (Windows): Qt6Widgets access violation and portable GUI/Memory settings recovery

**Status: PARTIALLY RESOLVED / ROOT CAUSE NOT YET PROVEN (2026-10-28).**

**Owner:** S001 Dolphin launcher; S000 coordinator for operator guidance; S002 source-selected RAM research downstream.

**Most important practical result:** On the operator's actual Windows installation, **reinstalling Felk Dolphin while copying the original portable \`User\` folder did not stop the native crash**. Moving the *entire* old portable \`User\` folder to a timestamped backup, then creating a fresh \`User\` containing the old \`StateSaves\`, \`Wii\`, \`GC\` and \`Config/WiimoteNew.ini\` DID allow \`Dolphin.exe\` to open and remain open **without an injected scripting bridge**. User confirmed "That one opened, and no crash." The user suspects Dolphin's **Memory debugger section**. This is plausible, **not yet proven**: the successfully launched GUI-only process is a different test from the still-unverified canonical \`--script <watched V1> --exec <game>\` path.

## Repro and native crash evidence

- Windows executable \`D:\Projects\Wii Golf AI\tools\FelkDolphin-Clean\Dolphin.exe\`.
- Failed canonical S001 first-ball startup reported \`Dolphin exited before bridge preflight, code=3221225477\` = \`0xC0000005\` access violation. Game savestate load/menu sequence, \`READY\`, read-only watcher arm, 45-observed-frame A lead, and swing **never began**.
- Application Event ID **1000** at local **2026-10-28 01:02:47** and **01:03:07**: \`Qt6Widgets.dll\` 6.5.1.0, exception \`0xc0000005\`, identical fault offset \`0x000000000005622b\`. Event 1001 recorded associated fault bucket. Events correlate temporally; PID-to-launch correlation was not established.
- A previous distinct Dolphin/Qt failure used offset \`0x5A587\`, **do not conflate offsets**. Earlier occasional \`Qt6Core.dll\` and \`ntdll\` faults were observed too.
- Pre-reset DLL/process hashes (historical evidence; reinstall may change them):
  - \`Dolphin.exe\` SHA256 \`D51EADA34E0FC83EF8FB3CB1E3279760C7DD52FBB5C8892C9ECE888FBB4F7FC6\`.
  - \`Qt6Widgets.dll\` SHA256 \`AFB9B6D440AA36CA55951C13CD912A17FF9F2BA0FA9D4254351D40DFF3826018\`.
  - \`Qt6Core.dll\` SHA256 \`21CC245C29B673E49E7FC7C606510AED4EEB52CD92668288997D89409914825A\`.
- Isolated generated watched historical V1 bridge SHA256 \`465b6b02a9ae3833c65233b0d7a26fca79c613330eedf4eeb1de2a5d89ff886b\`. **Matching hash proves only source identity, not native runtime safety.**
- \`portable.txt\` and an existing portable \`User\Config\WiimoteNew.ini\` were present; no Qt-related process environment overrides were detected. One check of \`platforms\qwindows.dll\` reported absent at that particular path, but alternate Qt plugin paths were not inventoried. **Do not name missing plugin as the cause without stronger evidence.**

## Relevant upstream code: why the Memory panel is a credible hypothesis

Felk Dolphin \`scripting-preview4\` source, not a post hoc guess:

1. \`Source/Core/DolphinQt/Settings.cpp\` \`Settings::GetQSettings()\` stores Qt GUI preferences in the portable **\`User/Config/Qt.ini\`** (\`File::GetUserPath(D_CONFIG_IDX)\`).
2. \`Source/Core/DolphinQt/MainWindow.cpp\` restores \`mainwindow/state\` and \`mainwindow/geometry\` on initialization; it constructs and docks the Memory widget.
3. \`Source/Core/DolphinQt/Debugger/MemoryWidget.cpp\` constructs a \`QDockWidget\` titled **Memory**, restores \`memorywidget/geometry\`, \`memorywidget/floating\` and splitter state, and uses the debugger visibility state. Bad saved layout is *plausible* as a Qt Widgets crash confound.
4. \`Settings::IsMemoryVisible()\` and \`SetMemoryVisible()\` use a default \`QSettings()\` instance rather than \`GetQSettings()\` in this source revision. That is a separate subtlety: resetting just \`Qt.ini\` may not clear all debugger visibility. Do not assume one preference file fully controls visibility.
5. A GUI-only launch after user-config reset **does not** demonstrate that \`memory.read_u32\` from the Felk scripting API or the P0 frame watcher caused the prior crash.

Upstream code: https://github.com/Felk/dolphin/tree/scripting-preview4/Source/Core/DolphinQt

## Safe recovery sequence — keep your old user data

**Do not overwrite or delete** the known-good original V1 bridge, separately generated watched V1 bridge, ROM, private \`Wii-AI-Golf-Data\`, named savestates, or active Dolphin installation. Never auto-trigger a swing while investigating a Qt crash.

### A. First try a *targeted, reversible Qt.ini reset* (not yet tested as a standalone fix)

Close Dolphin. From PowerShell:

\`\`\`powershell
& {
    $ErrorActionPreference = 'Stop'
    if (Get-Process Dolphin -ErrorAction SilentlyContinue) {
        throw 'Close Dolphin first'
    }
    $config = 'D:\Projects\Wii Golf AI\tools\FelkDolphin-Clean\User\Config'
    $qt = Join-Path $config 'Qt.ini'
    if (-not (Test-Path -LiteralPath $qt -PathType Leaf)) {
        Write-Host 'No Qt.ini to isolate; use the full User reset procedure if necessary.'
        return
    }
    $backup = Join-Path $config ("Qt.ini.pre-reset-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".bak")
    if (Test-Path -LiteralPath $backup) { throw 'Backup already exists' }
    Move-Item -LiteralPath $qt -Destination $backup
    Write-Host "Qt.ini isolated at: $backup"
    Write-Host 'Run Dolphin.exe without --script or --exec to test GUI only.'
}
\`\`\`

This is the **minimal candidate fix**, not the one proven effective by the operator. Back up the old file; do not simply copy the old \`Qt.ini\` back into the active \`User\Config\` before the next test.

### B. Verified GUI-only recovery: *isolate the whole User configuration*

The operator's successful remedial change was:

1. Stop/close every Dolphin process.
2. Verify \`FelkDolphin-Clean\portable.txt\`, \`User\StateSaves\` and \`User\Config\WiimoteNew.ini\` exist.
3. **Move** the old entire portable \`User\` folder into \`FelkDolphin-Clean\User-Backup-QtReset-YYYYMMDD-HHMMSS\`; **do not delete it**. This backup contains all unlisted preferences and save artifacts.
4. Create a new \`User\Config\`. **Copy** (not move) only \`StateSaves\`, \`Wii\`, \`GC\` folders if present, plus \`Config\WiimoteNew.ini\` from the backup into the new \`User\`. Keep all other original files in the backup for eventual selective restore.
5. Verify \`WiimoteNew.ini\` SHA256 and the number of files in \`StateSaves\` match the backup. Prefer additionally checking individual save hashes when possible. The repo's \`research/savestates.local.json\` name registry is outside the emulator directory and should remain untouched.
6. Start only \`FelkDolphin-Clean\Dolphin.exe\`, with **no \`--script\`, \`--exec\`, game or bridge**.
7. **Actual observed result:** this GUI-only startup succeeded without a crash. No claim yet about game+bridge.

**Warning:** a minimal new \`User\` may drop custom paths, game-specific INI settings, SD/other Dolphin user files and window preferences. Those remain in the timestamped backup. Do not restore the old \`Qt.ini\` (or the entire old \`User\Config\`) indiscriminately while testing; it may reintroduce the crash. The original operator run deliberately preserved \`StateSaves\`, \`Wii\`, \`GC\`, and \`WiimoteNew.ini\`.

### C. Rollback

Close Dolphin completely. Rename the new active \`User\` to a **new** \`User-PostReset-YYYYMMDD-HHMMSS\` folder, then rename the original \`User-Backup-QtReset-...\` back to \`User\`. Never overwrite the backup or merge folders blindly. This restores all original preferences, including any GUI setting that may have caused the crash; rollback is for recovery of original data, not an assumed permanent fix.

## Controlled isolation matrix — necessary before saying "solved"

Run tests **one at a time**; preserve the exact source/build/user path for each. Do not upload raw RAM or use a live swing as a diagnostic:

| Test | Expected safe scope | Evidence |
| --- | --- | --- |
| A. Fresh portable GUI-only \`Dolphin.exe\` | No bridge, game, savestate or input | **PASS observed by operator** |
| B. Fresh Dolphin with registered game but NO P0 watcher | Game startup only; do not overwrite state | **NOT TESTED after reset** |
| C. Fresh Dolphin + original historical V1 bridge \`--script\` (no watcher) | Bridge init only; no shot | **NOT TESTED after reset** |
| D. Fresh Dolphin + source-pinned watched V1 bridge (before \`golf.ball_watch.arm\`) | Watch dormant; no shot | **NOT TESTED after reset** |
| E. Canonical fresh \`green-pre-start\` launch, then \`qualify_v1_selected_watch_readonly.py\` at stable ball | 128 bridge ticks, 32 selected 51-word samples, 5ms ceiling, **no swing** | **NOT TESTED after reset** |
| F. One human-approved watched V1 shot | 45 **observed** Dolphin frames A-held then same 89-sample trace | **BLOCKED** pending E + S001/S002/S000 owner reviews |

**Interpretation:** If A passes and B crashes, look at Dolphin game/graphics/Qt initialization. If B/C pass but D crashes before arm, compare injected bridge init/API registration and native scripting. If D passes but E fails, investigate source gates and per-frame native read overhead. Do not treat a healthy Qt GUI as permission to run F.

## If the access violation returns

Before further resets, collect (read-only) Windows Application Event 1000/1001 for the exact newest \`Dolphin.exe\` crash, including timestamp, module, \`0xC0000005\`, fault offset and executable path. Correlate PID/time with the specific trial if possible. Capture Qt and Dolphin binary SHA; verify no unexpected \`QT_PLUGIN_PATH\`, \`QT_QPA_PLATFORM_PLUGIN_PATH\`, \`DOLPHIN_EMU_USERPATH\` overrides. Stop if an unexpected module, missing \`qwindows.dll\`, non-canonical user directory, stale Felk port 55355, or duplicate Dolphin process appears.

**Never claim:** the 51-word watcher caused this crash, ball world XYZ is verified, impact/power is verified, or training is approved. None of those conclusions follow from the crash or the clean-GUI startup.

## Future-agent handoff

- **Confirmed:** \`Qt6Widgets.dll\` 6.5.1 \`0xC0000005\` offset \`0x5622B\` native process crash on old portable settings; reinstall **with the same User** did not fix it; **new minimal User** restored GUI-only startup.
- **Working hypothesis:** saved Qt dock/Memory/debugger GUI configuration, not yet isolated to a single file/setting.
- **Next owner:** S001 should make minimal non-swing A–E test plan, with a separate review PR if behavior changes. S000 should retain this document in the agent index after the root cause is confirmed. S002 should keep raw selected-player evidence private and not conflate GUI Memory widget with Felk \`memory.read_u32\` RPC.
- **Update this document when:** \`Qt.ini\` isolated test, launcher/bridge smoke tests, and a true read-only watcher pass have been observed. Append date, exact binary/source hashes and a conclusion **supported by actual logs**. Do not silently change "partially resolved" to "solved".

**Related active research:** draft [#215](https://github.com/Nate27624/Wii-AI-Golf/pull/215) stationary V1 watch, [#211](https://github.com/Nate27624/Wii-AI-Golf/pull/211) private drain and human labels, [#206](https://github.com/Nate27624/Wii-AI-Golf/pull/206) observed 45-frame V1 collector, [#202](https://github.com/Nate27624/Wii-AI-Golf/pull/202) original-source watcher adapter, [#189](https://github.com/Nate27624/Wii-AI-Golf/pull/189) private 51-word record, [#166](https://github.com/Nate27624/Wii-AI-Golf/pull/166) shared bridge integration.
