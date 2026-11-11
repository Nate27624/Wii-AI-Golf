"""Fully offline synthetic native-bank streaming checks; no Dolphin or real data."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture_full_ram_private.py"
spec = importlib.util.spec_from_file_location("capture_full_ram_private", SCRIPT)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

B1 = m.Bank("MEM1", 0x80000000, 64, "mem1.raw")
B2 = m.Bank("MEM2", 0x90000000, 128, "mem2.raw")
BANKS = (B1, B2)


class FakeRPC:
    def __init__(self, mode=4, broken_at=None):
        self.frame = 0
        self.mode = mode
        self.calls = []
        self.broken_at = broken_at
        self.reads = 0
        self.mem1 = m.REV1_HEADER + bytes(range(8, 256))
        self.mem2 = bytes(((i * 61 + 3) % 256) for i in range(256))

    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == "bridge.ping":
            return {"bridge_version": "test-v1"}
        if method == "frame.get_count":
            self.frame += 1
            return self.frame
        if method == "memory.read_u32":
            return 0x90010000 if params[0] == m.GAME_CONFIG_PTR else self.mode
        if method == "memory.read_bytes":
            self.reads += 1
            if self.broken_at is not None and self.reads >= self.broken_at:
                return "NOT_HEX"
            addr, n = params
            if 0x80000000 <= addr < 0x80000100:
                pos = addr - 0x80000000
                return self.mem1[pos:pos+n].hex()
            if 0x90000000 <= addr < 0x90000100:
                pos = addr - 0x90000000
                return self.mem2[pos:pos+n].hex()
            raise AssertionError("unexpected region")
        raise AssertionError(method)


class FullRamCaptureTests(unittest.TestCase):
    def test_expected_native_wii_bank_dimensions(self):
        self.assertEqual([b.address for b in m.BANKS], [0x80000000, 0x90000000])
        self.assertEqual([b.length for b in m.BANKS], [24*1024**2, 64*1024**2])
        self.assertEqual(sum(b.length for b in m.BANKS), 88*1024**2)
        self.assertLess(m.MAX_RPC_CHUNK*2 + 1024, 65536)

    def test_probe_read_only_and_does_not_write_files(self):
        class Context:
            def __enter__(self):
                self.rpc = FakeRPC()
                return self.rpc
            def __exit__(self, *args):
                return False
        ctx = Context()
        with patch.object(m, "FelkRPC", return_value=ctx), patch.object(m.time, "sleep"), patch.object(m, "_secure_root", side_effect=AssertionError("probe must not touch disk")):
            self.assertEqual(m.main(["--probe", "--phase", "PRE"]), 0)
        self.assertIn("memory.read_bytes", [name for name, _ in ctx.rpc.calls])
        self.assertNotIn("controller.set_wiimote_buttons", [name for name, _ in ctx.rpc.calls])

    def test_full_banks_saved_as_exact_binary_not_json_only(self):
        with tempfile.TemporaryDirectory() as td:
            fake = FakeRPC()
            with patch.object(m.time, "sleep"):
                report = m.capture(fake, captures=Path(td), session="FULLRAM-T1234-PRIVATE",
                                   phase="PRE", confirmed=True, banks=BANKS, chunk_bytes=16,
                                   progress=lambda _: None)
            folder = Path(td)/"FULLRAM-T1234-PRIVATE"/"PRE-ROLLING"
            self.assertEqual((folder/"mem1.raw").read_bytes(), fake.mem1[:64])
            self.assertEqual((folder/"mem2.raw").read_bytes(), fake.mem2[:128])
            self.assertEqual((folder/"mem1.raw").stat().st_size, 64)
            self.assertEqual((folder/"mem2.raw").stat().st_size, 128)
            self.assertGreater(report["non_atomic_frame_span"], 0)
            for key in ("same_guest_frame_verified", "same_paused_bank_pair",
                        "approved_for_native_prepost_comparator", "approved_for_model_training",
                        "allowed_to_publish", "full_memory_banks_present"):
                self.assertFalse(report[key])
            manifest = json.loads((folder/"capture-meta-PRIVATE.json").read_text())
            self.assertEqual([x["bytes"] for x in manifest["banks"]], [64, 128])
            self.assertTrue(all(len(x["sha256"]) == 64 for x in manifest["banks"]))
            self.assertFalse((Path(td)/"FULLRAM-T1234-PRIVATE"/"capture-active.lock").exists())

    def test_second_same_phase_refused_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td, patch.object(m.time, "sleep"):
            def run():
                return m.capture(FakeRPC(), captures=Path(td), session="FULLRAM-T1234-PRIVATE",
                                 phase="PRE", confirmed=True, banks=BANKS,
                                 chunk_bytes=16, progress=lambda _: None)
            run()
            path = Path(td)/"FULLRAM-T1234-PRIVATE"/"PRE-ROLLING"/"mem1.raw"
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                run()
            self.assertEqual(original, path.read_bytes())

    def test_invalid_mode_fails_without_writing_any_bank(self):
        with tempfile.TemporaryDirectory() as td, patch.object(m.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "mode 4"):
                m.capture(FakeRPC(mode=3), captures=Path(td), session="FULLRAM-T1234-PRIVATE",
                          phase="PRE", confirmed=True, banks=BANKS,
                          chunk_bytes=16, progress=lambda _: None)
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_corrupted_hex_never_finalizes_memory(self):
        with tempfile.TemporaryDirectory() as td, patch.object(m.time, "sleep"):
            with self.assertRaisesRegex(ValueError, "bridge byte read"):
                m.capture(FakeRPC(broken_at=5), captures=Path(td), session="FULLRAM-T1234-PRIVATE",
                          phase="PRE", confirmed=True, banks=BANKS, chunk_bytes=16,
                          progress=lambda _: None)
            folder = Path(td)/"FULLRAM-T1234-PRIVATE"/"PRE-ROLLING"
            self.assertFalse((folder/"mem1.raw").exists())
            self.assertFalse((folder/"mem2.raw").exists())
            self.assertFalse((folder/"capture-meta-PRIVATE.json").exists())

    def test_post_requires_observed_displacement(self):
        with self.assertRaisesRegex(ValueError, "POST needs visible displacement"):
            m._safe_phase("POST", confirmed=True, observed_displacement=False)
        with self.assertRaisesRegex(ValueError, "only applies to POST"):
            m._safe_phase("PRE", confirmed=True, observed_displacement=True)

    def test_session_rejects_paths_and_untrusted_input(self):
        for session in ("../../../x", "/tmp/FULLRAM-2026-PRIVATE", "FULLRAM-..-PRIVATE",
                        "FULLRAM-x-PRIVATE", "FULLRAM-x PRIVATE", ""):
            with self.subTest(session=session), self.assertRaises(ValueError):
                m._check_session(session)

    def test_bounds_and_hex_length(self):
        rpc = FakeRPC()
        self.assertEqual(m._read_exact(rpc, B1.address, 8), m.REV1_HEADER)
        with self.assertRaises(ValueError):
            m._read_exact(rpc, B1.address, 0)
        with self.assertRaises(ValueError):
            m._read_exact(rpc, B1.address, m.MAX_RPC_CHUNK + 1)

    def test_result_phase_does_not_claim_mode4(self):
        with tempfile.TemporaryDirectory() as td, patch.object(m.time, "sleep"):
            report = m.capture(FakeRPC(mode=7), captures=Path(td),
                               session="FULLRAM-T1234-PRIVATE", phase="RESULT",
                               confirmed=True, banks=BANKS, chunk_bytes=16,
                               progress=lambda _: None)
            self.assertFalse(report["golf_mode4_verified_at_intervals"])

    def test_frozen_emulation_rejected(self):
        rpc = FakeRPC()
        previous = rpc.call
        rpc.call = lambda name, params=None: 1 if name == "frame.get_count" else previous(name, params)
        with tempfile.TemporaryDirectory() as td, patch.object(m.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "paused/not advancing"):
                m.capture(rpc, captures=Path(td), session="FULLRAM-T1234-PRIVATE",
                          phase="PRE", confirmed=True, banks=BANKS)

    def test_dry_run_no_connection_or_write(self):
        with patch.object(m, "FelkRPC", side_effect=AssertionError("must not connect")):
            self.assertEqual(m.main(["--session", "FULLRAM-T1234-PRIVATE"]), 0)

    def test_cli_requires_explicit_capture_and_operator_label(self):
        with patch.object(m, "FelkRPC", side_effect=AssertionError("must not connect")):
            self.assertEqual(m.main(["--capture", "--session", "FULLRAM-T1234-PRIVATE"]), 1)

    def test_header_belongs_to_rev1(self):
        rpc = FakeRPC()
        rpc.mem1 = b"RSPE01\x00\x00" + rpc.mem1[8:]
        with self.assertRaisesRegex(RuntimeError, "RSPE01 revision 1"):
            m._check_header_and_mode(rpc, require_mode=True)


if __name__ == "__main__":
    unittest.main()
