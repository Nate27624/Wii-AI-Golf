"""Completely fabricated PPC; no game bytes or Dolphin in CI."""
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_r31_local_cfg_private as m


def encode_mr():
    return (31<<26)|(3<<21)|(31<<16)|(3<<11)|(444<<1)


def encode_stfs():
    return (52<<26)|(31<<16)|0x90


def encode_d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)


def encode_b(pc,to,link=False):
    return (18<<26)|((to-pc)&0x03fffffc)|int(link)


def encode_bc(pc,to,link=False):
    return (16<<26)|((to-pc)&0xfffc)|int(link)


def synth(changes=None):
    words=[0x60000000]*((m.STORE-m.COPY)//4+1)
    words[0]=encode_mr()
    words[-1]=encode_stfs()
    for index,word in (changes or {}).items():
        words[index]=word
    return b"".join(struct.pack(">I",w) for w in words)


class TestLocalSourceCFG(unittest.TestCase):
    def test_original_copy_and_store_plain_path(self):
        x=m.analyze_window(synth())
        self.assertTrue(x["local_path_reaches_store"])
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertFalse(x["local_path_reaches_store_with_unknown_r31"])
        self.assertFalse(x["runtime_receiver_is_selected_player_record_verified"])

    def test_conditional_branch_both_paths_different_r31_status(self):
        x=m.analyze_window(synth({3:encode_bc(m.COPY+12,m.COPY+32),
                                  4:encode_d(14,31,30,1)}))
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertTrue(x["local_path_reaches_store_with_unknown_r31"])
        self.assertEqual(x["control_flow_edges"][0]["kind"],"conditional_branch")

    def test_unconditional_branch_skips_clobber(self):
        x=m.analyze_window(synth({3:encode_b(m.COPY+12,m.COPY+32),
                                  4:encode_d(14,31,30,1)}))
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertFalse(x["local_path_reaches_store_with_unknown_r31"])

    def test_linked_call_taints_r31_return(self):
        x=m.analyze_window(synth({3:encode_b(m.COPY+12,m.STORE,True)}))
        self.assertFalse(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertTrue(x["local_path_reaches_store_with_unknown_r31"])
        self.assertIn("linked_call_return_unverified",x["incomplete_path_reasons"])

    def test_bo_always_branch_does_not_fabricate_fallthrough(self):
        branch=(16<<26)|(20<<21)|((m.COPY+32-(m.COPY+12))&0xfffc)
        x=m.analyze_window(synth({3:branch, 4:encode_d(14,31,30,1)}))
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertFalse(x["local_path_reaches_store_with_unknown_r31"])
        self.assertEqual(x["control_flow_edges"][0]["kind"],"unconditional_branch")

    def test_op19_cr_logic_not_misclassified_as_branch(self):
        x=m.analyze_window(synth({3:(19<<26)|(193<<1)}))
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])
        self.assertEqual(x["control_flow_edges"],[])

    def test_op19_indirect_is_unresolved_flow(self):
        x=m.analyze_window(synth({3:(19<<26)|(16<<1)}))
        self.assertFalse(x["local_path_reaches_store"])
        self.assertIn("unresolved_indirect_or_system_flow",x["incomplete_path_reasons"])

    def test_update_form_address_base_taints(self):
        x=m.analyze_window(synth({4:encode_d(49,2,31,4)}))
        self.assertTrue(x["local_path_reaches_store_with_unknown_r31"])
        self.assertFalse(x["local_path_reaches_store_with_unmodified_r31"])

    def test_floating_nonupdate_doesnt_clobber_r31(self):
        x=m.analyze_window(synth({4:encode_d(48,31,31,4)}))
        self.assertTrue(x["local_path_reaches_store_with_unmodified_r31"])

    def test_malformed_copy_or_store_fails_closed(self):
        for data in (synth({0:0x60000000}),
                     synth({12:encode_d(52,0,30,0x90)}),
                     synth()[:-1]):
            with self.assertRaises(ValueError):
                m.analyze_window(data)

    def test_no_raw_words_or_private_names_in_report(self):
        raw=json.dumps(m.analyze_window(synth({3:encode_bc(m.COPY+12,m.STORE)})))
        for term in ("0x60000000","0x802A0244","private-session","ball-study-20261027"):
            self.assertNotIn(term,raw)

    def test_cli_invalid_private_root_redacted(self):
        class InvalidInput(Exception):pass
        upstream=sys.modules["audit_ball_xyz_source_callers_private"]
        original=getattr(upstream,"UntrustedInput",None)
        original_checked=getattr(upstream,"checked_private_b0",None)
        upstream.UntrustedInput=InvalidInput
        upstream.checked_private_b0=lambda s,r: (_ for _ in ()).throw(InvalidInput())
        try:
            stderr=io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code=m.main(["--data-root","/missing","--private-session","SECRET_PATH"])
            self.assertEqual(code,2)
            self.assertNotIn("SECRET_PATH",stderr.getvalue())
        finally:
            if original is None:delattr(upstream,"UntrustedInput")
            else:upstream.UntrustedInput=original
            if original_checked is None:delattr(upstream,"checked_private_b0")
            else:upstream.checked_private_b0=original_checked


if __name__=="__main__":
    unittest.main()
