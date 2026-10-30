"""Synthetic S001 PowerShell private staging tests. Never boot or contact Dolphin."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p0_stage_private_capture.ps1"
MEM1 = 24 * 1024 * 1024
MEM2 = 64 * 1024 * 1024
POWERSHELL = (shutil.which("powershell.exe") or shutil.which("powershell")
              or shutil.which("pwsh")) if os.name == "nt" else None


class CaptureStageContractTests(unittest.TestCase):
    def test_script_is_offline_and_uses_manager_preflight(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for token in ("p0_capture_manifest_preflight.py", "--mode", "checkpoint",
                      "--write-private-manifest", "CreateNew", "MEM1_SIZE",
                      "MEM2_SIZE", "training_approved=$false"):
            self.assertIn(token, source)
        for forbidden in ("Start-Process", "SendKeys", "Invoke-WebRequest",
                          "Invoke-RestMethod", "git push", "gh pr create",
                          "Process]::Start", "FelkRPC("):
            self.assertNotIn(forbidden, source)

    def test_explicit_abstention_not_guest_frame_claim(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("guest_frame_verified=$false", source)
        self.assertIn("same_shot_verified=$false", source)
        self.assertIn("contact_verified=$false", source)
        self.assertIn("G0_STOP_NATIVE_CRASH_UNRESOLVED", source)
        self.assertIn("CLEAN_PORTABLE_DOLPHIN_REQUIRED", source)
        self.assertIn("GIT_CHECKOUT_FORBIDDEN", source)


@unittest.skipUnless(POWERSHELL, "Windows PowerShell 5.1 runtime required for executable staging")
class WindowsCaptureStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.private = self.work / "Private"
        self.private.mkdir()
        self.exe_dir = self.work / "CleanPortable"
        self.exe_dir.mkdir()
        self.exe = self.exe_dir / "Dolphin.exe"
        # Deliberately synthetic MZ fixture; hash proves only file identity.
        self.exe.write_bytes(b"MZ" + b"\0" * 128)
        (self.exe_dir / "portable.txt").write_text("", encoding="ascii")
        self.exe_sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.session_id = "GOLF-SYNTH-001"
        self.session = self.private / self.session_id
        self.export = self.work / "Export"
        self.export.mkdir()

    def execute(self, action, *args, private=None, **kw):
        argv = [POWERSHELL, "-NoProfile", "-NonInteractive"]
        if "powershell" in Path(POWERSHELL).name.lower():
            argv += ["-ExecutionPolicy", "Bypass"]
        argv += ["-File", str(SCRIPT),
                 "-Action", action, "-PrivateRoot", str(private or self.private),
                 "-SessionId", self.session_id]
        for key, value in kw.items():
            if isinstance(value, bool):
                if value:
                    argv.append("-" + key)
            else:
                argv += ["-" + key, str(value)]
        argv += list(args)
        return subprocess.run(argv, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=160)

    def prepare(self):
        result = self.execute("Prepare")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.session / "p0-session-PRIVATE.json").is_file())
        return result

    def bank(self, name, size):
        path = self.export / name
        with path.open("wb") as stream:
            stream.truncate(size)  # Synthetic bank fixture, no real game memory.
        return path

    def stage(self, phase="B0", *, mem1=None, mem2=None, g0="Cleared",
              same_pause=True, **extra):
        base = dict(
            Phase=phase,
            Mem1Path=str(mem1 if mem1 is not None else self.bank("mem1.bin", MEM1)),
            Mem2Path=str(mem2 if mem2 is not None else self.bank("mem2.bin", MEM2)),
            G0Status=g0, G0EvidenceToken="B1CrashReviewed-01",
            RevisionEvidenceToken="RSPE01Rev1Checked-01",
            DolphinExe=str(self.exe), ExpectedDolphinSha256=self.exe_sha,
            PythonCommand=sys.executable, ExportMethod="ManualPausedExport",
            Observation="Synthetic label; no observed physical strike",
            Uncertainty="No guest-frame identity established",
            PairSamePauseAttested=same_pause,
        )
        base.update(extra)
        return self.execute("Stage", **base)

    def test_prepare_while_g0_blocked_and_no_automatic_dolphin(self):
        self.prepare()
        self.assertFalse((self.session / "B0-MEM1.bin").exists())
        self.assertFalse((self.session / "p0-capture-manifest-PRIVATE.json").exists())
        result = self.stage(g0="Blocked", mem1=self.export / "absent1",
                            mem2=self.export / "absent2")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(str(self.work), result.stdout + result.stderr)
        self.assertFalse((self.session / "B0-MEM1.bin").exists())

    def test_missing_pair_refuses_without_partial_writes(self):
        self.prepare()
        present = self.bank("mem1.bin", MEM1)
        result = self.stage(mem1=present, mem2=self.export / "missing.bin")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.session / "B0-MEM1.bin").exists())
        self.assertFalse((self.session / "B0-MEM2.bin").exists())

    def test_wrong_native_size_refuses(self):
        self.prepare()
        result = self.stage(mem1=self.bank("small.bin", 101),
                            mem2=self.bank("mem2.bin", MEM2))
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.session / "B0-MEM1.bin").exists())

    def test_no_attested_same_pause_and_wrong_dolphin_hash_refuse(self):
        self.prepare()
        a = self.bank("mem1.bin", MEM1)
        b = self.bank("mem2.bin", MEM2)
        self.assertEqual(self.stage(mem1=a, mem2=b, same_pause=False).returncode, 2)
        self.assertEqual(self.stage(mem1=a, mem2=b,
                                    ExpectedDolphinSha256="0" * 64).returncode, 2)
        self.assertFalse((self.session / "B0-MEM1.bin").exists())

    def test_refuse_repo_root_and_synced_output(self):
        (self.work / ".git").mkdir()
        nested = self.work / "WouldLeak"
        nested.mkdir()
        result = self.execute("Prepare", private=nested)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((nested / self.session_id).exists())
        (self.work / ".git").rmdir()
        synced = self.work / "OneDrive" / "Private"
        synced.mkdir(parents=True)
        self.assertEqual(self.execute("Prepare", private=synced).returncode, 2)
        self.assertFalse((synced / self.session_id).exists())

    def test_stages_two_operator_phases_and_finalizes_once(self):
        self.prepare()
        a = self.bank("mem1.bin", MEM1)
        b = self.bank("mem2.bin", MEM2)
        first = self.stage(mem1=a, mem2=b)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.stage(mem1=a, mem2=b).returncode, 2,
                         "Overwrite must be refused")
        mismatched = self.stage(phase="A0", mem1=a, mem2=b,
                                G0EvidenceToken="DifferentCrashReview-02")
        self.assertEqual(mismatched.returncode, 2, "Mixed-session G0 identity refused")
        self.assertFalse((self.session / "A0-MEM1.bin").exists())
        second = self.stage(phase="F0", mem1=a, mem2=b)
        self.assertEqual(second.returncode, 0, second.stderr)
        for label, index in (("B0", 1), ("F0", 2)):
            note = json.loads((self.session / (label + "-observation-PRIVATE.json"))
                              .read_text(encoding="utf-8-sig"))
            self.assertEqual(note["capture_order"], index)
            self.assertEqual(note["dolphin_sha256_private"], self.exe_sha)
            self.assertEqual(note["g0_evidence_token_private"], "B1CrashReviewed-01")
            self.assertFalse(note["guest_frame_verified"])
            self.assertFalse(note["contact_verified"])
            self.assertFalse(note["training_approved"])
        done = self.execute("Finalize", PythonCommand=sys.executable)
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads((self.session / "p0-capture-manifest-PRIVATE.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(len(report["pairs"]), 2)
        self.assertEqual(report["pairs"][0]["phase"], "B0")
        self.assertEqual(report["pairs"][1]["phase"], "F0")
        self.assertEqual(report["pairs"][0]["MEM1"]["bytes"], MEM1)
        self.assertEqual(report["pairs"][0]["MEM2"]["bytes"], MEM2)
        self.assertFalse(report["guest_frame_verified"])
        self.assertFalse(report["training_approved"])
        self.assertEqual(self.execute("Finalize", PythonCommand=sys.executable).returncode, 2)
        self.assertEqual(self.stage(phase="A0", mem1=a, mem2=b).returncode, 2)
        combined = first.stdout + second.stdout + done.stdout
        self.assertNotIn(str(self.work), combined)
        self.assertNotIn(self.exe_sha, combined)


if __name__ == "__main__":
    unittest.main()
