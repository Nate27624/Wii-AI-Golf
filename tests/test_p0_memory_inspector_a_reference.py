"""Synthetic sealed local A-trial reference tests: no Dolphin or real guest data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.a_reference import AReference, PassiveAIndicator, discover_reference, load_reference

SOURCE = "b" * 64
CAL = ("R0", "H0", "R1", "H1", "R2", "H2", "R3", "B0", "B1", "B2")
TRUTH = {"B0": "RELEASED", "B1": "RELEASED", "B2": "PRESSED"}


def bits(held: bool) -> list[str]:
    return [f"{(17 if held else 8) if i in (29, 37, 39, 40, 42, 44, 46, 48) else 42:08x}"
            for i in range(51)]


def fixture(root: Path, *, source: str = SOURCE, tamper: str | None = None) -> Path:
    folder = root / "p0-a-state-blind-20261030-test-PRIVATE"
    folder.mkdir()
    packets = []
    for phase in CAL:
        held = phase.startswith("H") or phase == "B2"
        for index in range(3):
            sample = len(packets)
            event = {"kind": "candidate_sample", "phase": phase, "sample_index": index,
                     "start_monotonic_ns": 1000 + sample * 100,
                     "end_monotonic_ns": 1050 + sample * 100,
                     "source_identity_digest_private": source,
                     "candidate_words_private_be_u32_hex": {
                         "selected_player_record_all_51": bits(held)}}
            if tamper == "owner" and sample == 24:
                event["source_identity_digest_private"] = "c" * 64
            if tamper == "heldout" and phase == "H2":
                event["candidate_words_private_be_u32_hex"]["selected_player_record_all_51"] = bits(False)
            packets.append(event)
    payload = "\n".join(json.dumps(p) for p in packets).encode("utf-8") + b"\n"
    digest = hashlib.sha256(payload).hexdigest()
    (folder / "candidate-events-PRIVATE.jsonl").write_bytes(payload)
    (folder / "manifest-PRIVATE.json").write_text(json.dumps({
        "status": "ABORTED", "reason_code": "AIM_MOVED_NO_CONTACT_PROTOCOL_STOP",
        "protocol": "p0-a-state-blind-v1", "candidate_samples": len(packets),
        "stream_sha256": digest, "operator_intent_truth": TRUTH,
        "predictions": TRUTH, "training_approved": False}))
    return folder


def record(held: bool) -> tuple[int, ...]:
    return tuple(int(w, 16) for w in bits(held))


class PrivateAReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_original_aborted_later_trial_reuses_three_valid_blind_windows(self):
        ref = load_reference(fixture(self.root))
        self.assertEqual(ref.source_digest, SOURCE)
        self.assertEqual(len(ref.model), 8)
        indicator = PassiveAIndicator(ref)
        self.assertEqual(indicator.observe(record(True), SOURCE, (1, 2, 3), (9,)), "UNKNOWN")
        self.assertEqual(indicator.observe(record(True), SOURCE, (1, 2, 3), (9,)), "PRESSED")
        self.assertEqual(indicator.observe(record(False), SOURCE, (1, 2, 3), (9,)), "UNKNOWN")
        self.assertEqual(indicator.observe(record(False), SOURCE, (1, 2, 3), (9,)), "RELEASED")

    def test_tampered_sha_fails_closed(self):
        folder = fixture(self.root)
        file = folder / "candidate-events-PRIVATE.jsonl"
        file.write_bytes(file.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            load_reference(folder)

    def test_wrong_owner_or_unfit_heldout_rejected(self):
        for mode in ("owner", "heldout"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    load_reference(fixture(Path(temp), tamper=mode))

    def test_blind_truth_failure_rejected(self):
        folder = fixture(self.root)
        path = folder / "manifest-PRIVATE.json"
        obj = json.loads(path.read_text())
        obj["operator_intent_truth"]["B2"] = "RELEASED"
        path.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            load_reference(folder)

    def test_wrong_source_unknown_and_unexpected_motion_blocks(self):
        ref = load_reference(fixture(self.root))
        monitor = PassiveAIndicator(ref)
        self.assertEqual(monitor.observe(record(True), "c"*64, (1, 2, 3), (9,)), "UNKNOWN")
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 3), (9,)), "UNKNOWN")
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 3), (9,)), "PRESSED")
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 4), (9,)), "UNKNOWN")
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 4), (9,)), "UNKNOWN")
        monitor.clear()
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 4), (9,)), "UNKNOWN")
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 4), (9,)), "PRESSED")

    def test_only_sibling_private_capture_directory_is_searched(self):
        worktree = self.root / "Wii-AI-Golf-Inspector"
        worktree.mkdir()
        data = self.root / "Wii-AI-Golf-Data" / "captures"
        data.mkdir(parents=True)
        fixture(data)
        self.assertEqual(discover_reference(worktree).source_digest, SOURCE)
        self.assertIsNone(discover_reference(self.root / "unrelated" / "repository"))

    def test_no_model_leaves_plain_unknown(self):
        monitor = PassiveAIndicator(None)
        self.assertEqual(monitor.observe(record(True), SOURCE, (1, 2, 3), (9,)), "UNKNOWN")

    def test_gui_a_calibration_buttons_not_present(self):
        content = (ROOT / "src" / "wii_ai_golf" / "inspector" / "gui.py").read_text()
        self.assertNotIn("Capture next A window", content)
        self.assertNotIn("Reset A detector", content)
        self.assertIn('self.a_status.set("A " + state)', content)

if __name__ == "__main__":
    unittest.main()
