"""Offline symbolic scene lookup must never mistake functions for instances."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scene_symbols", ROOT/"scripts"/"audit_golf_scene_symbols.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def load_fetch_module():
    spec = importlib.util.spec_from_file_location(
        "fetch_scene_symbols", ROOT / "scripts" / "fetch_golf_symbol_map.py")
    fetched = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetched)
    return fetched


class SceneSymbolTests(unittest.TestCase):
    def test_bundled_subset_can_be_scanned_without_network(self):
        self.assertTrue(mod.DEFAULT_MAP.is_file())
        with mod.DEFAULT_MAP.open(encoding="utf-8") as handle:
            report = mod.summarize(handle)
        groups = [r["symbol_group"] for r in report["matched_groups"]]
        self.assertIn("RPSysSceneMgr", groups)
        self.assertNotIn("RPSysScene", groups)
        self.assertIsNone(report["scene_object_pointer"])

    def test_optional_download_uses_pinned_source_and_cache(self):
        fetcher = load_fetch_module()
        self.assertIn(fetcher.UPSTREAM_COMMIT, fetcher.upstream_url("csv"))
        self.assertTrue(str(fetcher.DEFAULT_CACHE).endswith("Wii-AI-Golf-Data" + str(Path("/symbols"))))
        with tempfile.TemporaryDirectory() as td:
            class Response:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, n):
                    return b'"RPSysSceneMgr::getCurrentScene", 0x80186100\\n'

            with patch.object(fetcher, "urlopen", return_value=Response()) as mock:
                target = fetcher.fetch("csv", Path(td))
                self.assertEqual(target.name, "RSPE_r1.map.csv")
                self.assertTrue(target.is_file())
                mock.assert_called_once()
                with self.assertRaises(FileExistsError):
                    fetcher.fetch("csv", Path(td))
                mock.assert_called_once()

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
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(mod.main(["--map",str(Path(td)/"absent.map")]),1)

    def test_map_cli(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"RSPE_r1.map"
            f.write_text("8028DFA8 RPGolScene::OnCalculate\n",encoding="utf-8")
            self.assertEqual(mod.main(["--map",str(f)]),0)

if __name__=="__main__":
    unittest.main()
