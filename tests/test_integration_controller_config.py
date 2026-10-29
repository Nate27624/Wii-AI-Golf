"""S001: conservative Dolphin Wii Remote startup config tests (no emulator needed)."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

# Make unittest discovery use this source checkout, not a stale pip editable install.
import sys
_TEST_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_TEST_REPO_ROOT), str(_TEST_REPO_ROOT / "src")):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

from wii_ai_golf.integration.dolphin_controller_config import (
    ControllerConfigError, _replace_controller_section,
    ensure_emulated_controller, locate_controller_ini,
)


class DolphinControllerStartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.exe = self.base / "FelkDolphin" / "Dolphin.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"")
        self.home = self.base / "home"
        self.home.mkdir()
        self.roaming = self.base / "AppData" / "Roaming"
        self.roaming.mkdir(parents=True)

    def ini(self, user: Path, contents: str) -> Path:
        cfg = user / "Config" / "WiimoteNew.ini"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_bytes(contents.encode("utf-8"))
        return cfg

    def test_edit_only_source_and_extension_and_preserve_other_bindings(self):
        ini = self.ini(self.base / "user", (
            "; existing Dolphin preferences\r\n"
            "[Wiimote1]\r\nSource = 2\r\nExtension = Nunchuk\r\n"
            "Buttons/A = `F`\r\n"
            "[Wiimote2]\r\nSource = 2\r\n"
            "[Extra]\r\nSetting = 4\r\n"
        ))
        old = ini.read_bytes()
        result = ensure_emulated_controller(self.exe, user_dir=ini.parent.parent)
        self.assertTrue(result["changed"])
        now = ini.read_bytes()
        self.assertIn(b"Source = 1\r\nExtension = None\r\n", now)
        self.assertIn(b"Buttons/A = `F`\r\n", now)
        self.assertIn(b"[Wiimote2]\r\nSource = 2\r\n", now)
        self.assertIn(b"; existing Dolphin preferences\r\n", now)
        backup = Path(str(ini) + ".wii-ai-golf.original.bak")
        self.assertEqual(backup.read_bytes(), old)
        self.assertFalse(ensure_emulated_controller(self.exe, user_dir=ini.parent.parent)["changed"])
        self.assertEqual(backup.read_bytes(), old)

    def test_missing_source_or_extension_added_inside_existing_wiimote1(self):
        txt = "[Wiimote1]\nButtons/A = F\n[Wiimote2]\nSource = 2\n"
        modified, changed, old = _replace_controller_section(txt)
        self.assertTrue(changed)
        self.assertIsNone(old["source"])
        self.assertIn("Source = 1\n", modified)
        self.assertIn("Extension = None\n[Wiimote2]", modified)
        self.assertIn("[Wiimote2]\nSource = 2", modified)

    def test_duplicate_wiimote1_or_duplicate_source_fails_closed(self):
        for content in ("[Wiimote1]\nSource = 1\n[Wiimote1]\nSource = 2\n",
                        "[Wiimote1]\nSource = 1\nsource=2\n",
                        "[Wiimote2]\nSource = 2\n"):
            with self.subTest(content=content):
                with self.assertRaises(ControllerConfigError):
                    _replace_controller_section(content)

    def test_portable_user_directory_takes_precedence_over_appdata(self):
        (self.exe.parent / "portable.txt").touch()
        user = self.exe.parent / "User"
        expected = self.ini(user, "[Wiimote1]\nSource = 2\nExtension = Nunchuk\n")
        other = self.ini(self.roaming / "Dolphin Emulator", "[Wiimote1]\nSource = 2\n")
        located = locate_controller_ini(
            self.exe, environ={"APPDATA": str(self.roaming)}, home=self.home)
        self.assertEqual(located, expected)
        self.assertNotEqual(located, other)

    def test_ambiguous_user_directories_error_until_explicit(self):
        first = self.ini(self.roaming / "Dolphin Emulator", "[Wiimote1]\nSource = 2\n")
        second = self.ini(self.home / "Documents" / "Dolphin Emulator", "[Wiimote1]\nSource = 2\n")
        env = {"APPDATA": str(self.roaming)}
        with self.assertRaisesRegex(ControllerConfigError, "Multiple"):
            locate_controller_ini(self.exe, environ=env, home=self.home)
        self.assertEqual(locate_controller_ini(
            self.exe, user_dir=second.parent.parent, environ=env, home=self.home), second)
        self.assertEqual(first.read_text(), "[Wiimote1]\nSource = 2\n")

    def test_no_existing_config_refuses_creation(self):
        with self.assertRaisesRegex(ControllerConfigError, "Could not locate"):
            ensure_emulated_controller(
                self.exe, environ={"APPDATA": str(self.roaming)}, home=self.home
            )
        self.assertFalse((self.roaming / "Dolphin Emulator").exists())

    def test_preserve_bom_comments_and_inline_comment(self):
        ini = self.ini(self.base / "user", "[Wiimote1]\nSource = 2 ; connected real\nExtension = Nunchuk\n")
        ini.write_bytes(b"\xef\xbb\xbf" + ini.read_bytes())
        ensure_emulated_controller(self.exe, user_dir=ini.parent.parent)
        new = ini.read_bytes()
        self.assertTrue(new.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"Source = 1 ; connected real", new)
        self.assertIn(b"Extension = None", new)


if __name__ == "__main__":
    unittest.main()
