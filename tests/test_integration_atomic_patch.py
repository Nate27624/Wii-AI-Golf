import ast
import unittest

from wii_ai_golf.integration.atomic_patch import (
    _ATOMIC_SNIPPET, PATCH_MARKER, UnsupportedBridgeVersion, git_blob_sha, patch_bridge,
)


class FakeController:
    def __init__(self, ns):
        self.ns = ns
        self.records = []
    def set_wiimote_buttons(self, port, buttons):
        self.records.append((self.ns["_frame_count"], "buttons", port, buttons))
    def set_wiimote_acceleration(self, port, x, y, z):
        self.records.append((self.ns["_frame_count"], "accel", port, (x, y, z)))


class AtomicPatchTests(unittest.TestCase):
    def setUp(self):
        self.ns = {"_frame_count": 100}
        self.ctrl = FakeController(self.ns)
        self.ns["controller"] = self.ctrl
        exec(_ATOMIC_SNIPPET, self.ns)

    def advance(self):
        self.ns["_frame_count"] += 1
        self.ns["_wii_ai_tick"]()

    def test_atomic_same_frame_and_final_release(self):
        start = self.ns["_wii_ai_submit"]([0, [[True, 0, 1, 0], [True, 0, 2, 0], [False, 0, 1, 0]]])
        self.assertEqual(start["start_frame"], 101)
        self.assertEqual(self.ns["_wii_ai_status"]([])["state"], "scheduled")
        for _ in range(4):
            self.advance()
        status = self.ns["_wii_ai_status"]([])
        self.assertEqual(status["state"], "complete")
        self.assertEqual(status["applied_frames"], 3)
        records = self.ctrl.records
        self.assertEqual(len(records), 7)
        for i in range(3):
            self.assertEqual(records[2*i][0], records[2*i+1][0])
            self.assertEqual(records[2*i][1:3], ("buttons", 0))
            self.assertEqual(records[2*i+1][1:3], ("accel", 0))
        self.assertEqual(records[-1][-1], {"A": False})

    def test_aborts_and_rejects_concurrent_trace(self):
        self.ns["_wii_ai_submit"]([0, [[True, 0, 1, 0]]])
        with self.assertRaises(RuntimeError):
            self.ns["_wii_ai_submit"]([0, [[True, 0, 1, 0]]])
        self.assertEqual(self.ns["_wii_ai_abort"]([])["state"], "aborted")
        self.assertEqual(self.ctrl.records[-1][-1], {"A": False})
        self.assertEqual(self.ns["_wii_ai_submit"]([0, [[False, 0, 0, 1]]])["state"], "scheduled")

    def test_reject_invalid_values(self):
        invalid = [[], [[True, float("nan"), 1, 0]], [[1, 0, 0, 0]], [[True, 20, 0, 0]],
                   [[True, 0, 1]], [[True, "abc", 0, 0]]]
        for bad in invalid:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.ns["_wii_ai_submit"]([0, bad])
        self.assertEqual(self.ns["_wii_ai_status"]([])["state"], "idle")

    def test_fail_closed_for_other_upstream(self):
        with self.assertRaisesRegex(UnsupportedBridgeVersion, "SHA mismatch"):
            patch_bridge("HANDLERS = {}")

    def test_patcher_only_changes_expected_anchors(self):
        fixture = ('HANDLERS = {\n    "frame.get_count":                _frame_get_count,\n}\n'
                   'while True:\n    await event.frameadvance()\n    _frame_count += 1\n    _poll_sockets()\n')
        result = patch_bridge(fixture, expected_sha=git_blob_sha(fixture))
        self.assertIn(PATCH_MARKER, result)
        self.assertIn('"trace.submit": _wii_ai_submit', result)
        self.assertIn("    _wii_ai_tick()", result)
        compile(result, "patched_bridge.py", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


if __name__ == "__main__":
    unittest.main()
