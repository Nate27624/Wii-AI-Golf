"""Fabricated-only canonical #231 scene/source audit adapter integration tests."""
from __future__ import annotations
import json
from contextlib import ExitStack
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_simulate_r3_6b4_private as audit
import run_p0_simulate_r3_6b4_private as runner


def synthetic_report():
    return {"kind":"P0-SANITIZED-SIMULATE-R3-BASE-FOR-6B4",
        "status":"ABSTAIN_ENTRY_R3_OR_UNSUPPORTED_PRODUCER",
        "training_approved":False,"allowed_to_publish":False}


def source_loader(root):
    folders={n:root for n in range(1,8)}
    return SimpleNamespace(
        SIZE=(4,4),
        src=SimpleNamespace(_file=lambda d,name,size:d/name),
        roster=SimpleNamespace(TwoBankReader=lambda a,b:SimpleNamespace(
            u32=lambda pc:0x60000000)),
        _check_archive=lambda p:folders,
        _get=lambda r:{"scene":"synthetic", "selected":"synthetic"})


class SourceOriginalReaderTests(unittest.TestCase):
    def test_original_sha_pre_and_post_seven_scene_source_windows(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            for n in range(1,8):
                for i in (1,2):
                    (folder/f"{n}.{i}.raw").write_bytes(b"MOCK")
            seven=source_loader(folder)
            with ExitStack() as stack:
                stack.enter_context(patch.object(audit.existing,
                    "_import_from_path",return_value=seven))
                stack.enter_context(patch.object(audit.probe,"analyze",
                    return_value=synthetic_report()))
                with patch.object(seven,"_check_archive",
                    side_effect=[{n:folder for n in range(1,8)},
                                 {n:folder for n in range(1,8)}]) as chk:
                    result=audit.analyze(folder,folder)
                    self.assertEqual(chk.call_count,2)
                self.assertTrue(result["original_fourteen_bank_sha_pre_and_post_verified"])
                self.assertTrue(result["rspe01_rev1_source_selected_scene_all_seven"])
                self.assertTrue(result["ppc_source_window_equal_all_seven"])
                self.assertFalse(result["rendered_ball_global_or_roster_receiver_verified"])

    def test_source_code_changes_across_phases_abstains(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            for n in range(1,8):
                for i in (1,2):
                    (folder/f"{n}.{i}.raw").write_bytes(b"MOCK")
            seven=source_loader(folder)
            rd_count={"calls":0}
            original=seven.roster.TwoBankReader
            def different_code(a,b):
                rd_count["calls"]+=1
                return SimpleNamespace(u32=lambda pc:(
                    0x60000000+rd_count["calls"] if pc==audit.probe.ENTRY else
                    0x60000000))
            seven.roster.TwoBankReader=different_code
            with patch.object(audit.existing,"_import_from_path",return_value=seven), \
                 patch.object(audit.probe,"analyze",return_value=synthetic_report()):
                with self.assertRaises(ValueError):
                    audit.analyze(folder,folder)

    def test_isolated_python_startup_and_help(self):
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            for filename in ("audit_p0_simulate_r3_6b4_private.py",
                             "run_p0_simulate_r3_6b4_private.py"):
                p=subprocess.run(
                    [sys.executable,"-I",str(repo/"scripts"/filename),"--help"],
                    capture_output=True,text=True,cwd=td,timeout=20)
                self.assertEqual(p.returncode,0,p.stderr)

    def test_runner_never_claims_source_proof_from_raw_helper(self):
        from io import StringIO
        with patch.object(runner,"run",side_effect=ValueError("PRIVATE_RAM 0x9000")), \
             patch("sys.stdout",new_callable=StringIO) as stdout:
            self.assertEqual(runner.main(["--repo","X"]),2)
            self.assertNotIn("PRIVATE_RAM",stdout.getvalue())
            self.assertNotIn("0x9000",stdout.getvalue())


if __name__=="__main__":
    unittest.main()
