"""Synthetic-only source-gated test for Rev1 three-unit effect source writers."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_golf_effect_source_writers_private as effect


def dform(op, source, base, offset):
    return (op << 26) | (source << 21) | (base << 16) | offset


def source_with_hits():
    unit_names = list(effect.TEXT_UNITS)
    field_start = effect.TEXT_UNITS[unit_names[0]][0]
    draw_start = effect.TEXT_UNITS[unit_names[1]][0]
    ball_start = effect.TEXT_UNITS[unit_names[2]][0]
    words = {
        field_start + 4: dform(36, 7, 3, 0x78),   # stw r7,+0x78(r3)
        field_start + 8: dform(32, 8, 4, 0x7C),   # lwz r8,+0x7C(r4)
        field_start + 12: dform(32, 5, 6, 0x94),  # lwz r5,+0x94(r6)
        draw_start + 8: dform(52, 1, 9, 0x7C),   # stfs f1,+0x7C(r9)
        draw_start + 12: dform(32, 3, 6, 0x98), # lwz r3,+0x98(r6)
        ball_start + 4: dform(36, 3, 29, 0x78), # stw r3,+0x78(r29)
        ball_start + 8: dform(36, 3, 29, 0x7C), # stw r3,+0x7C(r29)
        ball_start + 12: dform(32, 3, 31, 0x9C),
    }
    return words


class EffectWriterSourceTests(unittest.TestCase):
    def test_exact_source_units_and_no_field_ownership_claim(self):
        words = source_with_hits()
        result = effect.analyze(lambda pc: words.get(pc, 0))
        self.assertEqual(len(result["source_units"]), 3)
        self.assertEqual(result["total_dform_hits"], 8)
        self.assertFalse(result["effect_slot_field_078_07C_ownership_proven"])
        self.assertFalse(result["game_field_pointer_type_proven"])
        self.assertFalse(result["ball_world_xyz_verified"])
        self.assertFalse(result["approved_for_model_training"])
        a, b, c = result["source_units"]
        self.assertEqual(a["paired_field_write_count"], 1)
        self.assertEqual(a["paired_field_read_count"], 1)
        self.assertEqual(a["effect_pointer_offset_hits"], 1)
        self.assertEqual(b["paired_field_write_count"], 1)
        self.assertEqual(c["paired_field_write_count"], 2)
        self.assertEqual([x["text_bounds"] for x in result["source_units"]],
                         [[f"0x{start:08X}", f"0x{end:08X}"]
                          for start, end in effect.TEXT_UNITS.values()])
        self.assertEqual(a["literal_hits"][0]["base_register"], "r3")
        self.assertEqual(a["literal_hits"][0]["value_register"], "r7")
        self.assertEqual(b["literal_hits"][0]["value_register"], "f1")
        self.assertEqual(c["literal_hits"][0]["offset"], "+0x078")
        self.assertFalse(a["literal_hits"][0]["runtime_effect_receiver_proven"])

    def test_bad_opcode_and_sign_does_not_trigger_false_match(self):
        base = effect.TEXT_UNITS["RPGolFieldManager.cpp"][0]
        cases = [
            dform(36, 3, 4, 0x78),  # proper stw
            dform(32, 3, 4, 0x7C),  # proper lwz
            dform(52, 3, 4, 0x78),  # proper stfs
        ]
        for word in cases:
            self.assertIsNotNone(effect.inspect_source_word(word, base))
        for word in (dform(36,3,4,0x79),
                     dform(36,3,4,0xFF78),  # negative signed displacement
                     dform(14,3,4,0x78),   # arithmetic, not load/store
                     0xFFFFFFFF):
            self.assertIsNone(effect.inspect_source_word(word, base))
        for word in (None, -1, 2**32, "stw"):
            with self.assertRaises(ValueError):
                effect.inspect_source_word(word, base)

    def test_contexts_never_escape_each_linker_bound(self):
        words = {
            start: dform(36, 4, 3, 0x78)
            for start, end in effect.TEXT_UNITS.values()
        }
        result = effect.analyze(lambda pc: words.get(pc, 0))
        for unit in result["source_units"]:
            self.assertEqual(len(unit["selected_source_contexts"]), 1)
            ctx = unit["selected_source_contexts"][0]["nearby_static_code_only"]
            self.assertEqual(ctx[0]["pc"], unit["text_bounds"][0])
            self.assertTrue(all(
                int(unit["text_bounds"][0], 16) <= int(row["pc"],16)
                < int(unit["text_bounds"][1],16) for row in ctx))
            self.assertFalse(unit["receiver_base_register_traced"])

    def test_no_matches_is_an_acceptable_finding(self):
        x = effect.analyze(lambda _:0)
        self.assertEqual(x["total_dform_hits"],0)
        self.assertTrue(all(not y["literal_hits"] for y in x["source_units"]))

    def test_source_hit_burst_fails_closed(self):
        start=effect.TEXT_UNITS["RPGolFieldManager.cpp"][0]
        def read(pc):
            if start <= pc < start + 4*(effect.MAX_HITS_PER_UNIT+1):
                return dform(32,3,4,0x78)
            return 0
        with self.assertRaisesRegex(ValueError,"Too many"):
            effect.analyze(read)

if __name__ == "__main__":
    unittest.main()
