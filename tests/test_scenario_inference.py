"""Reference positions from the user's real 417-sample upload; synthetic replays."""
import unittest

from wii_ai_golf.scenario_inference import TEE_XYZ, PIN_XYZ, infer_scene, StableSceneTracker


def snap(tee=0, pin=0, *, cup=True, mode="GAMEMODE_TR_NEARPIN"):
    data = {"game_id": "RSPE01", "disc_revision": 1, "mode": mode, "objects": {
        "current_start_obj_ptr": {"translation_xyz_unverified": list(TEE_XYZ[tee])},
        "current_pin_obj_ptr": {"translation_xyz_unverified": list(PIN_XYZ[pin])},
        "cup_obj_ptr": {"translation_xyz_unverified": [
            PIN_XYZ[pin][0], PIN_XYZ[pin][1] - 0.04, PIN_XYZ[pin][2]]}}}
    if not cup:
        data["objects"]["cup_obj_ptr"]["translation_xyz_unverified"] = [0, 0, 0]
    return data


class InferenceTests(unittest.TestCase):
    def test_all_ten_observed_starts_and_pin_variants(self):
        for i in range(10):
            for p in range(3):
                result = infer_scene(snap(i, p))
                self.assertEqual(result["tee_index_observed"], i + 1)
                self.assertEqual(result["pin_variant_observed"], p + 1)
                self.assertEqual(result["scene_status"], "aligned_candidate")

    def test_stale_cup_rejected(self):
        sample = snap(1, 1)
        sample["objects"]["cup_obj_ptr"]["translation_xyz_unverified"] = list(PIN_XYZ[0])
        self.assertEqual(infer_scene(sample)["scene_status"], "transitional_or_unknown")

    def test_bad_positions_and_unsupported(self):
        self.assertEqual(infer_scene(snap(mode="other"))["scene_status"], "unsupported_or_inactive")
        sample = snap()
        sample["objects"]["current_start_obj_ptr"]["translation_xyz_unverified"] = [99, 99, 99]
        self.assertIsNone(infer_scene(sample)["tee_index_observed"])
        sample = snap()
        sample["objects"]["current_pin_obj_ptr"]["translation_xyz_unverified"] = None
        self.assertFalse(infer_scene(sample)["pin_cup_aligned"])

    def test_three_sample_confirmation_and_transitions(self):
        tracker = StableSceneTracker(required_samples=3)
        self.assertFalse(tracker.feed(snap())["stable"])
        self.assertFalse(tracker.feed(snap())["stable"])
        self.assertTrue(tracker.feed(snap())["new_configuration"])
        self.assertFalse(tracker.feed(snap())["new_configuration"])
        self.assertFalse(tracker.feed(snap(1, 1, cup=False))["stable"])
        self.assertFalse(tracker.feed(snap(1, 1))["stable"])
        self.assertFalse(tracker.feed(snap(1, 1))["stable"])
        self.assertTrue(tracker.feed(snap(1, 1))["new_configuration"])

    def test_gated_region_and_arguments(self):
        sample = snap()
        sample["disc_revision"] = 0
        self.assertEqual(infer_scene(sample)["scene_status"], "unsupported_or_inactive")
        with self.assertRaises(ValueError):
            StableSceneTracker(1)
        with self.assertRaises(ValueError):
            infer_scene(snap(), match_tolerance=float("nan"))


if __name__ == "__main__":
    unittest.main()
