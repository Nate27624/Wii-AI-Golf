"""Synthetic-only SHA-gated replay regressions; no ROM, Dolphin or real captures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.replay import (AIM, BALL, CACHE, NESTED, CaptureError,
                                         float_hypothesis, load_replay, word_bits)


def bits(value: float) -> str:
    return struct.pack(">f", value).hex()


def event(phase="B0", index=0, source="a" * 64):
    return {
        "phase": phase, "sample_index": index, "start_monotonic_ns": 1000 + index * 1000,
        "end_monotonic_ns": 1200 + index * 1000,
        "bridge_frame_count_bracket_NOT_GUEST_PHYSICS": [10 + index, 11 + index],
        "source_identity_digest_private": source, "source_layout_qualified": True,
        "candidate_words_private_be_u32_hex": {
            BALL: [bits(2.2 + index), bits(-5.5), bits(-318)],
            CACHE: [bits(10), bits(20), bits(-350)],
            NESTED: [bits(2.2 + index), bits(-5.5), bits(-318)],
            AIM: [bits(0.25)]},
        "operator_annotation": "synthetic only"
    }


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.capture = self.base / "events-PRIVATE.jsonl"
        self.manifest = self.base / "manifest.json"

    def save(self, events, *, status="complete", schema="sha256"):
        blob = ("\n".join(json.dumps(e) for e in events) + "\n").encode()
        self.capture.write_bytes(blob)
        digest = hashlib.sha256(blob).hexdigest()
        manifest = ({schema: digest, "status": status} if schema != "files" else
                    {"files": [{"path": self.capture.name, "sha256": digest}], "status": status})
        self.manifest.write_text(json.dumps(manifest))
        return load_replay(self.capture, self.manifest)

    def test_sha_valid_raw_bits_and_floats(self):
        replay = self.save([event(), event("L1", 1)])
        self.assertEqual(len(replay.samples), 2)
        self.assertEqual(replay.samples[0].words[BALL][0], int(bits(2.2), 16))
        self.assertAlmostEqual(replay.samples[0].vec(BALL)[0], 2.2, places=5)
        self.assertEqual(replay.samples[0].words[CACHE][0], int(bits(10), 16))
        self.assertFalse(replay.training_approved)
        self.assertEqual(replay.terminated, "complete")

    def test_manifest_files_shape(self):
        self.assertEqual(len(self.save([event()], schema="files").samples), 1)

    def test_sha_mismatch(self):
        self.save([event()])
        with self.capture.open("ab") as out:
            out.write(b" ")
        with self.assertRaisesRegex(CaptureError, "SHA-256 mismatch"):
            load_replay(self.capture, self.manifest)

    def test_manifest_missing_digest(self):
        self.capture.write_text(json.dumps(event()) + "\n")
        self.manifest.write_text("{}")
        with self.assertRaisesRegex(CaptureError, "SHA-256"):
            load_replay(self.capture, self.manifest)

    def test_manifest_wrong_file(self):
        self.save([event()])
        data = json.loads(self.manifest.read_text())
        data["capture_file"] = "other.jsonl"
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(CaptureError, "different capture"):
            load_replay(self.capture, self.manifest)

    def test_manifest_conflicting_digests(self):
        self.save([event()])
        data = json.loads(self.manifest.read_text())
        data["capture_sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(CaptureError, "conflicting"):
            load_replay(self.capture, self.manifest)

    def test_missing_fields_fail_closed(self):
        bad = event()
        bad.pop("candidate_words_private_be_u32_hex")
        with self.assertRaisesRegex(CaptureError, "missing candidate"):
            self.save([bad])

    def test_invalid_words_fail_closed(self):
        bad = event()
        bad["candidate_words_private_be_u32_hex"][BALL] = ["baddd", "00000000", "00000000"]
        with self.assertRaisesRegex(CaptureError, "eight hexadecimal"):
            self.save([bad])
        with self.assertRaises(CaptureError):
            word_bits(True)
        with self.assertRaises(CaptureError):
            word_bits("0x123456789")

    def test_nonfinite_keeps_raw_word(self):
        bad = event()
        bad["candidate_words_private_be_u32_hex"][BALL][0] = "7fc00000"
        sample = self.save([bad]).samples[0]
        self.assertEqual(sample.words[BALL][0], 0x7FC00000)
        self.assertIsNone(sample.vec(BALL))
        self.assertIsNone(float_hypothesis(0x7F800000))

    def test_preserves_phase_and_quarantine(self):
        a, b = event(), event("M1", 1)
        b["segment_status"] = "quarantined"
        replay = self.save([a, b], status="aborted")
        self.assertEqual([s.phase for s in replay.samples], ["B0", "M1"])
        self.assertEqual(replay.terminated, "aborted")
        self.assertEqual(replay.samples[1].state, "quarantined")
        self.assertTrue(any("contact frame unverified" in msg for msg in replay.warnings))

    def test_last_truncated_jsonl_preserves_completed_packets(self):
        self.save([event()])
        blob = self.capture.read_bytes() + b'{"phase":"M1","candidate_'
        self.capture.write_bytes(blob)
        self.manifest.write_text(json.dumps({"sha256": hashlib.sha256(blob).hexdigest(), "status": "aborted"}))
        r = load_replay(self.capture, self.manifest)
        self.assertEqual(r.terminated, "incomplete")
        self.assertEqual(len(r.samples), 1)
        self.assertTrue(any("truncated" in m for m in r.warnings))

    def test_bad_middle_json_fails(self):
        blob = (json.dumps(event()) + "\n{bad\n" + json.dumps(event("L1", 1)) + "\n").encode()
        self.capture.write_bytes(blob)
        self.manifest.write_text(json.dumps({"sha256": hashlib.sha256(blob).hexdigest()}))
        with self.assertRaisesRegex(CaptureError, "event line 2"):
            load_replay(self.capture, self.manifest)

    def test_nonatomic_alias_warning(self):
        e = event()
        e["candidate_words_private_be_u32_hex"][NESTED][0] = bits(45)
        r = self.save([e])
        self.assertTrue(any("sequential reads" in m for m in r.messages(r.samples[0])))

    def test_source_identity_swaps_warn(self):
        replay = self.save([event(), event("M0", 1, "b" * 64)])
        self.assertTrue(any("Source identity" in x for x in replay.warnings))
        self.assertTrue(any("SOURCE IDENTITY CHANGED" in x for x in replay.messages(replay.samples[1])))

    def test_invalid_frame_or_time_abstains(self):
        e = event()
        e["end_monotonic_ns"] = -1
        with self.assertRaisesRegex(CaptureError, "nonnegative"):
            self.save([e])
        e = event()
        e["bridge_frame_count_bracket_NOT_GUEST_PHYSICS"] = [9, 8]
        with self.assertRaisesRegex(CaptureError, "frame bracket"):
            self.save([e])

    def test_missing_timing_or_source_not_qualified(self):
        e = event()
        e.pop("start_monotonic_ns")
        e.pop("source_layout_qualified")
        r = self.save([e])
        self.assertFalse(r.samples[0].source_qualified)
        self.assertTrue(any("Missing host sampling bracket" in m for m in r.messages(r.samples[0])))

    def archive_fixture(self, *, swap_owner=False, wrong_phase=False):
        phases = [p for p in ("I0", "AH", "AR", "M0", "I1") for _ in range(8)] + ["M1"] * 6
        records = [{"event": "operator_phase_marker", "phase": "I0", "label": "Operator idle"}]
        for n, phase in enumerate(phases):
            sample = event(phase, n % 8 if n < 40 else n - 40)
            sample["event"] = "candidate_sample"
            sample["monotonic_start_ns"] = 5000 + n * 1000
            sample["monotonic_end_ns"] = 5300 + n * 1000
            sample.pop("start_monotonic_ns")
            sample.pop("end_monotonic_ns")
            sample["source_owner_pointer_digest_private"] = "same-archive-owner" if not (swap_owner and n == 41) else "changed-owner"
            sample.pop("source_identity_digest_private")
            if wrong_phase and n == 20:
                sample["phase"] = "R1"
            if n == 40:
                records.append({"event": "human_visual_observation", "phase": "M1", "observation": "Human HIT (timing unknown)"})
            records.append(sample)
        blob = ("\n".join(json.dumps(e) for e in records) + "\n").encode()
        self.capture.write_bytes(blob)
        self.manifest.write_text(json.dumps({"status": "ABORTED", "protocol": "manual-a-miss-v1",
                                             "run_samples": 46, "training_approved": False,
                                             "private_sha256": hashlib.sha256(blob).hexdigest()}))
        return load_replay(self.capture, self.manifest)

    def test_original_archive_mixed_markers_and_quarantined_m1(self):
        replay = self.archive_fixture()
        self.assertEqual(len(replay.samples), 46)
        self.assertEqual(replay.terminated, "aborted")
        self.assertEqual(sum(s.state == "quarantined" for s in replay.samples), 6)
        self.assertTrue(any("human_visual_observation" in s.annotation for s in replay.samples))
        self.assertTrue(any("five 8-packet" in w for w in replay.warnings))
        self.assertFalse(replay.training_approved)

    def test_original_archive_rejects_wrong_owner_and_phase(self):
        with self.assertRaisesRegex(CaptureError, "source-owner"):
            self.archive_fixture(swap_owner=True)
        with self.assertRaisesRegex(CaptureError, "manifest/phase"):
            self.archive_fixture(wrong_phase=True)


    # The pin + tee are sampled by the existing source-qualified reader. The
    # viewer must show them as individual static markers, never cache/ball paths.
    def test_candidate_pin_and_tee_decode_from_current_packet(self):
        try:
            from wii_ai_golf.inspector.gui import candidate_landmarks, PIN, TEE
        except ImportError:
            self.skipTest("Tkinter unavailable on this runner")
        e = event()
        e["candidate_words_private_be_u32_hex"][PIN] = [bits(6), bits(2), bits(-380)]
        e["candidate_words_private_be_u32_hex"][TEE] = [bits(2.2), bits(-5.5), bits(-318)]
        r = self.save([e])
        landmarks = candidate_landmarks(r.samples[0])
        self.assertEqual(set(landmarks), {PIN, TEE})
        self.assertAlmostEqual(landmarks[PIN][2], -380)
        self.assertAlmostEqual(landmarks[TEE][0], 2.2, places=5)
        self.assertFalse(r.training_approved)

    def test_missing_or_nonfinite_pin_never_fabricated(self):
        try:
            from wii_ai_golf.inspector.gui import candidate_landmarks, PIN, TEE
        except ImportError:
            self.skipTest("Tkinter unavailable on this runner")
        missing = self.save([event()])
        self.assertEqual(candidate_landmarks(missing.samples[0]), {})
        e = event()
        e["candidate_words_private_be_u32_hex"][PIN] = ["7FC00000", bits(1), bits(2)]
        e["candidate_words_private_be_u32_hex"][TEE] = [bits(2), bits(3), bits(4)]
        nonfinite = self.save([e])
        self.assertEqual(set(candidate_landmarks(nonfinite.samples[0])), {TEE})

    def test_pin_abstains_on_unqualified_or_missing_owner_identity(self):
        try:
            from wii_ai_golf.inspector.gui import candidate_landmarks, PIN
        except ImportError:
            self.skipTest("Tkinter unavailable on this runner")
        e = event()
        e["candidate_words_private_be_u32_hex"][PIN] = [bits(1), bits(2), bits(3)]
        e["source_layout_qualified"] = False
        self.assertEqual(candidate_landmarks(self.save([e]).samples[0]), {})
        e["source_layout_qualified"] = True
        e.pop("source_identity_digest_private")
        self.assertEqual(candidate_landmarks(self.save([e]).samples[0]), {})

    def test_pin_and_tee_render_distinct_stationary_tags_over_cache(self):
        try:
            from wii_ai_golf.inspector.gui import Inspector, PIN, TEE
        except ImportError:
            self.skipTest("Tkinter unavailable on this runner")
        class Var:
            def __init__(self, value=None): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
        class Canvas:
            def __init__(self): self.ops = []
            def delete(self, *args): self.ops = []
            def winfo_width(self): return 900
            def winfo_height(self): return 470
            def __getattr__(self, name):
                if name not in {"create_polygon", "create_text", "create_line", "create_oval"}:
                    raise AttributeError(name)
                def draw(*args, **kwargs): self.ops.append((name, kwargs.get("tags", ()), kwargs))
                return draw
        e = event()
        e["candidate_words_private_be_u32_hex"][PIN] = [bits(10), bits(20), bits(-350)]
        e["candidate_words_private_be_u32_hex"][TEE] = [bits(2.2), bits(-5.5), bits(-318)]
        replay = self.save([e])
        # A zero-Tk object with a canvas recorder tests geometry and layering
        # on Windows and Ubuntu without a window or Dolphin.
        view = object.__new__(Inspector)
        view.canvas = Canvas()
        view.index = Var(0)
        view.landmark_status = Var("")
        view.replay = replay
        view.yaw, view.pitch = 0.65, 0.48
        view.draw_path()
        tags = [tag for _, group, _ in view.canvas.ops for tag in group]
        self.assertIn("pin_candidate", tags)
        self.assertIn("tee_candidate", tags)
        self.assertTrue(view.landmark_status.get().startswith("Pin / flag: sampled"))
        self.assertEqual(view.canvas.ops[-2][1], ("pin_candidate",))
        self.assertTrue(any(op[0] == "create_polygon" and op[1] == ("pin_candidate",)
                            for op in view.canvas.ops))
        # Omit the pin and verify that the viewer refuses to leave a stale flag.
        missing = self.save([event()])
        view.replay = missing
        view.draw_path()
        tags = [tag for _, group, _ in view.canvas.ops for tag in group]
        self.assertNotIn("pin_candidate", tags)
        self.assertIn("not sampled", view.landmark_status.get())

    def test_no_controller_bridge_or_training_imports(self):
        for path in (ROOT / "src/wii_ai_golf/inspector/replay.py", ROOT / "src/wii_ai_golf/inspector/gui.py", ROOT / "scripts/p0_memory_inspector.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn('rpc.call("controller.', source)
            self.assertNotIn('rpc.call("memory.write', source)
            self.assertNotIn("FelkRPC", source)
            self.assertNotIn("--swing", source)


if __name__ == "__main__":
    unittest.main()
