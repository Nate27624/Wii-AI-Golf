"""Synthetic four-phase native-size fixtures for the read-only PowerShell mapper."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "Invoke-P0SourceFieldMatrix.ps1"
MEM1, MEM2 = 0x80000000, 0x90000000
S1, S2 = 24 * 1024 * 1024, 64 * 1024 * 1024
MGR = MEM1 + 0x10000
CONFIG, FIELD, PM, SCENE = [MEM2 + x for x in (0x20000, 0x10000, 0x30000, 0x40000)]
BALL, START, PIN, CUP = [MEM2 + x for x in (0x50000, 0x60000, 0x70000, 0x80000)]
REC = PM + 4
PHASES = ("B0", "B1", "B2", "B3")
LABELS = ("idle_baseline", "idle_delayed", "wasd_aim_only", "idle_after_aim")


def put(file, base, addr, value):
    file.seek(addr - base)
    file.write(struct.pack(">I", value))

def vec(file, base, addr, values):
    for i, v in enumerate(values):
        put(file, base, addr + 4*i, struct.unpack(">I", struct.pack(">f", float(v)))[0])

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1 << 20), b""):
            h.update(buf)
    return h.hexdigest()

def fixture(private):
    checkpoints = {}
    for i, phase in enumerate(PHASES):
        a_path, b_path = [private/f"{phase}-{bank}.bin" for bank in ("MEM1", "MEM2")]
        for path, length in ((a_path,S1),(b_path,S2)):
            with path.open("wb") as f: f.truncate(length)
        with a_path.open("r+b") as a, b_path.open("r+b") as b:
            a.write(b"RSPE01\x00\x01")
            for addr, value in (
                (0x804BF4D8, MGR), (0x804BF4DC,0),
                (0x804BF8C4, CONFIG),(0x804BF868,FIELD),(0x804BF8D0,PM),
                (MGR+0x18,5),(MGR+0x0C,SCENE)):
                put(a,MEM1,addr,value)
            for addr, value in (
                (SCENE,0x803C7718),(PM,0x803C7DD0),(BALL,0x803C7918),
                (SCENE+0x1C,5),(SCENE+0x20,MGR),(SCENE+0x54,2),
                (CONFIG+0x94,4),(CONFIG+0x98,1),
                (FIELD+0x50,START),(FIELD+0x44,PIN),(FIELD+0x54,CUP),
                (PM+0x334,REC),(REC+0x88,BALL),(BALL+0x4C,BALL+0x30),
                (START+0x48,START+0x0C),(START+0x4C,START+0x30),
                (PIN+0x4C,PIN+0x30)):
                put(b,MEM2,addr,value)
            for addr, value in (
                (CONFIG+0x04+4*5, 9 if i==2 else 0),
                (FIELD+0x30, 5), (FIELD+0x3C, 1), (FIELD+0x48, 4),
                (FIELD+0x10, 2 if i==2 else 0),
                (FIELD+0x68, BALL if i==2 else 0)):
                put(b,MEM2,addr,value)
            # C++ booleans are one byte at the source-aligned field offset.
            for addr in (FIELD+0x6C, FIELD+0x7C, FIELD+0x88, FIELD+0xA4):
                b.seek(addr-MEM2)
                b.write(bytes([1 if i==2 else 0]))
            for addr, values in (
                (REC+0x54,(1,2,3)),(REC+0x60,(1,2,3)),
                (BALL+0x30,(1,2,3)),(BALL+0xCC,(1,2,3)),
                (BALL+0xF0,(1,2,3)),(BALL+0xFC,(1,2+int(i==2),3)),
                (START+0x30,(1,2,3)),(PIN+0x30,(5,6,7)),(CUP+0x30,(5,6,7))):
                vec(b,MEM2,addr,values)
            vec(b,MEM2,REC+0x3C,(0.5 if i==2 else 0.25,))
            vec(b,MEM2,REC+0x40, tuple(x+(0.1 if i==2 else 0) for x in (1,0,0,1)))
        checkpoints[phase] = {
            "phase_operator_label":LABELS[i],
            "operator_reports_gui_paused":True,
            "scene_source_chain_gated":True,
            "native_sizes_valid":True,
            "observed_game_mode":4,
            "sha256":{"MEM1":sha(a_path),"MEM2":sha(b_path)}
        }
    (private/"checkpoint-manifest-PRIVATE.json").write_text(
        json.dumps({"schema_version":1,"kind":"local-private-golf-paired-checkpoints",
                    "checkpoints":checkpoints}),encoding="utf8")

@unittest.skipUnless(shutil.which("pwsh") or shutil.which("powershell"), "PowerShell host not installed")
class MatrixPowerShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.data=Path(cls.tmp.name)/"Wii-AI-Golf-Data"
        cls.private=cls.data/"ball-study-synthetic"
        cls.private.mkdir(parents=True)
        cls.ps=shutil.which("pwsh") or shutil.which("powershell")
        fixture(cls.private)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def invoke(self):
        return subprocess.run([self.ps,"-NoProfile","-NonInteractive","-File",str(SCRIPT),
             "-PrivateRoot",str(self.private),"-DataRoot",str(self.data)],
             capture_output=True,text=True,timeout=120)

    def test_good_matrix_is_counts_only_and_not_training(self):
        p=self.invoke()
        self.assertEqual(p.returncode,0, (p.stdout+p.stderr)[-1000:])
        r=json.loads(p.stdout)
        self.assertTrue(r["hash_checks_all_passed"])
        self.assertTrue(r["selected_owner_slot_hole_stable"])
        self.assertTrue(r["fixed_scene_geometry_candidate_unchanged"])
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["actual_ball_world_xyz_verified"])
        self.assertEqual(len(r["field_comparisons"]),23)
        rows={x["registry_id"]:x for x in r["field_comparisons"]}
        self.assertEqual(rows["golf.ball_object.conditional_cache_fc"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.player.selected_record.aim_rotation"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.ball_object.current_translation_candidate"]["changed_components_B1_B2"],0)
        self.assertEqual(rows["golf.config.player_scores_4x9_candidate"]["component_count"],36)
        self.assertEqual(rows["golf.config.player_scores_4x9_candidate"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.config.mode_id"]["changed_components_B1_B2"],0)
        self.assertEqual(rows["golf.field.wind_object_pointer_present"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.field.minimap_visible"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.field.tree_shadow_update_timer"]["changed_components_B1_B2"],1)
        self.assertEqual(rows["golf.field.target_object_count"]["changed_components_B1_B2"],0)
        self.assertEqual(rows["golf.field.wind_object_pointer_present"]["evidence_class"],"pointer_presence_not_wind_speed_or_direction")
        self.assertEqual(rows["golf.config.player_scores_4x9_candidate"]["evidence_class"],"score_table_source_defined_not_verified_shot_label")
        self.assertNotIn(str(self.private),p.stdout)
        self.assertNotIn("0x900",p.stdout)

    def test_tampered_digest_fails_without_private_contents(self):
        path=self.private/"checkpoint-manifest-PRIVATE.json"
        data=json.loads(path.read_text())
        original=data["checkpoints"]["B1"]["sha256"]["MEM2"]
        data["checkpoints"]["B1"]["sha256"]["MEM2"]="0"*64
        path.write_text(json.dumps(data))
        try:
            p=self.invoke()
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ABORTED",p.stderr)
            self.assertNotIn(str(self.private),p.stderr)
        finally:
            data["checkpoints"]["B1"]["sha256"]["MEM2"]=original
            path.write_text(json.dumps(data))

    def test_wrong_scene_even_with_rehashed_bank_fails(self):
        bank=self.private/"B2-MEM1.bin"
        with bank.open("r+b") as f: put(f,MEM1,MGR+0x18,9)
        path=self.private/"checkpoint-manifest-PRIVATE.json"
        data=json.loads(path.read_text())
        original=data["checkpoints"]["B2"]["sha256"]["MEM1"]
        data["checkpoints"]["B2"]["sha256"]["MEM1"]=sha(bank)
        path.write_text(json.dumps(data))
        try:
            p=self.invoke()
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ABORTED",p.stderr)
        finally:
            with bank.open("r+b") as f: put(f,MEM1,MGR+0x18,5)
            data["checkpoints"]["B2"]["sha256"]["MEM1"]=original
            path.write_text(json.dumps(data))


    def test_mismatched_source_data_hint_rejected_with_rehashed_bank(self):
        bank=self.private/"B2-MEM2.bin"
        with bank.open("r+b") as f: put(f,MEM2,BALL,0)
        path=self.private/"checkpoint-manifest-PRIVATE.json"
        data=json.loads(path.read_text())
        old=data["checkpoints"]["B2"]["sha256"]["MEM2"]
        data["checkpoints"]["B2"]["sha256"]["MEM2"]=sha(bank)
        path.write_text(json.dumps(data))
        try:
            p=self.invoke()
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ABORTED",p.stderr)
            self.assertNotIn(str(self.private),p.stderr)
        finally:
            with bank.open("r+b") as f: put(f,MEM2,BALL,0x803C7918)
            data["checkpoints"]["B2"]["sha256"]["MEM2"]=old
            path.write_text(json.dumps(data))

    def test_wrong_operator_phase_label_is_not_trusted(self):
        path=self.private/"checkpoint-manifest-PRIVATE.json"
        data=json.loads(path.read_text())
        old=data["checkpoints"]["B2"]["phase_operator_label"]
        data["checkpoints"]["B2"]["phase_operator_label"]="flight_verified"
        path.write_text(json.dumps(data))
        try:
            p=self.invoke()
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ABORTED",p.stderr)
        finally:
            data["checkpoints"]["B2"]["phase_operator_label"]=old
            path.write_text(json.dumps(data))


    def test_invalid_ui_bool_fails_even_with_matching_manifest_hash(self):
        bank=self.private/"B2-MEM2.bin"
        with bank.open("r+b") as f:
            f.seek(FIELD+0x88-MEM2)
            f.write(b"\x02")
        path=self.private/"checkpoint-manifest-PRIVATE.json"
        data=json.loads(path.read_text())
        old=data["checkpoints"]["B2"]["sha256"]["MEM2"]
        data["checkpoints"]["B2"]["sha256"]["MEM2"]=sha(bank)
        path.write_text(json.dumps(data))
        try:
            p=self.invoke()
            self.assertNotEqual(p.returncode,0)
            self.assertIn("ABORTED",p.stderr)
        finally:
            with bank.open("r+b") as f:
                f.seek(FIELD+0x88-MEM2)
                f.write(b"\x01")
            data["checkpoints"]["B2"]["sha256"]["MEM2"]=old
            path.write_text(json.dumps(data))

class ContractTests(unittest.TestCase):
    def test_no_live_actions_or_upload(self):
        src=SCRIPT.read_text(encoding="utf8")
        for required in ("Get-FileHash","FileAccess]::Read","ConvertTo-Json",
                         "training_approved = $false","capture_provenance",
                         "actual_ball_world_xyz_verified"):
            self.assertIn(required,src)
        for forbidden in ("Invoke-WebRequest","Invoke-RestMethod","Start-Process",
                          "git push","Dolphin.exe","Remove-Item","Set-Content"):
            self.assertNotIn(forbidden,src)

if __name__=="__main__":
    unittest.main()
