"""Fail-closed Felk Dolphin controller preparation before starting an emulator.

Wii Remote source is an enum from Dolphin's WiimoteSettings.cpp:
0=None, 1=Emulated, 2=Real. The user controller configuration is
<User>/Config/WiimoteNew.ini, section [Wiimote1]. Never create a fresh
Dolphin User directory: doing so could hide the operator's savestates.

This code changes ONLY Source and Extension in [Wiimote1], retaining all
other bindings/sections, with a one-time backup of the original INI.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from typing import Mapping

_SECTION = re.compile(r"^\s*\[\s*([^\]]+?)\s*\]\s*(?:[;#].*)?$")
_KEY = re.compile(r"^(\s*)(Source|Extension)(\s*=\s*)([^;\r\n#]*?)(\s*(?:[;#].*)?)$", re.IGNORECASE)


class ControllerConfigError(RuntimeError):
    """Dolphin controller source cannot safely be configured."""


def _registry_user_directory(dolphin_parent: Path) -> Path | None:
    """Honor a Windows Dolphin user-path override when one is configured."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Dolphin Emulator") as key:
            try:
                local, _ = winreg.QueryValueEx(key, "LocalUserConfig")
                if int(local) == 1:
                    # Dolphin uses its local User folder when LocalUserConfig=1.
                    return dolphin_parent / "User"
            except OSError:
                pass
            try:
                value, _ = winreg.QueryValueEx(key, "UserConfigPath")
                return Path(value).expanduser() if value else None
            except OSError:
                return None
    except OSError:
        return None


def locate_controller_ini(dolphin: Path, *, user_dir: Path | None = None,
                          environ: Mapping[str, str] | None = None,
                          home: Path | None = None) -> Path:
    """Locate EXISTING WiimoteNew.ini; refuse ambiguous or missing user data.

    Priority: explicit user dir, portable.txt, DOLPHIN_EMU_USERPATH,
    Windows registry override, existing Roaming/legacy Documents candidates.
    Default candidate ambiguity is an error rather than writing the wrong file.
    """
    exe = Path(dolphin).expanduser().resolve()
    env = os.environ if environ is None else environ
    base_home = Path.home() if home is None else Path(home)
    if user_dir is not None:
        candidates = [Path(user_dir).expanduser().resolve()]
        forced = True
    elif (exe.parent / "portable.txt").exists():
        candidates = [exe.parent / "User"]
        forced = True
    elif env.get("DOLPHIN_EMU_USERPATH"):
        candidates = [Path(env["DOLPHIN_EMU_USERPATH"]).expanduser()]
        forced = True
    else:
        reg = _registry_user_directory(exe.parent) if os.name == "nt" and environ is None else None
        if reg:
            candidates = [reg]
            forced = True
        else:
            candidates = []
            if env.get("APPDATA"):
                candidates.append(Path(env["APPDATA"]) / "Dolphin Emulator")
            candidates.append(base_home / "Documents" / "Dolphin Emulator")
            candidates.append(base_home / "My Documents" / "Dolphin Emulator")
            forced = False
    # A custom user folder can be a symlink, but no new user directories are made.
    distinct = list(dict.fromkeys((p.resolve() / "Config" / "WiimoteNew.ini") for p in candidates))
    existing = [p for p in distinct if p.is_file()]
    if not existing:
        names = ", ".join(str(x) for x in distinct)
        raise ControllerConfigError(
            "Could not locate an EXISTING Dolphin Wii Remote configuration. "
            f"Checked: {names}. Open Dolphin > File > Open User Folder, "
            "then pass --dolphin-user PATH-TO-THAT-USER-FOLDER once. "
            "No files were changed."
        )
    if len(existing) != 1:
        names = ", ".join(str(x) for x in existing)
        raise ControllerConfigError(
            "Multiple Dolphin user configurations exist; refusing to guess: "
            f"{names}. Specify --dolphin-user once."
        )
    return existing[0]


def _replace_controller_section(original: str) -> tuple[str, bool, dict[str, str | None]]:
    lines = original.splitlines(keepends=True)
    spans = [(i, m.group(1).strip()) for i, line in enumerate(lines)
             if (m := _SECTION.fullmatch(line.rstrip("\r\n")))]
    wiis = [i for i, name in spans if name.lower() == "wiimote1"]
    if len(wiis) != 1:
        raise ControllerConfigError(
            "Expected exactly one [Wiimote1] section in WiimoteNew.ini; "
            "configure the emulated controller in Dolphin's GUI once."
        )
    start = wiis[0] + 1
    end = next((i for i, _ in spans if i >= start), len(lines))
    found: dict[str, tuple[int, re.Match[str]]] = {}
    for i in range(start, end):
        m = _KEY.fullmatch(lines[i].rstrip("\r\n"))
        if not m:
            continue
        key = m.group(2).lower()
        if key in found:
            raise ControllerConfigError(f"Ambiguous duplicate [Wiimote1] {key} keys")
        found[key] = (i, m)
    prior = {
        "source": found["source"][1].group(4).strip() if "source" in found else None,
        "extension": found["extension"][1].group(4).strip() if "extension" in found else None,
    }
    targets = {"source": "1", "extension": "None"}
    changed = False
    newline = "\r\n" if "\r\n" in original else "\n"
    for key, target in targets.items():
        if key in found:
            i, m = found[key]
            before = lines[i]
            eol = "\r\n" if before.endswith("\r\n") else "\n" if before.endswith("\n") else ""
            if m.group(4).strip() != target:
                lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{target}{m.group(5)}{eol}"
                changed = True
        else:
            # Insert only into EXISTING [Wiimote1] and keep all unrelated lines.
            lines.insert(end, f"{key.capitalize()} = {target}{newline}")
            end += 1
            changed = True
    return "".join(lines), changed, prior



