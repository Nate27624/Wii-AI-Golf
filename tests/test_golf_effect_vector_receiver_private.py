"""Synthetic-only PPC source-signature checks for two golf triplets."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_golf_effect_vector_receiver_private as receiver


def fixtures():
    words = dict(receiver.FIELD_SITES)
    words.update(receiver.BALL_SITES)
    words[0x80290D04]=0x9421FFC0  # plausible stack prologue
    words[0x80290D18]=0x7C7D1B78  # mr r29,r3
    words[0x802976F0]=0x9421FFC0
    return words


class VectorReceiverTests(unittest.TestCase):
    def test_two_exact_source_sequences_and_owner_uncertainty(self):
        words=fixtures()
        result=receiver.analyze(lambda pc:words.get(pc,0))
        self.assertEqual(len(result["source_foci"]),2)
        first,second=result["source_foci"]
        self.assertTrue(first["source_signature_verified"])
        self.assertTrue(second["float_triplet_store_source_verified"])
        self.assertIn("0x80290D18",first["r29_preserved_from_r3_literal_pcs"])
        self.assertIn("0x80290D04",first["possible_prologue_pcs_not_cfg_verified"])
        self.assertFalse(first["function_boundary_proven"])
        self.assertFalse(first["minimap_effect_object_receiver_verified"])
        self.assertFalse(second["active_ball_object_receiver_verified"])
        self.assertFalse(result["RPSysEffect_field_078_07C_type_proven"])
        self.assertFalse(result["training_allowed"])
        self.assertFalse(result["allowed_to_publish"])
        self.assertEqual(result["public_header_fieldmanager_effect_offsets"]["mMapBallEff"],"+0x09C")

    def test_any_changed_instruction_word_fails_closed(self):
        good=fixtures()
        for pc in list(receiver.FIELD_SITES)+list(receiver.BALL_SITES):
            bad=dict(good)
            bad[pc]^=1
            with self.subTest(pc=hex(pc)),self.assertRaisesRegex(
                    ValueError,"signature mismatch"):
                receiver.analyze(lambda addr:bad.get(addr,0))

    def test_no_unbounded_context_and_no_unrelated_byte_values(self):
        words=fixtures()
        result=receiver.analyze(lambda pc:words.get(pc,0))
        for row in result["source_foci"]:
            start,end=receiver.effect.TEXT_UNITS[row["source_unit"]]
            self.assertTrue(all(start<=int(item["pc"],16)<end
                for item in row["source_context"]))
            self.assertLessEqual(len(row["source_context"]),48)
        self.assertEqual(result["public_header_fieldmanager_offsets"]["mMapTreesObj"],"+0x078")

    def test_prologue_guess_does_not_promote_function_identity(self):
        words=fixtures()
        del words[0x80290D04]
        del words[0x80290D18]
        result=receiver.analyze(lambda pc:words.get(pc,0))
        self.assertEqual(result["source_foci"][0]["possible_prologue_pcs_not_cfg_verified"],[])
        self.assertEqual(result["source_foci"][0]["r29_preserved_from_r3_literal_pcs"],[])
        self.assertFalse(result["source_foci"][0]["minimap_effect_object_receiver_verified"])

if __name__=="__main__":
    unittest.main()
