"""Native-free adversarial source-global pointer first-use controls."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_p0_global_slot_load_consumers as m

P = m.UNIT_BASE + 0x2B64
DISP = -100

def d(op, rt, ra, imm=0):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 0xffff)

def mr(dest, src):
    return (31 << 26) | (src << 21) | (dest << 16) | (src << 11) | (444 << 1)

def fixture(reg=3):
    return {P: d(32,reg,13,DISP)}

def run(src,reg=3):
    words=fixture(reg)
    words.update(src)
    return m.first_consumer(lambda p: words.get(p,0x60000000),P,DISP)

class FirstUse(unittest.TestCase):
    def test_translation_field_load_candidate(self):
        result=run({P+4:d(32,5,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "field_load_from_source_global_pointer")
        self.assertEqual(result["source_syntactic_field_displacement"],0x4C)
        self.assertFalse(result["all_path_pointer_dataflow_verified"])

    def test_bounded_first_field_store(self):
        result=run({P+4:d(36,4,3,0x30)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "field_store_through_source_global_pointer")

    def test_source_pointer_stored_elsewhere(self):
        result=run({P+4:d(36,3,4,12)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "source_global_pointer_value_stored")

    def test_exact_null_compare_candidate(self):
        result=run({P+4:d(11,0,3,0)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "immediate_zero_compare_on_loaded_pointer")

    def test_direct_bl_only_if_r3_was_forwarded(self):
        words={P+4:mr(3,4),P+8:(18<<26)|1}
        self.assertEqual(run(words,4)["first_bounded_consumer_class"],
                         "direct_bl_after_r3_pointer_candidate")
        self.assertEqual(run({P+4:(18<<26)|1},4)["first_bounded_consumer_class"],
                         "branch_or_call_before_proven_consumer")

    def test_intervening_branch_stops_at_first_edge(self):
        result=run({P+4:(16<<26)|(12<<21)|(2<<16)|8,
                    P+8:d(32,4,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "branch_or_call_before_proven_consumer")

    def test_intervening_ra_write_stops(self):
        result=run({P+4:d(24,4,3,0),P+8:d(32,4,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_intervening_update_base_write_stops(self):
        result=run({P+4:d(37,0,3,4),P+8:d(32,4,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_lmw_range_invalidates_pointer_register(self):
        result=run({P+4:d(46,2,4,0),P+8:d(32,4,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_unknown_xform_abstains(self):
        result=run({P+4:(31<<26)|(5<<21)|(6<<16)|(444<<1)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "possible_register_clobber_before_proven_consumer")

    def test_ppc_r0_is_not_a_memory_base_pointer(self):
        # D-form rA=0 means effective address uses literal zero, NOT GPR0.
        for opcode in (32, 34, 40, 42, 48, 50, 36, 38, 44, 52, 54):
            with self.subTest(opcode=opcode):
                r=run({P+4:d(opcode,5,0,4)},reg=0)
                self.assertNotIn(
                    r["first_bounded_consumer_class"],
                    ("field_load_from_source_global_pointer",
                     "field_store_through_source_global_pointer"))

    def test_r0_can_still_be_mr_source_register(self):
        # True GPR copy is legal, even if r0 cannot be D-form address base.
        r=run({P+4:mr(3,0),P+8:(18<<26)|1},reg=0)
        self.assertEqual(r["first_bounded_consumer_class"],
                         "direct_bl_after_r3_pointer_candidate")

    def test_exact_15_sites_and_private_report_contract(self):
        sites=[{"source_unit":"RPGolMapObjBall",
                "source_access_type":"direct_lwz_read",
                "unit_relative_pc":"+0x%04X"%(0x2B64+i*0x10)}
               for i in range(15)]
        words={m.UNIT_BASE+0x2B64+i*0x10:d(32,3,13,DISP)
               for i in range(15)}
        r=m.analyze(lambda p:words.get(p,0x60000000),sites,DISP)
        self.assertEqual(r["exact_known_direct_loads_checked"],15)
        self.assertFalse(r["approved_for_model_training"])
        self.assertFalse(r["dynamic_rendered_object_role_verified"])
        rendered=json.dumps(r)
        for secret in ("private_path","heap_pointer","MEM1.bin","0x9000"):
            self.assertNotIn(secret,rendered)

    def test_wrong_source_word_or_r13_displacement_rejected(self):
        with self.assertRaises(ValueError):
            m.first_consumer(lambda p:d(32,3,13,DISP+4),P,DISP)
        with self.assertRaises(ValueError):
            m.first_consumer(lambda p:d(32,3,12,DISP),P,DISP)
        with self.assertRaises(ValueError):
            m.first_consumer(lambda p:-1,P,DISP)

    def test_duplicate_site_refused(self):
        src={"source_unit":"RPGolMapObjBall",
             "source_access_type":"direct_lwz_read",
             "unit_relative_pc":"+0x2B64"}
        with self.assertRaises(ValueError):
            m.analyze(lambda p:d(32,3,13,DISP),[src]*15,DISP)

    def test_first_use_window_has_no_unbounded_scan(self):
        result=run({P+28:d(32,5,3,0x4C)})
        self.assertEqual(result["first_bounded_consumer_class"],
                         "no_certified_consumer_in_six_words")

if __name__ == "__main__":
    unittest.main()
