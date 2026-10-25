"""Token-free export regressions: privacy, integrity, idempotence, and CLI routing."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf import cli
from wii_ai_golf.lab import export

RID = "20261025T011234123456Z-a1b2c3d4"


def private_record(rid=RID, status="finished"):
    return {
        "run_id": rid, "experiment_id": "core.tests", "mode": "offline",
        "execution_status": status, "exit_code": 0,
        "offline_log": "C:/Users/private/secret.log",
        "command": ["secret-executable", "game.rvz"],
        "raw_ram": {"contents": "secret"},
        "human_observation": {"contact": "yes", "person": "PRIVATE"},
        "game_score": 72,
    }


class TokenFreeExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "Wii-AI-Golf-Data" / "lab"
        (self.data / "runs").mkdir(parents=True)

    def record(self, row, *, filename=None):
        rid = filename or row["run_id"]
        (self.data / "runs" / (rid + ".json")).write_text(
            json.dumps(row), encoding="utf-8"
        )

    def test_allowlist_only_and_disk_bundle_verified_without_token(self):
        self.record(private_record())
        with patch.dict("os.environ", {
            "WII_GOLF_AUTO_PUBLISH": "1",
            "WII_GOLF_GITHUB_TOKEN": "should-never-use",
        }), patch("urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")):
            path, bundle, skipped = export.create_export(self.data)
        self.assertEqual(skipped, 0)
        self.assertEqual(bundle["record_count"], 1)
        self.assertEqual(export.verify_export_file(path), bundle)
        serialized = path.read_text(encoding="utf-8")
        for forbidden in ("private", "game.rvz", "raw_ram", "offline_log",
                          "game_score", "secret", "human_observation",
                          "WII_GOLF_GITHUB_TOKEN"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(bundle["records"][0]["claim"],
                         "PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE")

    def test_exact_repeat_is_idempotent_and_tampering_rejected(self):
        self.record(private_record())
        first_path, first, _ = export.create_export(self.data)
        second_path, second, _ = export.create_export(self.data)
        self.assertEqual(first_path, second_path)
        self.assertEqual(first, second)
        corrupted = {**second, "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "checksum"):
            export.verify_bundle(corrupted)
        with self.assertRaises(ValueError):
            export.verify_bundle({**second, "private_path": "C:/Users/hidden"})

    def test_conflicting_existing_bundle_fails_closed(self):
        self.record(private_record())
        path, _, _ = export.create_export(self.data)
        path.write_text('{"tampered":"secret"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            export.create_export(self.data)

    def test_nonfinal_and_mismatched_records_are_excluded(self):
        self.record(private_record(status="running"))
        self.record(private_record("20261025T011235123456Z-a1b2c3d4"),
                    filename="20261025T011236123456Z-a1b2c3d4")
        with self.assertRaisesRegex(ValueError, "No finalized valid Lab runs"):
            export.create_export(self.data)
        self.record(private_record("20261025T011237123456Z-a1b2c3d4"))
        _, bundle, skipped = export.create_export(self.data)
        self.assertEqual(bundle["record_count"], 1)
        self.assertEqual(skipped, 2)

    def test_duplicate_ids_and_extra_fields_rejected(self):
        safe = export.build_bundle([{
            "run_id": RID, "experiment_id": "core.tests", "mode": "offline",
            "execution_status": "finished", "exit_code": 0,
            "schema_version": 1, "claim": "PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE",
        }])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            export.build_bundle([safe["records"][0], safe["records"][0]])
        with self.assertRaisesRegex(ValueError, "non-allowlisted"):
            export.build_bundle([{**safe["records"][0], "filename": "private"}])

    def test_cli_export_and_verify_latest(self):
        self.record(private_record())
        fake_root = self.data.parent
        with patch.object(cli, "DATA_ROOT", fake_root), redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(cli.main(["lab", "export", "--json"]), 0)
        emitted = json.loads(stdout.getvalue())
        self.assertEqual(emitted["record_count"], 1)
        self.assertNotIn("C:/Users/", stdout.getvalue())
        with patch.object(cli, "DATA_ROOT", fake_root), redirect_stdout(io.StringIO()) as check:
            self.assertEqual(cli.main(["lab", "verify-export"]), 0)
        self.assertIn("VALID status bundle", check.getvalue())

    def test_research_test_reuses_existing_git_publisher_without_dolphin(self):
        with patch.object(cli, "_run", return_value=0) as runner:
            with redirect_stdout(io.StringIO()) as display:
                self.assertEqual(cli.main(["research", "test",
                                           "--pattern", "test_lab_export.py"]), 0)
        command = runner.call_args.args[0]
        self.assertEqual(Path(command[1]).name, "research_cli.py")
        self.assertEqual(command[2:], ["test", "--pattern", "test_lab_export.py"])
        self.assertNotIn("Dolphin", " ".join(command))
        self.assertIn("Git", display.getvalue())

    def test_research_test_local_only_forwards_no_upload(self):
        with patch.object(cli, "_run", return_value=0) as runner:
            with redirect_stdout(io.StringIO()) as display:
                self.assertEqual(cli.main(["research", "test", "--local-only"]), 0)
        self.assertEqual(runner.call_args.args[0][-1], "--no-upload")
        self.assertIn("LOCAL ONLY", display.getvalue())

    def test_research_study_delegates_existing_read_only_plan(self):
        with patch.object(cli, "_run", return_value=0) as runner:
            self.assertEqual(cli.main(["research", "study"]), 0)
        command = runner.call_args.args[0]
        self.assertEqual(Path(command[1]).name, "research_cli.py")
        self.assertEqual(command[2:], ["study"])

    def test_empty_directory_cannot_claim_success(self):
        with self.assertRaisesRegex(ValueError, "No finalized valid"):
            export.create_export(self.data)
        with self.assertRaisesRegex(ValueError, "No local export"):
            export.latest_export(self.data)


if __name__ == "__main__":
    unittest.main()
