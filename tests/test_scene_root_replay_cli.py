"""Single-CLI routing for pre-existing source-gated scene-root reports."""
from __future__ import annotations
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf import cli

RECORD_ID = "20261025T032225Z-720fcc31"


class SceneRootReplayCliTests(unittest.TestCase):
    def test_local_validation_does_not_launch_dolphin_or_publish(self):
        with patch.object(cli, "_run", return_value=0) as runner, \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["research", "publish-saved-scene-root",
                                       "--id", RECORD_ID, "--local-only"]), 0)
        command = runner.call_args.args[0]
        self.assertEqual(Path(command[1]).name, "research_cli.py")
        self.assertEqual(command[2:], ["publish-saved-scene-root", "--id",
                                       RECORD_ID, "--local-only"])
        self.assertNotIn("Dolphin", " ".join(command))
        self.assertIn("LOCAL VALIDATION ONLY", out.getvalue())

    def test_approved_publish_still_uses_existing_research_cli(self):
        with patch.object(cli, "_run", return_value=3) as runner, \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["research", "publish-saved-scene-root",
                                       "--id", RECORD_ID]), 3)
        self.assertEqual(runner.call_args.args[0][2:],
                         ["publish-saved-scene-root", "--id", RECORD_ID])
        self.assertIn("existing credentials", out.getvalue())


if __name__ == "__main__":
    unittest.main()
