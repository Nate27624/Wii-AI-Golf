"""Reject camera-responsive XYZ as labeled ball physics."""
import unittest
from wii_ai_golf.ball_identity_gate import classify_candidate,known_rejected_candidate

class IdentityGateTests(unittest.TestCase):
    def test_negative_camera_control_blocks_candidate(self):
        x=classify_candidate("0x925834D8",{
            "idle":{"samples_parsed":180,"moving_steps_below_reset":0},
            "aim_only":{"samples_parsed":240,"moving_steps_below_reset":96},
            "swing":{"samples_parsed":300,"moving_steps_below_reset":40}})
        self.assertEqual(x["decision"],"CAMERA_OR_AIM_SENSITIVE")
        self.assertFalse(x["training_eligible"])
    def test_missing_condition_never_accepted(self):
        x=classify_candidate("x",{"idle":{"samples_parsed":180,"moving_steps_below_reset":0}})
        self.assertEqual(x["decision"],"INSUFFICIENT_CONTROLS")
        self.assertFalse(x["training_eligible"])
    def test_no_motion_also_not_ball_proof(self):
        c={s:{"samples_parsed":10,"moving_steps_below_reset":0}
           for s in ("idle","aim_only","swing")}
        self.assertEqual(classify_candidate("x",c)["decision"],
                         "UNVERIFIED_REQUIRES_VISUAL_PHYSICS_IDENTITY")
    def test_known_negative_control(self):
        self.assertFalse(known_rejected_candidate()["training_eligible"])
if __name__=="__main__": unittest.main()
