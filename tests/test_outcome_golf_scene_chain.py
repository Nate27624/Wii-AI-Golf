"""Synthetic RPC-only S002 tests for read-only Rev1 golf scene chain gates."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "scene_chain", ROOT / "src/wii_ai_golf/audit/golf_scene_chain.py")
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)

CONFIG = 0x80100000
MANAGER = 0x80120000
SCENE = 0x80140000
CANDIDATE = 0x80160000


class SyntheticRPC:
    def __init__(self):
        self.calls = []
        self.header = b"RSPE01\x00\x01"
        self.frame = 120
        self.increment = 1
        self.words = {
            chain.GOLF_CONFIG_STATIC_SLOT: CONFIG,
            CONFIG + chain.GAME_MODE_OFFSET: 4,
            chain.SCENE_MANAGER_STATIC_SLOT: MANAGER,
            MANAGER + chain.CURRENT_SCENE_ID_OFFSET: 5,
            MANAGER + chain.CURRENT_SCENE_OFFSET: SCENE,
            SCENE + chain.MAIN_CANDIDATE_OFFSET: CANDIDATE,
        }

    def call(self, method, params):
        self.calls.append((method, tuple(params)))
        if method == "frame.get_count":
            value = self.frame
            self.frame += self.increment
            return value
        if method == "memory.read_bytes":
            if params != [chain.HEADER_ADDRESS, chain.HEADER_BYTES]:
                raise AssertionError("unexpected read bytes location")
            return self.header.hex()
        if method == "memory.read_u32":
            return self.words[params[0]]
        raise AssertionError("unexpected RPC method")


class SceneChainTests(unittest.TestCase):
    def test_success_is_still_not_claimed_rpgolmain_or_ball(self):
        rpc = SyntheticRPC()
        result = chain.observe_golf_scene_chain(rpc)
        self.assertEqual(result["sample_count"], 3)
        self.assertTrue(result["scene_pointer_stable"])
        self.assertTrue(result["manager_pointer_stable"])
        self.assertEqual(result["candidate_pointer_like_count"], 3)
        for key in ("candidate_type_verified", "golf_main_verified",
                    "club_pose_verified", "swing_power_verified",
                    "ball_coordinates_verified", "score_verified"):
            self.assertFalse(result[key])
        self.assertNotIn(f"0x{MANAGER:08X}", str(result))
        self.assertNotIn(f"0x{SCENE:08X}", str(result))
        self.assertNotIn(f"0x{CANDIDATE:08X}", str(result))
        self.assertTrue(all(method in ("frame.get_count", "memory.read_bytes",
                                       "memory.read_u32")
                            for method, _ in rpc.calls))
        self.assertNotIn(("memory.read_u32", (CANDIDATE,)), rpc.calls)

    def test_wrong_revision_fails_before_gameplay_read(self):
        rpc = SyntheticRPC()
        rpc.header = b"RSPE01\x00\x00"
        with self.assertRaisesRegex(chain.SceneChainGateError, "Rev1"):
            chain.observe_golf_scene_chain(rpc)
        self.assertFalse(any(chain.SCENE_MANAGER_STATIC_SLOT in params
                             for _, params in rpc.calls))

    def test_wrong_training_mode_fails_before_manager(self):
        rpc = SyntheticRPC()
        rpc.words[CONFIG + chain.GAME_MODE_OFFSET] = 3
        with self.assertRaisesRegex(chain.SceneChainGateError, "mode 4"):
            chain.observe_golf_scene_chain(rpc)
        self.assertFalse(any(chain.SCENE_MANAGER_STATIC_SLOT in params
                             for _, params in rpc.calls))

    def test_wrong_scene_id_does_not_read_scene_field(self):
        rpc = SyntheticRPC()
        rpc.words[MANAGER + chain.CURRENT_SCENE_ID_OFFSET] = 4
        with self.assertRaisesRegex(chain.SceneChainGateError, "Golf scene ID 5"):
            chain.observe_golf_scene_chain(rpc)
        self.assertNotIn(("memory.read_u32", (SCENE + 0x9C,)), rpc.calls)

    def test_missing_manager_fails_closed(self):
        rpc = SyntheticRPC()
        rpc.words[chain.SCENE_MANAGER_STATIC_SLOT] = 0
        with self.assertRaisesRegex(chain.SceneChainGateError, "scene manager"):
            chain.observe_golf_scene_chain(rpc)

    def test_bad_scene_pointer_fails_before_candidate_read(self):
        rpc = SyntheticRPC()
        rpc.words[MANAGER + chain.CURRENT_SCENE_OFFSET] = 0
        with self.assertRaisesRegex(chain.SceneChainGateError, "active golf scene"):
            chain.observe_golf_scene_chain(rpc)
        self.assertNotIn(("memory.read_u32", (SCENE + 0x9C,)), rpc.calls)

    def test_scene_changes_during_snapshot_fails(self):
        rpc = SyntheticRPC()
        count = [0]
        original = rpc.call
        def changing_call(method, params):
            if method == "memory.read_u32" and params == [chain.SCENE_MANAGER_STATIC_SLOT]:
                count[0] += 1
                if count[0] == 2:
                    return MANAGER + 0x100
            return original(method, params)
        rpc.call = changing_call
        with self.assertRaisesRegex(chain.SceneChainGateError, "changed during"):
            chain.observe_golf_scene_chain(rpc)

    def test_manager_changes_between_samples_fails(self):
        rpc = SyntheticRPC()
        count = [0]
        original = rpc.call
        def changing_call(method, params):
            if method == "memory.read_u32" and params == [chain.SCENE_MANAGER_STATIC_SLOT]:
                count[0] += 1
                if count[0] >= 3:
                    return MANAGER + 0x100
            if method == "memory.read_u32" and params == [MANAGER + 0x100 + chain.CURRENT_SCENE_ID_OFFSET]:
                return 5
            if method == "memory.read_u32" and params == [MANAGER + 0x100 + chain.CURRENT_SCENE_OFFSET]:
                return SCENE
            return original(method, params)
        rpc.call = changing_call
        with self.assertRaisesRegex(chain.SceneChainGateError, "between snapshots"):
            chain.observe_golf_scene_chain(rpc, samples=2)

    def test_frame_span_bound_fails_closed(self):
        rpc = SyntheticRPC()
        rpc.increment = 30
        with self.assertRaisesRegex(chain.SceneChainGateError, "frame-span"):
            chain.observe_golf_scene_chain(rpc, max_frame_span=12)

    def test_invalid_rpc_values_and_rpc_error_redacted(self):
        rpc = SyntheticRPC()
        rpc.words[chain.SCENE_MANAGER_STATIC_SLOT] = True
        with self.assertRaisesRegex(chain.SceneChainGateError, "u32"):
            chain.observe_golf_scene_chain(rpc)
        rpc = SyntheticRPC()
        def throwing_call(method, params):
            raise RuntimeError("private 0x80123456 RAM bytes")
        rpc.call = throwing_call
        with self.assertRaises(chain.SceneChainGateError) as ctx:
            chain.observe_golf_scene_chain(rpc)
        self.assertNotIn("0x80123456", str(ctx.exception))

    def test_unmapped_candidate_not_followed_or_typed(self):
        rpc = SyntheticRPC()
        rpc.words[SCENE + chain.MAIN_CANDIDATE_OFFSET] = 0
        result = chain.observe_golf_scene_chain(rpc, samples=2)
        self.assertEqual(result["candidate_pointer_like_count"], 0)
        self.assertFalse(result["golf_main_verified"])

    def test_operator_parameters_are_bounded(self):
        rpc = SyntheticRPC()
        for value in (0, 1, 6, True, 2.5):
            with self.subTest(samples=value), self.assertRaises(ValueError):
                chain.observe_golf_scene_chain(rpc, samples=value)
        self.assertEqual(rpc.calls, [])


if __name__ == "__main__":
    unittest.main()
