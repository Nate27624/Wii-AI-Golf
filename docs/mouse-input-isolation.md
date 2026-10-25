# Physical mouse isolation for Wii Sports Golf (S001)

## Why this matters

In upstream Dolphin's emulated Wii Remote, the default Point controls use `Cursor X/Y` for the IR pointer; Windows mouse clicks also map to A and B, and middle-click can trigger Shake. This creates an uncontrolled input during automated swing experiments. See upstream [WiimoteEmu.cpp](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/HW/WiimoteEmu/WiimoteEmu.cpp).

## Startup behavior (proposed controller preflight)

The existing, canonical `scripts/launch_golf.py` preflight calls `ensure_emulated_controller` **with Dolphin closed**. It now edits only **[Wiimote1]** in the located, existing `Config/WiimoteNew.ini`:

- Set `Source = 1` (Emulated) and `Extension = None` as before.
- Bind `IR/Up = W`, `IR/Down = S`, `IR/Left = A`, and `IR/Right = D` for Wii Remote 1 only, replacing the default cursor-axis mappings. **These are Wii pointer controls, not desktop mouse movement.**
- Set `IR/Relative Input = True` and clear `IR/Relative Input Hold`, so the pointer remains where moved instead of snapping back to the center when a key is released.
- Set `IMUIR/Enabled = False` to disable the alternate motion-pointing mode.
- Clear other `[Wiimote1]` bindings that directly include recognizable mouse controls: `Cursor`, `Click`, `Middle Click`, `Mouse X/Y/Button/Wheel`, `Wheel Up/Down`. A composite expression containing mouse input is cleared entirely rather than partially rewriting its logic. **Keyboard-only A/B mappings are retained**; `Device = DInput/0/Keyboard Mouse` is retained so that keyboard mapping still works.
- **Fail closed** if another Wii Remote 1 binding already uses a WASD key (for example `Buttons/A = A`), or if the selected controller Device is explicitly not `Keyboard Mouse`; this prevents moving the pointer from also triggering a swing/button or silently ignoring WASD. Do not alter these other bindings automatically.
- Fail closed on duplicate `[Wiimote1]` control keys, avoid touching `[Wiimote2]` and any other sections. Preserve BOM/line endings and the original `WiimoteNew.ini.wii-ai-golf.original.bak` one-time backup; repeated launches are idempotent.

Nothing in this change intercepts or disables Windows mouse movement globally or modifies the Felk bridge's scripted A/B and swing RPCs. Mouse movement can still navigate **Dolphin's own GUI**. The aim is to disconnect physical mouse inputs from **emulated Wii Remote 1**.

## Operator verification (required before calling the live problem solved)

1. Close **all** Dolphin processes. Pull the merged code from `main` only when the S001 owner has reviewed it.
2. From the normal Windows checkout, run `py -m unittest discover -s tests -p "test_integration_mouse_isolation.py" -v` and the full test suite with `py -m unittest discover -s tests -v`.
3. Start a normal first-shot session through `py scripts/golf.py play --slot 2` or the existing Lab UI path. Do **not** start a bare bridge or double-launch Dolphin.
4. In Dolphin, go to **Controllers → Wii Remote 1 (Emulated) → Configure → Motion Simulation → Point**. Direction mappings should read **Up W / Down S / Left A / Right D**, and **Relative Input** should be enabled. **Motion Simulation → Shake** must have no mouse-click bindings; **General/Buttons A and B** must have no mouse-click bindings. If these settings differ, stop: suspect a wrong user directory, a per-game controller profile, or an older Felk build.
5. On the game's interactive screen, verify **W/A/S/D** moves the *Wii hand pointer* up/left/down/right and that releasing a key leaves the pointer in place. Then move the physical mouse across the render view and click away from actionable UI: it must **not move the Wii hand/cursor, press A/B, or shake the club**. Dolphin's desktop mouse/GUI navigation is unaffected. Separately approve one known-good scripted swing and confirm its inputs still work. Record both observations; do not infer a hit from RPC acknowledgement.

If live tests show mouse input still affects the Wii Remote, report the actual `WiimoteNew.ini` path printed by launcher and the controller profile state, without uploading raw config/game data. Per-game Dolphin profile overrides and the actual Felk fork have not been verified in this code-only change.

## Restoring previous manual controls

With Dolphin fully closed, restore `Config/WiimoteNew.ini.wii-ai-golf.original.bak` into `Config/WiimoteNew.ini` if you want the previous pointer/mouse mappings for normal play. The next Wii-AI-Golf launch will reapply research-mode isolation. Do not delete the backup, savestates, or game image.
