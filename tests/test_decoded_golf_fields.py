"""Source-grounded struct field offsets: raw game data, not training scores."""
import struct
import unittest

from wii_ai_golf.decoded_golf_fields import (
    decode_documented_fields, summarize_documented_transitions,
)


def sample(mode="0x00000004", score=0, training=1):
    config = bytearray(0xC0)
    seq = bytearray(0xD0)
    field = bytearray(0xA8)
    struct.pack_into(">I", config, 0x94, 4)
    struct.pack_into(">I", config, 0x98, 1)
    struct.pack_into(">I", config, 0x04, score)
    struct.pack_into(">I", seq, 0x0C, training)
    struct.pack_into(">I", seq, 0x14, score)
    struct.pack_into(">I", field, 0x3C, 3)
    struct.pack_into(">I", field, 0x48, 10)
    return {
        "game_id": "RSPE01", "disc_revision": 1, "mode": mode,
        "windows": {
            "golf_config": {"bytes_hex": config.hex()},
            "sports_sequence": {"bytes_hex": seq.hex()},
            "golf_field": {"bytes_hex": field.hex()},
        },
    }


class DocumentedGolfFieldsTests(unittest.TestCase):
    def test_decoder_reads_only_documented_big_endian_fields(self):
        d = decode_documented_fields(sample(score=6))
        self.assertTrue(d["supported"])
        f = d["fields"]
        self.assertEqual(f["golf_config.golf_mode_raw"], 4)
        self.assertEqual(f["golf_config.current_course_hole_raw"], 1)
        self.assertEqual(f["sports_sequence.training_game_raw"], 1)
        self.assertEqual(f["golf_field.start_object_count_raw"], 10)
        self.assertEqual(f["golf_field.pin_object_count_raw"], 3)
        self.assertEqual(f["golf_config.standard_player_hole_scores_raw"][0][0], 6)
        self.assertEqual(f["sports_sequence.standard_golf_hole_scores_raw"][0][0], 6)
        self.assertIn("NOT decoded training score", d["warning"])

    def test_mode_and_revision_are_gated(self):
        self.assertFalse(decode_documented_fields(sample(mode="0x00000003"))["supported"])
        other = sample()
        other["disc_revision"] = 0
        self.assertEqual(decode_documented_fields(other)["fields"], {})

    def test_transition_report_summarizes_raw_arrays(self):
        rows = [sample(score=n) for n in (0, 0, 4, 8)]
        for row in rows:
            row["decoded_fields"] = decode_documented_fields(row)
        fields = summarize_documented_transitions(rows)["fields"]
        self.assertEqual(fields["golf_config.standard_player_hole_scores_raw"]["changed_steps"], 2)
        self.assertEqual(fields["sports_sequence.standard_golf_hole_scores_raw"]["changed_steps"], 2)
        self.assertEqual(fields["golf_field.start_object_count_raw"]["changed_steps"], 0)
        self.assertNotIn("first_raw", fields["golf_config.standard_player_hole_scores_raw"])

    def test_missing_sample_not_compared_across_gap(self):
        rows = [sample(score=n) for n in (0, 4, 8)]
        for row in (rows[0], rows[2]):
            row["decoded_fields"] = decode_documented_fields(row)
        fields = summarize_documented_transitions(rows)["fields"]
        self.assertEqual(fields["golf_config.standard_player_hole_scores_raw"]["changed_steps"], 0)


if __name__ == "__main__":
    unittest.main()
