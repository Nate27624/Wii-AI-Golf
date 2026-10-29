import unittest
from wii_ai_golf.lab.observation_schema import observation_v1


class ObservationSchemaTests(unittest.TestCase):
    def setUp(self):
        self.sample = {
            "human_observation": {
                "contact_human": "yes", "finished_on_green_human": "no",
                "displayed_distance_human": "8.75", "displayed_unit_human": "ft",
                "personal_notes": "private",
            },
            "known_good_swing_request": {
                "trace_sha256": "a" * 64, "a_button_only_prime_requests": 0,
            },
            "ram_dumps": {"raw": "private"},
            "local_path": "C:/secret/rom.rvz",
        }

    def test_strips_unknown_sensitive_fields(self):
        value = observation_v1(self.sample)
        self.assertEqual(value["distance_human"], 8.75)
        self.assertFalse(value["verified_game_score"])
        self.assertEqual(value["contact_human"], "yes")
        self.assertEqual(value["record_type"], "human_observation")
        self.assertNotIn("ram_dumps", str(value))
        self.assertNotIn("private", str(value))
        self.assertNotIn("secret", str(value))

    def test_rejects_unverified_trace_or_bad_labels(self):
        bad = dict(self.sample)
        bad["known_good_swing_request"] = {"trace_sha256": "fake"}
        with self.assertRaises(ValueError):
            observation_v1(bad)
        bad = dict(self.sample)
        bad["human_observation"] = {"contact_human": "yes;TOKEN"}
        with self.assertRaises(ValueError):
            observation_v1(bad)

    def test_no_false_numeric_claim(self):
        bad = dict(self.sample)
        bad["human_observation"] = {"displayed_distance_human": "nan",
                                    "displayed_unit_human": "ft"}
        with self.assertRaises(ValueError):
            observation_v1(bad)


if __name__ == "__main__":
    unittest.main()
