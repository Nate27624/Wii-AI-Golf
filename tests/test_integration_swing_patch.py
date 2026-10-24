import ast
import unittest

from wii_ai_golf.integration.atomic_patch import _ATOMIC_SNIPPET, git_blob_sha, patch_bridge
from wii_ai_golf.integration.swing_patch import (
    _SWING_HANDLER, SWING_MARKER, SwingExtensionError, extend_atomic_bridge_with_swing,
)


FIXTURE = ('HANDLERS = {\n    "frame.get_count":                _frame_get_count,\n}\n'
           'while True:\n    await event.frameadvance()\n    _frame_count += 1\n    _poll_sockets()\n')


class FakeController:
    def __init__(self, ns):
        self.ns = ns
        self.calls = []

    def set_wiimote_buttons(self, port, buttons):
        self.calls.append((self.ns["_frame_count"], "buttons", port, buttons))

    def set_wiimote_acceleration(self, port, x, y, z):
        self.calls.append((self.ns["_frame_count"], "accel", port, (x, y, z)))

    def set_wiimote_swing(self, port, *params):
        self.calls.append((self.ns["_frame_count"], "swing", port, params))


class SwingPatchTests(unittest.TestCase):
    def setUp(self):
        self.ns = {"_frame_count": 100}
        self.ns["controller"] = FakeController(self.ns)
        exec(_ATOMIC_SNIPPET + _SWING_HANDLER, self.ns)
        base = patch_bridge(FIXTURE, expected_sha=git_blob_sha(FIXTURE))
        self.patched = extend_atomic_bridge_with_swing(base)
        code = compile(self.patched, "patched.py", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        self.assertIsNotNone(code)
        tree = ast.parse(self.patched)
        tick = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_wii_ai_tick")
        exec(compile(ast.Module(body=[tick], type_ignores=[]), "patched_tick.py", "exec"), self.ns)

    def advance(self):
        self.ns["_frame_count"] += 1
        self.ns["_wii_ai_tick"]()

    def test_swing_uses_same_frame_A_and_motion_then_releases(self):
        s = [[True, 0, 1, 0, .3, 3, 1, 0],
             [True, 0, -1, 0, .3, 3, 1, 0],
             [False, 0, 0, 0, 0, 0, 0, 0]]
        response = self.ns["_wii_ai_submit_swing"]([0, s])
        self.assertEqual(response["kind"], "swing")
        for _ in range(4):
            self.advance()
        calls = self.ns["controller"].calls
        self.assertEqual([x[1] for x in calls], ["buttons", "swing"] * 3 + ["buttons"])
        for i in range(3):
            self.assertEqual(calls[2*i][0], calls[2*i+1][0])
        self.assertEqual(self.ns["_wii_ai_status"]([])["applied_frames"], 3)
        self.assertEqual(self.ns["_wii_ai_status"]([])["state"], "complete")
        self.assertEqual(calls[-1][-1], {"A": False})

    def test_existing_accel_path_still_works(self):
        self.ns["_wii_ai_submit"]([0, [[True, 0, 1, 0]]])
        for _ in range(2):
            self.advance()
        self.assertIn("accel", [x[1] for x in self.ns["controller"].calls])
        self.assertNotIn("swing", [x[1] for x in self.ns["controller"].calls])

    def test_rejects_concurrent_and_malformed_swing(self):
        invalid = [[True, 0, 1, 0, float("nan"), 2, 1, 0], [True, 2, 0, 0, .3, 2, 1, 0],
                   [True, 0, 1, 0, 3, 2, 1, 0], [True, 0, 1, 0], [1, 0, 1, 0, .3, 2, 1, 0]]
        for sample in invalid:
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                self.ns["_wii_ai_submit_swing"]([0, [sample]])
        self.ns["_wii_ai_submit_swing"]([0, [[True, 0, 1, 0, .3, 2, 1, 0]]])
        with self.assertRaises(RuntimeError):
            self.ns["_wii_ai_submit"]([0, [[True, 0, 1, 0]]])
        self.assertEqual(self.ns["_wii_ai_abort"]([])["state"], "aborted")

    def test_swing_unsupported_returns_error_and_releases_A(self):
        def broken_swing(*args):
            raise RuntimeError("unsupported by current emulator")
        self.ns["controller"].set_wiimote_swing = broken_swing
        self.ns["_wii_ai_submit_swing"]([0, [[True, 0, 1, 0, .3, 2, 1, 0]]])
        self.advance()
        status = self.ns["_wii_ai_status"]([])
        self.assertEqual(status["state"], "error")
        self.assertIn("unsupported", status["error"])
        self.assertEqual(self.ns["controller"].calls[-1][-1], {"A": False})
        self.assertIsNone(self.ns["_wii_ai_trace"])

    def test_patcher_guard(self):
        self.assertIn(SWING_MARKER, self.patched)
        with self.assertRaises(SwingExtensionError):
            extend_atomic_bridge_with_swing(self.patched)
        with self.assertRaises(SwingExtensionError):
            extend_atomic_bridge_with_swing(FIXTURE)


if __name__ == "__main__":
    unittest.main()
