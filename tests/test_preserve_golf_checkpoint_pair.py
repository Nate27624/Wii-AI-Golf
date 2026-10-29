"""Synthetic private checkpoint keeper tests: no emulator or copyrighted bytes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preserve_golf_checkpoint_pair import (
    preserve_pair, MANIFEST_NAME, MEM1_SIZE, MEM2_SIZE,
)

def u32(file, offset, value):
    file.seek(offset)
    file.write(struct.pack(">I", value))

class PrivateCheckpointKeeperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "Wii-AI-Golf-Data"
        self.data.mkdir()
        self.private = self.data / "test-session"
        self.private.mkdir()
        self.dump = self.root / "Dump"
        self.dump.mkdir()
        self.m1 = self.dump / "mem1.raw"
        self.m2 = self.dump / "mem2.raw"
        # Sparse native-sized files, with tiny synthetic source-gated fixtures.
        with self.m1.open("wb") as f:
            f.truncate(MEM1_SIZE)
        with self.m2.open("wb") as f:
            f.truncate(MEM2_SIZE)
        with self.m1.open("r+b") as f:
            f.write(b"RSPE01\x00\x01")
            for off, value in [
                    (0x4BF4D8, 0x80001000),
                    (0x4BF8C4, 0x90001000),
                    (0x4BF868, 0x90001100),
                    (0x4BF8D0, 0x90001200),
                    (0x1000+0x0C, 0x90000100),
                    (0x1000+0x18, 5)]:
                u32(f, off, value)
        with self.m2.open("r+b") as f:
            for off,value in [
                    (0x100+0x1C, 5),
                    (0x100+0x20, 0x80001000),
                    (0x100+0x54, 2),
                    (0x100+0x9C, 0x90000300),
                    (0x1000+0x94, 4),
                    (0x1000+0x98, 1),
                    (0x1100+0x3C, 6),
                    (0x1100+0x48, 31)]:
                u32(f, off, value)
        self.timestamp=1_700_000_000
        self.set_times(0)

    def set_times(self, stage):
        stamp=self.timestamp+stage*400
        os.utime(self.m1,ns=(stamp*10**9,stamp*10**9))
        os.utime(self.m2,ns=((stamp+1)*10**9,(stamp+1)*10**9))

    def keep(self, name, **kwargs):
        return preserve_pair(
            mem1_source=self.m1,
            mem2_source=self.m2,
            private_root=self.private,
            checkpoint=name,
            paused_confirmed=True,
            trusted_data_root=self.data,
            **kwargs)

    def test_valid_B0_copies_both_and_keeps_private_manifest(self):
        ack=self.keep("B0")
        self.assertTrue(ack["scene_source_identity_gated"])
        self.assertFalse(ack["same_frame_or_boot_proven"])
        self.assertEqual(ack["saved_native_banks"],2)
        self.assertEqual((self.private/"B0-MEM1.bin").stat().st_size,MEM1_SIZE)
        self.assertEqual((self.private/"B0-MEM2.bin").stat().st_size,MEM2_SIZE)
        manifest=json.loads((self.private/MANIFEST_NAME).read_text())
        self.assertEqual(tuple(manifest["checkpoints"]),("B0",))
        self.assertFalse(manifest["allowed_to_publish"])
        self.assertNotIn(str(self.root),json.dumps(manifest))
        self.assertEqual(len(manifest["checkpoints"]["B0"]["sha256"]["MEM1"]),64)

    def test_no_repeated_B0_and_no_skipping_to_B2(self):
        with self.assertRaises(ValueError):
            self.keep("B2")
        self.keep("B0")
        with self.assertRaises(ValueError):
            self.keep("B0")
        self.assertFalse((self.private/"B1-MEM1.bin").exists())

    def test_stale_dump_both_banks_rejected(self):
        self.keep("B0")
        with self.assertRaisesRegex(ValueError,"Stale"):
            self.keep("B1")
        self.assertFalse((self.private/"B1-MEM1.bin").exists())

    def test_both_reexported_but_identical_state_is_rejected(self):
        self.keep("B0")
        self.set_times(1)
        with self.assertRaisesRegex(ValueError,"identical"):
            self.keep("B1")
        self.assertFalse((self.private/"B1-MEM1.bin").exists())
        self.assertEqual(len(json.loads(
            (self.private/MANIFEST_NAME).read_text())["checkpoints"]),1)

    def test_changed_B1_then_B2_phase_sequence(self):
        self.keep("B0")
        self.set_times(1)
        with self.m2.open("r+b") as fp:
            u32(fp,0x300+0x74,100)
        self.set_times(1)
        self.keep("B1")
        self.set_times(2)
        with self.m2.open("r+b") as fp:
            u32(fp,0x300+0x74,200)
        self.set_times(2)
        ack=self.keep("B2")
        self.assertEqual(ack["previous_checkpoints_preserved"],2)
        manifest=json.loads((self.private/MANIFEST_NAME).read_text())
        self.assertEqual(tuple(manifest["checkpoints"]),("B0","B1","B2"))

    def test_wrong_game_gate_removes_partial_copies(self):
        with self.m1.open("r+b") as fp:
            fp.seek(0)
            fp.write(b"RSPE00")
        with self.assertRaises(ValueError):
            self.keep("B0")
        self.assertFalse((self.private/"B0-MEM1.bin").exists())
        self.assertFalse((self.private/"B0-MEM2.bin").exists())
        self.assertFalse((self.private/MANIFEST_NAME).exists())

    def test_B4_requires_user_observed_landed_shot(self):
        with self.assertRaisesRegex(ValueError,"observed landed"):
            self.keep("B4")

    def test_rejects_unpaused_or_untrusted_output(self):
        with self.assertRaises(ValueError):
            preserve_pair(
                mem1_source=self.m1,mem2_source=self.m2,
                private_root=self.private,checkpoint="B0",
                paused_confirmed=False,trusted_data_root=self.data)
        other=self.root/"repo"
        other.mkdir()
        with self.assertRaisesRegex(ValueError,"within"):
            preserve_pair(
                mem1_source=self.m1,mem2_source=self.m2,
                private_root=other,checkpoint="B0",
                paused_confirmed=True,trusted_data_root=self.data)

    def test_rejects_reversed_dump_order(self):
        stamp=self.timestamp
        os.utime(self.m1,ns=((stamp+2)*10**9,)*2)
        os.utime(self.m2,ns=((stamp+1)*10**9,)*2)
        with self.assertRaisesRegex(ValueError,"newer"):
            self.keep("B0")

if __name__ == "__main__":
    unittest.main()
