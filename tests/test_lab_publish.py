"""Offline privacy and branch-isolation checks for GitHub status publishing."""
import base64
import json
import unittest
from wii_ai_golf.lab.publish import public_record, publish_record

RECORD = {
    "run_id": "20261025T011234123456Z-a1b2c3d4",
    "experiment_id": "integration.swing", "mode": "live",
    "execution_status": "finished", "exit_code": 0,
    "command": ["private", "game.rvz"], "offline_log": "C:/private",
    "raw_ram": "secret", "human_observation": {"name": "private"},
    "game_score": 5,
}


class PublisherTests(unittest.TestCase):
    def test_only_allowlisted_fields(self):
        public = public_record(RECORD)
        serialized = json.dumps(public)
        for sensitive in ("private", "raw_ram", "game_score", "game.rvz", "offline_log"):
            self.assertNotIn(sensitive, serialized)
        self.assertEqual(public["claim"], "PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE")

    def test_reject_untrusted_identifiers(self):
        for key, value in (("run_id", "../private"), ("experiment_id", "private/secret"),
                           ("mode", "unknown"), ("execution_status", "running")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                public_record({**RECORD, key: value})

    def test_publish_only_to_results_branch(self):
        calls = []
        def api(method, path, token, payload=None):
            calls.append((method, path, payload))
            if method == "GET":
                return {"object": {"sha": "abc"}}
            return {}
        outcome = publish_record(RECORD, token="fake-token", api=api)
        self.assertEqual(outcome["status"], "published")
        self.assertEqual(len(calls), 2)
        put = calls[-1][2]
        self.assertEqual(put["branch"], "research-results")
        body = base64.b64decode(put["content"]).decode("utf-8")
        self.assertNotIn("game.rvz", body)
        self.assertEqual(json.loads(body)["experiment_id"], "integration.swing")

    def test_no_token_does_not_upload(self):
        self.assertEqual(publish_record(RECORD, token="")["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
