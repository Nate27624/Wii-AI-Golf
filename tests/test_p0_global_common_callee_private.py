"""Native-free adversarial controls for exact common global ball BL callee."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_common_callee as m

UNITS=(
    ("RPGolMain",0x8028E098,0x8028E900),
    ("RPGolFieldManager",0x80290B44,0x80294184),
    ("RPGolMapObjBall",0x80296FD8,0x8029B240),
    ("RPGolSimulateManager",0x8029B240,0x8029BBB4),
    ("RPGolPlayer",0x8029E62C,0x802A2210),
    ("RPGolPlayerManager",0x802A2210,0x802A3560),
)
CALLS=[{
    "direct_bl_source_relative_pc":off,
    "direct_bl_public_target_code_pc":"0x8029A5EC",
    "direct_source_global_pointer_is_runtime_r3_argument_verified":False,
} for off in("+0x2B70","+0x2BEC","+0x2C68")]

def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)

def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)

def bl(pc,dest):
    return (18<<26)|((dest-pc)&0x03fffffc)|1

def audit(changes=None,calls=None,units=UNITS):
    ins={m.ENTRY+i*4:0x60000000 for i in range(m.SIZE//4)}
    ins[m.ENTRY+4]=mr(31,3)
    ins[m.ENTRY+8]=d(32,4,31,0x4c)
    ins[m.ENTRY+12]=d(48,1,3,0)
    pc=m.ENTRY+0x18
    ins[pc]=bl(pc,0x8029AB78)
    ins.update(changes or {})
    return m.audit(ins.__getitem__,CALLS if calls is None else calls,units)

class CommonGlobalFunction(unittest.TestCase):
    def test_size_source_and_three_exact_callers(self):
        a=audit()
        self.assertEqual(a["source_function"],"fn_8029A5EC")
        self.assertEqual(a["source_words_scanned"],78)
        self.assertTrue(a["three_verified_source_BL_sites_same_target"])
        self.assertFalse(a["function_is_rendered_or_physics_method_verified"])

    def test_early_r3_to_r31_is_only_syntactic(self):
        a=audit()
        self.assertEqual(a["early_input_r3_callee_saved_copy_candidates"][0]["copy_candidate_GPR"],"r31")
        self.assertFalse(a["any_GPR31_field_load_is_receiver_proven"])

    def test_exact_field_and_call_source_inventory(self):
        a=audit()
        self.assertEqual(a["source_direct_field_access_count"],2)
        self.assertEqual(a["source_direct_GPR3_GPR31_field_accesses"][0]["source_field_signed_offset"],0x4c)
        self.assertEqual(a["source_direct_GPR3_GPR31_field_accesses"][1]["source_memory_opcode"],"lfs")
        self.assertEqual(a["source_direct_BL_count"],1)
        self.assertEqual(a["source_direct_BL_targets"][0]["public_target_code_pc"],"0x8029AB78")

    def test_wrong_callee_target_in_input_refused(self):
        c=[dict(x) for x in CALLS]
        c[0]["direct_bl_public_target_code_pc"]="0x8029A724"
        with self.assertRaises(ValueError):
            audit(calls=c)

    def test_wrong_global_caller_order_refused(self):
        with self.assertRaises(ValueError):
            audit(calls=list(reversed(CALLS)))

    def test_caller_runtime_true_is_rejected(self):
        c=[dict(x) for x in CALLS]
        c[1]["direct_source_global_pointer_is_runtime_r3_argument_verified"]=True
        with self.assertRaises(ValueError):
            audit(calls=c)

    def test_bad_public_source_unit_refused(self):
        with self.assertRaises(ValueError):
            audit(units=UNITS[:5])
        altered=list(UNITS)
        altered[2]=("wrong",altered[2][1],altered[2][2])
        with self.assertRaises(ValueError):
            audit(units=tuple(altered))

    def test_public_branch_destination_invalid_refused(self):
        pc=m.ENTRY+0x18
        with self.assertRaises(ValueError):
            audit({pc:bl(pc,0x81800000)})

    def test_unknown_source_word_abstains(self):
        with self.assertRaises(ValueError):
            audit({m.ENTRY+16:-1})

    def test_negative_field_offset_is_syntax_not_live_pointer(self):
        a=audit({m.ENTRY+8:d(32,4,31,-20)})
        self.assertEqual(a["source_direct_GPR3_GPR31_field_accesses"][0]["source_field_signed_offset"],-20)
        self.assertFalse(a["whole_function_dataflow_controlflow_verified"])

    def test_r0_memory_base_does_not_claim_receiver(self):
        a=audit({m.ENTRY+8:d(32,4,0,0x4c)})
        self.assertEqual(a["source_direct_field_access_count"],1)

    def test_output_never_contains_private_values_or_training_permission(self):
        a=audit()
        s=json.dumps(a)
        for word in ("private_path","MEM1.bin","runtime_object_address","raw_word","real_xyz"):
            self.assertNotIn(word,s)
        for key in ("training_approved","allowed_to_publish",
                    "function_is_rendered_or_physics_method_verified",
                    "source_called_at_runtime_verified",
                    "physical_xyz_velocity_power_impact_score_verified"):
            self.assertIs(a[key],False)

if __name__=="__main__":
    unittest.main()
