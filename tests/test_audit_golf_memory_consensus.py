"""Synthetic-only cross-capture RAM consensus tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("golf_memory_consensus", ROOT / "scripts" / "audit_golf_memory_consensus.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(phase, effect=0, config=0):
    effect_bytes = bytearray(0x200)
    effect_bytes[0x1EC:0x1F0] = effect.to_bytes(4, "big")
    config_bytes = bytearray(0xA0)
    config_bytes[0x94:0x98] = (4).to_bytes(4, "big")
    config_bytes[0x9C:0xA0] = config.to_bytes(4, "big")
    return {"game_id": "RSPE01", "disc_revision": 1, "phase": phase, "windows": {
        "minimap_ball_effect": {"address": "0x80020000", "bytes_hex": effect_bytes.hex()},
        "golf_config": {"address": "0x80010000", "bytes_hex": config_bytes.hex()}}}


def make(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


class CrossCaptureTests(unittest.TestCase):
    def test_consensus_repeats_and_demotes_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one = make(root / "one.jsonl", [row("pre", 1, 1), row("pre", 2, 2), row("post", 3, 3)])
            two = make(root / "two.jsonl", [row("pre", 5, 4), row("pre", 6, 5), row("post", 7, 6)])
            report = mod.aggregate([one, two])
            self.assertEqual(report["files_analyzed"], 2)
            self.assertEqual(report["candidate_count"], 2)
            self.assertEqual(report["candidates"][0]["window"], "golf_config")
            self.assertEqual(report["candidates"][0]["captures_within_phase"], 2)
            self.assertEqual(report["candidates"][1]["window"], "minimap_ball_effect")

    def test_bad_capture_skipped_not_publicized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            good = make(root / "good.jsonl", [row("pre", 1), row("post", 2)])
            bad = root / "private-secret.jsonl"
            bad.write_text("not json", encoding="utf-8")
            report = mod.aggregate([good, bad])
            self.assertEqual(report["files_analyzed"], 1)
            self.assertEqual(len(report["files_skipped"]), 1)
            self.assertNotIn(str(bad), str(report))

    def test_relocation_not_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = row("pre", 1)
            after = row("post", 2)
            after["windows"]["minimap_ball_effect"]["address"] = "0x80030000"
            report = mod.aggregate([make(root / "one.jsonl", [before, after])])
            self.assertEqual(report["files_analyzed"], 1)
            self.assertEqual(report["candidate_count"], 0)
            self.assertEqual(report["capture_summaries"][0]["relocation_skips"], 1)

    def test_bounds_and_empty(self):
        with self.assertRaises(ValueError):
            mod.aggregate([])
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(mod.main(["--capture-dir", temp]), 1)

    def test_cli_output_has_no_absolute_address_or_raw_hex(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            capture = make(root / "outcome-abc-RAW-PRIVATE.jsonl",
                           [row("pre", 1), row("post", 2)])
            out = root.parent / "golf-memory-consensus-fixture.json"
            if out.exists():
                out.unlink()
            try:
                self.assertEqual(mod.main(["--capture-dir", temp, "--out", str(out)]), 0)
                payload = out.read_text(encoding="utf-8")
                self.assertNotIn("0x80020000", payload)
                self.assertNotIn(str(capture), payload)
            finally:
                if out.exists():
                    out.unlink()


if __name__ == "__main__":
    unittest.main()