# Dolphin's default Win32 Wii Remote controls map mouse movement to the
# Point/IR axes, mouse clicks to A/B, and middle click to Shake. A/B/shake
# interference is especially problematic when collecting scripted swings.
_POINT_AXES = ("IR/Up", "IR/Down", "IR/Left", "IR/Right")
_CONTROL_ASSIGNMENT = re.compile(
    r"^(\s*)([^=;#\r\n]+?)(\s*=\s*)([^;#\r\n]*?)(\s*(?:[;#].*)?)$"
)
_MOUSE_CONTROL = re.compile(
    r"\b(?:Cursor\s+[XY]|Click\s+\d+|(?:Left|Right|Middle)\s+Click|"
    r"Mouse\s+(?:X|Y|Wheel|Button|Left|Right)|Wheel\s+(?:Up|Down|Left|Right))\b",
    re.IGNORECASE,
)


def _isolate_physical_mouse(original: str) -> tuple[str, bool, list[str]]:
    """Remove mouse controller bindings in Wii Remote 1, never global OS mouse.

    Force Point IR axes empty, even when not present in the INI: this makes
    their inactive state explicit across Dolphin defaults/profiles. Disable
    IMUIR (a second pointing mode). Clear other controls only if they name
    recognizably mouse-derived inputs (Click, Cursor, Wheel, etc.). Preserve
    keyboard-only A/B and all other Wii Remote and Dolphin sections.
    """
    lines = original.splitlines(keepends=True)
    spans = [(i, m.group(1).strip()) for i, line in enumerate(lines)
             if (m := _SECTION.fullmatch(line.rstrip("\r\n")))]
    wiis = [i for i, name in spans if name.lower() == "wiimote1"]
    if len(wiis) != 1:
        raise ControllerConfigError("Cannot isolate mouse without one [Wiimote1] section")
    start = wiis[0] + 1
    end = next((i for i, _ in spans if i >= start), len(lines))
    found: set[str] = set()
    cleared: list[str] = []
    changed = False
    newline = "\r\n" if "\r\n" in original else "\n"
    for i in range(start, end):
        raw = lines[i]
        match = _CONTROL_ASSIGNMENT.fullmatch(raw.rstrip("\r\n"))
        if match is None:
            continue
        key = match.group(2).strip()
        fold = key.lower()
        if fold in found:
            # Duplicate input keys make the effective Dolphin setting ambiguous.
            # Do not rewrite any file in this case.
            raise ControllerConfigError(f"Duplicate [Wiimote1] configuration key: {key}")
        found.add(fold)
        value = match.group(4)
        target: str | None = None
        if fold in (name.lower() for name in _POINT_AXES):
            target = ""
        elif fold == "imuir/enabled":
            target = "False"
        elif "/" in key and _MOUSE_CONTROL.search(value):
            # Conservatively disable the entire composite expression rather
            # than leave a branch that can still read the physical mouse.
            target = ""
        if target is not None and value.strip() != target:
            eol = "\r\n" if raw.endswith("\r\n") else "\n" if raw.endswith("\n") else ""
            lines[i] = (match.group(1) + match.group(2) + match.group(3) +
                        target + match.group(5) + eol)
            changed = True
            cleared.append(key)
    # Missing axis keys are explicitly added as blank. When Dolphin loads
    # the config, an empty control expression means no input bound.
    to_add = [(key, "") for key in _POINT_AXES if key.lower() not in found]
    if "imuir/enabled" not in found:
        to_add.append(("IMUIR/Enabled", "False"))
    if to_add:
        if end > 0 and not lines[end - 1].endswith(("\n", "\r")):
            lines[end - 1] += newline
        for offset, (key, value) in enumerate(to_add):
            lines.insert(end + offset, f"{key} = {value}{newline}")
        changed = True
        cleared.extend(key for key, _ in to_add)
    return "".join(lines), changed, cleared


def ensure_emulated_controller(dolphin: Path, *, user_dir: Path | None = None,
                               environ: Mapping[str, str] | None = None,
                               home: Path | None = None) -> dict[str, object]:
    ini = locate_controller_ini(dolphin, user_dir=user_dir, environ=environ, home=home)
    raw = ini.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        original = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ControllerConfigError(f"Unrecognized encoding in {ini}; no change") from exc
    rewritten, changed, before = _replace_controller_section(original)
    rewritten, isolated, cleared_mouse_controls = _isolate_physical_mouse(rewritten)
    changed = changed or isolated
    backup = ini.with_name(ini.name + ".wii-ai-golf.original.bak")
    if changed:
        # Never overwrite the very first backup even on subsequent launches.
        if not backup.exists():
            shutil.copy2(ini, backup)
        temp = ini.with_name(ini.name + ".wii-ai-golf.tmp")
        try:
            data = (b"\xef\xbb\xbf" if has_bom else b"") + rewritten.encode("utf-8")
            temp.write_bytes(data)
            os.chmod(temp, ini.stat().st_mode)
            os.replace(temp, ini)
        finally:
            if temp.exists():
                temp.unlink()
    return {
        "ini": str(ini),
        "user_dir": str(ini.parent.parent),
        "changed": changed,
        "prior": before,
        "source": "Emulated Wii Remote (1)",
        "extension": "None",
        "mouse_input_isolated": True,
        "mouse_controls_cleared": cleared_mouse_controls,
        "backup": str(backup) if backup.exists() else None,
    }
