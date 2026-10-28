"""Fabricated-only original-archive qualification and Omega r4/r30 join."""
from __future__ import annotations
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_outer_operand_r4_r30_private as driver
import omega_p0_offline_private as omega


def report():
    return {"kind":"P0-SANITIZED-OUTER-OPERAND-R4-R30-SOURCE-CANDIDATES",
            "training_approved":False,"allowed_to_publish":False,
            "outer_operand_source_rows":[{
                "outer_source_function":name,
                "tracked_source_operand":reg,
                "nearest_pre_mr_operand_write_class":"mr_from_r3",
                "status":"SOURCE_SYNTAX_CANDIDATE_NOT_CFG_PROOF",
                "control_transfer_after_candidate_write":False
             } for name,reg in (
                 ("SimulateManager_outer_to_ball_local","r4"),
                 ("MapObjBall_outer_to_ball_local","r30"))]}

def fake_seven(directory):
    folders={n:directory for n in range(1,8)}
    return SimpleNamespace(
        _check_archive=lambda path: folders,
        SIZE=(4,4),src=SimpleNamespace(_file=lambda root,name,size:root/name),
        roster=SimpleNamespace(TwoBankReader=lambda a,b:SimpleNamespace(
            u32=lambda pc:0x60000000)),
        _get=lambda rd:{"synthetic":True})

class NativeR4R30Tests(unittest.TestCase):
    def test_hosted_native_free_original_before_after_and_source_consistency(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for n in range(1,8):
                for b in (1,2):
                    (root/f"{n}.{b}.raw").write_bytes(b"mock")
            seven=fake_seven(root)
            with ExitStack() as stack:
                stack.enter_context(patch.object(driver.receiver,"_import_from_path",
                    return_value=seven))
                stack.enter_context(patch.object(driver.hints,"analyze",
                    return_value=report()))
                stack.enter_context(patch.object(driver.Path,"resolve",
                    autospec=True, side_effect=lambda self,strict=False:self))
                stack.enter_context(patch.object(driver.Path,"is_dir",
                    return_value=True))
                with patch.object(seven,"_check_archive",side_effect=[
                        {n:root for n in range(1,8)},
                        {n:root for n in range(1,8)}]) as check:
                    out=driver.analyze(root,root)
                    self.assertEqual(check.call_count,2)
                self.assertTrue(out["original_fourteen_native_banks_sha_verified_before_and_after"])
                self.assertEqual(len(out["source_operand_hints"]),2)
                self.assertFalse(out["runtime_receiver_is_global_or_player_ball_verified"])

    def test_omega_extract_requires_provenance_and_exact_two_cases(self):
        x={"original_fourteen_native_banks_sha_verified_before_and_after":True,
           "two_source_code_windows_identical_all_seven":True,
           "source_selected_scene_gated_for_all_seven":True,
           "source_operand_hints":report()["outer_operand_source_rows"]}
        out=omega._operand_extract(x)
        self.assertEqual([v["tracked_operand"] for v in out],["r4","r30"])
        for field in ("original_fourteen_native_banks_sha_verified_before_and_after",
                      "two_source_code_windows_identical_all_seven",
                      "source_selected_scene_gated_for_all_seven"):
            y=dict(x);y[field]=False
            with self.assertRaises(omega.Abstain):
                omega._operand_extract(y)
        y=dict(x);y["source_operand_hints"]=list(reversed(x["source_operand_hints"]))
        with self.assertRaises(omega.Abstain):
            omega._operand_extract(y)

    def test_isolated_python_cli_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            script=Path(__file__).resolve().parents[1]/"scripts"/"audit_p0_outer_operand_r4_r30_private.py"
            p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                            cwd=temp,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("--canonical-source-scripts",p.stdout)

    def test_failure_does_not_echo_private_archive(self):
        from io import StringIO
        with patch.object(driver,"analyze",side_effect=ValueError("PRIVATE 0xDEADBEEF")), \
             patch("sys.stdout",new_callable=StringIO) as out:
            rc=driver.main(["--archive","/fake","--canonical-source-scripts","/fake"])
            self.assertEqual(rc,2)
            self.assertNotIn("0xDEADBEEF",out.getvalue())

if __name__=="__main__":
    unittest.main()
