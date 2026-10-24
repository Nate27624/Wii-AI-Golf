import ast
import unittest

from wii_ai_golf.integration.atomic_patch import _ATOMIC_SNIPPET, git_blob_sha, patch_bridge
from wii_ai_golf.integration.swing_patch import (
    _SWING_HANDLER, SWING_MARKER, SWING_NEUTRAL_V2_MARKER,
    SwingExtensionError, extend_atomic_bridge_with_swing,
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
        self.assertEqual([x[1] for x in calls],
                         ["buttons", "swing", "buttons", "swing", "buttons", "buttons"])
        for i in (0, 2):
            self.assertEqual(calls[i][0], calls[i+1][0])
        self.assertEqual(self.ns["_wii_ai_status"]([])["applied_frames"], 3)
        self.assertEqual(self.ns["_wii_ai_status"]([])["state"], "complete")
        self.assertEqual(calls[-1][-1], {"A": False})

    def test_v2_capability_advertised_read_only(self):
        before = list(self.ns["controller"].calls)
        self.assertEqual(self.ns["_wii_ai_swing_capabilities"]([]),
                         {"swing_protocol": 2, "neutral_button_only": True,
                          "method": "trace.submit_swing", "button_first": True})
        self.assertEqual(before, self.ns["controller"].calls)
        self.assertIn('"trace.swing_capabilities": _wii_ai_swing_capabilities', self.patched)
        self.assertIn(SWING_NEUTRAL_V2_MARKER, self.patched)

    def test_neutral_preparation_and_long_followthrough_call_buttons_only(self):
        # 12 neutral A-held, 15 back, 20 forward, 90 neutral A-held,
        # 12 released = 149; only 35 physical motion calls allowed.
        neutral = [True, 0, 0, 0, 0, 0, 0, 0]
        back = [True, 0, -1, 0, .25, 1.2, 1.2, 0]
        forward = [True, 0, 1, 0, .6, 3.5, 2, 0]
        released = [False, 0, 0, 0, 0, 0, 0, 0]
        samples = ([neutral] * 12 + [back] * 15 + [forward] * 20 +
                   [neutral] * 90 + [released] * 12)
        response = self.ns["_wii_ai_submit_swing"]([0, samples])
        self.assertEqual(response["swing_protocol"], 2)
        for _ in range(len(samples) + 1):
            self.advance()
        calls = self.ns["controller"].calls
        buttons = [x for x in calls if x[1] == "buttons"]
        swing = [x for x in calls if x[1] == "swing"]
        self.assertEqual(len(buttons), 150)
        self.assertEqual(len(swing), 35)
        self.assertEqual([x[-1]["A"] for x in buttons[:137]], [True] * 137)
        self.assertEqual([x[-1]["A"] for x in buttons[137:]], [False] * 13)
        self.assertTrue(all(x[0] in range(113, 148) for x in swing))
        self.assertEqual(self.ns["_wii_ai_status"]([])["state"], "complete")
        self.assertEqual(self.ns["_wii_ai_status"]([])["applied_frames"], 149)

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
