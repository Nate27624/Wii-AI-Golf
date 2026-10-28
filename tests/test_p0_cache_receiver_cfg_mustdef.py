"""Fabricated PPC CFG must-alias tests. No native banks or emulator."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"review_p0_cache_receiver_cfg_mustdef.py"
spec=importlib.util.spec_from_file_location("cfg_under_test",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

E=0x80299ACC
C=E+28
NOP=0x60000000
BLR=0x4E800020

def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)
def dform(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&65535)
def bl(pc,target):
    return (18<<26)|((target-pc)&0x03FFFFFC)|1
def b(pc,target):
    return (18<<26)|((target-pc)&0x03FFFFFC)
def bc(pc,target):
    return (16<<26)|((target-pc)&0xFFFC)

def fixture():
    src={E+i*4:NOP for i in range(8)}
    src[E] = dform(37,1,1,-32) # stwu r1,-32(r1)
    src[E+4] = (31<<26)|(0<<21)|(339<<1) # mfspr r0
    src[E+8] = mr(31,3)
    src[E+12] = dform(11,0,31,0) # cmpwi, no GPR write
    src[E+16] = bc(E+16,E+24)
    src[E+20] = NOP
    src[E+24] = mr(3,31)
    src[C] = bl(C,mod.CACHE_TARGET)
    return src

def check(src):
    return mod.prove_caller(src.__getitem__,entry=E,callsite=C)

class CfgReceiverMustDefTests(unittest.TestCase):
    def test_good_two_branch_paths_prove_only_static(self):
        r=check(fixture())
        self.assertEqual(r["status"],"STATIC_ENTRY_R3_MUST_FLOW")
        self.assertTrue(r["all_reaching_paths_pass_entry_r3_through_r31_to_call_r3"])
        self.assertFalse(r["runtime_receiver_object_verified"])

    def test_reordered_src_branch_skips_r31_assignment(self):
        s=fixture()
        s[E+4]=bc(E+4,E+16)
        r=check(s)
        self.assertEqual(r["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_r3_clobber_on_one_branch(self):
        s=fixture()
        s[E+12]=dform(14,3,0,99)  # addi r3,r0,99
        s[E+16]=bc(E+16,E+24)  # branch jumps over re-copy
        s[E+20]=mr(3,31)
        s[E+24]=NOP
        r=check(s)
        self.assertEqual(r["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_repair_r3_on_both_paths(self):
        s=fixture()
        s[E+12]=dform(14,3,0,0)
        s[E+16]=bc(E+16,E+24)
        s[E+20]=NOP
        s[E+24]=mr(3,31)
        self.assertEqual(check(s)["status"],"STATIC_ENTRY_R3_MUST_FLOW")

    def test_r31_clobber_dform(self):
        s=fixture();s[E+20]=dform(32,31,1,16)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_other_b_l_branch_refused(self):
        s=fixture();s[E+16]=bl(E+16,mod.CACHE_TARGET)
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_indirect_branch_refused(self):
        s=fixture();s[E+20]=0x4E800420  # bctr
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_unsupported_xform_refused(self):
        s=fixture();s[E+20]=0x7C000214  # add r0,r0,r0 (not approved)
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_branch_outside_caller_refused(self):
        s=fixture();s[E+16]=bc(E+16,E+0x50)
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_valid_bypassed_return_path_not_wrongly_failed(self):
        s=fixture();s[E+16]=bc(E+16,E+24)
        s[E+20]=BLR  # some paths return, others reach target
        self.assertEqual(check(s)["status"],"STATIC_ENTRY_R3_MUST_FLOW")

    def test_no_reachable_call_abstains(self):
        s=fixture();s[E+12]=BLR
        self.assertEqual(check(s)["status"],"ABSTAIN_TARGET_UNREACHABLE")

    def test_direct_b_jump_good(self):
        s=fixture();s[E+16]=b(E+16,E+24)
        self.assertEqual(check(s)["status"],"STATIC_ENTRY_R3_MUST_FLOW")

    def test_backward_loop_has_finite_fixpoint(self):
        s=fixture();s[E+16]=bc(E+16,E+12)
        self.assertEqual(check(s)["status"],"STATIC_ENTRY_R3_MUST_FLOW")

    def test_zero_code_refused(self):
        s=fixture();s[E+12]=0
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_wrong_exact_bl_refused(self):
        s=fixture();s[C]=bl(C,mod.CACHE_TARGET+4)
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_wrong_instruction_type_refused(self):
        s=fixture();s[E+20]="private"
        self.assertEqual(check(s)["status"],"ABSTAIN_SOURCE_UNRESOLVED")

    def test_lmw_overwrites_r31(self):
        s=fixture();s[E+20]=dform(46,12,1,0)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_mr_original_r3_already_corrupted_not_proven(self):
        s=fixture();s[E+4]=dform(14,3,0,5)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_no_physics_or_training_flags(self):
        r=check(fixture())
        for name in ("incoming_entry_r3_object_class_verified",
                     "runtime_receiver_object_verified",
                     "executed_cache_write_verified",
                     "physical_xyz_velocity_power_contact_score_verified",
                     "training_approved","allowed_to_publish"):
            self.assertIs(r[name],False)

    def test_no_private_source_word_or_pointer_in_output(self):
        r=check(fixture())
        self.assertNotIn("0x80299",str(r))
        self.assertNotIn("0x9000",str(r))

    def test_first_real_caller_window_order_and_wrong_order_negative(self):
        # Regression: 0x80299ACC < 0x80299B64. First #240 caller interval
        # is arithmetic-valid, but still lacks independently verified CFG.
        name, entry, pc = mod.CALLERS[0]
        self.assertLess(entry, pc)
        self.assertEqual(pc-entry, 0x98)
        out = mod.prove_caller(
            lambda _: (_ for _ in ()).throw(AssertionError("no source read")),
            entry=pc+4, callsite=pc
        )
        self.assertEqual(out["status"],"ABSTAIN_SOURCE_UNRESOLVED")
        self.assertFalse(out["all_reaching_paths_pass_entry_r3_through_r31_to_call_r3"])

    def test_lmw_start_r2_clobbers_both_r3_and_r31(self):
        s=fixture()
        # PPC lmw loads r2,r3,...r31. rT need NOT equal 3.
        s[E+20]=dform(46,2,1,0)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_stmw_r3_does_not_write_source_register(self):
        s=fixture()
        # PPC stmw r3 stores source GPRs; must not kill r3 itself.
        s[E+20]=dform(47,3,1,0)
        self.assertEqual(check(s)["status"],"STATIC_ENTRY_R3_MUST_FLOW")

    def test_stwu_base_update_clobbers_r3_even_if_rs_is_r0(self):
        s=fixture()
        # PPC stwu r0,8(r3) updates address register r3.
        s[E+20]=dform(37,0,3,8)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_ori_ra_r3_overwrites_even_when_rs_not_r3(self):
        s=fixture()
        # PPC ori r3,r5,0 destination is rA, source is rS.
        s[E+20]=dform(24,5,3,0)
        self.assertEqual(check(s)["status"],"NOT_PROVEN_FOR_ALL_REACHING_PATHS")

    def test_native_free_cli(self):
        p=subprocess.run([sys.executable,str(SCRIPT)],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('"private_banks_read": false',p.stdout)
        self.assertIn('"dynamic_receiver_claim": false',p.stdout)


if __name__=="__main__":
    unittest.main()
