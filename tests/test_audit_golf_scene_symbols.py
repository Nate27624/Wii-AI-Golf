"""Offline symbolic scene lookup must never mistake functions for instances."""
import importlib.util
import json
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
        # The bundled data also includes two real RPSysScene methods and
        # two RPSysSceneCreator methods; neither belongs to the manager.
        self.assertIn("RPSysScene", groups)
        self.assertIn("RPSysSceneCreator", groups)
        counts = {r["symbol_group"]: r["matching_map_lines"]
                  for r in report["matched_groups"]}
        self.assertEqual(counts["RPSysSceneMgr"], 4)
        self.assertEqual(counts["RPSysScene"], 2)
        self.assertEqual(counts["RPSysSceneCreator"], 2)
        self.assertIsNone(report["scene_object_pointer"])

    def test_create_instance_function_is_not_a_static_pointer(self):
        result = mod.summarize([
            '"RPSysSceneCreator::createInstance", 0x80184e10',
            '"RPSysSceneMgr::getCurrentScene", 0x80186100',
        ])
        self.assertTrue(all(entry["classification"] == "symbol_location_only"
                            for entry in result["matched_groups"]))
        self.assertEqual({entry["symbol_group"] for entry in result["matched_groups"]},
                         {"RPSysSceneCreator", "RPSysSceneMgr"})
        self.assertIsNone(result["scene_object_pointer"])

    def test_exact_class_disambiguation_with_similar_prefixes(self):
        report = mod.summarize([
            '"RPSysScene::enter", 0x80185304',
            '"RPSysSceneMgr::getCurrentScene", 0x80186100',
            '"RPSysSceneCreator::createSportsScene", 0x80184000',
            '"RPSysSceneManagerFake::notReal", 0x80180000',
        ])
        counts = {e["symbol_group"]: e["matching_map_lines"]
                  for e in report["matched_groups"]}
        self.assertEqual(counts, {
            "RPSysScene": 1, "RPSysSceneMgr": 1, "RPSysSceneCreator": 1
        })
        self.assertIsNone(report["scene_object_pointer"])

    def test_source_anchored_layout_distinguishes_static_slot_from_runtime_pointer(self):
        layout = json.loads(mod.DEFAULT_LAYOUT.read_text(encoding="utf-8"))
        self.assertEqual(layout["region"], "RSPE01")
        self.assertEqual(layout["revision"], 1)
        mgr = layout["scene_manager"]
        self.assertEqual(mgr["current_scene_offset_hex"], "+0xC")
        self.assertEqual(mgr["current_scene_id_offset_hex"], "+0x18")
        self.assertEqual(mgr["current_scene_id_golf"], 5)
        # Public symbol maps do not name the singleton storage slot.
        # Independent, offline DOL instruction checks established a
        # *static storage location*, NOT its live pointer contents.
        self.assertIsNone(mgr["instance_storage_address"])
        self.assertEqual(
            mgr["instance_storage_status"],
            "no_public_symbol_map_storage_entry; see derived_static_storage_address",
        )
        self.assertEqual(mgr["derived_static_storage_address"], "0x804BF4D8")
        self.assertEqual(
            mgr["derived_static_storage_status"],
            "private_DOL_verified_signature_not_live_pointer_read",
        )
        self.assertIn("constructor load/store", mgr["derived_static_storage_evidence"])
        self.assertIsNone(mgr["runtime_instance_pointer"])
        golf = layout["golf_scene"]
        self.assertEqual(golf["main_member_offset_hex"], "+0x9C")
        self.assertIsNone(golf["scene_object_address"])
        self.assertIsNone(golf["golf_main_object_address"])

    def test_symbol_summary_never_promotes_a_runtime_pointer(self):
        summary = mod.summarize([
            '"RPSysSceneMgr::getCurrentScene", 0x80186100',
            '"RPGolScene::OnCalculate", 0x8028DFA8',
        ])
        self.assertEqual(summary["manager_current_scene_offset"], "+0xC")
        self.assertEqual(summary["manager_current_scene_id_offset"], "+0x18")
        self.assertEqual(summary["golf_scene_id"], 5)
        self.assertIsNone(summary["manager_singleton_storage_address"])
        self.assertIsNone(summary["scene_object_pointer"])
        self.assertIsNone(summary["golf_main_object_pointer"])

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
