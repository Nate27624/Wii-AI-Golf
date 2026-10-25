"""Synthetic, read-only scene-root checks; zero actual Dolphin or ROM access."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import probe_golf_scene_root as scene


class FakeRPC:
    def __init__(self, *, revision=1, mode=4, scene_id=5, relocate=False,
                 sport_id=2, vtable=None, two_slots=False,
                 own_scene_id=None, bad_backlink=False):
        self.own_scene_id = own_scene_id
        self.bad_backlink = bad_backlink
        self.sport_id = sport_id
        self.vtable = vtable
        self.two_slots = two_slots
        self.header = (b"RSPE01" + b"\0" + bytes([revision])).hex()
        self.mode = mode
        self.scene_id = scene_id
        self.relocate = relocate
        self.frames = 200
        self.passes = 0
        self.calls = []
        self.manager = 0x90020000
        self.scene = 0x90030000

    def call(self, method, args):
        self.calls.append((method, args))
        if method == "frame.get_count":
            self.frames += 1
            self.passes += 1
            return self.frames
        if method == "memory.read_bytes":
            if args != [0x80000000, 8]:
                raise AssertionError("Unexpected RAM read")
            return self.header
        if method != "memory.read_u32":
            raise AssertionError("Forbidden write or controller RPC: " + method)
        address = args[0]
        manager = self.manager + (0x1000 if self.relocate and self.passes > 2 else 0)
        scene_ptr = self.scene + (0x1000 if self.relocate and self.passes > 2 else 0)
        values = {
            scene.GOLF_CONFIG_STORAGE: 0x90010000,
            0x90010000 + scene.GOLF_MODE_OFFSET: self.mode,
            scene.ROOT_STORAGE_CELLS[0]: manager,
            scene.ROOT_STORAGE_CELLS[1]: manager if self.two_slots else 0,
            manager + scene.CURRENT_SCENE_ID_OFFSET: self.scene_id,
            manager + scene.CURRENT_SCENE_OFFSET: scene_ptr,
            scene_ptr: (scene.GOLF_SCENE_DATA_START + 0x18
                        if self.vtable is None else self.vtable),
            scene_ptr + scene.SCENE_SPORT_OFFSET: self.sport_id,
            scene_ptr + scene.SCENE_OWN_ID_OFFSET: (self.scene_id if self.own_scene_id is None
                                                    else self.own_scene_id),
            scene_ptr + scene.SCENE_MANAGER_BACKLINK_OFFSET: (
                manager + 0x100 if self.bad_backlink else manager),
            scene_ptr + scene.POSSIBLE_GOLF_MAIN_OFFSET: 0x90040000,
        }
        if address not in values:
            raise AssertionError("Unexpected RAM address requested")
        return values[address]


class SceneRootTests(unittest.TestCase):
    def test_main_local_sanitized_output_never_contains_pointer_values(self):
        class Context:
            def __enter__(self):
                return FakeRPC()
            def __exit__(self, typ, value, traceback):
                return False
        with tempfile.TemporaryDirectory() as tmp:
            outfile = Path(tmp) / "scene-summary.json"
            with patch.object(scene, "FelkRPC", return_value=Context()):
                self.assertEqual(scene.main(["--attach-running", "--no-upload",
                                             "--out", str(outfile)]), 0)
            data = json.loads(outfile.read_text(encoding="utf-8"))
            self.assertEqual(data["study_id"], "S002-GOLF-SCENE-ROOT-TRIAGE")
            self.assertEqual(data["stable_slot_indices"], [0])
            for value in ("90020000", "90030000", "90040000", "804BF4D8"):
                self.assertNotIn(value, outfile.read_text(encoding="utf-8"))

    def test_main_fails_without_explicit_attach_running(self):
        with patch.object(scene, "FelkRPC") as bridge:
            with self.assertRaises(SystemExit):
                scene.main([])
            bridge.assert_not_called()

    def test_known_golf_candidate_is_stable_but_not_type_verified(self):
        rpc = FakeRPC()
        result = scene.probe(rpc)
        self.assertEqual(result["stable_slot_indices"], [0])
        self.assertEqual(result["candidate_static_cells_checked"], 2)
        self.assertEqual(result["possible_main_pointer_ram_like_count"], 1)
        self.assertEqual(result["vtable_in_golf_scene_data_count"], 1)
        self.assertEqual(result["stable_sport_id_match_count"], 1)
        self.assertEqual(result["stable_scene_own_id_match_count"], 1)
        self.assertEqual(result["stable_manager_backlink_match_count"], 1)
        self.assertTrue(result["unique_stable_golf_scene_chain"])
        self.assertFalse(result["confirmed_manager_singleton_address"])
        self.assertFalse(result["confirmed_golf_power_address"])
        self.assertNotIn("90020000", json.dumps(result))
        self.assertNotIn("90030000", json.dumps(result))
        self.assertNotIn("90040000", json.dumps(result))
        self.assertTrue(all(method in ("frame.get_count", "memory.read_bytes",
                                       "memory.read_u32") for method, _ in rpc.calls))

    def test_wrong_golf_sport_cannot_promote_scene_or_read_main(self):
        rpc = FakeRPC(sport_id=1)
        result = scene.probe(rpc)
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)
        self.assertEqual(result["possible_main_pointer_ram_like_count"], 0)
        self.assertFalse(result["unique_stable_golf_scene_chain"])
        self.assertFalse(any(args == [rpc.scene + scene.POSSIBLE_GOLF_MAIN_OFFSET]
                             for name, args in rpc.calls
                             if name == "memory.read_u32"))

    def test_scene_vtable_outside_golf_data_cannot_read_main(self):
        rpc = FakeRPC(vtable=0x8028E030)  # executable FUNCTION address, not class vtable
        result = scene.probe(rpc)
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)
        self.assertFalse(any(args == [rpc.scene + scene.POSSIBLE_GOLF_MAIN_OFFSET]
                             for name, args in rpc.calls
                             if name == "memory.read_u32"))

    def test_stale_scene_own_id_blocks_scene_main_member(self):
        rpc = FakeRPC(own_scene_id=7)
        result = scene.probe(rpc)
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)
        self.assertFalse(result["unique_stable_golf_scene_chain"])
        self.assertFalse(any(args == [rpc.scene + scene.POSSIBLE_GOLF_MAIN_OFFSET]
                             for name, args in rpc.calls if name == "memory.read_u32"))

    def test_foreign_manager_backlink_blocks_scene_main_member(self):
        rpc = FakeRPC(bad_backlink=True)
        result = scene.probe(rpc)
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)
        self.assertFalse(any(args == [rpc.scene + scene.POSSIBLE_GOLF_MAIN_OFFSET]
                             for name, args in rpc.calls if name == "memory.read_u32"))

    def test_two_matching_root_cells_are_ambiguous_not_unique(self):
        rpc = FakeRPC(two_slots=True)
        result = scene.probe(rpc)
        self.assertEqual(result["stable_slot_indices"], [0, 1])
        self.assertEqual(result["stable_golf_scene_chain_count"], 2)
        self.assertFalse(result["unique_stable_golf_scene_chain"])
        self.assertFalse(result["confirmed_manager_singleton_address"])

    def test_source_gated_reads_remain_read_only(self):
        rpc = FakeRPC()
        scene.probe(rpc)
        self.assertTrue(all(name in ("frame.get_count", "memory.read_u32",
                                     "memory.read_bytes")
                            for name, _ in rpc.calls))
        self.assertFalse(any("controller." in name or "memory.write" in name
                             for name, _ in rpc.calls))

    def test_wrong_revision_fails_before_candidate_reads(self):
        rpc = FakeRPC(revision=0)
        with self.assertRaisesRegex(RuntimeError, "revision 1"):
            scene.probe(rpc)
        self.assertFalse(any(args == [scene.ROOT_STORAGE_CELLS[0]]
                             for _, args in rpc.calls))

    def test_wrong_game_mode_fails_before_candidate_reads(self):
        rpc = FakeRPC(mode=1)
        with self.assertRaisesRegex(RuntimeError, "mode 4"):
            scene.probe(rpc)
        self.assertFalse(any(args == [scene.ROOT_STORAGE_CELLS[0]]
                             for _, args in rpc.calls))

    def test_other_scene_does_not_claim_golf_chain(self):
        result = scene.probe(FakeRPC(scene_id=3))
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)
        self.assertEqual(result["possible_main_pointer_ram_like_count"], 0)

    def test_manager_relocation_rejects_apparent_stability(self):
        result = scene.probe(FakeRPC(relocate=True))
        self.assertEqual(result["stable_golf_scene_chain_count"], 0)

    def test_rejects_unbounded_snapshot_duration(self):
        class SlowRPC(FakeRPC):
            def call(self, method, args):
                if method == "frame.get_count":
                    self.frames += 100
                    self.passes += 1
                    return self.frames
                return super().call(method, args)
        with self.assertRaisesRegex(RuntimeError, "frame span"):
            scene.probe(SlowRPC())


if __name__ == "__main__":
    unittest.main()
