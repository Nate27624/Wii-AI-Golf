"""Synthetic fixed source-window and lightweight PPC decoder checks."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import audit_golf_aim_ppc_context_private as ctx
import audit_golf_aim_ppc_offsets_private as scan


def dform(op, reg, base, disp):
    return (op << 26) | (reg << 21) | (base << 16) | (disp & 0xFFFF)


def mr(dst, src):
    return (31 << 26) | (src << 21) | (dst << 16) | (src << 11) | (444 << 1)


class SourceContextTests(unittest.TestCase):
    def test_dform_instruction_annotator(self):
        pc = ctx.SPANS[0][1]
        self.assertEqual(ctx.decode(dform(52, 3, 29, 0x3C), pc),
                         "stfs f3, +0x3c(r29)")
        self.assertEqual(ctx.decode(dform(48, 0, 30, 0x40), pc),
                         "lfs f0, +0x40(r30)")
        self.assertEqual(ctx.decode(dform(36, 4, 1, 0x44), pc),
                         "stw r4, +0x44(r1)")
        self.assertEqual(ctx.decode(mr(29, 3), pc), "mr r29,r3")
        self.assertEqual(ctx.decode(dform(14, 30, 30, -0x44), pc),
                         "addi r30,r30,-0x44")

    def test_each_region_source_bounded_and_compact(self):
        for _name, start, end in ctx.ALL_SPANS:
            self.assertTrue(
                (scan.PLAYER_CODE_START <= start < end <= scan.PLAYER_CODE_END)
                or (ctx.MATH_START <= start < end <= ctx.MATH_END)
            )
            self.assertEqual((start | end) & 3, 0)
            self.assertLessEqual(end - start, 128)
        self.assertTrue(any(start <= 0x802A3894 < end
                            for _, start, end in ctx.MATH_HELPER_SPANS))

    def test_static_context_reads_only_fixed_boundaries(self):
        addresses = []
        def fake(pc):
            addresses.append(pc)
            if pc == 0x8029ED9C:
                return dform(52, 1, 3, 0x3C)
            return 0
        out = ctx.describe(fake)
        self.assertEqual(len(out), len(ctx.ALL_SPANS))
        self.assertIn("* 0x8029ED9C", out[0]["text"])
        self.assertIn("stfs f1, +0x3c(r3)", out[0]["text"])
        self.assertEqual(len(addresses), sum((end-start)//4
                                           for _, start, end in ctx.ALL_SPANS))
        self.assertEqual(addresses[0], ctx.SPANS[0][1])

    def test_malformed_instruction_refused(self):
        with self.assertRaises(ValueError):
            ctx.describe(lambda _pc: -1)
        with self.assertRaises(ValueError):
            ctx.describe(lambda _pc: "bad")
        with self.assertRaises(ValueError):
            ctx.describe(lambda _pc: 1 << 32)

    def test_math_helper_and_extra_receiver_spans_tested(self):
        hits = []
        out = ctx.describe(lambda pc: hits.append(pc) or 0)
        self.assertEqual(len(out), len(ctx.ALL_SPANS))
        self.assertIn(0x802A3894, hits)
        self.assertIn(0x8029ED00, hits)
        self.assertEqual(ctx.decode(dform(7, 3, 31, 4), ctx.SPANS[0][1]),
                         "mulli r3,r31,4")
        self.assertEqual(ctx.decode(dform(37, 1, 1, -0x80), ctx.SPANS[0][1]),
                         "stwu r1,-0x80(r1)")

    def test_branch_target_decode(self):
        pc = ctx.SPANS[0][1]
        # b +8
        b = (18 << 26) | 8
        self.assertEqual(ctx.decode(b, pc), f"b 0x{pc+8:08X}")
        bl = (18 << 26) | 9
        self.assertEqual(ctx.decode(bl, pc), f"bl 0x{pc+8:08X}")


if __name__ == "__main__":
    unittest.main()
