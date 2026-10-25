"""S001 offline regression: WASD Wii pointer with no physical mouse input."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)

from wii_ai_golf.integration.dolphin_controller_config import (
    ControllerConfigError, _isolate_physical_mouse, ensure_emulated_controller,
)


class MouseIsolationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.exe = self.root / "Dolphin.exe"
        self.exe.write_bytes(b"")
        self.ini = self.root / "User" / "Config" / "WiimoteNew.ini"
        self.ini.parent.mkdir(parents=True)

    def prepare(self, data):
        self.ini.write_bytes(data.encode("utf-8"))
        return ensure_emulated_controller(self.exe, user_dir=self.ini.parent.parent)

    def test_mouse_pointer_clicks_and_shake_removed_without_wiimote2_edits(self):
        original = (
            "[Wiimote1]\r\nSource = 2\r\nExtension = Nunchuk\r\n"
            "Device = DInput/0/Keyboard Mouse\r\n"
            "Buttons/A = `Click 0`\r\nButtons/B = `Click 1`\r\n"
            "Shake/X = `Click 2`\r\nShake/Y = `Click 2`\r\n"
            "IR/Up = `Cursor Y-`\r\nIR/Down = `Cursor Y+`\r\n"
            "IR/Left = `Cursor X-`\r\nIR/Right = `Cursor X+`\r\n"
            "IR/Hide = `Middle Click`\r\nIMUIR/Enabled = True\r\n"
            "Buttons/1 = `1`\r\n"
            "[Wiimote2]\r\nIR/Up = `Cursor Y-`\r\nButtons/A = `Click 0`\r\n"
        )
        report = self.prepare(original)
        changed = self.ini.read_bytes().decode()
        self.assertTrue(report["changed"])
        self.assertTrue(report["mouse_pointer_bindings_disabled_in_ini"])
        self.assertIn("Source = 1\r\nExtension = None\r\n", changed)
        self.assertIn("Device = DInput/0/Keyboard Mouse\r\n", changed)
        for key in ("Buttons/A", "Buttons/B", "Shake/X", "Shake/Y", "IR/Hide"):
            self.assertIn(key + " = \r\n", changed)
        for key, control in (("IR/Up", "W"), ("IR/Down", "S"),
                             ("IR/Left", "A"), ("IR/Right", "D")):
            self.assertIn(key + " = " + control + "\r\n", changed)
        self.assertIn("IR/Relative Input = True\r\n", changed)
        self.assertIn("IR/Relative Input Hold = \r\n", changed)
        self.assertEqual(report["pointer_keys"],
                         {"IR/Up": "W", "IR/Down": "S", "IR/Left": "A", "IR/Right": "D"})
        self.assertTrue(report["pointer_relative_input"])
        self.assertIn("IMUIR/Enabled = False\r\n", changed)
        self.assertIn("Buttons/1 = `1`\r\n", changed)
        self.assertIn("[Wiimote2]\r\nIR/Up = `Cursor Y-`", changed)
        backup = Path(str(self.ini) + ".wii-ai-golf.original.bak")
        self.assertEqual(backup.read_bytes(), original.encode())
        self.assertFalse(ensure_emulated_controller(
            self.exe, user_dir=self.ini.parent.parent)["changed"])
        self.assertEqual(changed, self.ini.read_bytes().decode())

    def test_missing_ir_defaults_mapped_to_wasd_with_relative_input(self):
        self.prepare("[Wiimote1]\nSource=1\nExtension=None\nButtons/A = F\n")
        updated = self.ini.read_text()
        for key, control in (("IR/Up", "W"), ("IR/Down", "S"),
                             ("IR/Left", "A"), ("IR/Right", "D")):
            self.assertEqual(updated.count(key + " = " + control + "\n"), 1)
        self.assertIn("IR/Relative Input = True\n", updated)
        self.assertIn("IR/Relative Input Hold = \n", updated)
        self.assertIn("IMUIR/Enabled = False\n", updated)
        self.assertIn("Buttons/A = F\n", updated)

    def test_keyboard_inputs_on_combined_device_remain(self):
        self.prepare(
            "[Wiimote1]\nSource=1\nExtension=None\n"
            "Device = DInput/0/Keyboard Mouse\n"
            "Buttons/A = `DInput/0/Keyboard Mouse:F`\n"
            "Buttons/B = G\nTilt/Left = LEFT\n"
        )
        updated = self.ini.read_text()
        self.assertIn("Buttons/A = `DInput/0/Keyboard Mouse:F`\n", updated)
        self.assertIn("Buttons/B = G\n", updated)
        self.assertIn("Tilt/Left = LEFT\n", updated)

    def test_composite_mouse_expressions_removed_entirely(self):
        self.prepare(
            "[Wiimote1]\nSource=1\nExtension=None\n"
            "Buttons/A = if(`Click 0`,F,G)\n"
            "Swing/Forward = `Cursor Y+`\n"
        )
        updated = self.ini.read_text()
        self.assertIn("Buttons/A = \n", updated)
        self.assertIn("Swing/Forward = \n", updated)

    def test_duplicate_ir_fails_closed_before_backup(self):
        data = "[Wiimote1]\nSource=1\nExtension=None\nIR/Up = A\nir/up = B\n"
        self.ini.write_text(data)
        with self.assertRaisesRegex(ControllerConfigError, "Duplicate"):
            ensure_emulated_controller(self.exe, user_dir=self.ini.parent.parent)
        self.assertEqual(data, self.ini.read_text())
        self.assertFalse(Path(str(self.ini) + ".wii-ai-golf.original.bak").exists())

    def test_comments_other_sections_and_crlf_survive(self):
        original = (
            "# Preserved\r\n[Wiimote1]\r\nSource = 1\r\nExtension = None\r\n"
            "IR/Up = `Cursor Y-` ; pointer\r\n"
            "[Wiimote2]\r\nIR/Up = X\r\n"
        )
        updated, changed, _ = _isolate_physical_mouse(original)
        self.assertTrue(changed)
        self.assertIn("IR/Up = W ; pointer\r\n", updated)
        self.assertIn("IMUIR/Enabled = False\r\n", updated)
        self.assertIn("Shake/Z = \r\n[Wiimote2]", updated)
        self.assertIn("[Wiimote2]\r\nIR/Up = X\r\n", updated)

    def test_inserting_when_section_has_no_trailing_newline(self):
        updated, changed, _ = _isolate_physical_mouse(
            "[Wiimote1]\nSource=1\nExtension=None"
        )
        self.assertTrue(changed)
        self.assertIn("Extension=None\nIR/Up = W\n", updated)
        self.assertEqual(updated.count("IR/Down = S\n"), 1)

    def test_existing_relative_input_and_hold_get_appropriate_values(self):
        self.prepare(
            "[Wiimote1]\nSource=1\nExtension=None\n"
            "IR/Up = W\nIR/Down = S\nIR/Left = A\nIR/Right = D\n"
            "IR/Relative Input = False\nIR/Relative Input Hold = Q\n"
        )
        updated = self.ini.read_text()
        self.assertIn("IR/Relative Input = True\n", updated)
        self.assertIn("IR/Relative Input Hold = \n", updated)
        self.assertNotIn("IR/Relative Input = False", updated)
        self.assertFalse(ensure_emulated_controller(
            self.exe, user_dir=self.ini.parent.parent)["changed"])

    def test_wasd_key_collision_on_wii_button_fails_without_file_write(self):
        for binding in ("Buttons/A = A", "Buttons/B = `W`",
                        "Swing/Up = if(S,F,Q)", "IR/Hide = D"):
            with self.subTest(binding=binding):
                original = "[Wiimote1]\nSource=1\nExtension=None\n" + binding + "\n"
                self.ini.write_text(original)
                with self.assertRaisesRegex(ControllerConfigError, "WASD pointer"):
                    ensure_emulated_controller(
                        self.exe, user_dir=self.ini.parent.parent)
                self.assertEqual(self.ini.read_text(), original)

    def test_missing_default_click_and_shake_controls_explicitly_unbound(self):
        self.prepare(
            "[Wiimote1]\nSource=1\nExtension=None\n"
            "Buttons/1 = Q\n"
        )
        updated = self.ini.read_text()
        for key in ("Buttons/A", "Buttons/B", "Shake/X", "Shake/Y", "Shake/Z"):
            self.assertEqual(updated.count(key + " = \n"), 1)
        self.assertIn("Buttons/1 = Q\n", updated)
        self.assertFalse(ensure_emulated_controller(
            self.exe, user_dir=self.ini.parent.parent)["changed"])

    def test_non_keyboard_device_fails_without_overwriting_controller_config(self):
        original = "[Wiimote1]\nSource=1\nExtension=None\nDevice = XInput/0/Gamepad\n"
        self.ini.write_text(original)
        with self.assertRaisesRegex(ControllerConfigError, "Keyboard Mouse"):
            ensure_emulated_controller(self.exe, user_dir=self.ini.parent.parent)
        self.assertEqual(self.ini.read_text(), original)

    def test_existing_wasd_mapping_is_idempotent(self):
        original = ("[Wiimote1]\nSource = 1\nExtension = None\n"
                    "IR/Up = W\nIR/Down = S\nIR/Left = A\nIR/Right = D\n"
                    "IR/Relative Input = True\nIR/Relative Input Hold = \n"
                    "IMUIR/Enabled = False\n"
                    "Buttons/A = \nButtons/B = \n"
                    "Shake/X = \nShake/Y = \nShake/Z = \n")
        self.ini.write_text(original)
        report = ensure_emulated_controller(self.exe, user_dir=self.ini.parent.parent)
        self.assertFalse(report["changed"])
        self.assertEqual(self.ini.read_text(), original)


if __name__ == "__main__":
    unittest.main()
