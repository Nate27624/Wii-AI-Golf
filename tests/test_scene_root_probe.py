"""Synthetic, read-only scene-root checks; zero actual Dolphin or ROM access."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import probe_golf_scene_root as scene


class FakeRPC:
    def __init__(self, *, revision=1, mode=4, scene_id=5, relocate=False):
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
            scene.ROOT_STORAGE_CELLS[1]: 0,
            manager + scene.CURRENT_SCENE_ID_OFFSET: self.scene_id,
            manager + scene.CURRENT_SCENE_OFFSET: scene_ptr,
            scene_ptr: scene.GOLF_SCENE_DATA_START + 0x18,
            scene_ptr + scene.POSSIBLE_GOLF_MAIN_OFFSET: 0x90040000,
        }
        if address not in values:
            raise AssertionError("Unexpected RAM address requested")
        return values[address]


class SceneRootTests(unittest.TestCase):
    def test_known_golf_candidate_is_stable_but_not_type_verified(self):
        rpc = FakeRPC()
        result = scene.probe(rpc)
        self.assertEqual(result["stable_slot_indices"], [0])
        self.assertEqual(result["candidate_static_cells_checked"], 2)
        self.assertEqual(result["possible_main_pointer_ram_like_count"], 1)
        self.assertEqual(result["vtable_in_golf_scene_data_count"], 1)
        self.assertFalse(result["confirmed_manager_singleton_address"])
        self.assertFalse(result["confirmed_golf_power_address"])
        self.assertNotIn("90020000", json.dumps(result))
        self.assertNotIn("90030000", json.dumps(result))
        self.assertNotIn("90040000", json.dumps(result))
        self.assertTrue(all(method in ("frame.get_count", "memory.read_bytes",
                                       "memory.read_u32") for method, _ in rpc.calls))

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
