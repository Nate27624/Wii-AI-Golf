"""Offline symbolic scene lookup must never mistake functions for instances."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scene_symbols", ROOT/"scripts"/"audit_golf_scene_symbols.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SceneSymbolTests(unittest.TestCase):
    def test_function_symbol_not_a_runtime_object(self):
        r=mod.summarize(["8028DFA8 00000004 RPGolScene::OnCalculate()"])
        self.assertIsNone(r["scene_object_pointer"])
        self.assertIsNone(r["golf_main_object_pointer"])
        self.assertEqual(r["matched_groups"][0]["classification"],"symbol_location_only")

    def test_candidate_static_name_still_not_verified(self):
        r=mod.summarize(["804BF000 RPGolScene::sInstance"])
        self.assertEqual(r["matched_groups"][0]["classification"],"candidate_static_data_symbol")
        self.assertIsNone(r["scene_object_pointer"])

    def test_other_classes_and_unrelated_symbols(self):
        r=mod.summarize(["8028DFA8 RPGolScene::OnCalculate", "80300000 Unrelated",
                         "80280000 RPSysSceneMgr::getCurrent"])
        self.assertEqual(len(r["matched_groups"]),2)
        self.assertNotIn("8028DFA8",str(r))

    def test_bad_input_rejected(self):
        self.assertEqual(mod.summarize([])["matched_groups"],[])
        with self.assertRaisesRegex(ValueError,"missing"):
            with tempfile.TemporaryDirectory() as td:
                mod.main(["--map",str(Path(td)/"absent.map")])

    def test_map_cli(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"RSPE_r1.map"
            f.write_text("8028DFA8 RPGolScene::OnCalculate\n",encoding="utf-8")
            self.assertEqual(mod.main(["--map",str(f)]),0)

if __name__=="__main__":
    unittest.main()
