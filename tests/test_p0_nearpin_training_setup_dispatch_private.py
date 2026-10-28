"""Synthetic-only tests for bounded public Golf training-setup source windows."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_nearpin_training_setup_dispatch_private as m

def bl(pc,target,link=True):
    off=(target-pc)&0x03FFFFFC
    return 0x48000000 | off | int(link)

def bc(pc,target):
    off=(target-pc)&0xFFFC
    return 0x40000000 | (12<<21) | off

def fixture():
    # No actual private PPC source or native capture values used.
    training=[0x60000000]*38
    game=[0x60000000]*23
    t=m.WINDOWS[0][1]; g=m.WINDOWS[1][1]
    training[2]=0x2C000004    # cmpwi (literal 4) is NOT proven mode4
    training[3]=bc(t+12,t+28)
    training[4]=bl(t+16,t+32,True)
    training[8]=bl(t+32,0x8029D810,True)
    training[-1]=0x4E800020 # blr
    game[3]=bl(g+12,0x8029D778,True)
    game[4]=0x28000003     # cmplwi 3
    game[5]=bl(g+20,g+32,False) # nonlinked branch
    game[-1]=0x4E800020
    return (tuple(training),tuple(game))

class P0TrainingSetupSourceTests(unittest.TestCase):
    def test_published_exact_public_function_bounds(self):
        self.assertEqual([(n,len(range(0,s,4))) for n,a,s in m.WINDOWS],
                         [("SetupTrainingGame",38),("SetupGame",23)])
        self.assertEqual(m.WINDOWS[0][1]+m.WINDOWS[0][2],m.WINDOWS[1][1])

    def test_literal_four_is_syntax_not_mode_semantics(self):
        res=m.summarize_observations({n:fixture() for n in range(1,8)})
        self.assertTrue(res["windows"][0]["direct_literal_mode4_compare_syntax_seen"])
        self.assertFalse(res["mode4_to_phase_source_dispatch_verified"])
        self.assertFalse(res["windows"][0]["mode4_branch_reachability_or_phase_receiver_proven"])

    def test_direct_bl_source_target_in_own_function(self):
        t=m.WINDOWS[0][1]
        y=m.classify_window(*m.WINDOWS[0],fixture()[0])
        c=next(q for q in y["direct_linked_branch_sites"] if q["site"]=="+0x010")
        self.assertEqual(c["target_region"],"IN_THIS_FUNCTION+0x020")
        self.assertTrue(c["link"])

    def test_direct_bl_to_separate_published_training_setup(self):
        res=m.summarize_observations({n:fixture() for n in range(1,8)})
        c=res["windows"][1]["direct_linked_branch_sites"]
        self.assertEqual(len(c),1)
        self.assertEqual(c[0]["target_region"],
                         "IN_PUBLISHED_CONFIG_UNIT+0x0D2C")

    def test_branch_negative_offset(self):
        pc=m.WINDOWS[0][1]+0x20
        self.assertEqual(m._branch_target(bl(pc,pc-0x10),pc,False),pc-0x10)
        self.assertEqual(m._branch_target(bc(pc,pc-0x10),pc,True),pc-0x10)

    def test_bcl_direct_link_counted_but_not_claimed_callee(self):
        words=list(fixture()[0])
        t=m.WINDOWS[0][1]
        words[6]=bc(t+24,t+36) | 1
        r=m.classify_window(*m.WINDOWS[0],tuple(words))
        self.assertEqual(r["unconditional_direct_bl_site_count"],2)
        self.assertEqual(r["conditional_direct_bcl_site_count"],1)
        self.assertEqual(r["direct_linked_branch_site_count"],3)
        match=[z for z in r["direct_linked_branch_sites"] if z["site"]=="+0x018"]
        self.assertEqual(len(match),1)
        self.assertEqual(match[0]["opcode_family"],"BC")
        self.assertTrue(match[0]["conditional"])
        self.assertTrue(match[0]["link"])
        self.assertEqual(match[0]["target_region"],"IN_THIS_FUNCTION+0x024")
        self.assertIn(match[0],r["direct_nonlinked_or_conditional_branches"])
        self.assertFalse(r["linked_sites_are_executed_calls_verified"])

    def test_nonlinked_conditional_branch_does_not_inflate_linked_counts(self):
        words=list(fixture()[0])
        t=m.WINDOWS[0][1]
        words[6]=bc(t+24,t+36)  # LK=0
        r=m.classify_window(*m.WINDOWS[0],tuple(words))
        self.assertEqual(r["conditional_direct_bcl_site_count"],0)
        self.assertEqual(r["unconditional_direct_bl_site_count"],2)
        self.assertEqual(r["direct_linked_branch_site_count"],2)

    def test_bcl_pc_plus_four_idiom_is_not_a_verified_function_call(self):
        words=list(fixture()[0])
        t=m.WINDOWS[0][1]
        words[6]=bc(t+24,t+28) | 1
        r=m.classify_window(*m.WINDOWS[0],tuple(words))
        row=next(z for z in r["direct_linked_branch_sites"]
                 if z["site"]=="+0x018")
        self.assertTrue(row["pc_plus_four_link_pattern"])
        self.assertEqual(row["target_region"],"IN_THIS_FUNCTION+0x01C")
        self.assertFalse(r["linked_sites_are_executed_calls_verified"])

    def test_bcl_absolute_direct_source_target(self):
        words=list(fixture()[0])
        t=m.WINDOWS[0][1]
        # Absolute BD=0x180, AA=1, LK=1. Not relative to Golf Config.
        words[6]=0x40000183
        r=m.classify_window(*m.WINDOWS[0],tuple(words))
        row=next(z for z in r["direct_linked_branch_sites"]
                 if z["site"]=="+0x018")
        self.assertTrue(row["absolute"])
        self.assertEqual(row["target_region"],
                         "OUTSIDE_PUBLISHED_CONFIG_UNIT_UNTYPED")
        self.assertEqual(r["conditional_direct_bcl_site_count"],1)

    def test_literal_three_and_five_are_controls(self):
        a=list(fixture()[0]);a[2]=0x2c000003;a[7]=0x28000005
        res=m.classify_window(*m.WINDOWS[0],tuple(a))
        self.assertEqual([z["compares_literal"] for z in res["mode_3_4_5_literal_compare_sites"]],[3,5])
        self.assertFalse(res["direct_literal_mode4_compare_syntax_seen"])

    def test_absolute_branch_destination_is_not_relative(self):
        pc=0x8029D810
        self.assertEqual(m._branch_target(0x48000002|0x180,pc,False),0x180)

    def test_no_private_code_words_or_addresses_in_report(self):
        y=m.summarize_observations({n:fixture() for n in range(1,8)})
        s=json.dumps(y)
        for private in ("0x60000000","0x2C000004","0x9000A000","manifest-PRIVATE","1.1.raw","sha256"):
            self.assertNotIn(private,s)
        self.assertFalse(y["training_approved"])
        self.assertFalse(y["allowed_to_publish"])
        self.assertFalse(y["commit_result_backing_state_verified"])
        self.assertFalse(y["actual_guest_physics_step_or_rendered_ball_verified"])

    def test_different_instruction_in_seventh_capture_rejects(self):
        x={n:fixture() for n in range(1,8)}
        z=list(x[7]);a=list(z[0]);a[1]^=1;z[0]=tuple(a);x[7]=tuple(z)
        with self.assertRaisesRegex(ValueError,"drift"):
            m.summarize_observations(x)

    def test_missing_or_extra_capture_rejects(self):
        for samples in ({}, {1:fixture()}, {n:fixture() for n in range(8)}):
            with self.subTest(n=len(samples)),self.assertRaises(ValueError):
                m.summarize_observations(samples)

    def test_truncated_function_rejects(self):
        with self.assertRaisesRegex(ValueError,"length"):
            m.classify_window(*m.WINDOWS[0],fixture()[0][1:])

    def test_wrong_function_identity_rejects(self):
        name,start,size=m.WINDOWS[0]
        with self.assertRaises(ValueError):
            m.classify_window("Unknown",start,size,fixture()[0])

    def test_untyped_code_words_reject(self):
        words=list(fixture()[0])
        for value in ("1",True,-1,0x100000000):
            with self.subTest(value=value),self.assertRaises(ValueError):
                words[0]=value
                m.classify_window(*m.WINDOWS[0],tuple(words))

    def test_selected_context_gated_before_source(self):
        called=[]
        def read(x):
            called.append(x)
            return 0
        for ctx in ({"selected_index":True,"hole":0},
                    {"selected_index":0,"hole":9},
                    {"selected_index":4,"hole":0},
                    {"selected_index":0,"hole":False},
                    {}):
            with self.subTest(ctx=ctx),self.assertRaises(ValueError):
                m.inspect(read,ctx)
        self.assertEqual(called,[])

    def test_source_reader_visits_only_61_preapproved_words(self):
        called=[]
        ctx={"selected_index":1,"hole":4}
        z=m.inspect(lambda pc:(called.append(pc) or 0x60000000),ctx)
        self.assertEqual(tuple(len(x) for x in z),(38,23))
        self.assertEqual(len(called),61)
        self.assertEqual(called[0],m.WINDOWS[0][1])
        self.assertEqual(called[-1],m.WINDOWS[1][1]+0x58)

    def test_cli_help_is_readonly_and_no_archive_required(self):
        f=Path(m.__file__).resolve()
        r=subprocess.run([sys.executable,"-I",str(f),"--help"],
                         capture_output=True,text=True,timeout=15,cwd=f.parents[2])
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("--archive",r.stdout)

if __name__=="__main__":
    unittest.main()
