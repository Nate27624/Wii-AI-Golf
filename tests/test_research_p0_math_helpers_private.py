"""Synthetic-only decoder/bounds tests; no Wii ROM, RAM, or Dolphin required."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "scripts" / "research_p0_math_helpers_private.py"
spec = importlib.util.spec_from_file_location("research_p0_math_helpers_private", FILE)
assert spec is not None and spec.loader is not None
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ResearchMathHelperTests(unittest.TestCase):
    def test_source_window_partition(self):
        windows = list(helper.SEGMENTS.values())
        self.assertEqual(windows[0][0], 0x802A3CF4)
        self.assertEqual(windows[-1][1], helper.SOURCE_UNIT[1])
        self.assertEqual(windows, sorted(windows))
        for idx, (lo, hi) in enumerate(windows):
            self.assertTrue(helper.SOURCE_UNIT[0] <= lo < hi <= helper.SOURCE_UNIT[1])
            self.assertEqual((hi - lo) // 4, 20)
            if idx + 1 < len(windows):
                self.assertEqual(hi, windows[idx + 1][0])

    def test_branch_calls_are_exact(self):
        for pc, dest in helper.CALLS.values():
            word = (18 << 26) | ((dest - pc) & 0x03FFFFFC) | 1
            self.assertEqual(helper.decode_bl(pc, word), (dest, True))
            self.assertIsNone(helper.decode_bl(pc, 0))

    def test_floating_registers_not_raw_words(self):
        word = ((59 << 26) | (2 << 21) | (3 << 16) |
                (4 << 11) | (5 << 6) | (29 << 1))
        row = helper.symbolize(helper.SOURCE_UNIT[0], word)
        self.assertEqual(row["class"], "fmadds")
        self.assertEqual((row["fra"], row["frb"], row["frc"]), (3, 4, 5))
        self.assertNotIn("raw", row)
        self.assertNotIn("word", row)

    def test_rejects_outside_public_unit(self):
        for pc in (helper.SOURCE_UNIT[0] - 4, helper.SOURCE_UNIT[1]):
            with self.assertRaises(helper.Abstain):
                helper.symbolize(pc, 0)


if __name__ == "__main__":
    unittest.main()
