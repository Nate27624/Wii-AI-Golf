"""Native-free schema contract checks for the B0 two-store PowerShell wrapper.

Prevent another stop after a successful original B0 audit because a Python
report field was spelled differently in the Windows PowerShell validator.
No game RAM, ROM, addresses, filenames, or native JSON is used.
"""
from __future__ import annotations
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_player_two_store_same_receiver_private as audit


def synthetic_blob():
    words=[0x60000000]*audit.COUNT
    words[0]=(52<<26)|(30<<16)|0x30
    words[5]=(31<<26)|(30<<21)|(3<<16)|(30<<11)|(444<<1)
    pc=audit.CALL
    words[-1]=(18<<26)|((audit.TARGET-pc)&0x03FFFFFC)|1
    return b"".join(struct.pack(">I",w) for w in words)


def example_report():
    x=audit.analyze(synthetic_blob())
    x["callee_local_source_path_preserves_copy_possible"]=True
    x["joined_two_store_source_possible_only"]=True
    x["original_B0_SHA_and_Rev1_verified_before_after"]=True
    return x


def wrapper_expectations():
    script=(ROOT/"scripts"/"Invoke-P0PlayerTwoStoreLink.ps1").read_text("utf-8")
    m=re.search(r"\$expected\s*=\s*\[ordered\]@\{(?P<body>.*?)\n\}",
                script,re.DOTALL)
    if not m:
        raise AssertionError("expected typed PowerShell contract block missing")
    expected={}
    for raw in m.group("body").splitlines():
        line=raw.strip()
        if not line: continue
        pair=re.fullmatch(r"([A-Za-z_0-9]+)\s*=\s*(\$true|\$false|'[^']*')",line)
        if pair is None:
            raise AssertionError("unrecognized PowerShell contract predicate")
        field,value=pair.groups()
        if field in expected:raise AssertionError("duplicate contract field")
        expected[field]=(True if value=="$true" else
                         False if value=="$false" else value[1:-1])
    return expected


def contract_violations(expected,report):
    out=[]
    for key,want in expected.items():
        if key not in report:
            out.append("MISSING:"+key)
        elif type(want) is not type(report[key]) or want!=report[key]:
            out.append("MISMATCH:"+key)
    return out


class TwoStoreContract(unittest.TestCase):
    def test_synthetic_report_matches_all_expected_contract_fields(self):
        self.assertEqual(contract_violations(wrapper_expectations(),example_report()),[])

    def test_flag_name_is_exactly_python_report_training_approved(self):
        expected=wrapper_expectations()
        self.assertIn("training_approved",expected)
        self.assertIs(expected["training_approved"],False)
        self.assertNotIn("approved_for_training",expected)
        self.assertIs(example_report()["training_approved"],False)

    def test_missing_training_gate_is_rejected(self):
        report=example_report()
        report.pop("training_approved")
        self.assertIn("MISSING:training_approved",
                      contract_violations(wrapper_expectations(),report))

    def test_promoted_training_gate_is_rejected(self):
        report=example_report()
        report["training_approved"]=True
        self.assertIn("MISMATCH:training_approved",
                      contract_violations(wrapper_expectations(),report))

    def test_other_claim_promotion_rejected(self):
        report=example_report()
        report["same_object_runtime_write_proven"]=True
        self.assertIn("MISMATCH:same_object_runtime_write_proven",
                      contract_violations(wrapper_expectations(),report))

    def test_no_reused_wrong_key_in_wrapper(self):
        script=(ROOT/"scripts"/"Invoke-P0PlayerTwoStoreLink.ps1").read_text("utf-8")
        self.assertNotIn("approved_for_training",script)
        self.assertIn("P0_TWO_STORE_REPORT_CONTRACT_ABSTAIN",script)
        self.assertIn("P0_TWO_PLAYER_FLOAT_STORES_LINK_COMPLETE",script)


if __name__=="__main__":
    unittest.main()
