"""Fixed S002 action router and no arbitrary paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("s002_route",ROOT/"scripts"/"run_s002_lab_capture.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class S002LiveRouteTests(unittest.TestCase):
    def test_exact_actions_not_arbitrary_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp)/"sports.wbfs";game.write_bytes(b"synthetic not real game")
            with self.assertRaises(ValueError):mod.command("../../bad.py",game)
            with self.assertRaises(ValueError):mod.command("minimap_swing",Path(tmp)/"bad.exe")
    def test_missing_real_game_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.command("landmarks",Path("nonexistent.wbfs"))
if __name__=="__main__":unittest.main()
