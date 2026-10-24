import ast
import unittest
from wii_ai_golf.integration.atomic_patch import (
    _BOOT_SNIPPET, BOOT_MARKER, git_blob_sha, patch_bridge,
)


class FakeSavestate:
    def __init__(self, raises=False):
        self.slots = []
        self.raises = raises
    def load_from_slot(self, slot):
        self.slots.append(slot)
        if self.raises:
            raise RuntimeError("Missing state")


class BootTests(unittest.TestCase):
    def test_one_shot_auto_load_at_first_tick(self):
        ns = {"savestate": FakeSavestate()}
        exec(_BOOT_SNIPPET.format(slot=36), ns)
        for _ in range(5):
            ns["_wii_ai_boot_tick"]()
        self.assertEqual(ns["savestate"].slots, [36])

    def test_boot_failure_does_not_repeat(self):
        ns = {"savestate": FakeSavestate(raises=True)}
        exec(_BOOT_SNIPPET.format(slot=20), ns)
        ns["_wii_ai_boot_tick"]()
        ns["_wii_ai_boot_tick"]()
        self.assertEqual(ns["savestate"].slots, [20])

    def test_boot_option_compiles_and_default_is_unmodified(self):
        fixture = ('HANDLERS = {\n    "frame.get_count":                _frame_get_count,\n}\n'
                   'while True:\n    await event.frameadvance()\n    _frame_count += 1\n    _poll_sockets()\n')
        normal = patch_bridge(fixture, expected_sha=git_blob_sha(fixture))
        self.assertNotIn(BOOT_MARKER, normal)
        patched = patch_bridge(fixture, expected_sha=git_blob_sha(fixture), startup_slot=20)
        self.assertIn(BOOT_MARKER, patched)
        self.assertIn('    _wii_ai_boot_tick()\n    _wii_ai_tick()', patched)
        compile(patched, "patched.py", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        for invalid in (-1, 100, True, "20"):
            with self.assertRaises(ValueError):
                patch_bridge(fixture, expected_sha=git_blob_sha(fixture), startup_slot=invalid)


if __name__ == "__main__":
    unittest.main()
