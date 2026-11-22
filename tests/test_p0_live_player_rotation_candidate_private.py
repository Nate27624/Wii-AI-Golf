"""Offline tests for direct source-record rotation candidate, not native yaw."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
P = ROOT / "scripts" / "p0_live_player_rotation_candidate_private.py"
spec = importlib.util.spec_from_file_location("rot_probe", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def bits(x):
    return int.from_bytes(struct.pack(">f", x), "big")


def words(a):
    return [bits(v) for v in (a, math.sin(a), math.cos(a),
                               -math.cos(a), math.sin(a))]


def row(phase, theta):
    r = m.decode_rotation(words(math.radians(theta)))
    return {"phase": phase, "record": r,
            "tee_pin_xz_bearing_candidate_degrees": 45.0}


def fixture():
    return [row("B0", 10), row("IDLE", 10.01),
            row("LEFT", 20), row("RIGHT", 0),
            row("RETURN", 10.5)]


class FakeRPC:
    def __init__(self, record, ball, theta, *, mutating=False,
                 bad_matrix=False, frame=20):
        self.record = record
        self.ball = ball
        self.frame = frame
        self.mutating = mutating
        self.bad_matrix = bad_matrix
        self.calls = []
        a = math.radians(theta)
        ws = words(a)
        if bad_matrix:
            ws[1] = bits(0.1)
        self.rotation = b"".join(w.to_bytes(4, "big") for w in ws).hex()
        self.quats = b"".join(bits(v).to_bytes(4, "big") for v in
                              ([0.0, 0.0, 0.0, 1.0] * 2)).hex()
        self.angle_word = ws[0]

    def call(self, method, args):
        self.calls.append((method, tuple(args)))
        if method == "memory.read_bytes":
            addr, size = args
            if (addr, size) == (self.ball + 0x30, 12):
                return "00" * 12
            if (addr, size) == (self.record + 0x3C, 20):
                return self.rotation
            if (addr, size) == (self.record + 0xA0, 32):
                return self.quats
        if method == "memory.read_u32" and args == [self.record + 0x3C]:
            return (self.angle_word + (1 if self.mutating else 0)) & 0xFFFFFFFF
        if method == "frame.get_count":
            return self.frame
        raise AssertionError("Unexpected RPC method or address: " + repr((method, args)))


def snapshot(rec, ball, theta, *, angle_override=None):
    ident = (0x80000100, 0x90000100, 0x90000200, 0x90000300,
             0x90000400, 0, rec, ball, 0x90002000,
             0x90003000, 0x90003100, 0x90004000, 0x90004100, 1)
    return {"identity": ident,
            "values": {
                "aim_candidate_plus_0x3c":
                    (bits(math.radians(theta)) if angle_override is None
                     else angle_override,),
                "tee_start_candidate": tuple(bits(v) for v in (0, 0, 0)),
                "pin_candidate": tuple(bits(v) for v in (5, 0, 5)),
            },
            "frame_bracket": (10, 11)}


class TestRotationSource(unittest.TestCase):
    def test_scalar_and_matrix_agree_without_baseline(self):
        r = m.decode_rotation(words(math.radians(120)))
        self.assertTrue(r["sincos_matrix_consistent"])
        self.assertAlmostEqual(r["candidate_record_angle_degrees"], 120,
                               places=3)
        self.assertAlmostEqual(
            r["candidate_rotation_matrix_angle_degrees"], 30, places=3)
        self.assertFalse(r["world_frame_verified"])

    def test_wrapped_matrix(self):
        r = m.decode_rotation(words(math.radians(179)))
        self.assertTrue(r["sincos_matrix_consistent"])
        self.assertAlmostEqual(r["candidate_rotation_matrix_angle_degrees"],
                               89, places=2)

    def test_quarter_turn_relation(self):
        r = m.decode_rotation(words(math.pi/2))
        self.assertTrue(r["sincos_matrix_consistent"])
        self.assertAlmostEqual(r["candidate_rotation_matrix_angle_degrees"],
                               0, places=3)

    def test_corrupted_matrix_not_promoted(self):
        w = words(0.7)
        w[2] = bits(0.0)
        self.assertFalse(m.decode_rotation(w)["sincos_matrix_consistent"])

    def test_nonunit_matrix_not_promoted(self):
        w = words(0.7)
        for i in range(1, 5):
            w[i] = bits(0.5 * m.f32(w[i]))
        self.assertFalse(m.decode_rotation(w)["sincos_matrix_consistent"])

    def test_nan_rejected(self):
        w = words(0.2)
        w[0] = 0x7FC00000
        with self.assertRaises(m.Abstain):
            m.decode_rotation(w)

    def test_boolean_not_int(self):
        with self.assertRaises(m.Abstain):
            m.decode_rotation([True]*5)

    def test_bad_word_count(self):
        with self.assertRaises(m.Abstain):
            m.decode_rotation(words(0.1)[:4])

    def test_bearing_xz_candidate(self):
        tee = [bits(v) for v in (0, 1, 0)]
        pin = [bits(v) for v in (3, 1, 3)]
        self.assertEqual(m.hypothetical_bearing(tee, pin), 45.0)

    def test_zero_bearing_unknown(self):
        tee = [bits(v) for v in (0, 1, 0)]
        self.assertIsNone(m.hypothetical_bearing(tee, tee))

    def test_directional_control_positive(self):
        s = m.assess(fixture())
        self.assertEqual(s["status"],
                         "SOURCE_SELECTED_PLAYER_ROTATION_CANDIDATE_SUPPORTED")
        self.assertTrue(all(s["checks"].values()))
        self.assertFalse(s["actual_player_world_yaw_verified"])
        self.assertFalse(s["training_approved"])

    def test_idle_drift_does_not_pass(self):
        e = fixture()
        e[1] = row("IDLE", 25)
        self.assertFalse(m.assess(e)["checks"]["idle_angle_stable_within_0_2deg"])

    def test_left_wrong_sign_does_not_pass(self):
        e = fixture()
        e[2] = row("LEFT", 1)
        self.assertFalse(m.assess(e)["checks"]["left_angle_increased_vs_baseline"])

    def test_right_wrong_sign_does_not_pass(self):
        e = fixture()
        e[3] = row("RIGHT", 30)
        self.assertFalse(m.assess(e)["checks"]["right_angle_decreased_vs_baseline"])

    def test_matrix_inconsistent_not_supported(self):
        e = fixture()
        e[0]["record"]["sincos_matrix_consistent"] = False
        self.assertFalse(m.assess(e)["checks"]["source_numeric_matrix_consistent_each_phase"])

    def test_missing_phase_abstains(self):
        with self.assertRaises(m.Abstain):
            m.assess(fixture()[:-1])

    def test_wrong_order_abstains(self):
        e = fixture()
        e[0], e[1] = e[1], e[0]
        with self.assertRaises(m.Abstain):
            m.assess(e)

    def test_read_is_source_bracketed_and_read_only(self):
        rec, ball = 0x90001000, 0x90005000
        rpc = FakeRPC(rec, ball, 37.5)
        with patch.object(m.source, "take_snapshot",
                          return_value=snapshot(rec, ball, 37.5)), \
             patch.object(m.epoch, "end_epoch_matches", return_value=True):
            v = m.sample(rpc)
        self.assertTrue(v["record"]["sincos_matrix_consistent"])
        self.assertEqual(v["source_frame_bracket_NOT_PHYSICS"], [10, 20])
        self.assertEqual(v["tee_pin_xz_bearing_candidate_degrees"], 45.0)
        self.assertTrue(all(method.startswith("memory.read") or
                            method == "frame.get_count"
                            for method, _ in rpc.calls))

    def test_changed_scalar_inside_read_abstains(self):
        rec, ball = 0x90001000, 0x90005000
        rpc = FakeRPC(rec, ball, 37.5, mutating=True)
        with patch.object(m.source, "take_snapshot",
                          return_value=snapshot(rec, ball, 37.5)), \
             patch.object(m.epoch, "end_epoch_matches", return_value=True):
            with self.assertRaises(m.Abstain):
                m.sample(rpc)

    def test_mismatched_source_identity_abstains(self):
        rec, ball = 0x90001000, 0x90005000
        rpc = FakeRPC(rec, ball, 37.5)
        with patch.object(m.source, "take_snapshot",
                          return_value=snapshot(rec, ball, 37.5)):
            with self.assertRaises(m.Abstain):
                m.sample(rpc, expected_identity=tuple(range(14)))

    def test_moving_ball_abstains(self):
        rec, ball = 0x90001000, 0x90005000
        rpc = FakeRPC(rec, ball, 37.5)
        with patch.object(m.source, "take_snapshot",
                          return_value=snapshot(rec, ball, 37.5)):
            with self.assertRaises(m.Abstain):
                m.sample(rpc, expected_ball="11"*12)

    def test_bad_nonatomic_frame_abstains(self):
        rec, ball = 0x90001000, 0x90005000
        rpc = FakeRPC(rec, ball, 37.5, frame=10)
        with patch.object(m.source, "take_snapshot",
                          return_value=snapshot(rec, ball, 37.5)), \
             patch.object(m.epoch, "end_epoch_matches", return_value=True):
            with self.assertRaises(m.Abstain):
                m.sample(rpc)

    def test_private_root_must_be_outside_repo(self):
        with self.assertRaises(m.Abstain):
            m.private_folder(ROOT)

    def test_private_sync_root_rejected(self):
        with tempfile.TemporaryDirectory(prefix="OneDrive-") as d:
            with self.assertRaises(m.Abstain):
                m.private_folder(Path(d))

    def test_private_missing_root_rejected(self):
        with self.assertRaises(m.Abstain):
            m.private_folder(Path("/does-not-exist-rot-probe"))


if __name__ == "__main__":
    unittest.main()
