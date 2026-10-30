"""Headless synthetic tests for explicit private OBJ inspector startup."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
LAUNCHER = ROOT / "scripts" / "p0_memory_inspector.py"
spec = importlib.util.spec_from_file_location("_p0_terrain_launcher", LAUNCHER)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

from wii_ai_golf.inspector.gui import Inspector
from wii_ai_golf.inspector.terrain import TerrainMesh

GOOD = "v 0 0 0\nv 2 0 0\nv 0 0 2\nf 1 2 3\n"


class TerrainLaunchTests(unittest.TestCase):
    def test_cli_forwards_explicit_project_obj_to_inspector(self):
        from wii_ai_golf.inspector import gui
        with patch.object(gui, "launch", return_value=0) as run:
            result = launcher.main(["--terrain-obj", "private.obj"])
        self.assertEqual(result, 0)
        run.assert_called_once_with("", "", "private.obj")

    def test_cli_without_obj_preserves_previous_default(self):
        from wii_ai_golf.inspector import gui
        with patch.object(gui, "launch", return_value=0) as run:
            self.assertEqual(launcher.main([]), 0)
        run.assert_called_once_with("", "", "")

    def test_headless_path_load_sets_visible_mesh(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private.obj"
            path.write_text(GOOD, encoding="ascii")
            ui = SimpleNamespace(
                terrain_mesh=None, terrain_status=Mock(),
                terrain_visible=Mock(), draw_path=Mock(),
            )
            ok = Inspector.load_terrain_path(ui, str(path), show_dialog=False)
            self.assertTrue(ok)
            self.assertIsInstance(ui.terrain_mesh, TerrainMesh)
            self.assertEqual(len(ui.terrain_mesh.faces), 1)
            ui.terrain_visible.set.assert_called_once_with(True)
            ui.draw_path.assert_called_once_with()

    def test_headless_invalid_path_fails_without_dialog(self):
        ui = SimpleNamespace(
            terrain_mesh=None, terrain_status=Mock(),
            terrain_visible=Mock(), draw_path=Mock(),
        )
        with patch("wii_ai_golf.inspector.gui.messagebox.showerror") as dialog:
            ok = Inspector.load_terrain_path(
                ui, "not-a-file-PRIVATE.obj", show_dialog=False)
        self.assertFalse(ok)
        dialog.assert_not_called()
        ui.draw_path.assert_not_called()
        self.assertIsNone(ui.terrain_mesh)


if __name__ == "__main__":
    unittest.main()
